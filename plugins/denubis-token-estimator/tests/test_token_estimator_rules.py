"""Pure-rule tests for the methodology primitives in verify.py.

These pin the rules that the whole disclosure rests on: how a recorded cwd maps to
(person, project), which user-text wrappers are machine-emitted (node 3 / node 4
allow-lists, NOT "starts with < or #"), and how people-roots are resolved. No live
logs, no I/O beyond a tmp config file.
"""

from __future__ import annotations

import verify as V


# ---------------------------------------------------------------- attribute (node 5)
class TestAttribute:
    def test_person_project_subdir(self):
        assert V.attribute("/r/Alice/ProjX/sub/dir", ["/r"]) == (
            "Alice",
            "ProjX",
            "sub/dir",
        )

    def test_project_root_no_subdir(self):
        assert V.attribute("/r/Alice/ProjX", ["/r"]) == ("Alice", "ProjX", "")

    def test_person_root_only(self):
        # one segment under the root -> person known, project is a sentinel
        assert V.attribute("/r/Alice", ["/r"]) == ("Alice", "(person-root)", "")

    def test_cwd_equals_root_is_unrooted(self):
        assert V.attribute("/r", ["/r"]) == ("(unrooted)", "/r", "")

    def test_outside_all_roots(self):
        assert V.attribute("/elsewhere/x", ["/r"]) == ("(unrooted)", "/elsewhere/x", "")

    def test_empty_and_none_cwd(self):
        assert V.attribute("", ["/r"]) == ("(no-cwd)", "(no-cwd)", "")
        assert V.attribute(None, ["/r"]) == ("(no-cwd)", "(no-cwd)", "")

    def test_longest_prefix_wins(self):
        # cwd matches both roots; the LONGER root is chosen, so the person/project
        # are read relative to "/a/b", not "/a".
        assert V.attribute("/a/b/Alice/Proj", ["/a", "/a/b"]) == ("Alice", "Proj", "")


# --------------------------------------------- lead_tag / MACHINE_TAGS (node 3)
class TestClaudeWrappers:
    def test_machine_tag_detected_and_listed(self):
        assert V.lead_tag("<system-reminder>x</system-reminder>") == "system-reminder"
        assert "system-reminder" in V.MACHINE_TAGS

    def test_tag_is_lowercased(self):
        assert V.lead_tag("  <Command-Name>do</Command-Name>") == "command-name"
        assert "command-name" in V.MACHINE_TAGS

    def test_human_pasted_markup_is_not_machine(self):
        # humans paste <p>/<div>; the rule is a NAMED allow-list, not "starts with <"
        assert V.lead_tag("<p>genuine pasted html</p>") == "p"
        assert "p" not in V.MACHINE_TAGS

    def test_heading_and_plain_text_have_no_tag(self):
        assert V.lead_tag("# a markdown heading") is None
        assert V.lead_tag("just some prose") is None


# --------------------------------------------------- codex_machine_marker (node 4)
class TestCodexMarkers:
    def test_named_machine_markers_excluded(self):
        assert (
            V.codex_machine_marker("<turn_aborted> The user interrupted")
            == "turn_aborted"
        )
        assert V.codex_machine_marker("<skill>SKILL.md body</skill>") == "skill"

    def test_agents_md_opener_excluded(self):
        assert V.codex_machine_marker("# AGENTS.md\nrepo rules") == "#AGENTS.md"

    def test_markdown_heading_prompt_is_kept(self):
        # "# Claude ..." is a human prompt heading, not the AGENTS opener -> kept (None)
        assert V.codex_machine_marker("# Claude, please do X") is None

    def test_pasted_markup_and_plain_text_kept(self):
        assert V.codex_machine_marker("<p>pasted by a human</p>") is None
        assert V.codex_machine_marker("just continue") is None


# ----------------------------------------------------------------- load_roots
class TestLoadRoots:
    def test_config_present_wins(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        root = tmp_path / "people"
        root.mkdir()
        (home / ".token-estimator").write_text(
            f'roots = ["{root}"]\n', encoding="utf-8"
        )
        monkeypatch.setattr(V.Path, "home", staticmethod(lambda: home))
        assert V.load_roots() == [str(root.resolve())]

    def test_config_absent_falls_back_to_target(self, tmp_path, monkeypatch):
        home = tmp_path / "empty_home"
        home.mkdir()
        monkeypatch.setattr(V.Path, "home", staticmethod(lambda: home))
        target = tmp_path / "some" / "project"
        target.mkdir(parents=True)
        assert V.load_roots(str(target)) == [str(target.resolve())]


def test_pct():
    assert V.pct(1, 4) == 25.0
    assert V.pct(0, 0) == 0.0
