# ADR 2026-11-02-bbs-fresh-session-passes-context-floor — A freshly cleared session has no context to measure, so the context floor does not refuse it

**Status:** Accepted (2026-11-02). Narrows the `supervising-codex` rule that an unreadable
meter refuses; the rule stands for every other state.

## Authority evidence

Original human message in session `f31135e5-0253-441f-8140-bdd86e8940bc`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`):

- `ccchat:v1:claude:f31135e5-0253-441f-8140-bdd86e8940bc:uuid:30c9f807-cfff-436a-8b3e-0f50d06efc10`
  (2026-11-02T02:11Z), answering "After a clear at phone width, may the first send go
  through when the session has no file yet?": "right after clear, there is no context to
  measure? What's the issue?"

Exact raw-record resolver:

```sh
cc-search-chats context 30c9f807-cfff-436a-8b3e-0f50d06efc10 --json
```

## Context

Brian controls supervision from a phone over mosh or ssh, and tmux shrinks the pane to fit.
Codex draws no context meter at 60 columns or narrower (observed 2026-11-02, GPT-6.1-Sol),
so the floor reads the session's rollout file instead. A session that has made no model
call has no rollout yet. Refusing there would fail the first send after every `--clear`
from a phone, and clearing between prompts is the default loop.

## Decision

With no meter on screen, a session that holds a lock and has no rollout has nothing to
measure, and `--send` and `--message` proceed, reporting that state rather than a
percentage. Every other unreadable state still refuses.

## Consequences

- The dispatch output distinguishes "no model call yet" from a measured percentage.
- A rollout that exists but cannot be found would be misread as fresh. The implementation
  owns narrowing that risk and tests must show the ambiguous states still refuse.
