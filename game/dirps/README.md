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
│   ├── g7-reference-validation.md
│   ├── phase-a-contextual-skill-validation.md
│   ├── phase-b-roadside-investigation-validation.md
│   ├── phase-c-frightened-witness-validation.md
│   ├── phase-d-washed-out-path-validation.md
│   ├── phase-e-bounded-combat-validation.md
│   ├── phase-f-recovery-consciousness-validation.md
│   ├── phase-g-scenario-progression-validation.md
│   ├── phase-h-session-history-validation.md
│   └── phase-i-web-target-validation.md
└── scenarios/
    └── scenario-01/
        ├── README.md
        ├── scenario.json
        └── export-contracts/
            └── README.md
```

## Maturity

DIRPS Scenario 01 is **G7 — Reference**. The bounded Scenario 01 reference gate was independently accepted and merged in PR #188.

The authored DODGE document remains schema/core-valid and retains `dirps@0.1.0` at both `source` and `resolved-game`. `tools/resolve_dirps_dodge.py` still produces `dirps-resolved-game.v1`; accepted Phase G supplies the composed `scenario-01-playable-initial` runtime snapshot and `dirps-scenario-progression-result.v1` transitions. Phase H adds `dirps-session-history.v1`, a target-neutral copy-on-append sequence that preserves declared actions, deterministic random inputs, state hashes, traces, and exact Phase G transition records, then replays them from the accepted initial state. Phase I adds a browser target at `/dirps/` that boots the same Python resolver/runtime through pinned Pyodide rather than duplicating gameplay semantics in JavaScript. Phase J completed the whole-system audit of the accumulated G1-G6 + Phase A-I implementation; `docs/g7-reference-validation.md` records the accepted reference evidence.

The generic TheFountain conformance runner must retain the DIRPS DODGE schema/source/resolver/resolved PASS lines. Discovered Python tests retain all accepted G5/G6 and Phase A-I evidence and add `tests/test_dirps_g7.py`, which audits canonical encounter claims against one complete replayed run, explicit unsupported scope, conservative proto maturity, and the complete reference evidence set.

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

The DODGE document targets DODGE 0.2.1 and remains resolved through the accepted G4 boundary. G5 adds a renderer-independent execution layer that consumes only `dirps-resolved-game.v1`; G6 first added a debug CLI that consumes the runtime rather than rereading or reinterpreting authored source. Phase I retains that CLI and adds a second target: the browser loads the registered DIRPS source/resolver/runtime into Pyodide and runs those same Python semantics directly. Its actor values explicitly declare actor ownership and Scenario 01 persistence; persistence beyond this bounded scenario remains intentionally unresolved for a later semantic gate. Anything that does not fit cleanly is declared in the DIRPS proto sidecar rather than smuggled into a renderer or runtime special case.

The proto sidecar records execution evidence without speculative promotion. G7 acceptance did not promote any DIRPS proto concept upstream merely to satisfy the reference gate. `dice_resolution`, `procedure_context`, `actor_character_model`, `skill_model`, `resolution_trace`, and `lookup_tables` remain `exercised` / `not-yet-candidate`. Phase E genuinely exercises `reaction_timing`, `derived_values`, `expressions`, and the bounded `damage_injury` gap; all remain `not-yet-candidate`. Phases F and G add no proto promotion. Phase H now exercises `replay_session_history` through a complete target-neutral Scenario 01 history/replay contract, but keeps it `not-yet-candidate`. `visibility_and_secret_state` remains `suspected`.

## Scenario 01

**The Missing Courier** is deliberately small. It is intended to exercise ordinary success rolls, a social interaction, an environmental challenge, one bounded combat exchange, state changes, rule-source traceability, and deterministic replay.

Scenario fiction and character values are DIRPS prototype assumptions. GURPS mechanics remain external authoritative rules and are not reproduced verbatim here.


Phase G evidence is in `docs/phase-g-scenario-progression-validation.md`: the accepted encounters share one neutral full-scenario snapshot, preserve information/consequences as they advance in canonical order, and terminate through explicit DODGE win/loss conditions. Phase H evidence is in `docs/phase-h-session-history-validation.md`: full sessions are recorded copy-on-append and replayed transition-by-transition with source identity, state hashes, random inputs, traces, and first-divergence detection. Phase I evidence is in `docs/phase-i-web-target-validation.md`: `/dirps/` presents character/scenario state, runtime-described actions, recorded random/result/provenance evidence, and session history while executing the same Python resolver/runtime in-browser. Phase J evidence is in `docs/g7-reference-validation.md`: every bounded Scenario 01 claim is mapped to source/DODGE/runtime/test evidence, authority and perturbation paths are audited, unsupported scope remains explicit, and no proto concept is promoted upstream without cross-game evidence.
