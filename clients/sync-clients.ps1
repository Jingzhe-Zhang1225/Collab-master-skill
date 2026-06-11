# sync-clients.ps1 — regenerate all per-client resident-gate files from AGENTS.md (canonical source).
# Usage:  pwsh ./sync-clients.ps1
# AGENTS.md is the single source of truth; everything below is generated.
# Writes UTF-8 WITHOUT BOM — a BOM before "---" would break Cursor/Windsurf frontmatter parsing.

$ErrorActionPreference = "Stop"
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $here "AGENTS.md"
if (-not (Test-Path $source)) { throw "canonical source not found: $source" }

# Canonical body = everything from the first markdown H1 onward (drops the maintainer comment).
$lines = Get-Content $source
$match = $lines | Select-String -Pattern '^# ' | Select-Object -First 1
if (-not $match) { throw "no H1 heading found in AGENTS.md" }
$body = ($lines[($match.LineNumber - 1)..($lines.Length - 1)] -join "`n")

$note = "Generated from AGENTS.md - do not edit here. Edit AGENTS.md and run sync-clients.ps1 / .sh."
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-File($relPath, $content) {
  $full = Join-Path $here $relPath
  $dir  = Split-Path -Parent $full
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText($full, $content, $utf8NoBom)
  Write-Output "wrote $relPath"
}

# 1) Plain copies: HTML-comment header + body
$plain = [ordered]@{
  "CLAUDE.md"                       = "Claude Code / Claude.ai"
  "GEMINI.md"                       = "Gemini CLI"
  ".github/copilot-instructions.md" = "GitHub Copilot"
}
foreach ($name in $plain.Keys) {
  Write-File $name ("<!-- $note ($($plain[$name])) -->`n`n" + $body)
}

# 2) Cursor MDC rule: frontmatter (alwaysApply:true) must be the very first bytes
$cursorFm = "---`ndescription: Collab Master resident control layer (always on)`nglobs:`nalwaysApply: true`n---`n`n<!-- $note (Cursor) -->`n`n"
Write-File ".cursor/rules/collab-master.mdc" ($cursorFm + $body)

# 3) Windsurf rule: frontmatter (trigger:always_on) must be the very first bytes
$windsurfFm = "---`ntrigger: always_on`n---`n`n<!-- $note (Windsurf) -->`n`n"
Write-File ".windsurf/rules/collab-master.md" ($windsurfFm + $body)

Write-Output "done. AGENTS.md remains the source of truth."
