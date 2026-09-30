# Technical Architecture and Build Guide

This document is the technical companion to the deliberately lightweight `README.md`. It explains how this repository is organized, how DODGE is being used, how to build/test the current targets, how GitHub Pages is structured, and what automation exists today.

For the narrative project history and the reasoning behind major milestones, see `HISTORY.md`.

## Architectural rule

The project follows the **official DODGE specification**. Wretched Demesne currently adopts **DODGE 0.2.1** as its working target. The specification is presently in `jmbjr/DODGE/draft/v0.2.1`; official conformance must be revalidated when that draft is promoted:

> Game semantics have a neutral source of truth. Web, Print-and-Play (PnP), and Tabletop Simulator (TTS) are adapters/renderers of that source, not independent implementations of the game definition.

A renderer can contain platform-specific presentation and interaction code. It should not own card stats, encounter balance, enemy health, scenario objectives, or other gameplay facts that belong in canonical data.

The long-term target is:

```text
             DODGE / canonical game data
                        +
                adjacent sidecars
                        |
                resolve + validate
                        |
                 shared game model
                /        |        \
               /         |         \
        GitHub Pages   PnP PDF    TTS ZIP
```

A change to game content should therefore be made once and flow to all three targets.

### DODGE conformance is a maintained constraint

The repository MUST track the official DODGE specification and MUST NOT create a private Wretched-specific dialect. A DODGE version change requires explicit conformance review/migration of the Wretched document, resolver, exporters, validation and docs. Schema validity alone is insufficient; official semantic validation rules also apply.

Under DODGE 0.2.1, exporters for a build must consume the same deterministic resolved component inventory and normalized rule/runtime semantics they support. PnP and TTS must not independently choose component membership or quantities. The 0.2.1 model also provides neutral rules/resources, timing and effect lifetime, ownership/binding, transformations, topology materialization, scenarios and campaign structure. Unsupported or prose-only semantics remain explicitly adjacent/provisional rather than being hidden in target-specific renderer data.

## Repository layout

```text
/
├── index.html                 Forbidden Places landing page
├── style.css                  Shared site styling
├── the-fountain/              The Fountain web route
├── wretched-demesne/          Wretched Demesne web route
├── game/                      Neutral game data, DODGE docs and sidecars
├── src/
│   ├── engine.js              Existing Fountain runtime logic
│   └── renderers/
│       └── web.js             Existing Fountain web adapter
├── tools/
│   ├── export_pnp.py          Current PnP adapter foundation
│   └── export_tts.py          Current TTS adapter foundation
├── HISTORY.md                 Conversational project chronology
├── TECHNICAL.md               This document
└── README.md                  Human-facing project introduction
```

### `game/`

This is the most important directory.

`game/game.json` is the original neutral Fountain prototype definition.

Wretched Demesne adds a more formal DODGE workflow:

- `wretched-demesne.dodge.v0.2.1.json` — active Wretched working document adopting DODGE 0.2.1 rules/state/topology/scenario semantics.\n- `wretched-demesne.dodge.v0.2.json` — historical DODGE 0.2.0 document retained for traceability.
- `wretched-demesne.dodge.v0.1.json` — historical pre-migration document retained for traceability.
- `wretched-demesne.gdd.sidecar.v0.1.json` — lossless DODGE-adjacent storage for semantics the current specification cannot represent.
- `wretched-demesne.scenario-01.mvp.v0.1.json` — executable prototype dataset for Scenario 01.
- `WRETCHED_DODGE_IMPORT.md` — import/losslessness contract.
- `WRETCHED_SCENARIO01_MVP.md` — MVP targets and provisional assumptions.

The sidecar is intentional. Teams should not block game development waiting for DODGE to learn every concept. Unsupported semantics can remain structured and lossless beside DODGE, then migrate into a future official specification.

## Wretched topology semantics and authority boundary

Topology is deliberately split into four layers rather than hidden in the Web renderer:

```text
Design Lead / GDD intent
        |
lossless GDD sidecar (provenance; unresolved intent stays unresolved)
        |
DODGE + canonical Scenario rules/data (normalized executable policy)
        |
shared runtime resolver (materializes and validates graph mutations)
        |
runtime state.connections (the actual discovered graph)
        |
Web / PnP / TTS views
```

