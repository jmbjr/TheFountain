# DIRPS → DODGE 0.2.1 compatibility audit

This is the bounded compatibility audit for DIRPS Scenario 01. The candidate has reached **G5 — Executable** for one ordinary success-roll path against TheFountain CI's pinned DODGE 0.2.1 contract. G2 core evidence remains in `g2-core-validation.md`, G3 source semantics in `g3-semantic-validation.md`, G4 neutral resolution in `g4-resolved-validation.md`, and the first bounded runtime evidence in `g5-executable-validation.md`.

The baseline is DODGE 0.2.1. The governing rule is the same one used by Wretched Demesne: model existing neutral semantics in DODGE first; keep canonical scenario facts in scenario data; put genuine format gaps into an explicit sidecar; do not hide unsupported semantics inside a target or renderer.

| Requirement | DODGE 0.2.1 classification | DIRPS treatment | Upstream status |
|---|---|---|---|
| Actor attributes and mutable state | Expressible | DODGE values + scene instance state | No |
| Ordered actions/procedures | Expressible | DODGE actions/procedures | No |
| Conditions and state changes | Expressible | DODGE conditions/effects where sufficient | No |
| 3d6/random roll resolution with preserved rolled terms | Gap | Proto sidecar + bounded G5 runtime: `dice_resolution` | **Exercised**; not candidate |
| Derived values/formulas | Gap | Proto sidecar: `derived_values` | Suspected; exercise first |
| Reusable arithmetic expression graph | Gap | Proto sidecar: `expressions` | Suspected; exercise first |
| Rules lookup tables | Gap | Proto sidecar: `lookup_tables` | Suspected; exercise first |
| Procedure-local inputs/locals/outputs | Gap | Proto sidecar + bounded G5 execution binding: `procedure_context` | **Exercised**; not candidate |
| Reaction/interrupt timing | Gap | Proto sidecar: `reaction_timing` | Suspected; exercise first |
| GM-only/hidden visibility | Gap | Proto sidecar: `visibility_and_secret_state` | Suspected; exercise first |
| RPG character organization | Partially expressible | DODGE actor state + resolved character structure consumed by G5 runtime | **Exercised**; not candidate |
| Skills/defaults/governing attributes | Gap | G5 executes one explicit resolved skill level only; defaults/governing-attribute derivation remain absent | **Exercised** narrowly; not candidate |
| Rules-resolution evidence | Gap | `dirps-execution-result.v1` traces action/procedure/target/dice/result/source | **Exercised**; not candidate |
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

Only the five concepts listed in the G5 result are currently **exercised**. Every other gap remains **suspected**; none is a DODGE candidate.

## Promotion test

A proto concept should become a DODGE candidate only after DIRPS can show:

1. a concrete scenario need;
2. a target-neutral representation;
3. resolver/runtime behavior driven from that representation;
4. deterministic or otherwise inspectable test evidence;
5. a plausible use outside GURPS-specific terminology.

Until then it stays in the sidecar.
