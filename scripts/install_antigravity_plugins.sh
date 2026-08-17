#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/install_antigravity_plugins.sh [--validate-only]

Validate the Antigravity-compatible plugins in this repository, then install
them into the local agy configuration.

Options:
  --validate-only  Only run plugin validation
  -h, --help       Show this help
EOF
}

validate_only="false"

while (($# > 0)); do
    case "$1" in
        --validate-only)
            validate_only="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
mapfile -t plugin_names < <(
    python3 - "$repo_root" <<'PY'
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
marketplace = json.loads(
    (repo_root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
)
for entry in marketplace["plugins"]:
    plugin_root = repo_root / entry["source"]
    if any((plugin_root / "skills").glob("*/SKILL.md")):
        print(entry["name"])
PY
)

for plugin_name in "${plugin_names[@]}"; do
    agy plugin validate "$repo_root/plugins/$plugin_name"
done

if [[ "$validate_only" == "true" ]]; then
    exit 0
fi

for plugin_name in "${plugin_names[@]}"; do
    agy plugin install "$repo_root/plugins/$plugin_name"
done

echo "Start a new agy session to load the installed plugins."
