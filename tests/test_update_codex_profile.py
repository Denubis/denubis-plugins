import importlib.util
import tomllib
from pathlib import Path

import pytest
import tomlkit
from hypothesis import given, settings
from hypothesis import strategies as st

_EDITOR = (
    Path(__file__).parents[1]
    / "plugins"
    / "denubis-external-agents"
    / "scripts"
    / "update_codex_profile.py"
)
_SPEC = importlib.util.spec_from_file_location("update_codex_profile", _EDITOR)
assert _SPEC is not None and _SPEC.loader is not None
profile_editor = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(profile_editor)


def test_rewrite_replaces_only_launcher_owned_skill_policy() -> None:
    source = '''hand_written = "preserve me" # user comment
literal = """
[[skills.config]]
this is string data, not a table
"""

[[skills.config]]
path = "/obsolete/SKILL.md"
enabled = false

[projects."/tmp/reviewed-project"]
trust_level = "trusted"

[hooks.state.test]
trusted_hash = "sha256:test-hook-trust"
'''

    result = profile_editor.rewrite_profile(source, ["/current/SKILL.md"])

    parsed = tomllib.loads(result)
    assert parsed["hand_written"] == "preserve me"
    assert parsed["literal"] == "[[skills.config]]\nthis is string data, not a table\n"
    assert parsed["skills"]["config"] == [
        {"path": "/current/SKILL.md", "enabled": False}
    ]
    assert parsed["projects"]["/tmp/reviewed-project"]["trust_level"] == "trusted"
    assert parsed["hooks"]["state"]["test"]["trusted_hash"] == (
        "sha256:test-hook-trust"
    )
    assert '# user comment' in result


def test_rewrite_accepts_inline_skills_table_and_preserves_siblings() -> None:
    source = (
        'skills = { config = [{ path = "/obsolete/SKILL.md", enabled = false }], '
        'custom = "preserve me" }\n'
    )

    result = profile_editor.rewrite_profile(source, ["/current/SKILL.md"])

    parsed = tomllib.loads(result)
    assert parsed["skills"]["custom"] == "preserve me"
    assert parsed["skills"]["config"] == [
        {"path": "/current/SKILL.md", "enabled": False}
    ]


_root_values = st.dictionaries(
    keys=st.from_regex(r"[a-z][a-z0-9_]{0,15}", fullmatch=True).filter(
        lambda key: key != "skills"
    ),
    values=st.one_of(
        st.booleans(),
        st.integers(min_value=-(2**63), max_value=2**63 - 1),
        # The property begins from TOML rendered by tomlkit, so generate text
        # that is valid TOML data rather than exercising tomlkit's handling of
        # prohibited control characters (for example ESC becomes invalid `\e`).
        st.text(
            alphabet=st.characters(exclude_categories=("Cc", "Cs")),
            max_size=80,
        ),
    ),
    max_size=8,
)


@settings(max_examples=50)
@given(root_values=_root_values)
def test_rewrite_preserves_arbitrary_root_values(
    root_values: dict[str, object],
) -> None:
    source = tomlkit.dumps(root_values)

    result = profile_editor.rewrite_profile(source, ["/current/SKILL.md"])

    parsed = tomllib.loads(result)
    preserved = {key: value for key, value in parsed.items() if key != "skills"}
    assert preserved == root_values
    assert parsed["skills"]["config"] == [
        {"path": "/current/SKILL.md", "enabled": False}
    ]


def test_rewrite_rejects_invalid_toml() -> None:
    with pytest.raises(tomlkit.exceptions.ParseError):
        profile_editor.rewrite_profile("stale profile\n", [])


def test_update_file_preserves_crlf_line_endings(tmp_path: Path) -> None:
    profile = tmp_path / "profile.toml"
    output = tmp_path / "output.toml"
    skill_list = tmp_path / "skills.list"
    profile.write_bytes(
        b'hand_written = "preserve me"\r\n'
        b"\r\n"
        b"[[skills.config]]\r\n"
        b'path = "/obsolete/SKILL.md"\r\n'
        b"enabled = false\r\n"
    )
    skill_list.write_bytes(b"/current/SKILL.md\0")

    profile_editor.update_file(profile, output, skill_list)

    result = output.read_bytes()
    assert b"\r\n" in result
    assert b"\n" not in result.replace(b"\r\n", b"")
    assert tomllib.loads(result.decode())["skills"]["config"] == [
        {"path": "/current/SKILL.md", "enabled": False}
    ]
