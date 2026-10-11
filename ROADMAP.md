# Roadmap

This is a lightweight view of where TheFountain is going. It is **not a commitment or detailed schedule**. Near-term items are concrete; later items are directional.

## Current state — October 2026

TheFountain has reached the first intended architectural milestone: it is now a **multi-game DODGE implementation hub** rather than a repository shaped around one Wretched Demesne scenario.

Authored source is game-scoped:

```text
game/
├── the-fountain/
├── wretched-demesne/
│   └── scenarios/
│       ├── scenario-01/
│       └── scenario-02/
└── gurps/
```

`tools/game_registry.py` discovers `game/<game-id>/game.json` descriptors and resolves scenario source, DODGE documents, sidecars, and export contracts by **game ID + scenario ID**. Adding another game should not require teaching repository-wide code a new set of hardcoded paths.

Historical SHA-addressed Wretched Beta builds remain immutable deployment evidence and are intentionally outside this authored-source refactor.

## Wretched Demesne Scenario 01 — reference implementation

Scenario 01 remains the preserved DODGE 0.2.1 reference implementation. Its purpose is now as much architectural as gameplay-facing: prove that one neutral source/resolver path can support multiple targets without allowing those targets to become independent game definitions.

### Shared resolver and validation — PASS

The current Scenario 01 pipeline is:

```text
Wretched authored source
        ↓
DODGE 0.2.1 schema validation
        ↓
Wretched semantic validation profile
        ↓
shared resolver
        ↓
wretched-resolved-game.v1
        ↓
Web / PnP / TTS
```

Source semantic validation, resolved-game validation, deterministic replay, target-manifest resolution, and rejected-action atomicity are established and covered by CI.

### Web — PASS / reference consumer

The Web implementation is the strongest current consumer of the shared resolved model.

Current accepted behavior includes:

- end-to-end Scenario 01 play;
- shared runtime/model;
- resolved starter decks and runtime semantic collections;
- deterministic replay and source-build provenance;
- replay verification and takeover;
- immutable Version Lab build history;
- topology/runtime semantics exercised by real playthroughs;
- save/load behavior tested across current and selected historical builds.

Further Web work should be driven by Scenario 02 or reusable DODGE/runtime needs rather than continued Scenario 01 convergence for its own sake.

### Print-and-Play — PASS

Resolver → PnP parity is established.

The PnP release path now:

- consumes the resolved DODGE target manifest;
- preserves a SHA-specific manifest beside each generated PDF;
- verifies the generated PDF against that manifest in CI;
- exposes target-only and noncanonical playtest quantities explicitly;
- keeps layout/presentation policy in the exporter rather than canonical game semantics.

PnP is considered sufficient for the current Scenario 01 reference release. Future work is presentation improvement, not a semantic blocker.

### Tabletop Simulator — PARTIAL PASS

Resolver → TTS semantic/package parity is established.

The TTS exporter now:

- derives starter, encounter, salvage, room, and crew-reference collections from the resolved TTS target manifest;
- derives token and Health-representation quantities from the same manifest;
- preserves the SHA-specific TTS manifest;
- verifies deck membership, quantities, GUID uniqueness, DeckID/CardID/CustomDeck consistency, build-scoped assets, and ZIP completeness.

Manual TTS testing split the result clearly:

**Cards: structural PASS**
- multiple decks load;
- cards can be drawn and manipulated;
- current layout/font quality is poor but is presentation work, tracked in **#159**.

**Tokens/bags: FAIL / current TTS blocker**
- supply bags appear poorly placed;
- pulling tokens can fail with `failed to load prefab` errors;
- token serialization and supply placement are tracked in **#160**.

The next TTS acceptance gate is simple:

> Load the save and pull at least one object from every bag without prefab/instantiation errors.

Do not spend Scenario 01 effort on card art/layout before the token serialization blocker is fixed.

## Multi-game hub — COMPLETE

Issue **#133** is complete.

The refactor:

- moved the original Fountain prototype into its own game namespace;
- moved Wretched authored source into `game/wretched-demesne/`;
- preserved Scenario 01 as a named reference scenario;
- reserved a sibling Scenario 02 home;
- created a clean GURPS/DODGE incubation namespace;
- added descriptor-based game/scenario discovery;
- updated active resolver, validation, exporters, tests, workflows, and project documentation;
- left generated historical Beta/Web builds untouched.

