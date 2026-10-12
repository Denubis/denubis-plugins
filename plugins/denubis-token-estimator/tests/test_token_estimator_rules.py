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


# ------------------------------------------- claude_machine_marker (node 3)
class TestClaudeMachineMarker:
    """Named markers beyond leading tags: the cross-session relay line that Claude Code
    prints before a <teammate-message> wrapper, and the interrupt boilerplate it writes
    when the human presses Escape. Neither is human-authored text."""

    def test_wrapper_tag_is_a_marker(self):
        marker = V.claude_machine_marker("<system-reminder>x</system-reminder>")
        assert marker is not None

    def test_cross_session_relay_is_a_marker(self):
        text = (
            "Another Claude session sent a message:\n"
            '<teammate-message teammate_id="reader" color="cyan">\n'
            "Note written; quotes verified.\n</teammate-message>"
        )
        assert V.claude_machine_marker(text) is not None

    def test_cross_session_sentence_typed_by_a_human_is_kept(self):
        # The relay line stands alone; a human sentence that happens to begin the same
        # way, with the message on the same line, is not the machine form.
        assert (
            V.claude_machine_marker(
                "Another Claude session sent a message: can you check it arrived?"
            )
            is None
        )

    def test_interrupt_boilerplate_is_a_marker(self):
        assert V.claude_machine_marker("[Request interrupted by user]") is not None
        assert (
            V.claude_machine_marker("  [Request interrupted by user for tool use]\n")
            is not None
        )

    def test_interrupt_followed_by_human_text_is_kept(self):
        assert (
            V.claude_machine_marker("[Request interrupted by user] no, do it this way")
            is None
        )

    def test_human_markup_heading_and_prose_are_kept(self):
        assert V.claude_machine_marker("<p>genuine pasted html</p>") is None
        assert V.claude_machine_marker("# Claude, please do X") is None
        assert V.claude_machine_marker("just some prose") is None


# ------------------------------------------ claude_user_excluded (node 3)
class TestClaudeUserRecordExclusion:
    """Record-level drops are structural flags on the user record, not text rules."""

    def test_compaction_summary_record_is_excluded(self):
        rec = {
            "type": "user",
            "isCompactSummary": True,
            "message": {"content": "This session is being continued from a previous"},
        }
        assert V.claude_user_excluded(rec) is not None

    def test_existing_structural_drops_still_apply(self):
        assert V.claude_user_excluded({"type": "user", "isSidechain": True}) is not None
        assert V.claude_user_excluded({"type": "user", "toolUseResult": {}}) is not None
        assert V.claude_user_excluded({"type": "user", "isMeta": True}) is not None

    def test_plain_human_record_is_kept(self):
        rec = {"type": "user", "uuid": "u1", "message": {"content": "hello"}}
        assert V.claude_user_excluded(rec) is None


# ------------------------------------------------------ split_pasted (node 3)
class TestSplitPasted:
    """Claude Code wraps a large paste in <pasted_content id="…">…</pasted_content
    id="…">. Words inside the wrapper are pasted material; words outside it are the
    human's own authorship. Both are counted, separately."""

    def test_no_wrapper_is_all_original(self):
        assert V.split_pasted("just my own words") == ("just my own words", "")

    def test_wrapper_mid_text_with_attributed_closing_tag(self):
        text = (
            'fix this\n\n<pasted_content id="863a">\nalpha beta gamma delta\n'
            '</pasted_content id="863a">\n\nplease'
        )
        original, pasted = V.split_pasted(text)
        assert original.split() == ["fix", "this", "please"]
        assert pasted.split() == ["alpha", "beta", "gamma", "delta"]

    def test_wrapper_at_start(self):
        original, pasted = V.split_pasted(
            '<pasted_content id="1">one two</pasted_content id="1"> ok'
        )
        assert original.split() == ["ok"]
        assert pasted.split() == ["one", "two"]

    def test_unclosed_wrapper_runs_to_end(self):
        original, pasted = V.split_pasted('see: <pasted_content id="7"> one two three')
        assert original.split() == ["see:"]
        assert pasted.split() == ["one", "two", "three"]

    def test_forwarded_side_agent_note_is_pasted_and_own_words_kept(self):
        text = (
            "Here is a note offered by a side agent:\n\n"
            "> Heads up · Older pastes still count.\n>\n"
            "> **Older pastes**\n> * one point\n\n"
            "arrgh"
        )
        original, pasted = V.split_pasted(text)
        assert original.split() == ["arrgh"]
        assert "Heads" in pasted and "point" in pasted

    def test_blockquote_without_the_note_header_is_own_words(self):
        original, pasted = V.split_pasted("> quoting myself\n> here")
        assert original.split() == [">", "quoting", "myself", ">", "here"]
        assert pasted == ""

    def test_two_wrappers(self):
        original, pasted = V.split_pasted(
            'a <pasted_content id="1">x</pasted_content id="1"> b '
            '<pasted_content id="2">y z</pasted_content id="2"> c'
        )
        assert original.split() == ["a", "b", "c"]
        assert pasted.split() == ["x", "y", "z"]


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
