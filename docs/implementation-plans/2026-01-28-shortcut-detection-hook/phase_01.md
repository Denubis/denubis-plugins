# Phase 1: Create Plugin Structure and Core Files

## Overview

Create the plugin directory structure and all core files for the shortcut detection hook.

## Tasks

### Task 1A: Create plugin directory structure

Create the following directory structure:

```
plugins/denubis-hook-shortcut-detection/
├── hooks/
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── hooks.json
│   └── shortcut-detector.py
├── README.md
└── LICENSE
```

**Verification:** All directories exist.

### Task 1B: Create plugin.json

Create `plugins/denubis-hook-shortcut-detection/hooks/.claude-plugin/plugin.json`:

```json
{
    "name": "denubis-hook-shortcut-detection",
    "description": "Stop hook that detects shortcut phrases and blocks until user approves approach changes.",
    "version": "1.0.0",
    "author": {
        "name": "Brian Ballsun-Stanton",
        "github": "denubis"
    },
    "homepage": "https://github.com/denubis/denubis-plugins",
    "repository": "https://github.com/denubis/denubis-plugins",
    "license": "CC-BY-SA-4.0",
    "keywords": ["hooks", "shortcuts", "quality"]
}
```

**Verification:** File exists and is valid JSON.

### Task 1C: Create hooks.json

Create `plugins/denubis-hook-shortcut-detection/hooks/hooks.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/shortcut-detector.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Verification:** File exists and is valid JSON.

### Task 1D: Create shortcut-detector.py

Create `plugins/denubis-hook-shortcut-detection/hooks/shortcut-detector.py`:

The script must:
1. Read stdin JSON to get `transcript_path`
2. Read JSONL transcript file
3. Extract last assistant message content
4. Match against phrase patterns (case-insensitive)
5. Output block decision with reason if matched

**High-signal phrases:**
- `let me try a different approach`
- `simpler approach`
- `let's just bail` / `let's bail`
- `for simplicity`
- `to simplify`
- `on second thought`
- `actually,? let me`
- `streamlined`

**Medium-signal phrases:**
- `instead of`
- `easier to`
- `more efficient`
- `more straightforward`

**Blocking message format:**
```
SHORTCUT DETECTED: "[phrase]"

Before changing approaches, you must:
1. Explain what specific error or problem you encountered
2. Describe what you tried to fix it
3. Explain why the original approach fundamentally cannot work
4. Ask the user explicitly: "Do you approve changing to [new approach]?"

Do not proceed until you have done the above and received user approval.
```

**Verification:** Script is syntactically valid Python (`python3 -m py_compile`).

### Task 1E: Create README.md

Create `plugins/denubis-hook-shortcut-detection/README.md` with:
- Plugin name and description
- What it detects (shortcut phrases)
- How it works (Stop hook, transcript reading)
- Installation instructions
- The full list of detected phrases

**Verification:** File exists.

### Task 1F: Create LICENSE

Create `plugins/denubis-hook-shortcut-detection/LICENSE` with CC-BY-SA-4.0 license text.

**Verification:** File exists.

## Phase Completion Criteria

- [ ] All directories created
- [ ] plugin.json is valid JSON
- [ ] hooks.json is valid JSON
- [ ] shortcut-detector.py passes syntax check
- [ ] README.md exists
- [ ] LICENSE exists
