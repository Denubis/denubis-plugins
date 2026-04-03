#!/usr/bin/env python3
"""
Stop hook that detects shortcut phrases in Claude's assistant messages.

Reads a transcript file and checks the last assistant message for phrases
that indicate Claude is taking shortcuts rather than debugging properly.

When triggered, blocks with an E-STOP so the user can decide whether
to continue or ask Claude to explain.

Loop prevention:
- After blocking, creates a session-specific lockfile.
- The lockfile is keyed to the transcript path, so it's unique per session.
- Once blocked in a session, stays quiet for the rest of that session.
- New session = new transcript path = no lockfile = re-armed.
"""
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

# High-signal phrases - almost always indicate Claude is taking a shortcut
HIGH_SIGNAL_PHRASES = [
    r"let me try a different approach",
    r"simpler approach",
    r"let's just bail",
    r"let's bail",
    r"for simplicity",
    r"to simplify",
    r"on second thought",
    r"actually,? let me",
    r"streamlined",
    r"directly rather than",
]

# Medium-signal phrases - context-dependent but worth flagging
MEDIUM_SIGNAL_PHRASES = [
    r"easier to",
    r"more efficient",
    r"more straightforward",
]

# Combine all patterns
ALL_PHRASES = HIGH_SIGNAL_PHRASES + MEDIUM_SIGNAL_PHRASES

LOCKFILE_DIR = Path(tempfile.gettempdir()) / "shortcut-detector"


def lockfile_for_session(transcript_path: str) -> Path:
    """Return a session-specific lockfile path based on the transcript path."""
    session_hash = hashlib.sha256(transcript_path.encode()).hexdigest()[:16]
    return LOCKFILE_DIR / f"{session_hash}.blocked"


def get_last_assistant_content(transcript_path: str) -> str | None:
    """Extract the last assistant message text from the transcript."""
    last_assistant_content = None

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") != "assistant":
                        continue

                    message = entry.get("message", {})
                    content_parts = message.get("content", [])
                    text_parts = []
                    for part in content_parts:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                        elif isinstance(part, str):
                            text_parts.append(part)
                    if text_parts:
                        last_assistant_content = " ".join(text_parts)
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, PermissionError, OSError):
        pass

    return last_assistant_content


def check_for_shortcuts(content: str) -> tuple[bool, str | None]:
    """Check content for shortcut phrases. Returns (found, matched_phrase)."""
    for pattern in ALL_PHRASES:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return True, match.group(0)
    return False, None


def main():
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    transcript_path = input_data.get("transcript_path")
    if not transcript_path:
        sys.exit(0)

    # Check if already blocked this session
    lockfile = lockfile_for_session(transcript_path)
    if lockfile.exists():
        sys.exit(0)

    # Get last assistant content
    content = get_last_assistant_content(transcript_path)
    if not content:
        sys.exit(0)

    # Check for shortcut phrases
    found, matched_phrase = check_for_shortcuts(content)

    if found:
        # Create lockfile — disarm for the rest of this session
        LOCKFILE_DIR.mkdir(parents=True, exist_ok=True)
        lockfile.write_text(matched_phrase)

        blocking_message = f'''SHORTCUT DETECTED: phrase "{matched_phrase}" found in assistant response.

This may indicate Claude is abandoning an approach without proper debugging.
If this is a false positive, tell Claude to continue. Otherwise, ask Claude to explain what went wrong before changing approach.'''

        output = {
            "decision": "block",
            "reason": blocking_message,
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