For Scenario 01, each room's canonical `connections` number is currently interpreted by the prototype `rules.topology.exploration_capacity` policy. `declared` is the safe default: Explore may add an edge only while the current room's materialized degree is below that value. `unbounded` intentionally permits over-capacity branching so the emergent/non-Euclidean behavior can be tested without forking the engine. This policy is marked a prototype assumption pending Design Lead issue #50; the exact field/value vocabulary is **not yet asserted to be final DODGE semantics**.

The runtime's `canExplore()` is the common rule boundary. `revealRoom()` guards it as well as `explore()`, preventing cards or future adapters from bypassing capacity. Move and Explore are distinct semantic actions: Move requires an explicit existing neighbor; Explore materializes a new room/edge from the current room. Deterministic replay records those semantic actions and topology diagnostics, making the origin of graph mutations inspectable.

If the Design Lead chooses stranger cave geometry, implement it by extending the neutral topology policy/resolver (and DODGE when appropriate), not with Web-only behavior. Candidate future semantics include selective unbounded rooms, loops, one-way edges, disappearing edges and event-driven rewiring.

## Current web architecture

GitHub Pages serves the repository as a static site.

The root `index.html` is the **Forbidden Places** game hub. It links to:

- `/the-fountain/`
- `/wretched-demesne/`

The Fountain is currently playable. Its page loads `src/renderers/web.js`, which loads neutral `game/game.json` and drives `src/engine.js`.

Wretched Demesne has a playable Pages route plus review PnP/TTS artifacts. The next architecture work is to make all three outputs consume the DODGE 0.2.1 resolved component inventory and shared normalized rule/runtime model.

## Release identity and cache-busting policy

A Wretched Beta release has **one source identity**: the human/source Git merge SHA that triggered the release build. The same identity is used for the visible Web BUILD, the PnP/TTS artifact names and manifests, and the browser cache key for the Beta Web entry module.

```text
        DODGE + canonical Scenario sources + sidecars
                         |
                  resolve / validate
                         |
               shared model + runtime
                         |
                  Git source SHA
                 /      |       \
                /       |        \
          Beta Web    PnP PDF    TTS ZIP
              |
       index.html BUILD
              |
              +--> wretched-beta-web.js?build=<source SHA>
                         |
                    ES module graph
                         |
                 shared engine / data
```

The SHA shown to the reviewer is the **source merge**, not the later GitHub Actions commit that checks generated artifacts into the repository. This lets every review artifact be cross-referenced to the source that produced it.

### Why the Web entry module is cache-keyed

GitHub Pages/CDN and browser caches can legitimately reuse a mutable URL. PR #42 exposed the failure mode: new HTML displayed the new BUILD while its unchanged, manually versioned renderer URL allowed a browser to execute an older cached renderer. The page therefore looked like one revision while behaving like another.

The release workflow now replaces the Beta renderer placeholder with the same 12-character source SHA used by the visible BUILD:

```html
<script type="module"
        src="../../src/renderers/wretched-beta-web.js?build=<source-sha>"></script>
```

A source merge therefore creates a new entry-module URL automatically. Manual date/increment cache tags are not release identity and MUST NOT be added to the Wretched Beta renderer dependency chain.

Static ES-module imports inside the renderer use their canonical paths. The entry module is the release boundary; shared modules remain source-controlled dependencies rather than independently hand-versioned mini-releases. If the Web build later gains bundling or hashed output files, that build may replace this mechanism while preserving the invariant: **one source revision must not silently execute assets from another release.**

The Beta release workflow contains guards against reintroducing manual date-style cache tags in the Beta entry/dependency chain. Do **not** depend on reviewers performing a hard refresh as a deployment mechanism.

## Local development

The site uses ES modules and fetches JSON, so opening the HTML directly as a `file://` URL is not a reliable test. Serve the repository over HTTP.

From the repository root:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

The game routes are:

```text
http://localhost:8000/the-fountain/
http://localhost:8000/wretched-demesne/
```

There is currently no JavaScript bundling/transpilation step. The Pages site is static HTML/CSS/ES modules.

## Current PnP build

Run from the repository root:

```bash
python tools/export_pnp.py
```

At the current project stage this exporter is an architectural proof for The Fountain. It reads `game/game.json` and writes:

```text
dist/pnp/prototype.txt
```

It does **not yet produce the target PnP PDF**.

For the Wretched Demesne MVP, this adapter will be replaced/expanded so the Scenario 01 canonical model produces the printable cards, characters, enemies, rooms/tile material, tokens and reference material required for play.

## Current TTS build

Run:

```bash
python tools/export_tts.py
```

The current adapter reads `game/game.json` and writes:

