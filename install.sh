#!/usr/bin/env bash
#
# install.sh — copy the curated bug-bounty skills into ~/.claude/skills/
#
# Each skill lives at Skills/<category>/<name>/SKILL.md in this repo. This
# script copies every such skill folder into the user's personal Claude
# skills directory, preserving the <category>/<name>/ layout. Existing skills
# with the same path are overwritten; other skills are left untouched.
#
# Usage:
#   ./install.sh                 # install to ~/.claude/skills
#   CLAUDE_SKILLS_DIR=/path ./install.sh   # install to a custom directory
#
set -euo pipefail

# Resolve the directory this script lives in, so it works from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/Skills"
DEST_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "error: Skills/ directory not found at $SRC_DIR" >&2
  exit 1
fi

echo "Installing skills from: $SRC_DIR"
echo "Destination:            $DEST_DIR"
echo

mkdir -p "$DEST_DIR"

count=0
# Find every skill folder (one containing a SKILL.md) and copy it over,
# keeping the <category>/<name>/ path relative to Skills/.
while IFS= read -r skill_md; do
  skill_dir="$(dirname "$skill_md")"
  rel="${skill_dir#"$SRC_DIR"/}"          # e.g. web/shilahunter-xss
  target="$DEST_DIR/$rel"
  mkdir -p "$target"
  cp "$skill_md" "$target/SKILL.md"
  echo "  installed: $rel"
  count=$((count + 1))
done < <(find "$SRC_DIR" -type f -name SKILL.md | sort)

echo
echo "Done. Installed $count skill(s) into $DEST_DIR"
