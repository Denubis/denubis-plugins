# ed3d-hook-claudemd-reminder

A Claude Code hook plugin that reminds to update CLAUDE.md files when committing changes.

## What it does

When you run `git status` or `git log`, this hook adds a gentle reminder to consider invoking the `project-claude-librarian` agent if your changes affect contracts, APIs, or domain structure.

## Integration

This hook works with:
- **ed3d-extending-claude:project-claude-librarian** - The agent that reviews changes and updates CLAUDE.md files
- **ed3d-extending-claude:maintaining-project-context** - The skill that defines when and how to update documentation

## Installation

Install via ed3d-plugins.
