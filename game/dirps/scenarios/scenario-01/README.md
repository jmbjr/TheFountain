# Scenario 01 — The Missing Courier

Scenario 01 is the specification for DIRPS's first planned executable vertical slice and follows the same role that Wretched Demesne Scenario 01 played for DODGE 0.2.1: keep the content small enough to understand, but demanding enough to expose architecture gaps.

## Current maturity

**G6 — Targeted, Phase A gameplay candidate.** The accepted resolved model remains the sole runtime input. The success-roll runtime now supports contextual checks whose modifiers come from resolved Scenario 01 source, plus deterministic generated 3d6 evidence and critical classification. `../../docs/phase-a-contextual-skill-validation.md` records the authority and test evidence. The debug CLI remains the accepted target, while Roadside Tracks state/consequences are deferred to Phase B.

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

Phase A can now resolve the prototype Roadside Tracking context as a real modified skill check and preserve modifier/random/critical provenance. It intentionally does **not** mutate encounter state or apply investigation consequences; those are Phase B. Social/environmental/combat/recovery/completion and immutable session history remain later roadmap work.
