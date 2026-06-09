# Intake

## Purpose

Turn a user message into the intake portion of `TaskState`. This skill is a pure parser: it understands what the user is trying to do, what context is present or missing, and which uncertainties block the next step.

Do not answer the user, optimize the prompt, classify risk, browse the web, or make safety/legal/medical judgments. Those belong to later modules.

## Contract

All `intent` / `taskType` / `domain` values, output fields, and language rules come from `../_shared/taskstate.schema.json`, the only machine contract. `../_shared/vocab.md` is human-readable commentary only. Never use a value or field not registered in the schema.

Input may include:

```json
{
  "userMessage": "",
  "conversationContext": "",
  "userProfile": {},
  "availableTools": [],
  "previousTaskState": {}
}
```

Output a JSON object containing only intake fields:

```json
{
  "intent": "",
  "taskTypes": [
    { "type": "", "role": "primary" }
  ],
  "knownContext": [],
  "missingContext": [],
  "assumptions": [],
  "uncertainPoints": [
    {
      "content": "",
      "level": "A",
      "reason": "",
      "action": "resolve_now"
    }
  ],
  "intentShiftDetected": false,
  "clarificationNeeded": false,
  "composite": false,
  "domains": [],
  "structuredConstraints": []
}
```

Allowed `uncertainPoints.level` values:

```text
A = blocks intent, object, safety-relevant execution, external action, or final answer direction
B = affects quality but a first version can proceed with an explicit assumption
C = low-impact style, naming, formatting, or minor preference
```

Allowed `action` values:

```text
resolve_now | assume_and_mark | defer
```

## Workflow

### 1. Separate Literal Input From Goal

Before assigning labels, ask internally:

```text
What did the user literally say?
What result are they trying to get?
Are those two different?
```

If literal wording says "why" but the real goal is repair, choose `intent=debug`, not `intent=learn`.

### 2. Assign Intent

`intent` MUST be exactly one of the values in `../_shared/taskstate.schema.json` `#/$defs/intent`. Never invent one, never leave it empty.

```text
learn | execute | decide | report | create | debug | explore
```

Map the common confusions (these words are taskTypes, NOT intents; see schema):

```text
"1+1?" / "latest iPhone?"      -> explore  (+ taskType fact-check)
"what is recursion?"           -> learn    (+ taskType explain)   # keeps COACH reachable downstream
"find what's wrong in report"  -> explore  (+ taskType analyze)
"which laptop should I buy"    -> decide   (+ taskType product-select)
"write a resignation letter"   -> execute  (+ taskType write)
"plan a study route"           -> execute  (+ taskType plan)
```

If the result is genuinely ambiguous, pick the **best-guess** intent AND set `clarificationNeeded=true`. Never output an empty intent.

Use `intentShiftDetected=true` when the current message appears to revise or switch the previous task. For ambiguous phrases like "try another angle", mark it and set `clarificationNeeded=true` unless context makes the target obvious.

### 3. Assign Task Types

`taskTypes` describe the cognitive work, not the user's goal. Return one primary type and optional secondary types:

```json
[
  { "type": "code", "role": "primary" },
  { "type": "analyze", "role": "secondary" }
]
```

Use only the taskTypes listed in `../_shared/taskstate.schema.json` `#/$defs/taskTypeName`. Do not invent compound types.

Domains (`medical / legal / financial / academic / safety / privacy`) are **tags, not taskTypes**. Put them in the `domains` array; the taskType stays a plain operation:

```text
"chest pain, what medicine should I take" -> taskTypes:[advise], domains:[medical]     OK
                                           -> taskTypes:[medical/advise]               BAD (don't slash-join)
```

Do not over-split. If the request is "write a palindrome checker function in Python", use one primary `code` type; do not invent extra types.

### 4. Extract Known Context

Put user-provided facts, files, code, text, constraints, goals, audience hints, and prior conversation anchors into `knownContext`.

Keep source visible:

```text
from current message: "budget 7000"
from attached code: "loop over dataframe rows"
from previousTaskState: "user wants a presentation outline"
```

Do not move guesses into `knownContext`. Guesses go into `assumptions`.

### 5. Find Missing Context

Add missing information only when it matters. Do not punish a clear request for missing nice-to-have details.

Mark as missing when the absent item is needed to identify:

```text
the object: "this/it/this report" with no recoverable referent
the target action: "send it out" without channel/recipient/content
the target language: translation request with no source or target language
the topic: "make a PPT" without theme
the task boundary: "try another angle" without knowing which prior direction to change
```

Do not mark as missing:

