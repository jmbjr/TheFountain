# Scenario 01 — The Missing Courier

Scenario 01 is the specification for DIRPS's first planned executable vertical slice and follows the same role that Wretched Demesne Scenario 01 played for DODGE 0.2.1: keep the content small enough to understand, but demanding enough to expose architecture gaps.

## Current maturity

**G6 — Targeted, Phase B gameplay candidate.** The accepted v1/v2 skill contracts remain intact. Roadside Tracks now has canonical encounter state/action/consequences normalized into standard DODGE scenario/runtime state and structured effects, while the runtime composes those consequences with the Phase A contextual Tracking result. `../../docs/phase-b-roadside-investigation-validation.md` records the state/authority/replay/target evidence.

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

Phase B can now enter the first encounter, expose its one valid investigation action, resolve the contextual Tracking check, and apply meaningful success/failure consequences to neutral runtime state. It intentionally does **not** auto-advance into Frightened Witness; social/environmental/combat/recovery/completion and immutable session history remain later roadmap work.
