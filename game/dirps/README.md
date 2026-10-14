# DIRPS

DIRPS is the RPG-focused DODGE implementation experiment in TheFountain.

Its first rules stress test uses **GURPS Lite (Third Edition-era, June 2003)**, but GURPS is the external rules source, not the implementation identity. The purpose of DIRPS is to find RPG-shaped gaps in DODGE, exercise candidate neutral solutions through a deliberately bounded scenario, and feed reusable contracts upstream.

The directory intentionally mirrors the Wretched Demesne authored-source layout so contributors can move between the two projects without learning a second repository vocabulary.

## Structure

```text
game/dirps/
├── game.json
├── dodge/
│   └── dirps-scenario-01.dodge.v0.2.1.json
├── sidecars/
│   └── dirps.proto.sidecar.v0.1.json
├── docs/
│   ├── compatibility-audit.md
│   ├── g2-core-validation.md
│   ├── g3-semantic-validation.md
│   ├── g4-resolved-validation.md
│   ├── g5-executable-validation.md
│   ├── g6-target-validation.md
│   ├── phase-a-contextual-skill-validation.md
│   ├── phase-b-roadside-investigation-validation.md
│   ├── phase-c-frightened-witness-validation.md
│   ├── phase-d-washed-out-path-validation.md
│   ├── phase-e-bounded-combat-validation.md
│   ├── phase-f-recovery-consciousness-validation.md
│   ├── phase-g-scenario-progression-validation.md
│   └── phase-h-session-history-validation.md
└── scenarios/
    └── scenario-01/
        ├── README.md
        ├── scenario.json
        └── export-contracts/
            └── README.md
```

## Maturity

DIRPS Scenario 01 remains **G6 — Targeted** and is now advancing through gameplay roadmap **Phase H — full session history / replay**.

The authored DODGE document remains schema/core-valid and retains `dirps@0.1.0` at both `source` and `resolved-game`. `tools/resolve_dirps_dodge.py` still produces `dirps-resolved-game.v1`; accepted Phase G supplies the composed `scenario-01-playable-initial` runtime snapshot and `dirps-scenario-progression-result.v1` transitions. Phase H adds `dirps-session-history.v1`, a target-neutral copy-on-append sequence that preserves declared actions, deterministic random inputs, state hashes, traces, and exact Phase G transition records, then replays them from the accepted initial state. `docs/phase-h-session-history-validation.md` records the current evidence. Phase I Web presentation and G7 remain unimplemented.

The generic TheFountain conformance runner must retain the DIRPS DODGE schema/source/resolver/resolved PASS lines. Discovered Python tests retain all accepted G5/G6 and Phase A-G evidence and add Phase H full-session, copy-on-append, source-identity, continuity, hash, and first-divergence evidence.

## Authority boundary

The intended working order is:

```text
external rules reference
        ↓
DIRPS source/scenario facts
        ↓
DODGE 0.2.1 document
        +
DIRPS proto sidecar
        ↓
semantic validation / resolver
        ↓
resolved game
        ↓
runtime / replay / targets
```

The DODGE document targets DODGE 0.2.1 and remains resolved through the accepted G4 boundary. G5 adds a renderer-independent execution layer that consumes only `dirps-resolved-game.v1`; G6 adds a debug CLI that consumes the runtime rather than rereading or reinterpreting authored source. Its actor values explicitly declare actor ownership and Scenario 01 persistence; persistence beyond this bounded scenario remains intentionally unresolved for a later semantic gate. Anything that does not fit cleanly is declared in the DIRPS proto sidecar rather than smuggled into a renderer or runtime special case.

The proto sidecar records execution evidence without speculative promotion. `dice_resolution`, `procedure_context`, `actor_character_model`, `skill_model`, `resolution_trace`, and `lookup_tables` remain `exercised` / `not-yet-candidate`. Phase E genuinely exercises `reaction_timing`, `derived_values`, `expressions`, and the bounded `damage_injury` gap; all remain `not-yet-candidate`. Phases F and G add no proto promotion. Phase H now exercises `replay_session_history` through a complete target-neutral Scenario 01 history/replay contract, but keeps it `not-yet-candidate`. `visibility_and_secret_state` remains `suspected`.

## Scenario 01

**The Missing Courier** is deliberately small. It is intended to exercise ordinary success rolls, a social interaction, an environmental challenge, one bounded combat exchange, state changes, rule-source traceability, and deterministic replay.

Scenario fiction and character values are DIRPS prototype assumptions. GURPS mechanics remain external authoritative rules and are not reproduced verbatim here.


Phase G evidence is in `docs/phase-g-scenario-progression-validation.md`: the accepted encounters share one neutral full-scenario snapshot, preserve information/consequences as they advance in canonical order, and terminate through explicit DODGE win/loss conditions. Phase H evidence is in `docs/phase-h-session-history-validation.md`: full sessions are now recorded copy-on-append and replayed transition-by-transition with source identity, state hashes, random inputs, traces, and first-divergence detection. Phase I Web presentation and G7 remain later work.
