# Scenario 01 — The Missing Courier

Scenario 01 is the specification for DIRPS's first planned executable vertical slice and follows the same role that Wretched Demesne Scenario 01 played for DODGE 0.2.1: keep the content small enough to understand, but demanding enough to expose architecture gaps.

## Current maturity

**G6 — Targeted (bounded).** The accepted G4 model remains the sole runtime input, the accepted G5 runtime remains the sole executable mechanic, and `tools/dirps_debug_target.py` provides one thin debug CLI consumer. `../../docs/g6-target-validation.md` records target, perturbation, error, provenance, and anti-hardcoding evidence. The rest of Scenario 01 remains unimplemented and G7 is not claimed.

## Goal

Eventually run a short solo tutorial that teaches core RPG resolution while pressure-testing DODGE + the DIRPS proto sidecar.

The intended path includes:

1. an ordinary skill/success roll;
2. a social or reaction-oriented interaction;
3. an environmental challenge;
4. one manageable combat exchange;
5. injury/recovery only as required by the scenario;
6. a replay record with source/rule traceability.

## Source-of-truth rules

- `scenario.json` owns scenario fiction, encounter order, the prototype character build, and tutorial acceptance criteria. Encounter ordering remains canonical in `scenario.json`; the G4 resolver now exposes it directly as the ordered `scenario.encounters` list in `dirps-resolved-game.v1` rather than inventing or reordering it.
- `../../dodge/dirps-scenario-01.dodge.v0.2.1.json` owns everything already expressible in DODGE 0.2.1.
- `../../sidecars/dirps.proto.sidecar.v0.1.json` owns explicit proto semantics that DODGE 0.2.1 cannot yet express.
- The external GURPS Lite rules reference remains authoritative for GURPS mechanics.
- Runtime and target code may implement algorithms, but may not invent gameplay semantics.

## Prototype assumptions

The scenario premise, character values, encounter composition, and pacing are implementation assumptions selected to create a useful tutorial. They are not GURPS canon and are not proposed as DODGE semantics.

## Future acceptance

The first target can now inspect actors/skills/capability data and execute the accepted bounded mechanic while displaying the exact runtime result and three-layer provenance trace. This does **not** satisfy the remaining social/environmental/combat/recovery/completion or immutable session-history goals.
