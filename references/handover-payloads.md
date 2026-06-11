# Handover Payloads

This reference is loaded only when compose 6d is active.

## Purpose

v1.6 handoff is adaptive:

```text
same upstream material -> selected downstream contract -> adapted payload
```

Do not force every downstream skill to accept `_shared/downstreamPayload.schema.json`. That schema is a stable fallback for `slides`, `diagram`, `document`, and `code`, not the universal interface.

## Registry Flow

1. Read `references/skill-registry.yaml`.
2. Filter candidates by requested `downstreamCapability`.
3. Drop candidates whose `inputContract` is not parseable.
4. Rank by `defaultRank`, capability fit, and explicit user wording.
5. If multiple candidates imply materially different output forms, ask the user to choose. This is the only blocking step.
6. While waiting for user choice, preload candidate contracts from `skillRef` where available.
7. After selection, adapt the same source material into the selected input format.

Never auto-install or run a missing downstream skill. Recommend installation only as a human-visible option.

## Handoff Modes

```yaml
none:
  useWhen: no downstream capability is needed
  output: machinePayload = null

direct-handoff:
  useWhen: one clear candidate, complete inputs, parseable contract
  output: selectedSkill + adapted payload + constraints + trigger

clarify-then-handoff:
  useWhen: A-level missing input blocks downstream execution
  output: hasQuestions=true; machinePayload records blockedByMissingInputs

candidate-selection:
  useWhen: several candidates can satisfy the request but output style/tool semantics differ
  output: human question with default; machinePayload lists candidateSkills

plan-then-handoff:
  useWhen: downstream action is high cost, multi-step, or irreversible
  output: humanContent includes plan; payload waits for confirmation

co-design-handoff:
  useWhen: visual taste or creative direction determines downstream shape
  output: offer 2-3 directions; adapt after user selects
```

## Machine Payload Envelope

Use this envelope inside `compose.machinePayload`.

```yaml
handoffNeeded: true
handoffMode: direct-handoff
downstreamCapability: slides
candidateSkills:
  - id: baoyu-slide-deck
    displayName: baoyu-slide-deck
    capabilities: [slides, presentation]
    bestFor: Professional slide deck images from structured content.
    inputContract:
      kind: native
      format: outline-plus-style-instructions
selectedSkill: baoyu-slide-deck
requiredInputs: []
defaultedInputs:
  - name: visualStyle
    value: professional
    reason: user did not specify style
blockedByMissingInputs: []
payload: {}
downstreamConstraints:
  forbidden: []
  hardLimits: []
  mustInclude: []
  truthConstraints: []
  qualityCriteria: []
downstreamTrigger:
  role: downstream skill executor
  instruction: execute selected payload exactly; do not reinterpret source task
  contractSource: references/skill-registry.yaml
verificationPlan:
  - validate payload against selected input contract when possible
  - check hard limits before dispatch
```

## Force Preflight Before CustomFile Injection (v1.8.3)

Before writing or injecting a `customFile`, run a preflight gate. This is not optional for constrained downstream work.

```yaml
handoffPreflight:
  force1Force3Check:
    passed: true
    checkedAgainst:
      - "templateId=corp-v3"
      - "locked title zones"
      - "reference styleProfile"
    mismatches: []
    resolution: proceed
  force2CapabilityCheck:
    passed: true
    compositionUsed: true
    toolPlan:
      - skillId: reference-deck-parser
        role: preprocessor
        capability: extract-style-profile
        contractFit: adapter-required
      - skillId: html-ppt
        role: renderer
        capability: slides
        contractFit: native
      - skillId: huashu-design
        role: verifier
        capability: design-review
        contractFit: native
    missingCapabilities: []
  injectionDecision: compose-tools
  recommendedInstall: []
  logicChain:
    - "force1 content satisfies locked template and reference grammar"
    - "single renderer cannot score design quality"
    - "compose html-ppt renderer with huashu-design verifier"
```

Rules:

```text
force1Force3Check fails:
  do not query downstream yet; revise force1 or ask user.

force2CapabilityCheck fails:
  do not inject into the selected skill.
  search registry for a better skill or a tool composition.
  if no match exists, ask the user to install/download the missing skill.

Tool composition is allowed:
  parser/preprocessor -> renderer -> verifier/reviewer.
  The final payload must say which tool owns which role.
```

## Fallback Payload

