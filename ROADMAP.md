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

## DODGE 0.2.1 / Wretched Stable promotion gate

Before DODGE 0.2.1 is promoted from draft to official, and before the current Wretched Beta is promoted to Stable, Wretched Demesne Scenario 01 must complete this conformance sequence. This is a release gate, not a parallel rewrite.

1. **Schema validation** — validate the active Wretched DODGE document and every active export contract against the exact current DODGE 0.2.1 draft schemas. Fix WD documents when they are wrong; open a DODGE blocker only when the game exposes a genuine schema/spec deficiency. CI must run the same validation so conformance cannot silently regress.
2. **Reference and semantic validation** — resolve local references and selected external/canonical sources; verify selected scene/scenario, representations, ownership, rule/procedure ordering, topology references and export-profile inclusions. Prose-only semantics must remain explicitly non-executable rather than being treated as implemented rules.
3. **One shared DODGE resolver** — replace target/runtime-specific interpretation with one resolver that starts from the active DODGE document and follows its declared canonical sources and lossless sidecars according to their authority. Sidecars remain the lossless home for Design Lead semantics that are not promoted into normalized DODGE. The resolver produces the shared playable Scenario 01 model plus deterministic component inventory; Pages, PnP and TTS must not maintain independent game definitions.
4. **Neutral topology materialization** — move the working Beta cave graph onto DODGE 0.2.1 topology semantics. Exploration materializes stable room nodes/edges in neutral runtime state; crew movement and enemy pathfinding consume that same topology. Target renderers may choose presentation/placement but may not redefine connectivity.
5. **Neutral rules and timing execution** — make the Scenario 01 turn/round loop consume the DODGE-declared actions, procedures, phases, AI priorities, ownership, timing/lifetime and scenario end conditions wherever 0.2.1 declares executable semantics. Preserve explicit prose fallbacks where the Design Lead source is not formal enough to execute.
6. **Runtime-state conformance** — represent resumable state using the 0.2.1 runtime-state concepts: selected scenario/scene, clocks and phase, bindings/owners, active and scheduled effects as applicable, materialized topology identity, and semantic events needed for deterministic continuation. Target saves may wrap this state but must not replace its neutral meaning.
7. **Deterministic inventory and representation resolution** — resolve the selected scene plus export profile into one deterministic neutral inventory, including Health representation modes and quantities. Resolve or explicitly document currently unresolved world-object supplies; no exporter may invent canonical quantities or game rules.
8. **Three-target parity** — build Web, PnP and TTS from the same source revision and resolved DODGE model. Verify target-owned details remain target-owned, physical dimensions remain normative, Beta representation bundles remain alternatives rather than duplicated game state, and manifests identify the same source/DODGE document.
9. **Scenario 01 conformance playtest** — run the complete Scenario 01 loop through the shared model: setup, exploration/backtracking, combat, search/loot, Noise/Threat, enemy AI/pathfinding, corpse feeding/chrysalises, Relay activation, retreat/extraction and win/loss. Use seeded deterministic replay files to preserve player actions and optional exact expected state after each step; replay must stop on rejected/nonsensical input or state mismatch. Fix implementation defects in shared code/data rather than per-target patches.
10. **Close release blockers and freeze the candidate** — classify every discovered problem as a WD implementation/data issue or a DODGE 0.2.1 specification issue. DODGE blockers must be resolved in the 0.2.1 draft and revalidated in WD. When no blockers remain, freeze the exact DODGE 0.2.1 candidate used by WD.
11. **Promote DODGE 0.2.1** — move the validated candidate to the official DODGE release location without semantic drift, rerun WD validation against that official copy, and record the official DODGE version/revision in build provenance.
12. **Promote Wretched Beta to Stable** — incorporate the Design Lead's Stable-release feedback, rerun schema/semantic tests, all three target builds and the Scenario 01 acceptance playtest, then promote the same validated WD source revision to Stable. Stable must not fork game data from the Beta candidate.

**Gate definition of done:** DODGE 0.2.1 is official; WD validates against that exact official version; Web/PnP/TTS derive from one neutral resolved model and source revision; Scenario 01 passes the shared-runtime acceptance loop; all Design Lead Stable-release feedback is addressed or explicitly deferred; and no known DODGE conformance blocker remains.

## After the MVP

Directionally, we expect to:

- Improve presentation, generated icons/art, card layouts, board/room visuals and accessibility across targets.
- Expand Wretched Demesne beyond *The Cave*: more cards, crew progression, enemies, regions, ship systems, Men of Leng, Black Pyramid and campaign structure.
- Feed lessons from Wretched Demesne back into DODGE, then deliberately migrate Wretched as official versions evolve; never create a private incompatible dialect.
- Strengthen reusable engines/exporters so adding another game increasingly means supplying game data rather than rebuilding infrastructure.
- Continue developing The Fountain and other **Forbidden Places** games through the same pipeline.
- Build toward a repeatable workflow: **design → neutral data → validate → play everywhere → playtest → tune the data**.

The roadmap should change whenever playtesting or better ideas tell us it should.