```text
style preferences when a reasonable default works
implementation environment for common debug questions, unless it blocks the first diagnostic step
optional details like title tone, exact length, or color preference
```

### 5b. Merge Structured Constraints

When `previousTaskState.structuredConstraints` exists, merge it with new constraints extracted from the current message. This prevents early user constraints from decaying across later turns.

Extract current-message constraints into schema-defined `structuredConstraint` objects:

```text
"不要动结构" -> {type:"forbidden", description:"不修改文档结构", source:"round-N"}
"保留专业术语" -> {type:"required", description:"保留专业术语", source:"round-N"}
"除非超过5000字，否则不要分章" -> {type:"conditional", description:"超过5000字才分章", condition:"字数>5000", action:"allow", source:"round-N"}
```

Merge rules:

```text
same semantic description as an old constraint:
  update source to the latest round and preserve the original type

new constraint conflicts with an old constraint:
  keep both entries, set old.status="deprecated", set new.status="active"

otherwise:
  append the new constraint; do not overwrite old constraints
```

Key anti-decay case:

```text
If the user says "改一下标题，但不要动结构", keep both:
  - the action target: change title
  - the constraint: do not modify document structure
Do not let the later title-edit request eat the earlier or same-turn structure constraint.
```

### 6. Create Assumptions

Use assumptions for B/C uncertainty that can be handled without stopping:

```text
[assumption] target audience is general reader
[assumption] code runs in a normal local Python environment
[assumption] rewrite should preserve original meaning
```

Every assumption should correspond to a missing or uncertain point. Do not use assumptions to hide invented facts.

### 7. Classify Uncertainty

Use A/B/C consistently:

```text
A: missing object, missing content, missing recipient/channel for external action,
   severe ambiguity in goal, incomplete medical/legal/financial context if the user asks what to do,
   academic request missing topic/source when direct authorship is requested

B: environment/version/use case affects quality but first pass can proceed,
   product recommendation missing preferences, contract snippet may be incomplete,
   code debug missing OS/package manager

C: tone, length, exact format, title style, naming preference, small visual/style choices
```

Set `clarificationNeeded=true` when any A-level uncertain point has `action=resolve_now`.

### 8. Detect Intent Drift

Compare `userMessage` with `previousTaskState.intent` and the prior goal:

```text
"No, I actually meant..." = goal correction inside same task
"Try another angle" = possible correction; ask what to change unless context is obvious
new unrelated topic = intent drift; reset downstream state
```

When drift is detected, do not carry stale assumptions into the new TaskState.

### 9. Flag Composite & Keep Language

Set `composite=true` when the request is "do A and produce B" (e.g. "analyze this book and make a PPT", "research the trend and draw a chart"). Put any domain tags in `domains`. Leave the downstream tool type to strategy/6d; intake only raises the flag.

Keep extracted snippets and other free-text fields in the user's own language: if the user writes Chinese, `knownContext` / `missingContext` / `assumptions` / `uncertainPoints.content` entries stay Chinese. Only field names and enum values follow vocab (ASCII).

## Hard Stop Rule

Set `clarificationNeeded=true` when:

```text
there is at least one A-level uncertainty that blocks the object, goal, or action
or assumptions count > 3 and at least one is A-level
or previous task context is required but unavailable
```

The output should identify the blocking uncertainty, but should not generate the actual user-facing question unless the test explicitly asks for it.

## Boundary Separation

This skill may label domains such as `medical`, `legal`, `financial`, `academic`, `safety`, or `privacy`, and task types such as `system-operation` when they describe the task. It must not decide:

```text
riskLevel
needWebCheck
needTool
canAnswerDirectly
truthConstraints
uncertainClaims
complexityTier
refusal / safety response
```

Those fields belong to boundary. If a mock row expects medical/legal/financial risk, intake should only surface the relevant intent, task type, missing context, and uncertainty level.

## Output Rules

- Keep field names stable.
- Prefer empty arrays over missing array fields.
- Use `clarificationNeeded=false` for clear negative controls.
- Do not add explanatory prose unless the caller asks for analysis.

## Self-Check

Before finalizing, check:

```text
Did I use an intent or taskType not defined in _shared/taskstate.schema.json?  (intent must be one of the schema values)
Did I treat the message as a demand to answer instead of a demand to parse?
Did I confuse intent with taskTypes? (write/plan/advise/fact-check are taskTypes, not intents)
Did I mark optional preferences as A-level blockers?
Did I create risk/web/safety fields that belong to boundary?
Did I slash-join a domain into a taskType (medical/advise)?
Did I carry stale previous context across an intent shift?
```
