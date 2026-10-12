# DIRPS → DODGE 0.2.1 compatibility audit

This is the bounded compatibility audit for DIRPS Scenario 01. The candidate has reached **G4 — Resolved** against TheFountain CI's pinned DODGE 0.2.1 contract. G2 core evidence remains in `g2-core-validation.md`, G3 source semantics in `g3-semantic-validation.md`, and the G4 neutral resolver/resolved-game contract in `g4-resolved-validation.md`. Executable claims and proto-gap promotion still require G5+ runtime evidence.

The baseline is DODGE 0.2.1. The governing rule is the same one used by Wretched Demesne: model existing neutral semantics in DODGE first; keep canonical scenario facts in scenario data; put genuine format gaps into an explicit sidecar; do not hide unsupported semantics inside a target or renderer.

| Requirement | DODGE 0.2.1 classification | DIRPS treatment | Upstream status |
|---|---|---|---|
| Actor attributes and mutable state | Expressible | DODGE values + scene instance state | No |
| Ordered actions/procedures | Expressible | DODGE actions/procedures | No |
| Conditions and state changes | Expressible | DODGE conditions/effects where sufficient | No |
| 3d6/random roll resolution with preserved rolled terms | Gap | Proto sidecar: `dice_resolution` | Suspected; exercise first |
| Derived values/formulas | Gap | Proto sidecar: `derived_values` | Suspected; exercise first |
| Reusable arithmetic expression graph | Gap | Proto sidecar: `expressions` | Suspected; exercise first |
| Rules lookup tables | Gap | Proto sidecar: `lookup_tables` | Suspected; exercise first |
| Procedure-local inputs/locals/outputs | Gap | Proto sidecar: `procedure_context` | Suspected; exercise first |
| Reaction/interrupt timing | Gap | Proto sidecar: `reaction_timing` | Suspected; exercise first |
| GM-only/hidden visibility | Gap | Proto sidecar: `visibility_and_secret_state` | Suspected; exercise first |
| RPG character organization | Partially expressible | DODGE actor state + proto character structure | Suspected; exercise first |
| Skills/defaults/governing attributes | Gap | Proto sidecar: `skill_model` | Suspected; exercise first |
| Rules-resolution evidence | Gap | Proto sidecar: `resolution_trace` | Suspected; exercise first |
| Immutable replay/session history | Gap | Proto sidecar: `replay_session_history` | Suspected; exercise first |

## G3 semantic-validation result

The `dirps@0.1.0` source profile enforces only DIRPS-specific implications that DODGE core cannot know: registered authority/provenance alignment, canonical PC build consistency, explicit actor-state initialization, bounded action/procedure meaning, tutorial action-choice completeness, concrete combat-opponent presence, target-duration consistency, and the explicit proto-sidecar bridge.

The profile deliberately does **not** claim that prose encounter purposes, social/reaction resolution, environmental consequences, active defense, damage/injury, recovery, scenario completion, dice terms, or replay are executable. Those remain later-gate concerns, and every proto-sidecar entry remains `suspected`.

## G4 resolution result

`tools/resolve_dirps_dodge.py` now resolves the G3-valid source once into `dirps-resolved-game.v1`. The model preserves DODGE sources/rules, resolves the selected scene into concrete instances, derives the canonical PC build and target duration from Scenario 01, preserves canonical encounter order, and carries the entire proto sidecar plus a derived unresolved index.

The `dirps@0.1.0` profile now also runs at `resolved-game` and rejects dropped/changed rules, incomplete scene realization, stale PC build facts, reordered/changed scenario semantics, lost provenance, or missing/altered proto material. No proto entry is promoted: all remain `suspected` because no runtime behavior consumes them yet.

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

Every gap in this audit is currently **suspected**, even when a likely future DODGE version is obvious.

## Promotion test

A proto concept should become a DODGE candidate only after DIRPS can show:

1. a concrete scenario need;
2. a target-neutral representation;
3. resolver/runtime behavior driven from that representation;
4. deterministic or otherwise inspectable test evidence;
5. a plausible use outside GURPS-specific terminology.

Until then it stays in the sidecar.
