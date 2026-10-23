#!/usr/bin/env bash
#
# install.sh — set up shila-hunt-bugs
#
#   1. copies every skill (Skills/<category>/<name>/SKILL.md) into ~/.claude/skills/,
#      preserving the <category>/<name>/ layout;
#   2. links the `shila` workflow launcher onto your PATH (~/.local/bin by default).
#
# Usage:
#   ./install.sh                         # skills + shila launcher
#   ./install.sh --no-shila              # skills only
#   CLAUDE_SKILLS_DIR=/path ./install.sh # custom skills dir
#   SHILA_BIN_DIR=/path ./install.sh     # custom dir for the shila launcher
#
set -euo pipefail

NO_SHILA=0
[[ "${1:-}" == "--no-shila" ]] && NO_SHILA=1

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

# --- shila launcher -------------------------------------------------------
install_launcher() {
  local src="$SCRIPT_DIR/workflow/shila"
  local bin="${SHILA_BIN_DIR:-$HOME/.local/bin}"
  local dst="$bin/shila"

  if [[ ! -f "$src" ]]; then
    echo "  (workflow/shila not found — skipping launcher)"
    return 0
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "  ⚠ python3 not found — shila needs it at runtime. Link skipped."
    return 0
  fi
  chmod +x "$src" 2>/dev/null || true
  mkdir -p "$bin"

  if [[ -e "$dst" || -L "$dst" ]]; then
    if [[ "$(readlink -f "$dst" 2>/dev/null || true)" == "$(readlink -f "$src" 2>/dev/null || true)" ]]; then
      echo "  shila already linked: $dst"
    else
      echo "  ⚠ $dst already exists and isn't ours — leaving it untouched."
      echo "    To use this one instead:  ln -sf \"$src\" \"$dst\""
      return 0
    fi
  else
    ln -s "$src" "$dst"
    echo "  linked: shila -> $dst"
  fi

  case ":$PATH:" in
    *":$bin:"*) : ;;
    *)
      echo "  note: $bin is not on your PATH yet. Add it, then reopen your shell:"
      echo "        echo 'export PATH=\"$bin:\$PATH\"' >> ~/.bashrc   # or ~/.zshrc"
      ;;
  esac
}

if [[ "$NO_SHILA" -eq 0 ]]; then
  echo
  echo "Setting up the shila launcher:"
  install_launcher
  echo
  echo "Try:  shila help      (then e.g.  shila hunt acme acme.com )"
fi
