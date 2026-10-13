# DIRPS → DODGE 0.2.1 compatibility audit

This is the bounded compatibility audit for DIRPS Scenario 01. The candidate has reached **G6 — Targeted** with one debug CLI consuming the accepted ordinary success-roll runtime against TheFountain CI's pinned DODGE 0.2.1 contract. G2 core evidence remains in `g2-core-validation.md`, G3 source semantics in `g3-semantic-validation.md`, G4 neutral resolution in `g4-resolved-validation.md`, G5 runtime evidence in `g5-executable-validation.md`, and G6 target evidence in `g6-target-validation.md`.

The baseline is DODGE 0.2.1. The governing rule is the same one used by Wretched Demesne: model existing neutral semantics in DODGE first; keep canonical scenario facts in scenario data; put genuine format gaps into an explicit sidecar; do not hide unsupported semantics inside a target or renderer.

| Requirement | DODGE 0.2.1 classification | DIRPS treatment | Upstream status |
|---|---|---|---|
| Actor attributes and mutable state | Expressible | DODGE values + scene instance state | No |
| Ordered actions/procedures | Expressible | DODGE actions/procedures | No |
| Conditions and state changes | Expressible | DODGE conditions/effects where sufficient | No |
| 3d6/random roll resolution with preserved rolled terms | Gap | Proto sidecar + bounded G5 runtime: `dice_resolution` | **Exercised**; not candidate |
| Derived values/formulas | Gap | Proto sidecar: `derived_values` | Suspected; exercise first |
| Reusable arithmetic expression graph | Gap | Proto sidecar: `expressions` | Suspected; exercise first |
| Rules lookup tables | Gap | Phase C reaction-table range lookup via `phase_c_lookup_tables` | **Exercised**; not candidate |
| Procedure-local inputs/locals/outputs | Gap | Proto sidecar + bounded G5 execution binding: `procedure_context` | **Exercised**; not candidate |
| Reaction/interrupt timing | Gap | Proto sidecar: `reaction_timing` | Suspected; exercise first |
| GM-only/hidden visibility | Gap | Proto sidecar: `visibility_and_secret_state` | Suspected; exercise first |
| RPG character organization | Partially expressible | DODGE actor state + resolved character structure consumed by G5 runtime | **Exercised**; not candidate |
| Skills/defaults/governing attributes | Gap | G5 executes one explicit resolved skill level only; defaults/governing-attribute derivation remain absent | **Exercised** narrowly; not candidate |
| Rules-resolution evidence | Gap | accepted G5 `dirps-execution-result.v1` plus contextual Phase A `dirps-execution-result.v2` traces | **Exercised**; not candidate |
| Immutable replay/session history | Gap | Proto sidecar: `replay_session_history` | Suspected; exercise first |

## G3 semantic-validation result

The `dirps@0.1.0` source profile enforces only DIRPS-specific implications that DODGE core cannot know: registered authority/provenance alignment, canonical PC build consistency, explicit actor-state initialization, bounded action/procedure meaning, tutorial action-choice completeness, concrete combat-opponent presence, target-duration consistency, and the explicit proto-sidecar bridge.

The profile deliberately did **not** claim at G3 that prose encounter purposes, social/reaction resolution, environmental consequences, active defense, damage/injury, recovery, scenario completion, dice terms, or replay were executable. At that gate every proto-sidecar entry remained `suspected`; the G5 section below records the small subset now exercised.

## G4 resolution result

`tools/resolve_dirps_dodge.py` now resolves the G3-valid source once into `dirps-resolved-game.v1`. The model preserves DODGE sources/rules, resolves the selected scene into concrete instances, derives the canonical PC build and target duration from Scenario 01, preserves canonical encounter order, and carries the entire proto sidecar plus a derived unresolved index.

The `dirps@0.1.0` profile now also runs at `resolved-game` and rejects dropped/changed rules, incomplete scene realization, stale PC build facts, reordered/changed scenario semantics, lost provenance, or missing/altered proto material.

## G5 executable result

`tools/dirps_runtime.py` consumes only `dirps-resolved-game.v1` and executes the bounded `attempt-skill → success-roll` path. The selected skill target comes from resolved character semantics through the explicit sidecar `g5_execution_bindings.attempt-skill` declaration; the runtime does not hard-code a skill value or reread canonical source.

The runtime uses supplied die terms, derives the 3d6/sum/lte contract from the resolved `dice_resolution` proto semantics, and accepts only effective targets 4..16 under the explicit G5 execution binding. Outside that range it fails visibly rather than approximating success-roll edge semantics. The emitted `dirps-execution-result.v1` distinguishes authoritative GURPS action/procedure trace from the provisional `dirps-proto` binding and the provisional Scenario 01 / `prototype_assumption` skill target. It can re-evaluate a recorded result and detect divergence, including trace/provenance tampering. No RNG, modifiers, derived targets, critical-result consequences, session-history framework, or target adapter is implemented.

Actual G5 evidence moves `dice_resolution`, `procedure_context`, `actor_character_model`, `skill_model`, and `resolution_trace` to **exercised** only. They remain `not-yet-candidate`. `derived_values` and `replay_session_history` remain **suspected**, as do the other untouched proto gaps.

## G6 target result

`tools/dirps_debug_target.py` is the first real target consumer. It calls `describe_attempt_skill()` and `execute_attempt_skill()` from the accepted DIRPS runtime, exposes resolved actors/skills, the runtime-declared target/dice capability, the exact runtime result, and the three-layer provenance trace, and maps runtime failures to visible target errors.

