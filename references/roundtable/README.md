# Roundtable Operator (LensTable) — v1.5 v0.2

Controlled divergence operator. **Not** multi-agent chat, **not** thinker cosplay. Creates genuine cognitive differences → exposes disagreements → chair synthesizes with discipline.

Runtime isolation: this subtree loads only on full-tier roundtable trigger, never in v1 main chain. Light tier uses roles only, never reads `lenses.yaml`. All internal: lens selection, session reasoning, chair synthesis — never exposed to user (per global principle A).

## Why not just ask several AIs the same question?

Asking multiple AIs without structure produces the appearance of divergence, not the substance. Four failure modes hit every time:

| Naive multi-agent | Roundtable's answer |
|---|---|
| Models trained similarly → tend to agree → fake divergence | Roles have **forbidden zones**: claims outside your domain are invalid, excluded from synthesis |
| No falsification → opinions accumulate, nothing gets tested | `falsificationTest` is **mandatory**: a session without one is invalid, not counted |
| Roles drift — "implementer" starts speaking for users | Domain-crossing enforcement: the round's statement is voided, chair excludes it |
| Aggregation theater — chair just summarizes everyone | Chair must reject proposals, record real disagreements, explain selection reason — empty fields = FAIL |

The structural difference: naive multi-agent produces more text. Roundtable produces genuine disagreement: the chair is required to reject weak proposals (`rejectedIdeas` non-empty), name specific conflicts (`actualDisagreements` non-empty), and explain why the selected direction was chosen over the alternatives (`reasonForSelection` mandatory). If any of these are empty, the roundtable result is invalid.

**Where it sits in collab-master:** Roundtable is not a peer module — it's an escalation path inside solution-space. The normal divergence path runs first; only if it fails (angles too few / no counter-intuitive direction / all same category) does Roundtable open. Most tasks never reach it.

## Trigger (escalation, not peer module)

```
solution-space runs divergenceMode → novelty gate
  PASS → normal compose (no roundtable)
  FAIL (angles < threshold / no counter-intuitive / all same category) → roundtableDecision, open roundtable
```

**Disabled (any one hit → skip):** fact query / simple code fix / user wants speed / clear acceptance criteria / solution-space already produced ≥1 counter-intuitive direction / execution-control token budget insufficient.

**High-risk domains (medical/legal/financial):** lens assists only; boundary and professional judgment take priority. Roundtable must not bypass boundary/safety/source check.

## Two tiers (only these)

```
light: single-model plays 3-4 roles + chair, one round of cross-examination, chair synthesizes. No subagent, saves token. No lens stacking.
full:  independent subagent sessions (each role has isolated context, can wear ≤1 lens), Chair Hub protocol, chair synthesizes.
```

Light consensus collapse (all roles summarizable in one sentence) → auto-upgrade to full or fail. Genuine divergence is only stable in full (isolated contexts).

## Roles (skeleton) + lenses (optional enhancement)

**Roles** (functionally orthogonal, small fixed set, mandatory): `user-advocate / implementer / critic / divergent-thinker / steward (values, ethics, risk) / chair (always present)`. Selected per `divergenceMode` (see `selectors.yaml` `role_sets`), aiming to cover 5 slots (user/system/value/implementation/critique).

Each role has a **domain + forbidden zone** (defined in `selectors.yaml` `role_definitions`, the single source of truth). Forbidden zones are boundary-crossing criteria — this is role-level anti-cosplay, same mechanism as lens `output_obligation`:

- **Enforcement:** a role making claims in another's domain or touching its own forbidden → **that round's statement is invalid**, excluded from chair synthesis.
- Example: `user-advocate` claims "technically this can do X" (crosses into implementer domain) → invalid. `critic` says "this is wrong" without `falsificationTest` → invalid. `divergent-thinker` throws names without `reasoningPath` → invalid.

**Steward entry/skip:** per `selectors.yaml` `steward_triggers / steward_skip` (high-risk domain / automated human decision-making / loaded ethics·politics·eastern lens / downstream audience is external stakeholder → enter; pure tech selection / personal tool / fact query → skip). In high-risk domains steward assists only, boundary rules.

