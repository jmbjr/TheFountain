# Scenario 01 — The Missing Courier

Scenario 01 is the specification for DIRPS's first planned executable vertical slice and follows the same role that Wretched Demesne Scenario 01 played for DODGE 0.2.1: keep the content small enough to understand, but demanding enough to expose architecture gaps.

## Current maturity

**G6 — Targeted, Phase H gameplay candidate.** Accepted Phases A-G remain intact. Scenario 01 now has a complete target-neutral session-history layer over the accepted ordered runtime, preserving step evidence and deterministically replaying a full run. `../../docs/phase-h-session-history-validation.md` records the history/replay evidence.

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

Phases B/C/D/E/F/G are accepted gameplay slices. Phase G composes them into one bounded tutorial state. Phase H records that runtime as an immutable copy-on-append multi-step evidence sequence and can reproduce a complete success or failure run. Long-term waking/healing and player-facing Web presentation remain later roadmap work.


## Phase D — Washed-Out Path

The environmental encounter now executes one bounded `attempt-attribute → success-roll` DX crossing check. Success records `crossed`; failure records `detour-required` in neutral runtime state. The check reuses accepted success-roll/random/critical semantics and remains separate from later automatic encounter progression. Evidence: `../../docs/phase-d-washed-out-path-validation.md`.


## Phase E — Bandit Scout combat

The combat encounter supports one Rook Broadsword swing against the bandit scout. Ordinary hits open one Dodge reaction; a failed defense rolls bounded ST10 broadsword cutting damage and persists HP/stun/consciousness-check state. The exchange is intentionally one-shot and visibly rejects unsupported defenses, weapons, ST damage rows, and broader combat options. Evidence: `../../docs/phase-e-bounded-combat-validation.md`.


## Phase F — Bandit Scout recovery

The recovery slice consumes the exact post-combat state from Phase E. Consciousness is checked first when HP <= 0 and the stay-conscious obligation is active; physical-stun recovery follows only if the scout remains conscious. A successful stay-conscious roll does not clear the obligation while HP remains <= 0, so a later turn still requires another check. Long-term recovery from unconsciousness is explicitly unsupported. Evidence: `../../docs/phase-f-recovery-consciousness-validation.md`.


## Phase G — Scenario progression / completion

Full play begins from the neutral `scenario-01-playable-initial` runtime snapshot. The runtime exposes only the action for the current canonical encounter, merges the accepted mechanic result back into that full snapshot, retains prior information/consequences, and advances to the next encounter from `scenario.encounters`.

At the Bandit Scout, the accepted Phase E exchange either ends immediately if no recovery is required or enters the accepted Phase F recovery step. The resulting `can_act_normally` state drives the canonical bounded completion branch. DODGE `scenario-success` / `scenario-failure` conditions and `missing-courier-success` / `missing-courier-failure` end conditions make the terminal state explicit.

Phase G emits `dirps-scenario-progression-result.v1` and leaves every accepted Phase A-F record identity unchanged. One-record replay remains supported and is the transition primitive consumed by Phase H. Evidence: `../../docs/phase-g-scenario-progression-validation.md`.


## Phase H — Full session history / replay

Phase H adds `dirps-session-history.v1` without changing gameplay semantics. A session begins from `scenario-01-playable-initial` and appends only complete accepted Phase G transition records.

Each step preserves declared action identity, exact deterministic random inputs, canonical JSON SHA-256 before/after state identities, the Phase G resolution trace, and the full transition record. The append API validates and replays the existing history before adding a new step and returns a deep-copied history rather than mutating prior evidence.

Full-session replay re-executes each action from the accepted initial state and fails at the first inconsistent step. The resulting execution evidence moves `replay_session_history` from `suspected` to `exercised`, while keeping it `not-yet-candidate`. Evidence: `../../docs/phase-h-session-history-validation.md`.
