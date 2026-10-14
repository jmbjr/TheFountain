# Scenario 01 — The Missing Courier

Scenario 01 is the specification for DIRPS's first planned executable vertical slice and follows the same role that Wretched Demesne Scenario 01 played for DODGE 0.2.1: keep the content small enough to understand, but demanding enough to expose architecture gaps.

## Current maturity

**G6 — Targeted, Phase G gameplay candidate.** Accepted Phases A-F remain intact. Scenario 01 now composes their neutral state into one ordered runtime from Roadside Tracks through Bandit Scout completion, with explicit success/failure end states. `../../docs/phase-g-scenario-progression-validation.md` records the authority/state/perturbation/replay evidence.

## Goal

Run a short solo tutorial from start to deterministic completion while pressure-testing DODGE + the DIRPS proto sidecar.

The intended path includes:

1. an ordinary skill/success roll;
2. a social or reaction-oriented interaction;
3. an environmental challenge;
4. one manageable combat exchange;
5. injury/recovery only as required by the scenario;
6. a replay record with source/rule traceability.

## Source-of-truth rules

- `scenario.json` owns scenario fiction, encounter order, the prototype character build, tutorial acceptance criteria, and Phase G's bounded success/failure interpretation. The resolver exposes that order and progression source directly in `dirps-resolved-game.v1`; runtime code does not keep a second order.
- `../../dodge/dirps-scenario-01.dodge.v0.2.1.json` owns everything already expressible in DODGE 0.2.1.
- `../../sidecars/dirps.proto.sidecar.v0.1.json` owns explicit proto semantics that DODGE 0.2.1 cannot yet express.
- The external GURPS Lite rules reference remains authoritative for GURPS mechanics.
- Runtime and target code may implement algorithms, but may not invent gameplay semantics.

## Prototype assumptions

The scenario premise, character values, encounter composition, and pacing are implementation assumptions selected to create a useful tutorial. They are not GURPS canon and are not proposed as DODGE semantics.

## Future acceptance

Phases B/C/D/E/F are accepted gameplay slices. Phase G composes them into one bounded tutorial state. Encounter failures before the Bandit Scout are retained as consequences but are nonterminal; the final bounded combat/recovery result determines whether Rook can establish the courier's fate. Long-term waking/healing and immutable multi-step session history remain later roadmap work.


## Phase D — Washed-Out Path

The environmental encounter now executes one bounded `attempt-attribute → success-roll` DX crossing check. Success records `crossed`; failure records `detour-required` in neutral runtime state. The check reuses accepted success-roll/random/critical semantics and remains separate from later automatic encounter progression. Evidence: `../../docs/phase-d-washed-out-path-validation.md`.


## Phase E — Bandit Scout combat

The combat encounter supports one Rook Broadsword swing against the bandit scout. Ordinary hits open one Dodge reaction; a failed defense rolls bounded ST10 broadsword cutting damage and persists HP/stun/consciousness-check state. The exchange is intentionally one-shot and visibly rejects unsupported defenses, weapons, ST damage rows, and broader combat options. Evidence: `../../docs/phase-e-bounded-combat-validation.md`.


## Phase F — Bandit Scout recovery

The recovery slice consumes the exact post-combat state from Phase E. Consciousness is checked first when HP <= 0 and the stay-conscious obligation is active; physical-stun recovery follows only if the scout remains conscious. A successful stay-conscious roll does not clear the obligation while HP remains <= 0, so a later turn still requires another check. Long-term recovery from unconsciousness is explicitly unsupported. Evidence: `../../docs/phase-f-recovery-consciousness-validation.md`.


## Phase G — Scenario progression / completion

Full play begins from the neutral `scenario-01-playable-initial` runtime snapshot. The runtime exposes only the action for the current canonical encounter, merges the accepted mechanic result back into that full snapshot, retains prior information/consequences, and advances to the next encounter from `scenario.encounters`.

At the Bandit Scout, the accepted Phase E exchange either ends immediately if no recovery is required or enters the accepted Phase F recovery step. The resulting `can_act_normally` state drives the canonical bounded completion branch. DODGE `scenario-success` / `scenario-failure` conditions and `missing-courier-success` / `missing-courier-failure` end conditions make the terminal state explicit.

Phase G emits a new `dirps-scenario-progression-result.v1` wrapper and leaves every accepted Phase A-F record identity unchanged. One-record replay is supported; append-only whole-session history is deliberately deferred to Phase H. Evidence: `../../docs/phase-g-scenario-progression-validation.md`.
