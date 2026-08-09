"""Tests for denubis-plan-and-execute/hooks/session-start.py.

This hook replaced a bash implementation that hand-rolled JSON escaping for
only ``\\ " \\n \\r \\t``. The escaping test below feeds control characters the
bash version would have emitted raw (producing invalid JSON) and asserts the
Python hook round-trips them through json.dumps correctly.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

_HOOK_PATH = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-plan-and-execute"
    / "hooks"
    / "session-start.py"
)


def _run(plugin_root: Path | None) -> tuple[int, str, dict | None]:
    """Run the hook, optionally pointing CLAUDE_PLUGIN_ROOT at a seam dir.

    Returns (returncode, raw_stdout, parsed_json_or_None).
    """
    env = {**os.environ}
    if plugin_root is None:
        env.pop("CLAUDE_PLUGIN_ROOT", None)
    else:
        env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        capture_output=True,
        timeout=10,
        env=env,
    )
    raw = result.stdout.decode()
    parsed = json.loads(raw) if raw.strip() else None
    return result.returncode, raw, parsed


def _seed_skill(root: Path, content: str) -> None:
    """Write a using-plan-and-execute SKILL.md under a fake plugin root."""
    skill_dir = root / "skills" / "using-plan-and-execute"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Real skill file (fallback to __file__) — mirrors the prior bats coverage
# ---------------------------------------------------------------------------
class TestRealSkill:
    def test_outputs_valid_session_start_json(self):
        code, _raw, output = _run(None)
        assert code == 0
        assert output is not None
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_includes_skill_content(self):
        """The wrapper names its source so a reader can find the file it came
        from. It previously asserted the `EXTREMELY_IMPORTANT` framing, which
        was dropped on 2026-08-09 when the injected directives were brought in
        line with `writing-claude-directives`: that framing is rhetorical
        emphasis on an ordinary instruction, not a true boundary. Embedding of
        the file's actual bytes is proved by TestEscaping below, which seeds a
        known string through the seam."""
        _code, _raw, output = _run(None)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "using-plan-and-execute" in context
        assert "skill" in context


# ---------------------------------------------------------------------------
# Escaping — the justification for the swap
# ---------------------------------------------------------------------------
class TestEscaping:
    def test_control_characters_round_trip(self, tmp_path: Path):
        """Chars the bash escaper missed (U+0001, U+000B, U+000C) plus quotes
        and backslashes must survive as valid, correctly-escaped JSON."""
        nasty = 'quote " backslash \\ vtab \x0b ff \x0c soh \x01 done'
        _seed_skill(tmp_path, nasty)

        code, raw, output = _run(tmp_path)
        assert code == 0
        # Raw stdout must be parseable — raw control chars would break this.
        assert json.loads(raw) is not None
        context = output["hookSpecificOutput"]["additionalContext"]
        assert nasty in context


# ---------------------------------------------------------------------------
# Missing file — the OSError branch (untested under bash)
# ---------------------------------------------------------------------------
class TestMissingSkill:
    def test_missing_file_uses_error_fallback(self, tmp_path: Path):
        code, _raw, output = _run(tmp_path)  # empty dir, no SKILL.md
        assert code == 0
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "Error reading using-plan-and-execute skill" in context
