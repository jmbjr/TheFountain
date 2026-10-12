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
│   └── phase-a-contextual-skill-validation.md
└── scenarios/
    └── scenario-01/
        ├── README.md
        ├── scenario.json
        └── export-contracts/
            └── README.md
```

## Maturity

DIRPS Scenario 01 remains **G6 — Targeted** and is now advancing through gameplay roadmap **Phase A — contextual skill checks**.

The authored DODGE document remains schema/core-valid and retains `dirps@0.1.0` at both `source` and `resolved-game`. `tools/resolve_dirps_dodge.py` produces `dirps-resolved-game.v1`; `tools/dirps_runtime.py` preserves the accepted G5/G6 v1 API and adds separate Phase A contextual v2 APIs driven by resolved Scenario 01 modifiers; and `tools/dirps_debug_target.py` remains the accepted v1 target consumer. `docs/phase-a-contextual-skill-validation.md` records the current gameplay evidence. Phase B encounter consequences and G7 reference quality are not claimed.

The generic TheFountain conformance runner must retain the DIRPS DODGE schema/source/resolver/resolved PASS lines. Discovered Python tests retain the named G5/G6 evidence and add a named Phase A contextual-skill PASS line.

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

The proto sidecar records execution evidence without speculative promotion. `dice_resolution`, `procedure_context`, `actor_character_model`, `skill_model`, and `resolution_trace` remain `exercised` / `not-yet-candidate`. Phase A reassesses `derived_values` and `expressions` but keeps both `suspected`: the runtime performs one bounded effective-target calculation rather than implementing either proposed generic proto shape.

## Scenario 01

**The Missing Courier** is deliberately small. It is intended to exercise ordinary success rolls, a social interaction, an environmental challenge, one bounded combat exchange, state changes, rule-source traceability, and deterministic replay.

Scenario fiction and character values are DIRPS prototype assumptions. GURPS mechanics remain external authoritative rules and are not reproduced verbatim here.
