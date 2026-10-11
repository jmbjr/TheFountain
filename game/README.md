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