```text
dist/tts/TheFountain.json
```

This is a TTS-friendly manifest foundation, not yet the target packaged ZIP.

For the Wretched Demesne MVP the exporter must generate the required TTS save/object data and visual assets from the same resolved model as Web/PnP, then package the result as a ZIP.

## Desired unified build

The MVP target is a single build entry point that conceptually does:

```text
validate the adopted DODGE 0.2.1 schema + semantic conformance
resolve DODGE 0.2.1 + declared sidecar + MVP data
produce one deterministic component inventory
build web
build PnP PDF
build TTS ZIP
write build manifest / hashes
```

Expected output:

```text
dist/
├── web/
├── pnp/
│   └── wretched-demesne-mvp.pdf
├── tts/
│   └── wretched-demesne-mvp.zip
└── manifest.json
```

`manifest.json` should identify the common source/build version so artifacts can be proven to come from the same data revision.

## GitHub Pages and Actions — current state

Wretched Beta now has a checked-in unified release workflow at `.github/workflows/wretched-beta-pnp.yml`. It validates the exporters/PnP geometry and Web cache-identity invariants, generates matching PnP/TTS artifacts from the triggering source SHA, stamps the Beta Web release identity, and commits generated release artifacts with the bot.

GitHub Pages is available for the repository and has been publishing the static site, but there is not yet a repository-owned workflow that performs the desired unified DODGE build.

Therefore, do not assume that merging to `main` currently generates the PnP PDF or TTS ZIP. It does not.

### Target Actions architecture

The intended workflow is:

1. Trigger on pushes/merges to `main`, with optional manual dispatch.
2. Validate canonical data plus official DODGE schema and semantic conformance.
3. Build the Web, PnP and TTS targets in one workflow from the same checkout.
4. Create a build manifest containing the commit SHA and artifact hashes.
5. Deploy the web artifact to GitHub Pages.
6. Publish the PnP PDF and TTS ZIP as downloadable build/release artifacts.
7. Fail the workflow if any required target fails, preventing silent target drift.

Once that workflow is implemented, this section should be updated with the exact workflow filename, jobs, permissions, artifact names, and troubleshooting commands.

## DODGE development rules

When adding or changing gameplay:

1. First decide whether the concept belongs in official DODGE, existing canonical game data, or a DODGE-adjacent sidecar.
2. Preserve source information losslessly.
3. Mark prototype assumptions as prototype assumptions.
4. Do not solve an unsupported DODGE concept by hiding the rule inside a renderer.
5. Web, PnP and TTS MUST consume the same DODGE-resolved component inventory and resolved values.
6. Prefer data-driven tuning over target-specific code changes.
7. If a concept exposes a DODGE gap, use a declared sidecar or namespaced extension as allowed by the official spec and record the gap.
8. Review and deliberately migrate when adopting a new official DODGE version; update validation/tests/docs together.
9. Never fix a target by adding gameplay/component membership or quantities only to that target.

## Documentation roles

To keep the repository approachable:

- **README.md** — short project introduction and useful entry points.
- **HISTORY.md** — conversational history: what we did and why.
- **TECHNICAL.md** — architecture, builds, CI/CD, cache policy and implementation details.
- **game/*.md** — game/import-specific assumptions and contracts.

This keeps technical plumbing available without turning the README into an operations manual.

## Immediate technical roadmap

The next major implementation step is to realign the existing Wretched Web/PnP/TTS review build around the DODGE 0.2.1 resolver/rules/runtime/inventory contract, then improve PnP/TTS presentation from that common inventory.

After the three targets work locally, add the unified GitHub Actions workflow so a merge to `main` validates and publishes all three together.

At that point, update this document from “target architecture” to the exact production build procedure.


### Wretched Beta PnP

DODGE **0.2.1 is the current project baseline**. `tools/export_wretched_beta_pnp.py` reads the active `game/wretched-demesne.dodge.v0.2.1.json`, follows its declared Scenario 01 source, and renders a cuttable Beta PDF. The exporter owns page/card/token layout only; game rules and balance stay in neutral sources. The Beta artifact is isolated at `wretched-demesne/beta/downloads/` and must not replace the Stable Design Lead review artifact under `wretched-demesne/downloads/`.

The first physical build intentionally labels its token-sheet counts non-canonical because Scenario 01 does not yet declare physical supply quantities. The known Medic starter deck discrepancy is likewise rendered from source rather than silently corrected. GitHub Actions generates the Beta PDF after the 0.2.1 adoption reaches `main`.
