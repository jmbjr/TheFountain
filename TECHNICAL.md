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

Wretched Demesne has a playable Pages route plus generated Beta PnP/TTS review artifacts. A single Beta release workflow now builds all three deploy targets from the same triggering source revision. The remaining DODGE work is deeper semantic convergence: make the Web runtime and both exporters consume the same DODGE 0.2.1 resolved model/inventory rather than merely sharing the same checkout and canonical sources.

## Release identity and atomic Web policy

A Wretched Beta release has **one source identity**: the human/source Git merge SHA that triggered the release. The visible Web BUILD, PnP/TTS artifact names and manifests, and the executable Beta Web tree all use that identity.

```text
source revision <SHA>
       |
 unified release workflow
       |
       +-- PnP/TTS artifacts stamped <SHA>
       |
       +-- beta/web/<SHA>/
             +-- renderer
             +-- shared engine/model/replay/topology modules
             +-- canonical Scenario JSON
```

The SHA shown to the reviewer is the source merge, never the later bot commit that checks generated artifacts into the repository.

### Why the whole Web dependency graph is build-addressed

PR #45 cache-keyed the Beta entry module, but later testing exposed a remaining hole: that entry module statically imported mutable canonical module URLs. A page could therefore display the current BUILD while a browser reused an older transitive engine/model/replay module. In one observed run the exported runtime state contained a normal hand and log while the page rendered those collections empty.

The release boundary is now the **entire executable Web tree**, not merely the entry module. The workflow copies the renderer, its shared Wretched JavaScript dependencies, and canonical Scenario JSON into `wretched-demesne/beta/web/<source-sha>/`. The generated Beta HTML loads the renderer from that source-addressed directory, and all of its relative imports/data loads remain inside the same directory.

A refresh may cache an old immutable build or fetch a new immutable build, but it must not assemble one runtime from files belonging to multiple source revisions. Manual date/increment query tags are forbidden; reviewers must not need a hard refresh for correctness.

Canonical source files remain under `src/` and `game/`. The SHA-addressed Web tree is generated deployment material, not another source of truth. Future bundling/content-hashed assets may replace this mechanism only if they preserve the same invariant: **one visible source revision executes only assets derived from that revision.**


## Reusable release architecture for future projects

This section is deliberately written as a starter pattern. A future game project should be able to begin here rather than rediscovering the release plumbing.

### 1. Separate canonical source, runtime code, and generated deployment output

Use three visibly different layers:

```text
canonical source                 authored runtime/adapters             generated release
---------------                  -------------------------             -----------------
game/*.json + DODGE + sidecars   src/engine + renderers + tools   ->   site/beta/web/<SHA>/...
                                                                        downloads/*-<SHA>.pdf
                                                                        downloads/*-<SHA>.zip
                                                                        build manifests
```

Generated files may be checked in for static hosting, but they are never edited as game source. A generated artifact commit is transport/deployment bookkeeping, not a new game revision.

### 2. Give one human/source commit one release identity

The triggering merge SHA is the release identity. Derive a short display SHA from it, but retain the full SHA in manifests. Use that same source identity for:

- the visible Web BUILD stamp;
- the Web release directory;
- PnP/TTS filenames;
- TTS/PnP metadata where supported; and
- build manifests.

Do **not** replace that identity with the SHA of the later bot commit that checks generated files into the repository. Otherwise a reviewer cannot map the thing being tested back to the source change that produced it.

### 3. Make a static Web release atomic, not merely cache-busted

Cache-busting only an entry module is insufficient when that module imports other mutable URLs. The browser can legally combine a fresh entry module with cached transitive modules or data. Instead, publish the complete executable dependency graph under one immutable source-addressed directory:

```text
beta/web/<SOURCE_SHA>/
├── renderers/
│   └── game-web.js
├── runtime/
│   ├── engine.js
│   ├── model.js
│   └── replay.js
└── game/
    └── scenario.json
```

The page should point to exactly one such tree. Relative imports and data loads must stay inside it. A visible BUILD then identifies the actual executable graph, not just the first file the browser loaded.

### 4. Remember that JavaScript module-relative and document-relative URLs are different

A subtle browser rule caused the Wretched Beta 404: `fetch("../game/data.json")` does **not** become relative to the JavaScript module containing that call. A relative fetch URL is resolved against the document/base URL unless code explicitly supplies another base.

