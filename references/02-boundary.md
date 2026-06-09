# Boundary

## Purpose

Turn an intake-stage `TaskState` into a boundary decision. This skill decides whether the task is answerable now, what must not be claimed, what risk level applies, whether current/source verification is required, and which complexity tier should drive the later chain.

It is a judge, not an author. Do not answer the user, generate the clarification question, browse the web, execute tools, or call downstream skills.

## Contract

Use `../_shared/taskstate.schema.json` as the only machine contract for `intent`, `taskTypes`, `domains`, uncertainty levels, `riskLevel`, `complexityTier`, boundary output fields, and free-text language rules. `../_shared/vocab.md` is commentary only. Do not invent alternate enum values or output fields.

Input:

```json
{
  "userMessage": "",
  "conversationContext": "",
  "availableTools": [],
  "intake": {
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
}
```

Output JSON only:

```json
{
  "canAnswerDirectly": true,
  "needClarification": false,
  "needTool": false,
  "needWebCheck": false,
  "needSourceCheck": false,
  "riskLevel": "low",
  "complexityTier": "low",
  "truthConstraints": [],
  "uncertainClaims": [],
  "sourceConflicts": [],
  "responseConstraints": [],
  "structuredConstraints": []
}
```

Allowed values:

```text
riskLevel: low | medium | high
complexityTier: low | medium | high
```

Enum values and JSON keys must stay ASCII. Free-text fields such as `truthConstraints`, `uncertainClaims`, and `responseConstraints` must follow the user's language.

## Workflow

### 1. Inherit Intake Blocks

First inspect intake uncertainty:

```text
if any uncertainPoints.level == "A":
  needClarification = true
  canAnswerDirectly = false
```

A-level gaps block direct answering when they affect the task object, target action, safety-relevant execution, external action, final answer direction, or professional judgment.

B-level gaps usually do not block:

```text
if only B/C gaps exist:
  canAnswerDirectly = true
  add explicit assumptions to truthConstraints or uncertainClaims
```

Do not convert every missing preference into a blocker. Missing laptop use-case, resignation letter company details, or coding environment can often be handled by assumptions.

### 2. Laziness Anchor: Classify Risk by Actual Task, Not Keywords

Risk follows what the user is asking the assistant to do, not topic words inside the sentence.

```text
medical diagnosis, medication, triage, health action advice -> high
legal rights, liability, contract conclusion, compliance advice -> high
financial investment, asset allocation, return promises, trading advice -> high
academic cheating, exam/essay ghostwriting, fabricated citations -> high
credential bypass, evasion, unauthorized access, policy circumvention -> high
privacy-sensitive personal data handling -> high
code execution, system operation, debugging with environment changes -> medium
consumer purchase recommendation with current prices/models -> medium
fact claims involving dates, rankings, versions, public figures, policy, data -> medium
ordinary translation, rewriting, stable explanation, simple calculation -> low
```

Keyword precision rule:

```text
"medical device document grammar" is language analysis, not medical advice.
"invest time learning Python" is planning, not financial advice.
```

If a sensitive word appears only as subject matter and the requested action is harmless analysis, do not escalate to high. Add a narrow truth constraint such as "only analyze language" if useful.

### 3. Decide Web or Source Verification

Set `needWebCheck=true` when the answer depends on information that may have changed or must be sourced:

```text
latest/current/today/now/recent
prices, product models, exchange rates, rankings, versions, laws, policies
specific public facts after the model knowledge cutoff
third-party book/chapter/article existence if no source text is provided
statistics, GDP, market data, official announcements
```

Set `needSourceCheck=true` when the task depends on a source text, book chapter, attached file, citation, dataset, or quoted material whose existence/content has not been provided or verified. This can be true even when `needWebCheck=false`.

Set `needWebCheck=false` for stable knowledge:

```text
basic arithmetic
general programming concepts
stable CSS/Python patterns
translation or rewriting of provided text
debugging from provided code/logs where web is optional
```

If source text is required but absent, set `needSourceCheck=true`, put it in `uncertainClaims`, and usually set `canAnswerDirectly=false` only when it blocks the task.

Set `sourceConflicts` only when the input contains conflicting sources or claims. If no conflicting sources are provided, keep `sourceConflicts=[]`; do not invent conflict analysis.

### 4. Set Answerability

Use this order:

```text
if high-risk request asks for unsafe/professional final action:
  canAnswerDirectly = false
  responseConstraints include refusal or safe-completion direction
elif A-level intake gap blocks the task:
  canAnswerDirectly = false
  needClarification = true
elif source text/data is essential and unavailable:
  canAnswerDirectly = false
  needClarification = true
else:
  canAnswerDirectly = true
```

