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

## Red Lines

- Do not dump a long prose analysis into downstream and ask it to infer structure.
- Do not show machinePayload to the user unless they request it, manual transfer is required, or no machine channel exists.
- Do not skip A-level missing inputs that determine downstream execution.
- Do not let downstream skills revise truth constraints, forbidden items, or hard limits.
- Do not treat downstream skill selection as fixed binding; it is a strategy result for this task.