When data belongs to a module-addressed release, anchor it deliberately:

```js
const url = new URL(path, import.meta.url);
const response = await fetch(url);
```

Then test the path from the module that actually performs this resolution. If a renderer passes `../game/...` to a loader in `runtime/model.js`, and the loader calls `new URL(path, import.meta.url)`, the effective base is **model.js**, not the renderer and not the HTML document.

### 5. Make release generation idempotent

A release workflow runs against a repository that may already contain the previous generated release. Every rewrite must therefore accept both the source/template form and the previous generated form.

The Wretched failure mode was instructive: the first atomic release changed the HTML entry from a source URL to `./web/<OLD_SHA>/...`. The next build's `sed` only recognized the original source URL, silently changed nothing, and a later grep failed because the HTML still referenced the old SHA.

Prefer a stable semantic anchor—here, the Beta `<script type="module" ...>` entry—and replace its current value regardless of which prior SHA it contains. Test the postcondition: the final HTML must reference the current `SOURCE_SHA`.

### 6. Treat CI assertions as executable architecture documentation

Assertions should prove invariants rather than mirror implementation trivia. Useful release assertions include:

- every required generated file exists;
- the HTML entry points to the current SHA-addressed tree;
- renderer imports remain within that tree;
- canonical data resolves to the copied data inside that same tree;
- PnP/TTS filenames contain the same source SHA;
- manually maintained date/version cache tags are absent; and
- the workflow cannot recursively trigger itself from its generated commit.

When a shell step exits with no traceback, identify the **first command after the last visible successful output** before editing anything. With `bash -e` / `pipefail`, commands such as `grep -q` intentionally fail silently with exit code 1. Do not assume the preceding Python assertion failed merely because it is visually nearby.

### 7. Be deliberate about shell/Python boundaries

A quoted heredoc such as `<<'PY'` intentionally disables shell interpolation. Therefore this:

```bash
python - <<'PY'
from pathlib import Path
Path("$WEB_DIR")   # literal "$WEB_DIR", not the shell value
PY
```

is wrong if Python needs the shell variable. Pass it explicitly through the environment and read `os.environ` instead. This is safer and clearer than mixing shell interpolation into embedded Python.

### 8. Recommended release sequence

For a new static game project, establish this sequence early:

1. Checkout exactly one human/source revision.
2. Validate canonical data, schemas, exporters, and critical physical geometry.
3. Resolve/prepare the neutral game model.
4. Build every target from that same checkout/model.
5. Stamp every target with the triggering source SHA.
6. Build the entire Web dependency graph into an immutable SHA-addressed directory.
7. Rewrite the Web entry idempotently to the current directory.
8. Assert cross-target identity and Web dependency closure.
9. Commit/publish generated artifacts with a bot while suppressing recursive builds.
10. Preserve the human/source SHA as the visible release identity.

For DODGE projects, add schema + semantic conformance before target generation and require every target to consume the same deterministic resolved inventory.

### 9. Debugging order for release failures

Avoid patch-by-patch guessing. Inspect the exact source revision, checked-in generated state, workflow, and failing command together. Classify the failure before changing code:

1. **Source problem** — canonical data/runtime/exporter is wrong.
2. **Generation problem** — build produced the wrong tree/artifact.
3. **Reference problem** — HTML/module/data path points at the wrong generated file.
4. **Identity problem** — displayed SHA and executable/artifact SHA differ.
5. **Cache/atomicity problem** — dependencies can come from multiple revisions.
6. **CI assertion problem** — test models the architecture incorrectly.
7. **Deployment problem** — repository output is correct but hosting did not publish it.

A test should be weakened only if the invariant itself was wrong. If the invariant is correct, fix the generator or architecture instead.

Finally, test the **runtime mechanism itself**, not only a filesystem analogue of the mechanism. During the Wretched atomic-release work, CI correctly proved that `../game/...` would reach the generated JSON *if* the loader resolved it from `model.js`; however, the checked-in loader still used plain `fetch(url)`. The assertion validated our intended design rather than the code the browser actually executed. For module-addressed data, CI should therefore also verify that the generated loader contains/uses the module-relative resolution boundary (or, preferably, exercise the loader in an integration test).

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
