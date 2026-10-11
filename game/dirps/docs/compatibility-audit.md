# DIRPS → DODGE 0.2.1 compatibility audit

This is the bounded compatibility audit for DIRPS Scenario 01.

The baseline is DODGE 0.2.1. The governing rule is the same one used by Wretched Demesne: model existing neutral semantics in DODGE first; keep canonical scenario facts in scenario data; put genuine format gaps into an explicit sidecar; do not hide unsupported semantics inside a target or renderer.

| Requirement | DODGE 0.2.1 classification | DIRPS treatment | Candidate upstream |
|---|---|---|---|
| Actor attributes and mutable state | Expressible | DODGE values + scene instance state | No |
| Ordered actions/procedures | Expressible | DODGE actions/procedures | No |
| Conditions and state changes | Expressible | DODGE conditions/effects where sufficient | No |
| 3d6/random roll resolution with preserved rolled terms | Gap | Proto sidecar: `dice_resolution` | 0.2.2 |
| Derived values/formulas | Gap | Proto sidecar: `derived_values` | 0.2.2 |
| Reusable arithmetic expression graph | Gap | Proto sidecar: `expressions` | 0.2.2 |
| Rules lookup tables | Gap | Proto sidecar: `lookup_tables` | 0.2.2 |
| Procedure-local inputs/locals/outputs | Gap | Proto sidecar: `procedure_context` | 0.2.2 |
| Reaction/interrupt timing | Gap | Proto sidecar: `reaction_timing` | 0.2.2 |
| GM-only/hidden visibility | Gap | Proto sidecar: `visibility_and_secret_state` | 0.2.2 |
| RPG character organization | Partially expressible | DODGE actor state + proto character structure | Maybe 0.2.2 |
| Skills/defaults/governing attributes | Gap | Proto sidecar: `skill_model` | 0.2.2 |
| Rules-resolution evidence | Gap | Proto sidecar: `resolution_trace` | 0.2.2 |
| Immutable replay/session history | Gap | Proto sidecar: `replay_session_history` | 0.2.2 |

## Non-goals for this pass

- Do not encode the full GURPS ruleset.
- Do not reproduce GURPS prose.
- Do not add speculative DODGE vocabulary simply because an RPG might need it someday.
- Do not build target-specific gameplay logic.
- Do not promote a proto concept upstream until Scenario 01 has exercised it.

## Promotion test

A proto concept should be proposed to DODGE only after DIRPS can show:

1. a concrete scenario need;
2. a target-neutral representation;
3. resolver/runtime behavior driven from that representation;
4. deterministic or otherwise inspectable test evidence;
5. a plausible use outside GURPS-specific terminology.

Until then it stays in the sidecar.
