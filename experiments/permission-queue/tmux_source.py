"""Read native tmux identity, colour and screen evidence for the attention viewer."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import shlex
import subprocess
import sys
import uuid
from dataclasses import dataclass, replace
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
    socket_path: str = ""
    server_pid: int | None = None
    server_start_ticks: int | None = None
    pane_start_ticks: int | None = None
    state_since: float | None = None
    state_since_source: str = ""
    state_approximate: bool = False
    thread_id: str = ""
    approvals: tuple = ()
    native_pane: PaneSnapshot | None = None
    thread_data: object | None = None


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


def process_start_ticks(pid: int) -> int | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return int(fields[19])
    except OSError, IndexError, ValueError:
        return None


@lru_cache(maxsize=2)
def sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        "permission_queue_" + name, Path(__file__).with_name(name + ".py")
    )
    if spec is None or spec.loader is None:
        raise SourceError(f"{name} adapter unavailable")
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
    def __init__(
        self, session: str = "main", socket: str | Path | None = None, *, codex=None
    ):
        self.session = session
        self.prefix = ["tmux"] + (["-S", str(socket)] if socket is not None else [])
        self.codex = codex
        self.last_error = ""
        self.claude = None

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

    def server_identity(self) -> tuple[str, int | None, int | None]:
        try:
            fields = (
                self.command("display-message", "-p", "#{socket_path}\t#{pid}")
                .strip()
                .split("\t")
            )
            if len(fields) != 2:
                return "", None, None
            socket_path, pid = fields
            server_pid = int(pid)
            return (
                str(Path(socket_path).resolve()),
                server_pid,
                process_start_ticks(server_pid),
            )
        except SourceError, ValueError:
            return "", None, None

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

    def client(self):
        if self.codex is None:
            self.codex = sibling("codex_server").CodexServer()
        return self.codex

    def thread_for_pane(self, data: dict, preview: str, loaded: list[str]):
        socket_path, server_pid, server_ticks = self.server_identity()
        pane_pid = int(data["pane_pid"])
        foreground_pid, foreground_ticks = foreground_identity(pane_pid)
        key = (
            socket_path,
            server_pid,
            server_ticks,
            data["session_id"],
            data["window_id"],
            data["pane_id"],
            pane_pid,
            process_start_ticks(pane_pid),
            foreground_pid,
            foreground_ticks,
        )
        return (
            sibling("codex_identity")
            .CodexIdentity()
            .resolve(
                preview,
                pane_key=key,
                loaded_threads=loaded,
                height=int(data["pane_height"]),
            )
            .thread_id
        )

    @staticmethod
    def thread_view(thread, native: PaneSnapshot | None = None) -> PaneSnapshot:
        key = "codex:" + thread.thread_id
        if native is None:
            native = PaneSnapshot(
                session_id="codex",
                session_name="Codex",
                window_id=key,
                window_index=0,
                window_name="Codex",
                pane_id=key,
                pane_index=0,
                pane_pid=0,
                title=thread.title or thread.thread_id,
                cwd=thread.cwd,
                pane_current_command="codex",
                pane_bg="",
                pane_fg="",
                header_spans=[],
                state=thread.state,
                idle_since=None,
                status_detail="Codex server session; pane not linked",
                preview_ansi="",
            )
            link = None
        else:
            link = native
        return replace(
            native,
            pane_id=native.pane_id if link else key,
            thread_id=thread.thread_id,
            state=thread.state,
            state_since=thread.state_since,
            state_since_source=thread.state_since_source,
            approvals=thread.requests,
            native_pane=link,
            thread_data=thread,
            status_detail="Codex server state"
            + ("; verified pane context" if link else "; pane not linked"),
        )

    def enrich_native_state(
        self, pane: PaneSnapshot, data: dict, threads: dict
    ) -> PaneSnapshot:
        if pane.pane_current_command == "codex":
            observed = sibling("codex_pane_state").observe(
                data, pane.preview_ansi, list(threads.values()), pane.foreground_pid
            )
            return replace(
                pane,
                state=observed.state if observed.state != "unknown" else "unverified",
                state_since=observed.since,
                state_since_source=observed.source,
                state_approximate=observed.approximate,
                status_detail="Codex native state; " + observed.source,
            )
        if self.claude is None:
            self.claude = sibling("claude_state").ClaudeState()
        observed = self.claude.for_pane(pane)
        if observed is not None:
            return replace(
                pane,
                state=observed.state if observed.state != "unknown" else "unverified",
                state_since=observed.state_since,
                state_since_source=observed.state_since_source,
                state_approximate=observed.approximate,
                status_detail=observed.status_detail,
            )
        if pane.pane_current_command in {"claude", "claude-code"}:
            return replace(
                pane,
                state="unverified",
                status_detail="Claude native status record unavailable",
            )
        return pane

    def snapshots(self) -> list[PaneSnapshot]:
        socket_path, server_pid, server_ticks = self.server_identity()
        rows = self.command(
            "list-panes",
            "-s",
            "-t",
            f"={self.session}",
            "-F",
            "\t".join("#{" + field + "}" for field in FIELDS),
        )
        result = []
        threads = {}
        self.last_error = ""
        try:
            loaded = self.client().loaded_threads()
            for thread_id in loaded:
                try:
                    thread = self.client().snapshot(thread_id)
                except RuntimeError as error:
                    self.last_error = f"Session {thread_id}: {error}"
                    continue
                if not getattr(thread, "parent_thread_id", None):
                    threads[thread_id] = thread
        except RuntimeError as error:
            self.last_error = str(error)
            threads = {}
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
            is_codex = data["pane_current_command"] == "codex"
            state = "unknown"
            detail = "Provider state unknown"
            thread_id = (
                self.thread_for_pane(data, preview, list(threads))
                if is_codex and threads
                else None
            )
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
                    idle_since=None,
                    status_detail=detail,
                    preview_ansi=preview,
                    foreground_pid=foreground_pid,
                    foreground_start_ticks=foreground_ticks,
                    socket_path=socket_path,
                    server_pid=server_pid,
                    server_start_ticks=server_ticks,
                    pane_start_ticks=process_start_ticks(int(data["pane_pid"])),
                )
            )
            result[-1] = self.enrich_native_state(result[-1], data, threads)
            if thread_id in threads:
                native = result.pop()
                result.append(self.thread_view(threads[thread_id], native))
        return result

    def select(self, snapshot: PaneSnapshot) -> PaneSnapshot:
        if not snapshot.thread_id:
            return snapshot
        thread = self.client().select(snapshot.thread_id)
        return self.thread_view(thread, snapshot.native_pane)

    def answer(self, snapshot: PaneSnapshot, occurrence_id: str, decision: str):
        if not snapshot.thread_id or not any(
            item.occurrence_id == occurrence_id and item.thread_id == snapshot.thread_id
            for item in snapshot.approvals
        ):
            raise SourceError("Request is not part of the displayed Codex session")
        return self.client().answer(occurrence_id, decision)

    def close(self):
        if self.codex is not None:
            self.codex.close()

    @staticmethod
    def conversation(thread) -> str:
        lines = []
        for turn in reversed(thread.recent_turns):
            for item in turn.get("items", []):
                kind = item.get("type", "")
                if kind in {"userMessage", "agentMessage"}:
                    text = item.get("text")
                    if text is None:
                        text = "\n".join(
                            part.get("text", "")
                            for part in item.get("content", [])
                            if isinstance(part, dict)
                        )
                    lines.extend(
                        ["You" if kind == "userMessage" else "Codex", text, ""]
                    )
                elif kind == "commandExecution":
                    lines.extend(
                        [
                            "Command: " + item.get("command", ""),
                            item.get("aggregatedOutput") or "",
                            "",
                        ]
                    )
        if getattr(thread, "history_error", ""):
            lines.append("History unavailable: " + thread.history_error)
        return "\n".join(lines) or "No conversation history available yet."

    def capture(self, snapshot: PaneSnapshot) -> str:
        if snapshot.thread_id:
            if snapshot.native_pane is not None:
                native = snapshot.native_pane
                try:
                    height = self.validate(native)
                    data = {**vars(native), "pane_height": str(height)}

                    def linked_now():
                        viewport = self.command(
                            "capture-pane",
                            "-p",
                            "-e",
                            "-N",
                            "-t",
                            native.pane_id,
                            "-S",
                            "0",
                            "-E",
                            str(height - 1),
                        )
                        return (
                            self.thread_for_pane(data, viewport, [snapshot.thread_id])
                            == snapshot.thread_id
                        )

                    if linked_now():
                        captured = self.capture(native)
                        if linked_now():
                            return captured
                except SourceError:
                    # The independently identified server conversation remains usable.
                    return self.conversation(snapshot.thread_data)
            return self.conversation(snapshot.thread_data)
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
        if snapshot.thread_id:
            if snapshot.native_pane is None:
                raise SourceError("This Codex session has no verified tmux pane link")
            snapshot = snapshot.native_pane
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
        if snapshot.thread_id:
            raise SourceError(
                "Use the displayed Codex request choices; terminal input is disabled"
            )
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
