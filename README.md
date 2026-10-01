# The Fountain

Lovecraftian survival-horror prototype built around **survival through transformation**.

## DODGE architecture — firm requirement

This repository must remain compliant with the **official DODGE specification**. Wretched Demesne currently adopts **DODGE 0.2.1** via `game/wretched-demesne.dodge.v0.2.1.json`. The governing 0.2.1 specification is still under `jmbjr/DODGE/draft/v0.2.1`, so this is a working adoption and must be revalidated when 0.2.1 is promoted to `official/`. Older DODGE documents are retained for history/traceability.

Canonical game facts may remain in referenced sources as DODGE permits. DODGE governs scene composition and resolved component inventory. Targets are adapters/renderers, never independent game definitions:

- GitHub Pages: `src/renderers/web.js`
- PnP: `tools/export_pnp.py`
- Tabletop Simulator: `tools/export_tts.py`

Do not encode gameplay content directly in a renderer or introduce target-specific workarounds that violate DODGE. If a rule/card/encounter changes, change the neutral definition and regenerate/render every target from it.

## Current Wretched Beta

Wretched Demesne Scenario 01 is playable in the Beta and is the release gate for DODGE 0.2.1. The normal Beta route always serves the newest source build. New replay exports carry their source Git SHA, and the separate **Version Lab** retains immutable SHA-addressed Beta web builds for replay compatibility/debugging. Historical retention begins with the Version Lab release; older builds can be reconstructed deliberately if needed.

Scenario 01 currently uses an interim **single-origin exploration** rule: each room may originate Explore once, producing a linear cave. Future branching, loops, connection tiers and objective-placement semantics remain a Design Lead decision rather than an implementation assumption.

Stable remains isolated for Design Lead review. TTS gameplay work is paused while Web/PnP and DODGE 0.2.1 convergence are completed.

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
