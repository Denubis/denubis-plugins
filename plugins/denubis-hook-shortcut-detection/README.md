# denubis-hook-shortcut-detection

A Claude Code Stop hook that detects when Claude is taking shortcuts by abandoning the original approach without proper justification.

## What It Detects

Claude sometimes gives up on a working approach when it encounters difficulties, switching to a "simpler" or "streamlined" solution without explaining what went wrong. This hook catches those moments by detecting tell-tale phrases like:

- "let me try a different approach"
- "simpler approach"
- "for simplicity"
- "on second thought"

When detected, the hook blocks Claude and requires it to:

1. Explain what specific error or problem it encountered
2. Describe what it tried to fix it
3. Explain why the original approach fundamentally cannot work
4. Ask the user explicitly for approval to change approaches

## How It Works

This plugin uses Claude Code's **Stop hook** mechanism. Stop hooks run after Claude finishes a response, receiving the conversation transcript via stdin.

The hook:

1. Reads the transcript JSONL file path from stdin
2. Extracts the last assistant message content
3. Matches against shortcut phrase patterns (case-insensitive regex)
4. Outputs a `block` decision with explanation if a match is found

When blocked, Claude must address all four requirements before the user allows it to continue.

## Installation

Add to your Claude Code configuration:

```bash
claude mcp add-plugin denubis-hook-shortcut-detection
```

Or manually add the plugin path to your settings.

## Detected Phrases

### High-Signal Phrases

These almost always indicate Claude is taking a shortcut:

| Phrase | What It Usually Means |
|--------|----------------------|
| `let me try a different approach` | Abandoning current strategy |
| `simpler approach` | Simplifying without justification |
| `let's just bail` / `let's bail` | Giving up entirely |
| `for simplicity` | Dropping complexity without explaining why |
| `to simplify` | Same as above |
| `on second thought` | Reversing course mid-stream |
| `actually, let me` | Changing direction |
| `streamlined` | Making things "simpler" |

### Medium-Signal Phrases

These are context-dependent but worth flagging:

| Phrase | Notes |
|--------|-------|
| `instead of` | May indicate legitimate alternative |
| `easier to` | Could be genuine improvement |
| `more efficient` | Context matters |
| `more straightforward` | May be appropriate |

## License

CC-BY-SA-4.0
