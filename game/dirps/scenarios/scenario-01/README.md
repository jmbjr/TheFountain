# Scenario 01 — The Missing Courier

Scenario 01 is the specification for DIRPS's first planned executable vertical slice and follows the same role that Wretched Demesne Scenario 01 played for DODGE 0.2.1: keep the content small enough to understand, but demanding enough to expose architecture gaps.

## Current maturity

**G6 — Targeted, Phase C gameplay candidate.** The accepted skill and Roadside encounter contracts remain intact. Frightened Witness now executes through an authoritative GURPS Lite reaction roll/table, a canonical reassuring-approach modifier and information mapping, neutral DODGE witness state/effects, deterministic replay evidence, and the same thin target boundary. `../../docs/phase-c-frightened-witness-validation.md` records the social authority/lookup/state/replay evidence.

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

Phases B and C are accepted stateful encounters. Phase D now resolves Washed-Out Path through a distinct DX attribute check and persists `crossed` or `detour-required` in neutral state. It intentionally does **not** auto-advance into combat; combat/recovery/completion and immutable session history remain later roadmap work.


## Phase D — Washed-Out Path

The environmental encounter now executes one bounded `attempt-attribute → success-roll` DX crossing check. Success records `crossed`; failure records `detour-required` in neutral runtime state. The check reuses accepted success-roll/random/critical semantics and remains separate from later automatic encounter progression. Evidence: `../../docs/phase-d-washed-out-path-validation.md`.
