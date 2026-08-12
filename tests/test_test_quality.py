"""Meta-tests for automated checks that merely freeze documentation wording."""

from pathlib import Path
from runpy import run_path

ROOT = Path(__file__).resolve().parents[1]
find_prose_change_assertions = run_path(
    str(ROOT / "scripts" / "test_quality.py")
)["find_prose_change_assertions"]


def test_detector_finds_direct_document_wording_assertion() -> None:
    source = '''
from pathlib import Path

SKILL = Path("plugin") / "SKILL.md"

def test_rule_is_present():
    text = SKILL.read_text()
    assert "required wording" in text
'''

    violations = find_prose_change_assertions(source, filename="test_rule.py")

    assert [violation.line for violation in violations] == [8]


def test_detector_follows_whitespace_normalising_helpers() -> None:
    source = '''
from pathlib import Path

SKILL = Path("plugin") / "SKILL.md"

def _skill():
    return " ".join(SKILL.read_text().split())

def test_rule_is_absent():
    text = _skill()
    for scar in {"old wording", "another phrase"}:
        assert scar not in text
'''

    violations = find_prose_change_assertions(source, filename="test_rule.py")

    assert [violation.line for violation in violations] == [12]


def test_detector_finds_inline_path_read() -> None:
    source = '''
from pathlib import Path

def test_rule_is_present():
    assert "required" in Path("SKILL.md").read_text()
'''

    violations = find_prose_change_assertions(source, filename="test_rule.py")

    assert [violation.line for violation in violations] == [5]


def test_detector_finds_wording_comparison_nested_in_all() -> None:
    source = '''
from pathlib import Path

SKILL = Path("SKILL.md")

def test_rules_are_present():
    text = SKILL.read_text()
    assert all(word in text for word in ("required",))
'''

    violations = find_prose_change_assertions(source, filename="test_rule.py")

    assert [violation.line for violation in violations] == [8]


def test_detector_finds_regex_probe_of_raw_document() -> None:
    source = '''
import re
from pathlib import Path

SKILL = Path("SKILL.md")

def test_rule_is_present():
    assert re.search("required", SKILL.read_text())
'''

    violations = find_prose_change_assertions(source, filename="test_rule.py")

    assert [violation.line for violation in violations] == [8]


def test_detector_allows_assertions_on_program_output() -> None:
    source = '''
def test_cli_result():
    output = run_cli()
    assert "ready" in output
'''

    assert find_prose_change_assertions(source, filename="test_cli.py") == []


def test_detector_allows_assertions_on_parsed_structure() -> None:
    source = '''
import json
from pathlib import Path

MANIFEST = Path("candidate.json")

def test_manifest_state():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["state"] == "candidate"
'''

    assert find_prose_change_assertions(source, filename="test_manifest.py") == []


def test_python_tests_have_no_detectable_markdown_wording_assertions() -> None:
    """Apply the positively controlled lint within its stated Python-test scope."""
    paths = sorted(ROOT.glob("tests/test_*.py"))
    paths.extend(sorted(ROOT.glob("plugins/**/tests/test_*.py")))
    violations = [
        violation
        for path in paths
        for violation in find_prose_change_assertions(
            path.read_text(encoding="utf-8"),
            filename=str(path.relative_to(ROOT)),
        )
    ]

    assert not violations, "\n".join(str(violation) for violation in violations)
