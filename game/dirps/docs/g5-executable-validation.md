# DIRPS Scenario 01 — G5 executable-mechanic evidence

This is the durable G5 execution contract for the first bounded executable DIRPS mechanic.

- Baseline: accepted/merged G4 PR #175
- G4 accepted head: `3d8bdc0db0c4a63369e5cc51793f5c6c46d94fdb`
- G4 merge SHA: `bd24f5edc757769fe6ec1aa1ad5c9c36db7e2654`
- G5 branch base: `8af5689a8c5144949e0f9e5e1fd389891425df6c`
- DODGE version: `0.2.1`
- DODGE revision pinned by TheFountain CI: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- Runtime: `tools/dirps_runtime.py`
- Resolved input: `dirps-resolved-game.v1`
- Result identity: `dirps-execution-result.v1`
- G6 status: intentionally not claimed

## Bounded mechanic

G5 implements exactly one executable path:

```text
attempt-skill
→ success-roll
→ supplied 3d6 evidence
→ compare total <= effective target
→ success/failure + margin
```

The runtime does not execute social/reaction resolution, environmental consequences, attack/defense/damage, recovery, scenario completion, or any target/UI behavior.

## Authority path

The runtime consumes only the accepted G4 resolved model. It does not reread `scenario.json`, the authored DODGE file, or the sidecar from disk.

The executable authority chain is:

```text
canonical Scenario 01 PC skill value
→ G3-validated DODGE character extension
→ G4 resolved PC character.skills
→ DIRPS proto-sidecar G5 execution binding
→ DIRPS runtime
→ structured result evidence
```

A G5-specific sidecar declaration, `g5_execution_bindings.attempt-skill`, owns the otherwise-missing relationship that DODGE 0.2.1 cannot express first-class:

- action: `attempt-skill`;
- procedure: `success-roll`;
- runtime actor input: `actor_ref`;
- runtime target input: `skill_ref`;
- target source: the selected resolved character skill level;
- effective-target policy: the selected skill level directly;
- modifier policy: unsupported in this bounded slice;
- dice contract: `dice_resolution`;
- result format: `dirps-execution-result.v1`;
- state mutation: none.

This prevents `tools/dirps_runtime.py` from silently inventing the skill → effective-target binding.

## Execution input contract

`execute_attempt_skill(resolved, actor_ref=..., skill_ref=..., dice_terms=...)` requires:

1. `resolved.format == dirps-resolved-game.v1`;
2. the declared G5 execution binding;
3. `attempt-skill` available in the resolved scenario;
4. resolved `attempt-skill.procedure_ref == success-roll`;
5. the actor present in the resolved scene;
6. the accepted `actor-conscious` condition to allow the action;
7. an explicit resolved character skill value for `skill_ref`;
8. the exercised `dice_resolution` contract;
9. supplied ordered die terms satisfying that contract.

No uncontrolled RNG is used.

No modifier/default/derived-value input is accepted. If such semantics become required, they must be added at the proper source/proto/resolver boundary before runtime support.

## Dice and outcome contract

The executable `dice_resolution` proto contract remains:

- kind: `dice-pool`;
- count: 3;
- sides: 6;
- combine: `sum`;
- comparator: `lte` against `effective-target`;
- outputs include `rolled_terms`, `total`, `success`, and `margin`.

For the bounded success roll:

```text
total = sum(three supplied d6 terms)
success = total <= effective_target
margin = effective_target - total
```

The runtime derives the count/sides/comparator contract from the resolved sidecar. The DIRPS semantic profile guards the exact G5 executable proto contract and refuses drift.

## Structured result / trace

`dirps-execution-result.v1` preserves:

- actor and selected skill inputs;
- action ref;
- procedure ref;
- effective target;
- explicit supplied die terms;
- die total;
- success/failure;
- margin;
- action source ref + authority;
- procedure source ref + authority;
- referenced source identity/provenance;
- empty `state_delta` for this non-mutating mechanic.

The result does not copy external rules prose. Stable semantic/source identities are sufficient traceability.

## Determinism and bounded replay

`replay_attempt_skill(resolved, record)` re-evaluates one recorded result from:

- the same resolved model;
- recorded actor/skill inputs;
- recorded die terms.

It compares the recomputed structured result with the supplied record and raises a visible divergence error if any recorded target/result/trace field is inconsistent.

This is **single-record re-evaluation**, not an immutable session/replay-history system.

## Tests

`tests/test_dirps_runtime.py` proves:

1. known success: Tracking 12 + dice `[2,3,4]` → total 9, success, margin +3;
2. known failure: Tracking 12 + dice `[5,5,5]` → total 15, failure, margin -3;
3. identical inputs/evidence produce byte-equivalent Python structured results;
4. changed die evidence changes total/outcome appropriately;
5. authoritative skill-value perturbation is made through the proper source + DODGE extension → G4 resolver path and changes runtime outcome;
6. the runtime does not mutate the resolved model;
7. wrong die count fails;
8. out-of-range die terms fail;
9. unavailable action fails;
10. drift in the declared G5 execution binding fails;
11. wrong/missing action→procedure binding fails;
12. missing selected skill target fails;
13. unconscious actor cannot execute `attempt-skill`;
14. malformed executable dice semantics fail visibly;
15. record replay succeeds when consistent and detects tampered result evidence.

The positive test emits a named CI evidence line:

```text
PASS dirps/scenario-01: executable attempt-skill -> success-roll
```

## Proto maturity after G5

G5 provides actual runtime evidence for these concepts, so they move from `suspected` to `exercised`:

- `dice_resolution` — the declared 3d6 pool/comparator/output contract is executed;
- `procedure_context` — named actor/skill/random inputs and target/result outputs are required by the bounded procedure;
- `actor_character_model` — runtime consumes the resolved character skill binding;
- `skill_model` — one explicit resolved skill level is executed as a target;
- `resolution_trace` — structured action/procedure/target/random/result/source evidence is emitted.

They remain `not-yet-candidate`. One DIRPS-private executable shape is not sufficient evidence for a reusable DODGE proposal.

These remain `suspected`:

- `derived_values` — no derived target or modifier formula executes;
- `expressions`;
- `lookup_tables`;
- `reaction_timing`;
- `visibility_and_secret_state`;
- `replay_session_history` — one-record re-evaluation is not immutable session history.

## Explicit remaining gaps

G5 does not implement:

- situational modifiers or derived/effective-target formulas;
- skill defaults/governing-attribute derivation;
- random-number generation;
- full replay/session history;
- attack/active defense/damage/injury;
- recovery state transitions;
- social/reaction resolution;
- environmental consequence resolution;
- deterministic scenario win/loss;
- Web/debug/PnP/TTS targets;
- target manifests.

The next work must remain separate from this PR. G6 starts only after independent G5 acceptance.
