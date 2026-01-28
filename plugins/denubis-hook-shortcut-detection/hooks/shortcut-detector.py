#!/usr/bin/env python3
"""
Stop hook that detects shortcut phrases in Claude's assistant messages.

Reads a transcript file and checks the last assistant message for phrases
that indicate Claude is taking shortcuts rather than debugging properly.
"""
import json
import re
import sys

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


def get_last_assistant_content(transcript_path: str) -> str | None:
    """Read JSONL transcript and extract last assistant message content."""
    last_assistant_content = None

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Look for assistant messages
                    if entry.get("type") == "assistant":
                        message = entry.get("message", {})
                        content_parts = message.get("content", [])
                        # Extract text from content blocks
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
        return None

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
        # Invalid input, allow to proceed
        sys.exit(0)

    transcript_path = input_data.get("transcript_path")
    if not transcript_path:
        # No transcript path, allow to proceed
        sys.exit(0)

    # Get last assistant message content
    content = get_last_assistant_content(transcript_path)
    if not content:
        # No content found, allow to proceed
        sys.exit(0)

    # Check for shortcut phrases
    found, matched_phrase = check_for_shortcuts(content)

    if found:
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

    # No shortcut detected, allow to proceed
    sys.exit(0)


if __name__ == "__main__":
    main()
