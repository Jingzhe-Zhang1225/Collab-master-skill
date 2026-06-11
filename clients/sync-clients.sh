#!/usr/bin/env bash
# sync-clients.sh — regenerate all per-client resident-gate files from AGENTS.md (canonical source).
# Usage:  ./sync-clients.sh
# AGENTS.md is the single source of truth; everything below is generated (UTF-8, no BOM).

set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$here/AGENTS.md"
[ -f "$src" ] || { echo "canonical source not found: $src" >&2; exit 1; }

# Canonical body = from the first markdown H1 to EOF (drops the maintainer comment).
body="$(sed -n '/^# /,$p' "$src")"
note="Generated from AGENTS.md - do not edit here. Edit AGENTS.md and run sync-clients.ps1 / .sh."

write_file() {
  local rel="$1" content="$2"
  local full="$here/$rel"
  mkdir -p "$(dirname "$full")"
  printf '%s' "$content" > "$full"
  echo "wrote $rel"
}

# 1) plain copies: HTML-comment header + body
write_file "CLAUDE.md"                       "$(printf '<!-- %s (Claude Code / Claude.ai) -->\n\n%s' "$note" "$body")"
write_file "GEMINI.md"                       "$(printf '<!-- %s (Gemini CLI) -->\n\n%s' "$note" "$body")"
write_file ".github/copilot-instructions.md" "$(printf '<!-- %s (GitHub Copilot) -->\n\n%s' "$note" "$body")"

# 2) Cursor MDC rule: frontmatter must be the very first bytes
write_file ".cursor/rules/collab-master.mdc" \
  "$(printf -- '---\ndescription: Collab Master resident control layer (always on)\nglobs:\nalwaysApply: true\n---\n\n<!-- %s (Cursor) -->\n\n%s' "$note" "$body")"

# 3) Windsurf rule: frontmatter must be the very first bytes
write_file ".windsurf/rules/collab-master.md" \
  "$(printf -- '---\ntrigger: always_on\n---\n\n<!-- %s (Windsurf) -->\n\n%s' "$note" "$body")"

echo "done. AGENTS.md remains the source of truth."
