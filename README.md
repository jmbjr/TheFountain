# The Fountain

Lovecraftian survival-horror prototype built around **survival through transformation**.

## DODGE architecture — firm requirement

**One neutral game definition:** `game/game.json`

That definition is the source of truth. Targets are adapters/renderers, never independent game definitions:

- GitHub Pages: `src/renderers/web.js`
- PnP: `tools/export_pnp.py`
- Tabletop Simulator: `tools/export_tts.py`

Do not encode gameplay content directly in a renderer. If a rule/card/encounter changes, change the neutral definition and regenerate/render every target from it.

## Prototype

The first slice demonstrates health, humanity, mutation stages, knowledge, death/resurrection, and encounters.

## Export

```bash
python tools/export_pnp.py
python tools/export_tts.py
```

These initial exporters establish the shared-source contract. PnP PDF/card layout and full TTS object/deck generation are subsequent adapters.

## Design North Star

> Immortality is not the reward. Immortality is the mechanism by which the horror happens.
