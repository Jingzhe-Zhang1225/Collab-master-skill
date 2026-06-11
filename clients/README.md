# Collab Master — cross-client resident gate

This folder makes Collab Master a **resident control layer** that runs in front of every
request, across multiple agent clients — not just Claude. It is the portable counterpart to
the Claude-only `SKILL.md` packaging in the repo root.

## Why this exists

Skills (and Claude Code hooks) are Claude-only mechanisms; they don't load in Codex, OpenCode,
Gemini CLI, etc. The only thing every agent client honors is its **standing-instruction file**
— a plain markdown file it reads each session. The clients differ only in the *filename*. So
we keep one source of truth and fan it out.

## Resident vs on-demand — and why we recommend resident

Collab can run two ways. **If you want it resident (always front), install the client file from
this folder** (see *Install* below). If you skip this and only keep the Claude `SKILL.md`, you
get the on-demand behavior instead.

| | On-demand (skill only) | **Resident (install this folder)** |
|---|---|---|
| When it runs | Only when the harness judges the request "complex enough" to consult the skill | **Every request passes through it first** |
| Simple / borderline tasks | Often skipped — agents deliberately bypass skills for one-step tasks | Still supervised: tone/audience fit, anti-filler, mother-tongue gate, uncertainty marking, constraint-preservation all apply |
| Context awareness | Re-judged per request, blind to it on the turns it doesn't fire | **Always weighs the established user profile + prior constraints**, even on a simple answer |
| Consistency | A "did it trigger this time?" lottery | Uniform — same quality bar on every turn |
| Clients | Claude only | **Cross-client** (Codex / Gemini / OpenCode / …) |
| Cost | Zero overhead on trivial turns; no setup | A small always-on cost (one thin file read per turn) + one-time install |

**Recommended: resident.** The whole point of Collab is *consistent* process control — deciding
when to ask, assume, verify, hand off, or stop. The on-demand path silently drops that control
on exactly the medium and borderline tasks where it matters most (and misses the long tail of
simple turns where prior context should still shape the answer). The resident gate is deliberately
thin, so the per-turn cost is small while supervision becomes uniform and portable across clients.

## The files

| File | Read by | Notes |
|------|---------|-------|
| `AGENTS.md` | Codex, OpenCode, Amp, Zed, Jules, Roo Code … | **Canonical source. Edit this one.** |
| `CLAUDE.md` | Claude Code, Claude.ai | Generated, plain copy |
| `GEMINI.md` | Gemini CLI (and Qwen Code as `QWEN.md`) | Generated, plain copy |
| `.github/copilot-instructions.md` | GitHub Copilot (VS Code) | Generated, plain copy |
| `.cursor/rules/collab-master.mdc` | Cursor | Generated, MDC frontmatter (`alwaysApply: true`) |
| `.windsurf/rules/collab-master.md` | Windsurf | Generated, frontmatter (`trigger: always_on`) |

`AGENTS.md` is the de-facto cross-agent standard and already covers the majority of clients. The
plain copies are byte-for-byte the same gate with a generated header. The two IDE rule files wrap
that same gate body in the frontmatter each tool needs to treat it as an **always-on** rule.

## Install (per client)

Each client reads its standing file at **project level** (repo root) and/or **global level**.
The files already sit at the right relative path inside this folder — copy the matching file (or
subtree) into your target location.

| Client | Project-level | Global-level (applies everywhere) |
|--------|---------------|-----------------------------------|
| Codex / OpenCode | `./AGENTS.md` | usually `~/.codex/AGENTS.md` |
| Claude Code | `./CLAUDE.md` | `~/.claude/CLAUDE.md` |
| Gemini CLI | `./GEMINI.md` | usually `~/.gemini/GEMINI.md` |
| GitHub Copilot | `./.github/copilot-instructions.md` | — (project-level only) |
| Cursor | `./.cursor/rules/collab-master.mdc` | Cursor Settings → Rules (User Rules) |
| Windsurf | `./.windsurf/rules/collab-master.md` | Windsurf → global rules |

Two ways to install:

**A. Standalone** — copy the matching file (for the IDE ones, the whole `.cursor/` / `.windsurf/`
/ `.github/` subtree) into your project. Simplest; good for trying it in one project.

**B. Import into an existing file** — if you already have a `CLAUDE.md` / `AGENTS.md` / etc. with
your own content, don't overwrite it. Append an import line instead so your file pulls the gate in:

```
# Claude Code  (in your CLAUDE.md)
@/absolute/path/to/collab-master-skill/clients/CLAUDE.md

# Gemini CLI   (in your GEMINI.md)
@/absolute/path/to/collab-master-skill/clients/GEMINI.md
```

(Codex/OpenCode read nested `AGENTS.md` files automatically; placing one at project root is
enough. Cursor/Windsurf auto-load every rule file in their rules directory.)

**Windsurf size note:** Windsurf caps rule files (~6–12K chars depending on version); this gate is
~7K. If your Windsurf version truncates it, trim §5 or split the gate into two rule files.

## Deep modules

The gate is **self-contained** for trivial/standard tasks — it needs nothing else. For **deep**
or **composite** tasks it will try to load the method modules in `../references/`. Keep the full
`collab-master-skill` folder intact and reachable from where you install the gate, and the agent
will load only the modules a given task needs. If the modules aren't present, the gate degrades
gracefully and still applies its inline summary.

## Maintaining

`AGENTS.md` is the single source of truth. After editing it, regenerate the copies:

```
pwsh ./sync-clients.ps1     # Windows / PowerShell
./sync-clients.sh           # macOS / Linux
```

Never hand-edit a generated file (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`,
`.cursor/rules/collab-master.mdc`, `.windsurf/rules/collab-master.md`) — your changes will be
overwritten on the next sync. Edit `AGENTS.md` only.
