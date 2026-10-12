# Scenario 01 — The Missing Courier

Scenario 01 is the specification for DIRPS's first planned executable vertical slice and follows the same role that Wretched Demesne Scenario 01 played for DODGE 0.2.1: keep the content small enough to understand, but demanding enough to expose architecture gaps.

## Current maturity

**G3 — Semantic-valid.** The candidate remains G2 core-valid and now passes the declared `dirps@0.1.0` source-stage semantic profile. The semantic-contract audit and negative evidence live in `../../docs/g3-semantic-validation.md`. A neutral resolver, resolved-game validation, runtime execution, replay, and targets are not yet claimed.

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

- `scenario.json` owns scenario fiction, encounter order, the prototype character build, and tutorial acceptance criteria. At G3, encounter ordering is canonical-source-only and is not yet normalized into DODGE; a future G4 resolver must preserve or explicitly expose that order rather than invent or reorder it.
- `../../dodge/dirps-scenario-01.dodge.v0.2.1.json` owns everything already expressible in DODGE 0.2.1.
- `../../sidecars/dirps.proto.sidecar.v0.1.json` owns explicit proto semantics that DODGE 0.2.1 cannot yet express.
- The external GURPS Lite rules reference remains authoritative for GURPS mechanics.
- Runtime and target code may implement algorithms, but may not invent gameplay semantics.

## Prototype assumptions

The scenario premise, character values, encounter composition, and pacing are implementation assumptions selected to create a useful tutorial. They are not GURPS canon and are not proposed as DODGE semantics.

## Future acceptance

When DIRPS advances to the executable gates, a first runtime is not accepted merely because narration works. It should be able to show which rule/procedure was used, preserve random outcomes, detect state divergence, and fail visibly when a required rule is unavailable or unresolved.
