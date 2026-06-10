"""Tests for denubis-hook-shortcut-detection/hooks/shortcut-detector.py."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_HOOK_PATH = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-hook-shortcut-detection"
    / "hooks"
    / "shortcut-detector.py"
)
_spec = importlib.util.spec_from_file_location("shortcut_detector", _HOOK_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

check_for_shortcuts = _mod.check_for_shortcuts
get_last_assistant_content = _mod.get_last_assistant_content
lockfile_for_session = _mod.lockfile_for_session


# ---------------------------------------------------------------------------
# check_for_shortcuts
# ---------------------------------------------------------------------------
class TestCheckForShortcuts:
    @pytest.mark.parametrize(
        "text",
        [
            "let me try a different approach",
            "Here's a simpler approach to the problem",
            "Let's just bail on that",
            "For simplicity, I'll skip the validation",
            "On second thought, let me do this instead",
            "Actually, let me rewrite the whole thing",
            "This streamlined version should work",
            "Let's do it directly rather than through the API",
        ],
    )
    def test_high_signal_phrases_detected(self, text):
        found, phrase = check_for_shortcuts(text)
        assert found, f"Expected to detect shortcut in: {text}"
        assert phrase is not None

    @pytest.mark.parametrize(
        "text",
        [
            "It would be easier to use a dictionary here",
            "This is more efficient than the previous version",
            "A more straightforward solution would be",
        ],
    )
    def test_medium_signal_phrases_detected(self, text):
        found, phrase = check_for_shortcuts(text)
        assert found, f"Expected to detect shortcut in: {text}"

    def test_normal_text_not_detected(self):
        found, phrase = check_for_shortcuts("I've implemented the feature as requested.")
        assert not found
        assert phrase is None

    def test_case_insensitive(self):
        found, _ = check_for_shortcuts("LET ME TRY A DIFFERENT APPROACH")
        assert found


# ---------------------------------------------------------------------------
# get_last_assistant_content
# ---------------------------------------------------------------------------
class TestGetLastAssistantContent:
    def test_extracts_last_assistant_text(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        lines = [
            json.dumps({"type": "human", "message": {"content": "hello"}}),
            json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "first response"}]},
            }),
            json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "second response"}]},
            }),
        ]
        transcript.write_text("\n".join(lines))
        result = get_last_assistant_content(str(transcript))
        assert result == "second response"

    def test_multiple_text_parts_joined(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "part one"},
                    {"type": "tool_use", "name": "Read"},
                    {"type": "text", "text": "part two"},
                ],
            },
        }
        transcript.write_text(json.dumps(entry))
        result = get_last_assistant_content(str(transcript))
        assert result == "part one part two"

    def test_missing_file_returns_none(self):
        assert get_last_assistant_content("/nonexistent/path") is None

    def test_empty_file_returns_none(self, tmp_path):
        transcript = tmp_path / "empty.jsonl"
        transcript.write_text("")
        assert get_last_assistant_content(str(transcript)) is None

    def test_no_assistant_entries(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({"type": "human", "message": {"content": "hi"}}))
        assert get_last_assistant_content(str(transcript)) is None


# ---------------------------------------------------------------------------
# lockfile_for_session
# ---------------------------------------------------------------------------
class TestLockfileForSession:
    def test_deterministic(self):
        a = lockfile_for_session("/path/to/transcript")
        b = lockfile_for_session("/path/to/transcript")
        assert a == b

    def test_different_paths_differ(self):
        a = lockfile_for_session("/path/a")
        b = lockfile_for_session("/path/b")
        assert a != b

    def test_returns_path_in_lockfile_dir(self):
        result = lockfile_for_session("/any/path")
        # Lockfiles live in a "shortcut-detector" dir under the system temp dir.
        # Derive the expectation from gettempdir() (the source of truth the code
        # uses) rather than hardcoding /tmp — $TMPDIR is set on some hosts/CI.
        assert result.parent == Path(tempfile.gettempdir()) / "shortcut-detector"
        assert result.name.endswith(".blocked")


# ---------------------------------------------------------------------------
# Integration: main() via subprocess
# ---------------------------------------------------------------------------
class TestMainIntegration:
    def _run(self, input_data: dict) -> tuple[int, dict | None]:
        result = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input=json.dumps(input_data).encode(),
            capture_output=True,
            timeout=10,
        )
        stdout = result.stdout.decode().strip()
        parsed = json.loads(stdout) if stdout else None
        return result.returncode, parsed

    def test_no_transcript_path_exits_clean(self):
        rc, output = self._run({})
        assert rc == 0
        assert output is None

    def test_shortcut_detected_blocks(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        entry = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Let me try a different approach here."}],
            },
        }
        transcript.write_text(json.dumps(entry))

        # Clean up any leftover lockfile
        lockfile = lockfile_for_session(str(transcript))
        lockfile.unlink(missing_ok=True)

        rc, output = self._run({"transcript_path": str(transcript)})
        assert rc == 0
        assert output is not None
        assert output["decision"] == "block"
        assert "SHORTCUT DETECTED" in output["reason"]

        # Clean up lockfile created by the test
        lockfile.unlink(missing_ok=True)

    def test_lockfile_prevents_retrigger(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        entry = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Let me try a different approach"}],
            },
        }
        transcript.write_text(json.dumps(entry))

        lockfile = lockfile_for_session(str(transcript))
        lockfile.unlink(missing_ok=True)

        # First run should block
        _, output1 = self._run({"transcript_path": str(transcript)})
        assert output1 is not None
        assert output1["decision"] == "block"

        # Second run should be silent (lockfile exists)
        _, output2 = self._run({"transcript_path": str(transcript)})
        assert output2 is None

        lockfile.unlink(missing_ok=True)

    def test_clean_content_passes(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        entry = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Here is the implementation you asked for."}],
            },
        }
        transcript.write_text(json.dumps(entry))
        rc, output = self._run({"transcript_path": str(transcript)})
        assert rc == 0
        assert output is None

    def test_bad_json_exits_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input=b"not json",
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0
