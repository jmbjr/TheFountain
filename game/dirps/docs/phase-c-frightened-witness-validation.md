# DIRPS Scenario 01 — Phase C Frightened Witness social evidence

This is the durable evidence contract for **Phase C — Frightened Witness social encounter** from TheFountain issue #178.

Phase C is gameplay expansion inside the accepted **G6 — Targeted** implementation. It does not claim G7.

- Fresh branch base/current main at start: `7a65f2c8669e4d7bd10f99f5c40cf626ead57444`
- Accepted Phase B PR: #180
- Phase B accepted head: `5d6e8371f4cd5c94e8502d1bf6e08b746df590e5`
- Phase B merge SHA: `086a5e6f94708ab557fcf59f2281d2f37c598a01`
- DODGE version: `0.2.1`
- DODGE revision pinned by TheFountain CI: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- Resolved model: `dirps-resolved-game.v1`
- Reaction record: `dirps-reaction-result.v1`
- Social encounter record: `dirps-social-encounter-result.v1`
- Target view: `dirps-debug-social-target.v1`
- Gameplay roadmap: #178
- Maturity tracker: #163

## Phase C playable slice

The bounded social path is:

```text
fresh witness runtime state
→ Frightened Witness exposes reassure-and-question
→ roll 3d6
→ apply source-owned reaction modifier
→ classify modified total through authoritative Reaction Table
→ select canonical information consequence
→ apply normalized DODGE set effects
→ preserve reaction evidence + before/after state + state delta
→ debug target displays the same runtime-owned result
```

This path is materially different from Phase A/B success-roll resolution:

- there is no target number;
- higher modified totals are better;
- the outcome is an eight-band table lookup rather than success/failure comparison.

Phase C intentionally stops after resolving Frightened Witness. It does not auto-progress into Washed-Out Path.

## External rule authority

The authoritative rules source remains GURPS Lite, June 2003.

Phase C uses its Reaction Rolls / Reaction Table rules:

- a reaction roll uses 3d6;
- reaction modifiers apply directly to the roll;
- higher totals are better;
- requests for information are an ordinary use of reaction rolls;
- the modified total is classified through the Reaction Table.

Stable source locators used by the sidecar/runtime trace:

- `p. 3, Reaction Rolls`;
- `p. 3, Reaction Modifiers`;
- `p. 3, Reaction Table`.

The authoritative table is normalized in the DIRPS sidecar as:

```text
<= 0    disastrous
1..3    very-bad
4..6    bad
7..9    poor
10..12  neutral
13..15  good
16..18  very-good
>= 19   excellent
```

The runtime reads this table. It does not duplicate the thresholds in Python.

## Scenario authority

Canonical Scenario 01 owns the provisional social-gameplay facts.

Encounter:

`frightened-witness`

Action:

`reassure-and-question`

The action binds directly to the authoritative DODGE `reaction-roll` procedure.

Scenario 01 also owns one prototype approach modifier:

```text
reassuring-approach
amount: +1
authority: provisional
provenance: prototype_assumption
rule authority: gurps-lite / p. 3 Reaction Modifiers
```

The +1 is a Scenario 01 judgment that this bounded approach qualifies as a “good approach.” It is not represented as a universal GURPS constant.

The semantic validator therefore checks modifier type/source/provenance/rule authority but does not hard-code the numeric amount. Perturbing the canonical modifier changes the resolved reaction outcome.

## Social consequences

Canonical Scenario 01 also owns the information consequence for each reaction category.

The specific reaction category is preserved in neutral state.

Information is grouped into three scenario results:

```text
disastrous / very-bad / bad / poor
→ no-useful-account

neutral
→ partial-account

good / very-good / excellent
→ useful-lead
```

Each category has its own player-readable information text.

The canonical consequence mapping is the authority. Sidecar consequence effect refs are validated against that canonical mapping so the sidecar cannot silently become a second story source.

## DODGE normalization

Phase C uses standard DODGE 0.2.1 state/effect semantics.

Added scenario-owned values:

- `frightened-witness-status`;
- `frightened-witness-reaction`;
- `frightened-witness-information`.

Added DODGE procedure:

- `reaction-roll` — authoritative / `gurps-lite`.

Added normalized `set` effects for:

- resolved witness status;
- all eight reaction categories;
- the three information-result values.

To preserve the accepted Phase B encounter record, Phase C does **not** expand `scenario-01-initial`.

Instead it uses a bounded separate neutral snapshot:

`runtime_states.scenario-01-frightened-witness-initial`

Initial witness state:

```text
status      = ready
reaction    = unresolved
information = unknown
```

This keeps Phase B’s accepted `dirps-encounter-result.v1` before/after state stable while Phase G remains responsible for whole-scenario state/progression unification.

## Proto gap exercised: lookup tables

DODGE 0.2.1 has no first-class executable value-range lookup semantic.

Phase C is the first concrete DIRPS execution need for that gap.

`lookup_tables` advances:

```text
suspected → exercised
```

It remains:

`candidate_for_dodge: not-yet-candidate`

The exercised bounded shape is:

```text
key_ref
rows:
  when: { min, max }
  value
fallback
```

Phase C table:

`phase_c_lookup_tables.gurps-lite-reaction-table`

The table is target-neutral, resolver-preserved, runtime-executed, and covered by deterministic/negative tests. One originating use is still not enough to call it a reusable DODGE candidate.