The target contains no private rule literals for action/procedure identity, skill values, dice shape, comparator, target-domain bounds, or source/provenance IDs. A fake-runtime regression proves that deliberately unusual runtime totals/targets/outcomes are passed through unchanged rather than recomputed in the adapter. A source perturbation test proves a changed Scenario 01 skill value flows through DODGE → resolver → runtime → target.

This debug CLI does not use the DODGE export-contract/target-manifest model, so no fake manifest is declared. The generic G6 manifest lifecycle remains applicable only to registered `export_contracts`. No proto status changes at G6: the five G5 concepts remain `exercised` / `not-yet-candidate`, and all untouched gaps remain `suspected`.

## Phase A contextual skill-check result

Gameplay roadmap Phase A extends the accepted G5/G6 success-roll path without changing DIRPS maturity. Scenario 01 now owns a provisional `roadside-tracks-tracking` context with a prototype `-2` Tracking modifier. The neutral resolver preserves that context; the runtime derives effective target from base skill plus resolved modifiers, supports supplied or deterministic seeded 3d6 evidence, and classifies critical success/failure from the declared external-rule contract.

The authority split remains explicit: `gurps-lite` owns modifier/effective-skill and critical-boundary rules; `scenario-01-source` owns the provisional tutorial modifier magnitude; `dirps-proto` owns the provisional executable bridge. The result trace records all three layers.

Record identity is versioned rather than redefined in place. The accepted G5 `g5_execution_bindings.attempt-skill` contract remains unchanged and continues to emit `dirps-execution-result.v1`. Phase A uses separate `phase_a_execution_bindings.attempt-skill` and emits `dirps-execution-result.v2`. Legacy v1 replay and contextual v2 replay explicitly reject the other version as a contract mismatch rather than generic divergence.

Phase A reassesses `derived_values` and `expressions` but does **not** promote either. The bounded effective-target calculation does not implement the proposed generic derived-value/dependency/recompute shape or a reusable expression graph. The five previously exercised proto concepts remain `exercised` / `not-yet-candidate`; every other proto concept remains `suspected`.

Phase A does not mutate encounter/scenario state or apply investigation consequences. Those begin in roadmap Phase B.

## Phase B Roadside investigation result

Gameplay roadmap Phase B makes the first encounter stateful without changing DIRPS maturity. Canonical Scenario 01 owns the Roadside initial state, one investigation action, and success/failure consequence values/text. Those facts are normalized using standard DODGE 0.2.1 scenario-owned values, `scenario.initial_state`, `runtime_states`, and structured `set` effects. DIRPS source validation derives the normalized contract from canonical Scenario 01 so stale DODGE copies fail before resolution.

The sidecar adds only `phase_b_encounter_bindings.roadside-tracks`: a provisional bridge from the accepted Phase A v2 Boolean success result to the ordered normalized DODGE effect refs. The sidecar does not duplicate the consequence values.

`execute_investigation()` consumes a neutral runtime-state snapshot, executes the Phase A contextual skill path, applies the selected effect list, and emits `dirps-encounter-result.v1` with nested skill evidence, before/after state, ordered state delta, and provenance. `replay_investigation()` re-evaluates the one encounter record deterministically.

No new proto concept is promoted. Public Roadside information does not exercise hidden-state semantics, and one encounter replay does not satisfy the append-only `replay_session_history` proposal.

## Phase C Frightened Witness social result

Gameplay roadmap Phase C adds a materially different noncombat resolution path while formal maturity remains G6. GURPS Lite remains authoritative for reaction-roll semantics: 3d6, direct reaction modifiers, higher-is-better interpretation, requests for information as a normal use, and the eight-band Reaction Table. Scenario 01 owns the provisional `reassure-and-question` action, the +1 reassuring-approach judgment, and what information each reaction category reveals.

The DODGE document adds an authoritative `reaction-roll` procedure plus standard scenario-owned witness values/effects and a separate neutral witness runtime snapshot. The separate snapshot intentionally preserves accepted Phase B encounter-record state shape until Phase G unifies whole-scenario progression.

DODGE 0.2.1 lacks an executable value-range lookup primitive, so Phase C exercises `lookup_tables` through `phase_c_lookup_tables.gurps-lite-reaction-table`. Runtime code reads the declared table and does not duplicate its thresholds. `lookup_tables` moves to **exercised / not-yet-candidate**. `reaction_timing` remains **suspected**: a reaction roll is an NPC-attitude mechanic, not an interrupt/reaction window.

`execute_social_interaction()` emits `dirps-social-encounter-result.v1` around a nested `dirps-reaction-result.v1`, preserving random terms, raw/modified totals, modifier provenance, matched table row, reaction category, canonical consequence, exact before/after state, ordered state delta, and source trace. Deterministic replay re-executes the social record from its recorded evidence.

## Non-goals for this pass

- Do not encode the full GURPS ruleset.
- Do not reproduce GURPS prose.
- Do not add speculative DODGE vocabulary simply because an RPG might need it someday.
- Do not build target-specific gameplay logic.
- Do not promote a proto concept upstream until Scenario 01 has exercised it.

## Maturity rule

The sidecar uses the onboarding progression:

```text
suspected → exercised → candidate
```

The five G5 concepts plus Phase C `lookup_tables` are currently **exercised**. All remain `not-yet-candidate`. Every other gap remains **suspected**; none is a DODGE candidate.

## Promotion test

A proto concept should become a DODGE candidate only after DIRPS can show:

1. a concrete scenario need;
2. a target-neutral representation;
3. resolver/runtime behavior driven from that representation;
4. deterministic or otherwise inspectable test evidence;
5. a plausible use outside GURPS-specific terminology.

Until then it stays in the sidecar.
