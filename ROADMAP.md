# Roadmap

This is a lightweight view of where the project is going. It is **not a commitment or detailed schedule**. The next few steps should be concrete; everything farther out is directional.

## Next MVP — playable Wretched Demesne vertical slice

**MVP target:** Scenario 01: *The Cave* is playable from the same canonical data on GitHub Pages, as a Print-and-Play PDF, and in Tabletop Simulator, while remaining compliant with the current DODGE working target (0.2.1; draft pending official promotion).

1. **Shared runtime/model** — resolve the DODGE 0.2.1 Wretched scene + declared sidecar + Scenario 01 data into one playable model and deterministic component inventory. Implement the core turn/action, exploration, combat, search, Noise/Threat, enemy AI, spider ecosystem, retreat and extraction loop.
2. **Playable GitHub Pages version** — build the browser UI around that shared model and make Scenario 01 playable end-to-end.
3. **PnP PDF exporter** — **in progress on Beta.** Generate cuttable cards, crew references, enemies, rooms, tokens and reference material from the DODGE 0.2.1-declared Scenario 01 source. DODGE issues #25 and #27 are exercised through a Health representation laboratory: one Beta PnP export profile bundles individual tokens, a numbered track + marker, and a crew-card marker track into the same PDF without duplicating the game. Standard cards use 63 × 88 mm MTG-size dimensions and portrait 3×3 adjacent imposition. Compare these physical alternatives, then continue resolving room/tile sizing, world-object inventory and other representation choices before TTS.
4. **TTS exporter/package** — generate the corresponding TTS objects/assets/save and package them as a usable ZIP.
5. **Unified build + GitHub Actions** — validate the adopted DODGE 0.2.1 schema + semantic conformance once, then revalidate against the official copy on promotion, build all three targets from the same revision, deploy Pages, publish PnP/TTS artifacts, record source/build hashes, and automate cache-busting.
6. **MVP playtest and tuning** — test all three forms, fix usability/rules gaps, and tune provisional values in canonical data rather than in individual renderers.

## After the MVP

Directionally, we expect to:

- Improve presentation, generated icons/art, card layouts, board/room visuals and accessibility across targets.
- Expand Wretched Demesne beyond *The Cave*: more cards, crew progression, enemies, regions, ship systems, Men of Leng, Black Pyramid and campaign structure.
- Feed lessons from Wretched Demesne back into DODGE, then deliberately migrate Wretched as official versions evolve; never create a private incompatible dialect.
- Strengthen reusable engines/exporters so adding another game increasingly means supplying game data rather than rebuilding infrastructure.
- Continue developing The Fountain and other **Forbidden Places** games through the same pipeline.
- Build toward a repeatable workflow: **design → neutral data → validate → play everywhere → playtest → tune the data**.

The roadmap should change whenever playtesting or better ideas tell us it should.
