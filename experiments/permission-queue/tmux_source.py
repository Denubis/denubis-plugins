"""Read native tmux identity, colour and screen evidence for the attention viewer."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class SourceError(RuntimeError):
    """The source or the invoking viewer cannot be identified safely."""


@dataclass(frozen=True)
class PaneSnapshot:
    session_id: str
    session_name: str
    window_id: str
    window_index: int
    window_name: str
    pane_id: str
    pane_index: int
    pane_pid: int
    title: str
    cwd: str
    pane_current_command: str
    pane_bg: str
    pane_fg: str
    header_spans: list[dict]
    state: str
    idle_since: float | None
    status_detail: str
    preview_ansi: str
    foreground_pid: int | None = None
    foreground_start_ticks: int | None = None


FIELDS = (
    "session_id",
    "session_name",
    "window_id",
    "window_index",
    "window_name",
    "pane_id",
    "pane_index",
    "pane_pid",
    "pane_title",
    "pane_current_path",
    "pane_current_command",
    "pane_bg",
    "pane_fg",
    "pane_height",
)
CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
STYLE = re.compile(r"(?<!#)#\[([^\]]*)\]")
PASTE_LIMIT = 64 * 1024
KEYS = {
    "enter": "Enter",
    "escape": "Escape",
    "tab": "Tab",
    "shift+tab": "BTab",
    "backspace": "BSpace",
    "delete": "DC",
    "insert": "IC",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "home": "Home",
    "end": "End",
    "pageup": "PPage",
    "pagedown": "NPage",
}


def foreground_identity(pane_pid: int) -> tuple[int | None, int | None]:
    """Read Linux tty foreground group identity, without changing the process."""
    try:
        pane = Path(f"/proc/{pane_pid}/stat").read_text().rsplit(")", 1)[1].split()
        foreground_pid = int(pane[5])
        if foreground_pid <= 0:
            return None, None
        foreground = Path(f"/proc/{foreground_pid}/stat").read_text()
        ticks = int(foreground.rsplit(")", 1)[1].split()[19])
        return foreground_pid, ticks
    except OSError, IndexError, ValueError:
        # Viewing remains available when foreground identity cannot be verified.
        return None, None


@lru_cache(maxsize=1)
def classifier():
    path = (
        Path(__file__).resolve().parents[2]
        / "plugins"
        / "denubis-external-agents"
        / "scripts"
        / "codex_supervisor.py"
    )
    spec = importlib.util.spec_from_file_location("permission_source_classifier", path)
    if spec is None or spec.loader is None:
        raise SourceError("the existing Codex classifier could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def header_spans(strip: str) -> list[dict]:
    result = []
    controls = list(STYLE.finditer(strip))
    for index, control in enumerate(controls):
        attributes = control[1].split(",")
        colours = dict(item.split("=", 1) for item in attributes if "=" in item)
        if not all(
            re.fullmatch(r"#[0-9a-fA-F]{6}", colours.get(key, ""))
            for key in ("fg", "bg")
        ):
            continue
        end = controls[index + 1].start() if index + 1 < len(controls) else len(strip)
        result.append(
            {
                "text": strip[control.end() : end].replace("##", "#"),
                "fg": colours["fg"],
                "bg": colours["bg"],
                "bold": "bold" in attributes,
            }
        )
    return result


class TmuxSource:
    def __init__(self, session: str = "main", socket: str | Path | None = None):
        self.session = session
        self.prefix = ["tmux"] + (["-S", str(socket)] if socket is not None else [])
        self._idle: dict[str, tuple[tuple, float]] = {}

    def command(self, *arguments: str, input_text: str | None = None) -> str:
        try:
            result = subprocess.run(
                [*self.prefix, *arguments],
                capture_output=True,
                text=True,
                input=input_text,
                timeout=5,
                check=False,
            )
        except OSError as error:
            raise SourceError(str(error)) from error
        except subprocess.TimeoutExpired as error:
            raise SourceError("tmux did not respond within five seconds") from error
        if result.returncode:
            raise SourceError(result.stderr.strip() or "tmux command failed")
        return result.stdout

    def cached_header(self, cwd: str, title: str) -> list[dict]:
        try:
            configured = self.command(
                "show-environment", "-g", "XDG_RUNTIME_DIR"
            ).strip()
        except SourceError:
            configured = ""
        # This is the installed helper's existing read-only cache location.
        directory = configured.removeprefix("XDG_RUNTIME_DIR=") or "/tmp"  # noqa: S108
        key = hashlib.md5(
            (cwd + "\n" + title).encode(), usedforsecurity=False
        ).hexdigest()
        cache = Path(directory) / f"branch-bg-{os.getuid()}" / key
        try:
            strip = cache.read_text().splitlines()[0]
        except OSError:
            return []
        except IndexError:
            return []
        return header_spans(strip)

    def observe(self, data: dict, preview: str) -> tuple[str, float | None, str]:
        lead = data["pane_title"].split(" | ", 1)[0].strip().casefold()
        known = lead in {
            "ready",
            "working",
            "waiting",
            "action required",
        } or re.fullmatch(r"\[\s*!\s*\]\s*action required", lead)
        observation = None
        state = "unknown"
        if data["pane_current_command"] == "codex" and known:
            policy = classifier()
            observation = policy.classify_snapshot(lead, CSI.sub("", preview))
            if observation.kind is policy.ObservationKind.APPROVAL or lead.endswith(
                "action required"
            ):
                state = "blocked"
            elif lead == "ready" and observation.kind in {
                policy.ObservationKind.DONE,
                policy.ObservationKind.QUESTION,
            }:
                state = "idle"
            elif lead in {"working", "waiting"}:
                state = "running"
        pane_id = data["pane_id"]
        if state != "idle":
            self._idle.pop(pane_id, None)
            return (
                state,
                None,
                {
                    "blocked": "Native action-required or pending-approval evidence",
                    "running": "Native running state observed",
                    "unknown": "Provider state unknown; silence is not idle evidence",
                }[state],
            )
        identity = (
            data["session_id"],
            data["window_id"],
            data["pane_pid"],
            data["pane_current_command"],
            observation.key,
        )
        moment = time.monotonic()
        previous = self._idle.get(pane_id)
        since = (
            previous[1] if previous is not None and previous[0] == identity else moment
        )
        self._idle[pane_id] = (identity, since)
        return (
            state,
            since,
            f"Ready first observed {int(max(0, moment - since))}s ago; "
            "actual idle start unknown",
        )

    def snapshots(self) -> list[PaneSnapshot]:
        rows = self.command(
            "list-panes",
            "-s",
            "-t",
            f"={self.session}",
            "-F",
            "\t".join("#{" + field + "}" for field in FIELDS),
        )
        result = []
        for row in rows.splitlines():
            values = row.split("\t")
            if len(values) != len(FIELDS):
                raise SourceError("tmux returned an incomplete source identity")
            data = dict(zip(FIELDS, values, strict=True))
            height = int(data["pane_height"])
            preview = self.command(
                "capture-pane",
                "-p",
                "-e",
                "-N",
                "-t",
                data["pane_id"],
                "-S",
                "0",
                "-E",
                str(height - 1),
            )
            spans = self.cached_header(data["pane_current_path"], data["pane_title"])
            state, idle_since, detail = self.observe(data, preview)
            foreground_pid, foreground_ticks = foreground_identity(
                int(data["pane_pid"])
            )
            if not spans:
                detail += "; cached header unavailable"
            result.append(
                PaneSnapshot(
                    session_id=data["session_id"],
                    session_name=data["session_name"],
                    window_id=data["window_id"],
                    window_index=int(data["window_index"]),
                    window_name=data["window_name"],
                    pane_id=data["pane_id"],
                    pane_index=int(data["pane_index"]),
                    pane_pid=int(data["pane_pid"]),
                    title=data["pane_title"],
                    cwd=data["pane_current_path"],
                    pane_current_command=data["pane_current_command"],
                    pane_bg=data["pane_bg"],
                    pane_fg=data["pane_fg"],
                    header_spans=spans,
                    state=state,
                    idle_since=idle_since,
                    status_detail=detail,
                    preview_ansi=preview,
                    foreground_pid=foreground_pid,
                    foreground_start_ticks=foreground_ticks,
                )
            )
        present = {snapshot.pane_id for snapshot in result}
        self._idle = {
            pane: value for pane, value in self._idle.items() if pane in present
        }
        return result

    def capture(self, snapshot: PaneSnapshot) -> str:
        height = self.validate(snapshot)
        captured = self.command(
            "capture-pane",
            "-p",
            "-e",
            "-N",
            "-t",
            snapshot.pane_id,
            "-S",
            "-200",
            "-E",
            str(height - 1),
        )
        self.validate(snapshot)
        return captured

    def validate(self, snapshot: PaneSnapshot) -> int:
        target = f"{snapshot.session_id}:{snapshot.window_id}.{snapshot.pane_id}"
        identity = (
            self.command(
                "display-message",
                "-p",
                "-t",
                target,
                "#{session_id}\t#{window_id}\t#{pane_id}\t#{pane_pid}\t#{pane_height}",
            )
            .strip()
            .split("\t")
        )
        expected = [
            snapshot.session_id,
            snapshot.window_id,
            snapshot.pane_id,
            str(snapshot.pane_pid),
        ]
        if len(identity) != 5 or identity[:4] != expected:
            raise SourceError(
                "source pane, window, session or process changed; refresh first"
            )
        return int(identity[4])

    def open_source(self, snapshot: PaneSnapshot) -> None:
        self.validate(snapshot)
        caller = os.environ.get("TMUX_PANE")
        if caller is None or re.fullmatch(r"%\d+", caller) is None:
            raise SourceError("the invoking viewer's tmux pane is unknown")
        board_session, board_name = (
            self.command(
                "display-message", "-p", "-t", caller, "#{session_id}\t#{session_name}"
            )
            .strip()
            .split("\t")
        )
        clients = self.command(
            "list-clients", "-t", board_session, "-F", "#{client_name}"
        ).splitlines()
        if len(clients) != 1:
            raise SourceError("Open source requires one attached viewer client")
        client = clients[0]
        source_clients = self.command(
            "list-clients", "-t", snapshot.session_id, "-F", "#{client_name}"
        ).splitlines()
        if any(other != client for other in source_clients):
            raise SourceError(
                "another client is attached to the source session; "
                "its window would move"
            )
        target = f"{snapshot.session_id}:{snapshot.window_id}.{snapshot.pane_id}"
        expected_count = "1" if board_session == snapshot.session_id else "0"
        viewer_here = (
            "#{L:#{?#{==:#{client_name},"
            + client
            + "},#{==:#{client_session},"
            + board_name
            + "},}}"
        )
        board_clients = "#{L:#{?#{==:#{client_session}," + board_name + "},1,}}"
        guard = (
            "#{&&:#{==:#{session_attached}," + expected_count + "},"
            "#{&&:#{==:#{pane_pid}," + str(snapshot.pane_pid) + "},"
            "#{&&:#{==:" + board_clients + ",1}," + viewer_here + "}}}"
        )
        refusal = "source or viewer changed; navigation refused"
        result = self.command(
            "if-shell",
            "-F",
            "-t",
            target,
            guard,
            shlex.join(["switch-client", "-c", client, "-t", target]),
            shlex.join(["display-message", "-p", refusal]),
        )
        if result.strip():
            raise SourceError(result.strip())

    def input_guard(self, snapshot: PaneSnapshot) -> tuple[str, str]:
        """Verify original foreground identity, then guard native tmux routing."""
        self.validate(snapshot)
        expected = (snapshot.foreground_pid, snapshot.foreground_start_ticks)
        if None in expected or foreground_identity(snapshot.pane_pid) != expected:
            raise SourceError(
                "source foreground process changed or is unknown; refresh first"
            )
        if re.fullmatch(r"[A-Za-z0-9_.+-]+", snapshot.pane_current_command) is None:
            raise SourceError("source command cannot be verified for input")
        target = f"{snapshot.session_id}:{snapshot.window_id}.{snapshot.pane_id}"
        current = (
            self.command(
                "display-message",
                "-p",
                "-t",
                target,
                "#{pane_current_command}\t#{pane_synchronized}",
            )
            .strip()
            .split("\t")
        )
        if not current or current[0] != snapshot.pane_current_command:
            raise SourceError("source process changed; refresh first")
        if len(current) != 2 or current[1] != "0":
            raise SourceError(
                "input refused while synchronize-panes is enabled or unknown"
            )
        comparisons = [
            ("session_id", snapshot.session_id),
            ("window_id", snapshot.window_id),
            ("pane_id", snapshot.pane_id),
            ("pane_pid", str(snapshot.pane_pid)),
            ("pane_current_command", snapshot.pane_current_command),
            ("pane_synchronized", "0"),
        ]
        guard = "1"
        for field, value in comparisons:
            guard = "#{&&:#{==:#{" + field + "}," + value + "}," + guard + "}"
        return target, guard

    def guarded_input(self, snapshot: PaneSnapshot, arguments: list[str]) -> None:
        target, guard = self.input_guard(snapshot)
        refusal = "source process changed or synchronize-panes enabled; input refused"
        result = self.command(
            "if-shell",
            "-F",
            "-t",
            target,
            guard,
            shlex.join(arguments),
            shlex.join(["display-message", "-p", refusal]),
        )
        if result.strip():
            raise SourceError(result.strip())

    def send_key(
        self, snapshot: PaneSnapshot, key: str, character: str | None = None
    ) -> None:
        """Route one human key event to its original, still-current source."""
        name = key.casefold()
        mapped = KEYS.get(name)
        if mapped is None and re.fullmatch(r"ctrl\+[a-z@\[\\\]\^_]", name):
            mapped = "C-" + name.removeprefix("ctrl+")
        if mapped is None and name == "ctrl+space":
            mapped = "C-Space"
        if mapped is None and name.startswith("ctrl+"):
            special = KEYS.get(name.removeprefix("ctrl+"))
            if special is not None:
                mapped = "C-" + special
        if mapped is None and re.fullmatch(r"f(?:[1-9]|1[0-2])", name):
            mapped = name.upper()
        arguments = ["send-keys", "-t", snapshot.pane_id]
        if mapped is not None:
            arguments.append(mapped)
        elif character is not None and len(character) == 1 and character.isprintable():
            arguments.extend(["-l", "--", character])
        else:
            raise SourceError(f"unsupported terminal key: {key}")
        self.guarded_input(snapshot, arguments)

    def send_text(self, snapshot: PaneSnapshot, text: str) -> None:
        """Paste exact UTF-8 text; native tmux adds brackets when requested."""
        if len(text.encode("utf-8")) > PASTE_LIMIT:
            raise SourceError("paste exceeds the experiment's 64 KiB UTF-8 limit")
        if not text:
            return
        self.input_guard(snapshot)
        name = "permission-input-" + uuid.uuid4().hex
        self.command("load-buffer", "-b", name, "-", input_text=text)
        try:
            self.guarded_input(
                snapshot,
                ["paste-buffer", "-p", "-r", "-S", "-b", name, "-t", snapshot.pane_id],
            )
        finally:
            self.command("delete-buffer", "-b", name)
