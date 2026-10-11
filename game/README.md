# Multi-game source registry

`game/` contains authored game source. Each immediate child directory with a `game.json` file is an independent game namespace.

## Convention

```text
game/<game-id>/
├── game.json                 # repository discovery descriptor
├── source/                   # optional game-level canonical source
├── dodge/                    # game-level/current DODGE documents when appropriate
├── sidecars/                 # lossless source/design material
└── scenarios/
    └── <scenario-id>/
        ├── scenario.json     # canonical executable scenario source
        └── export-contracts/ # target selection/presentation contracts
```

A descriptor may point a scenario at a game-level DODGE document or at a future scenario-local document. Generated Web/PnP/TTS artifacts are not canonical source and do not belong under `game/`.

Adding a new unrelated game should require adding a new directory and descriptor, not changing a central hardcoded game list.

## Adding a new game

Start with [`docs/ADDING_A_GAME.md`](../docs/ADDING_A_GAME.md). It maps the DODGE implementation lifecycle onto TheFountain's exact directory, registry, validation, resolver, testing, CI, and target conventions.

Do not treat a familiar directory layout or a green repository workflow as DODGE conformance. The candidate game itself must pass the maturity gates described there.

## Conformance discovery

A scenario with an active DODGE implementation should declare its repository-specific resolver in `game.json`:

```json
"conformance": {
  "maturity": "G4",
  "resolver": "tools/resolve_my_game_dodge.py"
}
```

Semantic validator ownership remains in the DODGE document through `validation.required_profiles`; do not duplicate those profile declarations in `game.json`. The repository-wide runner `tools/validate_registered_dodge.py` discovers both pieces and executes the standard schema → semantic source → resolver → semantic resolved → target-manifest pipeline.

Explicit `planned`, `scaffold`, or `G0` scenarios may remain outside the active conformance pipeline. Other DODGE-backed scenarios without a conformance declaration fail CI so a new game cannot be accidentally invisible.