High-risk does not always mean no answer. Legal/medical/financial text can sometimes be analyzed if framed as non-professional, limited, and caveated:

```text
contract snippet interpretation -> canAnswerDirectly=true with limitations
chest pain medication advice -> canAnswerDirectly=false, urgent-care safety direction
essay ghostwriting -> canAnswerDirectly=false, offer outline/research help
```

### 5. Create Truth Constraints

`truthConstraints` are read-only constraints for all later modules. They preserve the user's intent and stop hallucinated certainty.

Add constraints for:

```text
do not change user goal or target
do not invent missing code environment, source text, API, price, stock, citation, contract context
do not claim current facts without verification
do not provide professional medical/legal/financial conclusions
do not execute or publish external actions before confirmation
do not provide bypass/evasion instructions
keep analysis limited to the provided text when domain keywords are incidental
```

Use concrete constraints, not vague morality. Good:

```text
"do not invent pandas 3.0 APIs"
"do not assume package manager or OS"
"do not change the original meaning of the resignation letter"
"do not send/publish anything without object, channel, and recipient confirmation"
```

### 5b. Formalize Conditional Negations

When `truthConstraints` or `responseConstraints` contain natural-language conditionals, convert the machine-checkable part into `structuredConstraints`.

Detection cues:

```text
unless / except / if not / without / otherwise
除非 / 否则 / 如果不 / 除了
```

Patterns:

```text
"除非 A, 否则不要 B"
  -> {type:"conditional", condition:"not A", description:"不做B", action:"prohibit", source:"boundary"}

"if not X, fall back to Y"
  -> {type:"conditional", condition:"not X", description:"回退到Y", action:"allow", source:"boundary"}

"只在 Z 的情况下才可以 W"
  -> {type:"conditional", condition:"Z", description:"可以做W", action:"allow", source:"boundary"}
```

Rules:

```text
1. Keep the natural-language constraint in truthConstraints for compose 6c.
2. Add the structured version to structuredConstraints for execution-control.
3. Do not replace one with the other; the same constraint can exist in both forms.
4. If the condition boundary cannot be made explicit, do not force structure.
```

### 6. Mark Uncertain Claims

Put claims in `uncertainClaims` when they must not be treated as known facts:

```text
current product/model/price/exchange rate
unverified book, chapter, article, citation, or dataset
future or recently changed software version/API
medical cause or appropriate medication
legal liability or contract enforceability
investment return or product suitability
missing runtime environment details
```

Do not duplicate every assumption. Only include uncertainties that later output must label, verify, avoid, or caveat.

### 7. Set Complexity Tier

Complexity controls the later chain, not the answer length alone.

```text
low:
  stable fact, simple rewrite/translation, single small code request,
  clear input, no high risk, no multi-step strategy

medium:
  debugging, product selection, planning, medium-code/system operations,
  B-level assumptions, current info needed, moderate external consequences

high:
  high-risk medical/legal/financial/academic/safety,
  many dependencies, unclear high-stakes action, long/complex source analysis,
  multi-step downstream toolchain, major design/strategy decisions
```

High risk usually implies `complexityTier=high`. A simple current-fact lookup can be `complexityTier=low` even when `needWebCheck=true`.

### 8. Tool Need

Set `needTool=true` only when an actual tool is needed to complete or verify the task:

```text
web/current facts -> needTool=true if web/search is available
file/screenshot/document analysis -> needTool=true if the file must be read
code execution/test requested or required -> needTool=true
external send/post/install/publish -> needTool=true, but also require confirmation
```

If the task only needs a conceptual answer, keep `needTool=false`.

## Output Rules

- Never include the final answer to the user.
- Never ask the clarification question; only set `needClarification`.
- Never browse or execute tools from inside this skill.
- Preserve intake fields; do not re-label intent/taskTypes unless explicitly testing boundary against malformed intake.
- Prefer fewer, sharper `truthConstraints` over generic lists.
- Use ASCII enum values and user-language free text, per `../_shared/taskstate.schema.json`.

## Self-Check

Before finalizing, verify:

```text
1. Did I classify risk by requested action, not by keyword?
2. Did A-level gaps block answerability, while B/C gaps became assumptions?
3. Did I mark current/changeable facts as needWebCheck?
4. Did I avoid making high-risk professional conclusions?
5. Did I create concrete truthConstraints later modules can enforce?
6. Did I keep simple tasks low complexity?
7. Did I avoid answering the user?
```
