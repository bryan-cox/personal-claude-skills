#!/usr/bin/env bash
# Symlink skills into ~/.agents/skills and ~/.claude/skills so
# that Pi, OpenCode, GitHub Copilot CLI, and Claude Code all discover them.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DESTS=("$HOME/.agents/skills" "$HOME/.claude/skills")

for DEST in "${DESTS[@]}"; do
  mkdir -p "$DEST"
done

# Find all skill directories containing SKILL.md under plugins/
find "$REPO/plugins" -type f -name "SKILL.md" | while read -r skill_file; do
  skill_dir="$(dirname "$skill_file")"
  name="$(basename "$skill_dir")"

  for DEST in "${DESTS[@]}"; do
    target="$DEST/$name"
    if [ -e "$target" ] || [ -L "$target" ]; then
      rm -rf "$target"
    fi
    ln -sfn "$skill_dir" "$target"
    echo "linked: $name -> $skill_dir in $DEST"
  done
done
