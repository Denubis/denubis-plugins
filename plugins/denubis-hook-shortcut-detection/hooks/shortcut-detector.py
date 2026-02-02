#!/usr/bin/env python3
"""
Stop hook that detects shortcut phrases in Claude's assistant messages.

Reads a transcript file and checks the last assistant message for phrases
that indicate Claude is taking shortcuts rather than debugging properly.

Loop prevention:
- After blocking, skip the next assistant message (Claude re-explaining)
- Re-arm after user sends a message (user stop)
"""
import json
import re
import sys
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
]

# Medium-signal phrases - context-dependent but worth flagging
MEDIUM_SIGNAL_PHRASES = [
    r"instead of",
    r"easier to",
    r"more efficient",
    r"more straightforward",
]

# Combine all patterns
ALL_PHRASES = HIGH_SIGNAL_PHRASES + MEDIUM_SIGNAL_PHRASES

# State file to track blocking state
STATE_FILE = Path("/tmp/shortcut-detector-state.json")


def load_state() -> dict:
    """Load state from file."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_state(state: dict) -> None:
    """Save state to file."""
    try:
        STATE_FILE.write_text(json.dumps(state))
    except OSError:
        pass


def clear_state() -> None:
    """Clear state file."""
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except OSError:
        pass


def count_messages(transcript_path: str) -> tuple[int, int, str | None]:
    """Count assistant and user messages, return last assistant content.

    Returns (assistant_count, user_count, last_assistant_content)
    """
    assistant_count = 0
    user_count = 0
    last_assistant_content = None

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    msg_type = entry.get("type")

                    if msg_type == "assistant":
                        assistant_count += 1
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
                    elif msg_type == "human":
                        user_count += 1
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, PermissionError, OSError):
        pass

    return assistant_count, user_count, last_assistant_content


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

    # Get message counts and last assistant content
    assistant_count, user_count, content = count_messages(transcript_path)
    if not content:
        sys.exit(0)

    # Load state
    state = load_state()
    blocked_at_assistant = state.get("blocked_at_assistant")
    blocked_at_user = state.get("blocked_at_user")

    # Check if we're in cooldown (blocked recently)
    if blocked_at_assistant is not None:
        # We blocked when there were N assistant messages
        # Skip if this is the immediate next assistant message (N+1)
        # AND user hasn't sent a new message yet (user count same as when we blocked)
        if assistant_count == blocked_at_assistant + 1 and user_count == blocked_at_user:
            # Claude is re-explaining, skip but keep state for re-arm check
            sys.exit(0)

        # User has sent a message (user_count > blocked_at_user) - re-arm
        clear_state()

    # Check for shortcut phrases
    found, matched_phrase = check_for_shortcuts(content)

    if found:
        # Save state: record when we blocked
        save_state({
            "blocked_at_assistant": assistant_count,
            "blocked_at_user": user_count,
        })

        blocking_message = f'''SHORTCUT DETECTED: "{matched_phrase}"

Before changing approaches, you must:
1. Explain what specific error or problem you encountered
2. Describe what you tried to fix it
3. Explain why the original approach fundamentally cannot work
4. Ask the user explicitly: "Do you approve changing to [new approach]?"

Do not proceed until you have done the above and received user approval.'''

        output = {
            "decision": "block",
            "reason": blocking_message,
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
