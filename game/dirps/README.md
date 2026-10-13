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
│   └── phase-e-bounded-combat-validation.md
└── scenarios/
    └── scenario-01/
        ├── README.md
        ├── scenario.json
        └── export-contracts/
            └── README.md
```

## Maturity

DIRPS Scenario 01 remains **G6 — Targeted** and is now advancing through gameplay roadmap **Phase E — bounded combat vertical slice**.

The authored DODGE document remains schema/core-valid and retains `dirps@0.1.0` at both `source` and `resolved-game`. `tools/resolve_dirps_dodge.py` produces `dirps-resolved-game.v1` and preserves standard DODGE runtime-state snapshots; `tools/dirps_runtime.py` preserves the accepted Phase A-D contracts and adds one bounded attack → Dodge → damage → injury exchange; and `tools/dirps_debug_target.py` dispatches combat through the same runtime-owned encounter boundary. `docs/phase-e-bounded-combat-validation.md` records the current gameplay evidence. Phase F recovery/consciousness and later mechanics remain unimplemented; G7 is not claimed.

The generic TheFountain conformance runner must retain the DIRPS DODGE schema/source/resolver/resolved PASS lines. Discovered Python tests retain the named G5/G6/Phase A/Phase B/Phase C evidence and add named Phase D environmental/runtime-target PASS lines.

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

The proto sidecar records execution evidence without speculative promotion. `dice_resolution`, `procedure_context`, `actor_character_model`, `skill_model`, `resolution_trace`, and `lookup_tables` remain `exercised` / `not-yet-candidate`. Phase E now genuinely exercises `reaction_timing`, `derived_values`, `expressions`, and the new bounded `damage_injury` gap; all remain `not-yet-candidate`. `replay_session_history` and `visibility_and_secret_state` remain `suspected`.

## Scenario 01

**The Missing Courier** is deliberately small. It is intended to exercise ordinary success rolls, a social interaction, an environmental challenge, one bounded combat exchange, state changes, rule-source traceability, and deterministic replay.

Scenario fiction and character values are DIRPS prototype assumptions. GURPS mechanics remain external authoritative rules and are not reproduced verbatim here.


Phase E evidence: `docs/phase-e-bounded-combat-validation.md`. The combat path uses resolved Broadsword skill, an explicit active-defense reaction window, sidecar-driven derived/lookup/damage contracts, neutral actor state, deterministic replay, and the existing runtime/target boundary. Recovery/consciousness and G7 remain later work.