## Why reaction_timing is not promoted

The existing `reaction_timing` proto concept describes interrupt/reaction windows such as active defense after an attack.

A GURPS **reaction roll** is an NPC-attitude/random-response mechanic.

They share a word but not a semantic role.

Phase C therefore reassesses `reaction_timing` and keeps it:

`suspected`

No interrupt window, responder timing, or constrained defensive response executes in this tranche.

## Random evidence

Reaction rolls use the same deterministic evidence policy established earlier:

- supplied ordered die terms; or
- a recorded seed using `sha256-rejection-v1`.

The Phase C binding declares its own reaction-roll randomizer:

```text
3d6
combine: sum
```

The reaction result preserves:

- evidence kind;
- seed/algorithm when generated;
- individual die terms;
- raw total;
- ordered modifier rows;
- modifier total;
- modified total;
- matched lookup-table row;
- reaction category.

## Reaction result

`dirps-reaction-result.v1` contains:

- encounter/action/actor identity;
- procedure identity;
- reaction modifiers;
- modifier total;
- random evidence;
- raw total;
- modified total;
- reaction category;
- lookup-table identity and matched row;
- GURPS procedure/modifier/table source trace;
- Scenario 01 modifier authority;
- DIRPS binding authority.

It is not a success-roll record and is intentionally not `dirps-execution-result.v2`.

## Stateful social encounter result

`execute_social_interaction()`:

1. validates the Phase C social bridge;
2. validates current neutral witness state;
3. validates action/actor/procedure binding;
4. executes the reaction roll;
5. selects the canonical consequence by reaction category;
6. resolves the canonical-derived ordered DODGE effect refs;
7. applies neutral DODGE `set` effects;
8. increments the runtime-state revision;
9. emits `dirps-social-encounter-result.v1`.

The social encounter record preserves:

- complete nested reaction result;
- selected reaction category;
- canonical consequence;
- exact state before;
- exact state after;
- ordered state delta;
- action/source/provenance;
- binding source;
- consequence source and DODGE effect refs.

A resolved witness interaction cannot be repeated.

## Replay

`replay_social_interaction()` re-executes from recorded `state_before`.

It reuses:

- recorded supplied terms; or
- recorded generated seed.

The entire social record must match exactly.

Tampering with:

- reaction category;
- random evidence;
- lookup result;
- consequence;
- state delta;
- before/after state;
- source trace

causes divergence.

This remains one-record deterministic re-evaluation, not append-only session history.

## Target support

The debug CLI remains thin.

Phase C adds:

- `inspect_social_target()`;
- `execute_social_target()`;
- `dirps-debug-social-target.v1`.

The existing `--encounter` CLI surface now asks the runtime for the encounter kind:

- Phase B → investigation runtime;
- Phase C → social runtime.

The target does not hard-code Roadside or Frightened Witness identifiers.

Social CLI example:

```bash
python tools/dirps_debug_target.py \
  --encounter frightened-witness \
  --action reassure-and-question \
  --actor pc \
  --dice 4 4 4
```

or use `--seed`.

On success the target refreshes capability from the post-action runtime state, just as the accepted Phase B parity fix requires.

## Deterministic, negative, and perturbation evidence

`tests/test_dirps_phase_c.py` proves:

1. exact neutral initial witness state;
2. exactly one runtime-described social action;
3. authoritative reaction procedure/table exposure;
4. good reaction → useful-lead state consequence;
5. neutral → partial-account;
6. poor → no-useful-account;
7. all eight Reaction Table bands execute at their boundaries;
8. canonical reaction-modifier perturbation changes modified total/reaction;
9. modifier rule-authority drift is rejected;
10. authoritative lookup-table drift is rejected;
11. canonical consequence change with stale sidecar bridge is rejected;
12. canonical + bridge consequence perturbation changes runtime state;
13. seeded reaction evidence is deterministic;
14. a changed seed changes terms/reaction;
15. social replay succeeds;
16. tampered reaction/state evidence diverges;
17. resolved witness interaction cannot be repeated;
18. `lookup_tables` is exercised/not-yet-candidate;
19. `reaction_timing` remains suspected;
20. target inspect/execute uses the same runtime state;
21. generic target dispatch preserves Phase B and adds Phase C;
22. fake social result/capability passes through without target recomputation;
23. target source contains no Phase C gameplay identifiers;
24. actual registered CLI executes the social encounter.

Named evidence:

```text
PASS dirps/scenario-01: Phase C Frightened Witness social encounter
PASS dirps/scenario-01: Phase C debug target consumes social runtime
```

## Existing contracts preserved

Phase C does not modify the accepted:

- `g5_execution_bindings`;
- `phase_a_execution_bindings`;
- `phase_b_encounter_bindings`;
- G5/v1 record;
- Phase A/v2 record;
- Phase B encounter record format.

Phase C is additive.

## Explicitly deferred to Phase D+

Phase C does not add:

- automatic encounter-order progression;
- Washed-Out Path environmental mechanics;
- combat;
- active-defense reaction timing;
- damage/injury;
- recovery;
- scenario completion;
- append-only session history;
- Web presentation;
- G7.

The next roadmap tranche after independent Phase C acceptance is **Phase D — Washed-Out Path environmental challenge**.