**Lenses** (optional, full tier only): one role session loads ≤1 lens (see `lenses.yaml`) to deepen the analysis frame, e.g. `critic + pre-mortem`, `divergent-thinker + first-principles`. 30 cards across 10 categories, each with `core_question`, `sees`, `ignores`, `default_moves`, `attack_questions`, `output_obligation`, `safety_boundary` (mandatory for politics/ethics/eastern).

## Session protocol

```
1. Load role (mandatory) + optional 1 lens card.
2. Analyze via lens default_moves, find blind spots via attack_questions.
3. Produce roundtableSessionOutput:
   - falsificationTest mandatory and specific
   - must satisfy worn lens's output_obligation (mismatch = didn't actually use the lens = session invalid)
4. No persona voice: "from X lens, the real problem is…" only; banned: "as a X-ist, I think…"
```

## Chair Hub protocol

```
Each session → chair (submit position)
chair → domain-crossing check: per session, check against selectors role_definitions.forbidden
        domain-cross / missing falsificationTest / unmet lens output_obligation → mark invalid, exclude from synthesis
chair → assign 1-2 conflict points, send back for questioning (valid sessions only)
Each session → respond to conflicts
chair → concept dedup + shape dedup → merge/reject → chairOutput
```

Chair is judge, not summarizer: first remove invalid statements, then extract real disagreements, reject weak proposals, retain unresolved disputes, give direction + reason.

**Effective sessions < 3**: no merged conclusion (insufficient sample). Degrade to "list valid perspectives + note why insufficient for synthesis."

## Anti-cosplay hard gates (quality-gate roundtable special, machine-checkable)

**Session level:**
- `output_obligation` unmet → session invalid (strongest gate)
- `falsificationTest` missing or vague → session invalid
- Domain-crossing → that round's statement invalid
- "As an X-ist / X school" persona voice → word-scan FAIL
- `questionsForOthers` generic, not hitting opponent's blind spot → return for revision

**Chair level:**
- `rejectedIdeas` empty / `actualDisagreements` empty / `reasonForSelection` empty → FAIL (fake roundtable)
- ≥3 sessions using the same cognitive shape (drill-down / 2x2 …) → collective collapse → reassign shapes
- All core assumptions summarizable in one sentence → performative roundtable → FAIL

## Safety

`lenses.yaml` entries in politics/ethics/eastern categories must have `safety_boundary` filled and validated: do not promote one ideology as uniquely correct, do not turn analysis into political mobilization, must declare applicable boundaries and blind spots. Lens is an analytical perspective, not a position.

## Output contracts (pending schema registration)

```
roundtableDecision      { enabled, tier: light|full, reasonsMet[], disableReasonsHit[] }
roundtableSessionOutput { role, lens?, mainClaim, reasoningPath[], whatThisSees[], whatOthersMiss[],
                          proposedSolution, biggestRisk, falsificationTest(mandatory), questionsForOthers[],
                          confidence{level,reason} }
chairOutput             { taskRestatement, activeRoles[], candidateIdeas[],
                          actualDisagreements{factual,value,causal,feasibility},
                          rejectedIdeas[](roles≥3 must be non-empty), mergedInsights[],
                          selectedDirection, reasonForSelection(mandatory), unresolvedQuestions[], nextAction }
```

`validate.py lenses` command: each lens card against `lens_schema.json` + each `conflicts_with/compatible_with/selector` id ∈ registry + `reuses_framework` id matches `frameworkName` spelling.

## v0.2 scope

**Done:** 30 lens cards (3/category) + `lens_schema.json` + `selectors.yaml` + Chair Hub + light/full tiers + role forbidden zones + steward triggers + domain-crossing enforcement.

**Not done:** Sparse Ring / Adversarial Pair protocols, graph-based auto-orthogonality, `conflicts_with` auto-exclusion, 80-120 card library.

**Validated:** 3 real-task cases — different roles/lenses produce different judgments ✓, disagreements extractable ✓, weak proposals rejected ✓, outperforms single-agent baseline ✓.
