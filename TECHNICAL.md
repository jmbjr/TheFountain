# Technical Architecture and Build Guide

This document is the technical companion to the deliberately lightweight `README.md`. It explains how this repository is organized, how DODGE is being used, how to build/test the current targets, how GitHub Pages is structured, and what automation exists today.

For the narrative project history and the reasoning behind major milestones, see `HISTORY.md`.

## Architectural rule

The project follows the **DODGE** pattern:

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

- `wretched-demesne.dodge.v0.1.json` — concepts representable by official DODGE v0.1.
- `wretched-demesne.gdd.sidecar.v0.1.json` — lossless DODGE-adjacent storage for semantics the current specification cannot represent.
- `wretched-demesne.scenario-01.mvp.v0.1.json` — executable prototype dataset for Scenario 01.
- `WRETCHED_DODGE_IMPORT.md` — import/losslessness contract.
- `WRETCHED_SCENARIO01_MVP.md` — MVP targets and provisional assumptions.

The sidecar is intentional. Teams should not block game development waiting for DODGE to learn every concept. Unsupported semantics can remain structured and lossless beside DODGE, then migrate into a future official specification.

## Current web architecture

GitHub Pages serves the repository as a static site.

The root `index.html` is the **Forbidden Places** game hub. It links to:

- `/the-fountain/`
- `/wretched-demesne/`

The Fountain is currently playable. Its page loads `src/renderers/web.js`, which loads neutral `game/game.json` and drives `src/engine.js`.

Wretched Demesne currently has its landing/placeholder route plus its canonical MVP data. Its shared playable runtime is the next major implementation milestone.

## Cache-busting policy

GitHub Pages/CDN and browser caches can make a deployment appear stale even when the repository has changed. We use **versioned asset URLs** for mutable static assets.

Example:

```html
<link rel="stylesheet" href="../style.css?v=20260928-1">
<script type="module" src="../src/renderers/web.js?v=20260928-1"></script>
```

Game-data fetches that are under active development should also avoid silently reusing stale responses:

```js
fetch("../game/game.json?build=20260928-1", { cache: "no-store" })
```

### Convention

When a PR changes a Pages-served CSS, JavaScript, JSON, image, or other mutable asset and stale caching could matter, bump the build/version query string in the HTML entry point that references it.

The version does not have semantic meaning; it only needs to change. A date plus increment is readable and sufficient, for example:

```text
20260928-1
20260928-2
20260929-1
```

Do **not** depend on users performing a hard refresh as the normal deployment mechanism.

A future build system should automate this by injecting the Git commit SHA or build identifier into asset URLs/manifests. Until then, explicit version query strings are the repository convention.

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
validate source
resolve DODGE + sidecar + MVP data
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

As of this document's creation, **there is no checked-in `.github/workflows/` directory in the repository**.

GitHub Pages is available for the repository and has been publishing the static site, but there is not yet a repository-owned workflow that performs the desired unified DODGE build.

Therefore, do not assume that merging to `main` currently generates the PnP PDF or TTS ZIP. It does not.

### Target Actions architecture

The intended workflow is:

1. Trigger on pushes/merges to `main`, with optional manual dispatch.
2. Validate canonical/DODGE data.
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
5. Web, PnP and TTS should consume the same resolved values.
6. Prefer data-driven tuning over target-specific code changes.
7. If a new concept exposes a DODGE specification gap, keep moving using the sidecar and record the gap for future DODGE work.

## Documentation roles

To keep the repository approachable:

- **README.md** — short project introduction and useful entry points.
- **HISTORY.md** — conversational history: what we did and why.
- **TECHNICAL.md** — architecture, builds, CI/CD, cache policy and implementation details.
- **game/*.md** — game/import-specific assumptions and contracts.

This keeps technical plumbing available without turning the README into an operations manual.

## Immediate technical roadmap

The next major implementation step is to consume the merged Wretched Demesne Scenario 01 dataset through a shared runtime/model, then have the Web, PnP and TTS adapters consume that same model.

After the three targets work locally, add the unified GitHub Actions workflow so a merge to `main` validates and publishes all three together.

At that point, update this document from “target architecture” to the exact production build procedure.
