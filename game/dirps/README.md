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
│   └── g4-resolved-validation.md
└── scenarios/
    └── scenario-01/
        ├── README.md
        ├── scenario.json
        └── export-contracts/
            └── README.md
```

## Maturity

DIRPS Scenario 01 currently reaches **G4 — Resolved**.

The authored DODGE document remains schema/core-valid and now declares `dirps@0.1.0` at both `source` and `resolved-game` stages. `tools/resolve_dirps_dodge.py` produces one target-neutral `dirps-resolved-game.v1` model, and `docs/g4-resolved-validation.md` records its preservation/perturbation evidence. This does **not** yet claim G5 runtime execution, replay, or target support.

The generic TheFountain conformance runner must report the DIRPS DODGE schema PASS, `semantic source dirps@0.1.0`, `neutral resolver`, and `semantic resolved-game dirps@0.1.0`.

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

The DODGE document targets DODGE 0.2.1 and is resolved at G4: source semantics pass, one neutral resolver produces `dirps-resolved-game.v1`, and the exact output passes the declared resolved-game profile. Its actor values explicitly declare actor ownership and Scenario 01 persistence; persistence beyond this bounded scenario remains intentionally unresolved for a later semantic gate. Anything that does not fit cleanly is declared in the DIRPS proto sidecar rather than smuggled into a renderer or runtime special case.

The proto sidecar records suspected gaps to exercise. A proto concept is not a DODGE 0.2.2 candidate until Scenario 01 actually exercises it through the neutral validation/resolver/runtime path.

## Scenario 01

**The Missing Courier** is deliberately small. It is intended to exercise ordinary success rolls, a social interaction, an environmental challenge, one bounded combat exchange, state changes, rule-source traceability, and deterministic replay.

Scenario fiction and character values are DIRPS prototype assumptions. GURPS mechanics remain external authoritative rules and are not reproduced verbatim here.