This is the baseline repository architecture going forward.

## Next major work streams

### 1. Wretched TTS token/loadability round

Fix **#160** first.

Scope:

- identify the correct Tabletop Simulator object/prefab representation for tokens;
- ensure bag-contained objects instantiate successfully;
- reject unsupported object/prefab names where practical;
- arrange supply bags in a deliberate table area;
- preserve all manifest-driven quantities.

After token loadability passes, address **#159** for TTS card typography/layout.

### 2. Wretched Demesne Scenario 02

Scenario 02 should implement the revised Design Lead direction as a sibling of Scenario 01, not mutate the preserved reference implementation.

Authoritative/review inputs remain open in:

- **#99** — Backpack System;
- **#101 / #102** — Character Sheet & Inventory System;
- **#103** — Turn Structure & Predetermined Hidden Topology;
- **#104** — reconciliation / implementation direction.

Before coding Scenario 02:

1. preserve the authoritative source losslessly;
2. perform a compatibility audit against the current DODGE version;
3. classify each requirement as canonical game data, DODGE semantics, engine machinery, target presentation, or a genuine DODGE gap;
4. define the executable Scenario 02 scope;
5. build through the shared resolver/runtime boundary rather than copying Scenario 01 target logic.

Scenario 01 should remain reproducible while Scenario 02 evolves.

### 3. GURPS DODGE experiment

The `game/gurps/` namespace is ready for a separate implementation effort.

The purpose is not merely to implement GURPS. It is a second independent stress test of DODGE so that abstractions proven only by Wretched do not become accidental specification assumptions.

Use the GURPS work to identify:

- genuinely reusable neutral concepts;
- Wretched-specific assumptions that should not live in shared infrastructure;
- missing DODGE contracts;
- opportunities to generalize resolver/validation/target tooling.

Reusable contract improvements belong in DODGE rather than private GURPS or Wretched dialects.

## DODGE 0.2.1 / reference-release direction

Scenario 01 has now exercised the important architecture:

- neutral DODGE source;
- game-owned semantic validation;
- shared resolution;
- Web runtime;
- PnP target manifest and verification;
- TTS target manifest and verification;
- deterministic replay/source provenance;
- multi-game repository discovery.

Remaining Scenario 01 work should be limited to real blockers or release-quality improvements, especially TTS token loadability.

When DODGE 0.2.1 is promoted to an official release, rerun Scenario 01 validation against that exact official revision and record the official DODGE identity in release provenance. Do not silently reinterpret the preserved Scenario 01 implementation during that promotion.

## Repository principles going forward

**Game and scenario are separate identities.**  
A game may contain multiple preserved scenarios or executable variants.

**Targets are projections.**  
Web, PnP, TTS, simulation, and future physical/electronic implementations consume neutral resolved semantics; they do not redefine the game.

**Generated builds are evidence, not authored source.**  
Source belongs under `game/`; SHA-addressed Beta output remains generated deployment material.

**Preserve before normalizing.**  
Lossless sidecars retain design intent that DODGE cannot yet represent.

**Fail loudly at authority boundaries.**  
Missing required semantics should fail validation instead of reviving old defaults.

**Use multiple games to shape DODGE.**  
Wretched provided the first deep implementation. Scenario 02 and GURPS should now pressure-test what is truly generic.

## Longer-term direction

- Improve reusable presentation systems for cards, tokens, boards, icons, and accessibility without coupling them to one game.
- Expand Wretched Demesne beyond *The Cave*: more scenarios, progression, enemies, regions, ship systems, Men of Leng, Black Pyramid, and campaign structure.
- Continue The Fountain prototype through the same game-scoped pipeline where useful.
- Add further games without changing central discovery code.
- Extend target support when real games require it, including future physical/electronic representations.
- Keep feeding implementation lessons back into DODGE.

The long-term workflow remains:

```text
design
  ↓
lossless source
  ↓
neutral/canonical game data
  ↓
validate
  ↓
resolve once
  ↓
play everywhere
  ↓
playtest
  ↓
tune the source
```

The roadmap should change whenever playtesting, a second game, or better implementation evidence shows that it should.
