# Scenario 01 — The Missing Courier

Scenario 01 is the specification for DIRPS's first planned executable vertical slice and follows the same role that Wretched Demesne Scenario 01 played for DODGE 0.2.1: keep the content small enough to understand, but demanding enough to expose architecture gaps.

## Current maturity

**G6 — Targeted, Phase F gameplay candidate.** Accepted Phases A-E remain intact. The Bandit Scout's post-combat HP/stun/consciousness-check state now feeds bounded next-turn HT consciousness and physical-stun recovery checks over the same neutral combat snapshot. `../../docs/phase-f-recovery-consciousness-validation.md` records the recovery authority/state/replay evidence.

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

Phases B/C/D/E are accepted gameplay slices. Phase F consumes the combat consequences: a bandit at HP <= 0 must make the bounded beginning-of-turn stay-conscious HT check, and a conscious stunned bandit can make the physical-stun recovery HT check. Long-term waking/healing, automatic scenario progression/completion, and immutable session history remain later roadmap work.


## Phase D — Washed-Out Path

The environmental encounter now executes one bounded `attempt-attribute → success-roll` DX crossing check. Success records `crossed`; failure records `detour-required` in neutral runtime state. The check reuses accepted success-roll/random/critical semantics and remains separate from later automatic encounter progression. Evidence: `../../docs/phase-d-washed-out-path-validation.md`.


## Phase E — Bandit Scout combat

The combat encounter supports one Rook Broadsword swing against the bandit scout. Ordinary hits open one Dodge reaction; a failed defense rolls bounded ST10 broadsword cutting damage and persists HP/stun/consciousness-check state. The exchange is intentionally one-shot and visibly rejects unsupported defenses, weapons, ST damage rows, and broader combat options. Evidence: `../../docs/phase-e-bounded-combat-validation.md`.


## Phase F — Bandit Scout recovery

The recovery slice consumes the exact post-combat state from Phase E. Consciousness is checked first when HP <= 0 and the stay-conscious obligation is active; physical-stun recovery follows only if the scout remains conscious. A successful stay-conscious roll does not clear the obligation while HP remains <= 0, so a later turn still requires another check. Long-term recovery from unconsciousness is explicitly unsupported. Evidence: `../../docs/phase-f-recovery-consciousness-validation.md`.
