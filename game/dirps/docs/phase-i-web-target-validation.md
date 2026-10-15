# DIRPS Phase I — player-facing Web target validation

Phase I keeps DIRPS at **G6 — Targeted** while turning the accepted Scenario 01 runtime into a browser-playable teaching/debug surface.

## Baseline

- Phase H accepted/merged PR: #186.
- Phase H final head: `f0ccf25ca90332df63e2d2c59b0563bf4c6fc79b`.
- Phase H merge SHA: `000af3995b7b2cade635c1a7f93bfb34839cd0b6`.
- Phase I branch baseline: post-merge generated `main` at `3db047d5d423195a30a3be8aaffb50fac50b3852`.
- DODGE remains pinned by CI to `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`.
- Formal maturity remains **G6 — Targeted**. Phase I is additional target evidence, not G7.

## Architecture

The browser target deliberately does **not** reimplement DIRPS gameplay in JavaScript.

```text
GitHub Pages
→ dirps/index.html
→ src/renderers/dirps-web.js
→ pinned Pyodide
→ mounted repository-authored Python/data
→ tools/resolve_dirps_dodge.py
→ dirps-resolved-game.v1
→ tools/dirps_runtime.py
→ tools/dirps_web_target.py
→ browser presentation
```

The renderer loads a pinned versioned Pyodide runtime, mounts the exact DIRPS resolver/runtime modules plus the registered Scenario 01 DODGE, canonical source, sidecar, and game descriptor, then imports the normal Python target adapter.

The browser therefore runs the same neutral resolver and accepted Python runtime used by repository conformance. There is no parallel JavaScript success-roll, social, environmental, combat, recovery, progression, or replay engine.

## Target responsibilities

`tools/dirps_web_target.py` is a thin target adapter.

It may:

- shape resolved character data for display;
- ask Phase H for a new session;
- replay a session to obtain its current full state;
- call `describe_scenario()` for current progress/actions;
- pass a browser-selected `action_id`, `actor_ref`, and deterministic `random_seed` to `append_scenario_session_step()`;
- return the unchanged accepted transition record for presentation;
- expose runtime errors visibly.

It may not:

- choose which semantic actions are legal;
- calculate target numbers, reaction bands, defenses, damage, injury, recovery, progression, or completion;
- translate a browser action into encounter-specific random-input shapes;
- maintain a second state machine.

Every accepted Phase G mechanic path already accepts `random_seed` as common random evidence, so the Web target always sends the same neutral input shape:

```json
{"random_seed":"<browser-selected seed>"}
```

The runtime decides how that seed becomes the mechanic's recorded dice terms.

## Browser presentation

The page presents:

- resolved Rook attributes, exact resolved runtime state (including HP, fatigue, stun/unconsciousness/check flags), skills, equipment, and provenance;
- current scenario encounter/progress state;
- only the runtime-described `available_actions`;
- optional deterministic seed input;
- the latest accepted mechanic/result record;
- recorded random evidence;
- scenario/mechanic trace and authority data;
- retained encounter state;
- Phase H append-only session evidence and state hashes;
- a full raw runtime/debug view behind a disclosure control.

The low-level debug CLI remains registered and unchanged.

## Pyodide boundary

Phase I intentionally chooses Python-in-the-browser instead of duplicating Python semantics in JavaScript.

The renderer pins Pyodide `v0.29.1` at a versioned jsDelivr path. The external runtime is transport/execution infrastructure only; it does not own DIRPS semantics.

Mounted repository files are:

- `tools/game_registry.py`;
- `tools/dirps_semantic_validation.py`;
- `tools/resolve_dirps_dodge.py`;
- `tools/dirps_runtime.py`;
- `tools/dirps_web_target.py`;
- `game/dirps/game.json`;
- the active Scenario 01 DODGE document;
- canonical Scenario 01 JSON;
- DIRPS proto sidecar.

The resolver still constructs `dirps-resolved-game.v1` from those inputs in the browser.

## Evidence

`tests/test_dirps_phase_i.py` proves:

- the initial Web view equals `describe_scenario()` over the Phase H initial session;
- the Web presentation model carries the exact resolved Rook `state` object with no target-owned defaults;
- the Web adapter's execution history exactly equals direct `append_scenario_session_step()` output for the same action/seed;
- generated random evidence remains owned by the accepted runtime;
- the target can drive a complete Scenario 01 run using only runtime-described actions;
- unsupported browser selections fail visibly without mutating the input history;
- neither the Python Web adapter nor JavaScript renderer contains Scenario 01 encounter/action gameplay literals;
- JavaScript contains no mechanic-specific random-input keys and no `Math.random`;
- the browser mounts the exact resolver/runtime/source files;
- the static page contains character, action, scenario, result, provenance, replay, and debug surfaces;
- a real headless Chromium smoke test serves the exact checkout, loads `/dirps/`, imports pinned Pyodide, fetches/mounts the repository files through browser URL resolution, waits for the shared Python resolver/runtime to report ready, verifies exact rendered HP/fatigue/status values, clicks a runtime-described action, and observes a Phase H history step plus recorded random evidence;
- the browser smoke fails if the fatal runtime panel appears or any browser request/page error occurs;
- `game/dirps/game.json` registers both the debug CLI and browser target;
- the Forbidden Places hub links to `/dirps/`.

The named CI evidence line is:

```text
PASS dirps/scenario-01: Phase I player-facing Web target consumes shared runtime
```

## CI boundary

The generic conformance workflow now watches `dirps/**`, the root hub entry/style, and continues to watch `src/**`, `game/**`, `tools/**`, and `tests/**`. Web-only presentation edits therefore cannot silently bypass DIRPS conformance.

Phase I browser evidence is not a filesystem analogue: CI installs pinned Playwright `1.64.1`/Chromium, starts a local HTTP server from the exact checkout, and runs `tests/dirps-web-smoke.mjs` against the actual HTML → JS module → CDN Pyodide → fetch/mount → Python import/resolve/runtime → DOM path.

## Proto maturity

Phase I adds **no proto promotion**.

The Web target consumes the existing resolved/runtime/replay contracts. `replay_session_history` remains **exercised / not-yet-candidate** and `visibility_and_secret_state` remains **suspected**.

## Explicit deferrals

Phase I does not add:

- new RPG mechanics;
- a JavaScript gameplay engine;
- save-file packaging/migration;
- secret/GM-only state;
- long-term healing/unconscious recovery;
- broader combat;
- simulation/PnP/TTS DIRPS targets;
- G7 reference status.

Independent review of the first Phase I candidate found two target-evidence gaps: the adapter exposed resolved character state but the renderer dropped it, and CI proved only Python adapter parity rather than the actual browser/Pyodide transport. The corrected target renders the resolved state verbatim and adds a real headless-browser boot/action smoke test. No resolver/runtime/proto change was required.

Exact-head CI identity belongs in the pull request and #178/#163 after the final literal PR head passes.