Use `_shared/downstreamPayload.schema.json` only when:

- registry has no better selected contract,
- the chosen registry entry says `inputContract.kind: downstreamPayload`,
- or the platform has no machine channel and the payload must be saved as internal scratch.

The fallback kinds are:

```text
slides | diagram | document | code
```

Unknown kinds intentionally do not pass the fallback schema.

## Reference Deck Payload (v1.8.1)

When the user provides a handmade high-quality PPT/deck as a reference, do not ask the downstream slide skill to invent a generic template. Convert the artifact into a `customFile` with two extra internal fields:

```yaml
referenceArtifact:
  kind: pptx | pdf | image-set | html-deck
  sourceRef: attachment-or-local-path
  usage: style-reference | layout-reference | content-reference
  extractionStatus: pending | extracted | unavailable
  notes: []

styleProfile:
  reusePolicy: interpret-not-copy | strict-template-clone | theme-only
  visualDNA: []
  layoutGrammar: []
  componentPatterns: []
  typography: []
  colorSystem: []
  spacingRhythm: []
  chartRules: []
  imitationBoundaries: []
```

Extraction target:

```text
visualDNA             -> overall deck feel and density
layoutGrammar         -> repeated slide skeletons and hierarchy rules
componentPatterns     -> cards, dividers, callouts, metric strips, image masks
typography            -> type scale, weight rhythm, title/body behavior
colorSystem           -> palette, accent use, background logic
spacingRhythm         -> margins, grid, alignment, breathing room
chartRules            -> how data is visualized and annotated
imitationBoundaries   -> what must not be copied or inferred
```

Default policy is `interpret-not-copy`. Use `strict-template-clone` only when the user owns the source deck or provides a company template and explicitly asks for exact reuse.

`imitationBoundaries` is a hard IP/privacy line, not a soft style note. Every entry must also be copied into `constraints.forbidden` so the verification gate enforces it as an exact-match redline. The styleProfile array alone is advisory; `constraints.forbidden` is what gets checked. Non-empty `imitationBoundaries` → non-empty `constraints.forbidden`.

## Force4 Design Review Payload (v1.8.2)

After a downstream PPT/deck artifact exists, attach an optional `designReview` to the next `customFile` when the user wants improvement or when an artifact review is part of the workflow.

```yaml
designReview:
  enabled: true
  rubric: huashu-ppt
  trigger: artifact-produced | user-dissatisfied | manual-request
  scores:
    - dimension: philosophy_consistency
      score: 7.5
      evidence: "The deck follows the reference mood but loses the editorial opener."
      advice: "Restore one strong opening contrast before the metrics section."
    - dimension: visual_hierarchy
      score: 6.5
      evidence: "Metric cards compete with the page title."
      advice: "Reduce metric card weight and make the slide title the dominant anchor."
  agentSuggestion: "Make the opener more editorial and reduce metric-card visual weight."
  diagnosticChain:
    - "force1 content was valid against force3 constraints"
    - "html-ppt rendered the deck but left placeholder space"
    - "huashu-ppt scoring found weak visual hierarchy"
  influencePolicy: advisory-only | soft-force4 | force4-locked
  appliedToCustomFile: false
```

Policy:

```text
enterprise/render-engine/locked template:
  influencePolicy=advisory-only
  appliedToCustomFile=false
  user sees a change proposal; template and locked zones stay fixed.

personal/co-creator/loose template:
  influencePolicy=soft-force4
  appliedToCustomFile=true
  agentSuggestion may be appended to constraints.softGuidance for the next round.

explicit user approval:
  influencePolicy=force4-locked
  only then may the suggestion become a stronger customFile constraint.
```

## Red Lines

- Do not dump a long prose analysis into downstream and ask it to infer structure.
- Do not show machinePayload to the user unless they request it, manual transfer is required, or no machine channel exists.
- Do not skip A-level missing inputs that determine downstream execution.
- Do not let downstream skills revise truth constraints, forbidden items, or hard limits.
- Do not treat downstream skill selection as fixed binding; it is a strategy result for this task.
- Do not let downstream slide skills invent a style when a reference deck was supplied but not inspected.
- Do not let force4 override user/template constraints; enterprise scenarios receive force4 as advice only unless the user explicitly authorizes template change.
- Do not inject a customFile into a downstream skill that failed force2 capability fit; switch tools, compose tools, or ask for installation.
