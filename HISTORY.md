# Project History

This is the conversational history of **The Fountain / Forbidden Places** repository: what we were trying to accomplish at each step, what changed, and why. It is intentionally more narrative than a changelog. Pull requests remain the precise code-level record.

The architectural thread running through the project is **DODGE**: game content should have a neutral source of truth, while the web game, Print-and-Play output, and Tabletop Simulator package are different renderers/adapters of that same underlying game.

## The beginning — The Fountain becomes the first playable game

We started with **The Fountain**, a Lovecraftian survival-horror design centered on a nasty inversion: immortality works, but resurrection and survival progressively transform the player. The first goal was not to build the whole game. It was to get a small playable browser prototype into the repository while establishing the architecture we wanted to keep using.

### PR #1 — Initial Fountain prototype with DODGE architecture

**Merged September 28, 2026.**

PR #1 created the first playable GitHub Pages prototype and, more importantly, established the initial DODGE-shaped project structure.

The key decision was that the browser version should not become the game definition. Neutral game data lives separately, and target-specific code consumes it. The repository gained a web renderer plus early PnP and TTS adapters so all three targets could eventually be generated from the same underlying content.

At this point the PnP and TTS exporters were architectural foundations rather than finished artifacts: PnP emitted a prototype manifest rather than a polished PDF, and TTS emitted a JSON foundation rather than a complete packaged ZIP. That distinction became important later when we clarified that our real target is an automated three-output build.

**Milestone:** the repository had its first playable game and its first explicit DODGE pipeline.

PR: https://github.com/jmbjr/TheFountain/pull/1

---

## The repository becomes a home for more than one game

The design direction then expanded. Instead of having GitHub Pages open directly into The Fountain, we wanted the root site to feel like a thematic collection of strange games or places.

### PR #2 — Add Lovecraftian landing hub and Wretched Demesne

**Merged September 28, 2026.**

We refactored the Pages root into a Lovecraftian game-selection landing page called **Forbidden Places**.

The existing Fountain prototype moved under its own `/the-fountain/` route without changing its gameplay. A second entry, **Wretched Demesne**, was added under `/wretched-demesne/` as a placeholder. Both games received navigation back to the main archive.

An important implementation detail was preserving The Fountain's connection to its neutral game data after moving the page. The route changed; the DODGE principle did not.

**Milestone:** the project changed from “a web page for The Fountain” into a small game hub capable of hosting multiple DODGE-driven games.

PR: https://github.com/jmbjr/TheFountain/pull/2

### PR #3 — Make the game hub more thematic and visual

**Merged September 28, 2026.**

The first hub worked structurally, but on a phone it still read too much like ordinary web links. We wanted choosing a game to feel like entering somewhere.

PR #3 stripped the cards down to short chapter labels, large game titles, and **ENTER**, then restyled them as atmospheric title-card portals with subtle environmental texture. The Fountain and Wretched Demesne became visual destinations instead of blocks of explanatory hyperlink text.

This was primarily presentation work, but it established a useful UI principle for the hub: **mood first, minimal words, obvious destination**.

**Milestone:** Forbidden Places acquired the visual identity intended for the public-facing Pages site.

PR: https://github.com/jmbjr/TheFountain/pull/3

---

## Wretched Demesne enters the project

Next we brought in the 31-page **Wretched Demesne: Plateau of Leng — GDD Prototype v0.1**.

The GDD described much more game semantics than DODGE v0.1 could formally represent: turn structure, action economy, resources, enemy AI, Noise and Threat, exploration, ship systems, the spider feeding/evolution ecosystem, campaign concepts, prototype goals, and intentionally unresolved design questions.

We did not want to either throw those details away or prematurely change the DODGE specification just to accommodate one game.

### PR #4 — Lossless GDD import using DODGE + sidecar

**Merged September 28, 2026.**

This produced a pattern we expect to be useful beyond Wretched Demesne.

Information that fits official DODGE v0.1 was represented in a normal DODGE document. Information that does **not** fit the current spec went into a **DODGE-adjacent sidecar JSON**.

The sidecar is deliberately structured to make future promotion into DODGE straightforward. It preserves machine-readable concepts such as the action system, enemy behavior, spider ecosystem, progression, resources, scenario ideas, and open design questions. It also includes the complete parsed GDD transcription as a fidelity fallback.

That last piece matters: “lossless” means we should be able to improve the schema later without discovering that an earlier conversion silently discarded something.

We also preserved unresolved questions as unresolved rather than inventing answers during import.

**Milestone:** Wretched Demesne was represented losslessly without forcing game-specific concepts into the official DODGE v0.1 schema.

PR: https://github.com/jmbjr/TheFountain/pull/4

---

## Turning the design into something we can actually test

Once the GDD was safely represented, the next question was what a playable MVP should prove.

We settled on a stronger target than merely “make the browser game work”:

> **One canonical game definition → GitHub Pages + PnP PDF + TTS ZIP.**

The three outputs must be siblings. No exporter gets to quietly become its own version of the rules.

The GDD intentionally leaves several mechanical details open, so a playable prototype requires assumptions. We agreed that those assumptions should be made pragmatically, clearly labeled as provisional, and kept data-driven so playtesting can change them without rewriting renderers.

### PR #5 — Define the Scenario 01 canonical MVP dataset

**Merged September 28, 2026.**

PR #5 turned **Scenario 01: The Cave** into a concrete vertical-slice dataset.

It added provisional but executable definitions for the crew roles, starter cards/decks, enemies, rooms, encounters, salvage, combat, Ammo, Noise, Threat, the spider corpse/feeding/pupation lifecycle, retreat and extraction, and Scenario 01 setup/win/loss conditions.

Where the GDD supplied a fact, the data preserves that provenance. Where we had to choose a value simply to make a test possible, the record identifies it as a **prototype assumption** rather than GDD canon.

We also added `game/wretched-demesne/scenarios/scenario-01/README.md`, which records the assumptions and target explicitly. The core acceptance goal is for a playtest to exercise exploration, the five-card hand, three-action turns, searching and loot, firearm ammo and Noise, global Threat, enemy activation, Spider Corpses, feeding, chrysalis/evolution, voluntary retreat, the objective chain, extraction, and both win and loss.

Just as importantly, that note codifies the tuning rule: **change the canonical data, not the individual Web/PnP/TTS implementations.**

**Milestone:** we now have enough defined game content to begin building one playable vertical slice across all three targets.

PR: https://github.com/jmbjr/TheFountain/pull/5

---

## Where we are now

The project currently has two related tracks.

**The Fountain** proved the basic browser/DODGE architecture and remains a playable prototype.

**Wretched Demesne** is now the more demanding DODGE test. Its source GDD has been imported losslessly, unsupported concepts are safely held in a DODGE-adjacent sidecar, and Scenario 01 has a canonical MVP dataset with explicit prototype assumptions.

The next major milestone is implementation rather than further design decomposition:

```text
DODGE + sidecar + Scenario 01 canonical data
                    |
              resolve / validate
                    |
             shared game model
             /       |       \
            /        |        \
    GitHub Pages   PnP PDF   TTS ZIP
```

The desired development loop is eventually simple: change the neutral game definition, validate it, and automatically regenerate all three playable representations together.

That is the point of the current MVP—not merely to prove Wretched Demesne is fun, but to prove that **DODGE can carry a real game from design data to multiple playable targets without those targets drifting apart.**

---

## History maintenance

Update this file when a PR represents a meaningful design, architecture, tooling, or playable-product milestone. It does not need an entry for every small fix.

Keep entries conversational: explain what problem we were solving, the decision we made, and what became possible afterward. Link the corresponding PR so the implementation details remain easy to find.


### PR #7 — Technical architecture and cache policy

**September 28, 2026.**

Before implementing the Wretched Demesne runtime, we paused to make the repository's technical operating model explicit. We had also seen GitHub Pages occasionally appear stale after updates, so this milestone establishes a cache-busting convention using versioned asset URLs rather than relying on users to hard-refresh.

A root `TECHNICAL.md` now separates implementation/build/CI details from the intentionally approachable README. It documents the DODGE source-of-truth rule, repository layout, current Web/PnP/TTS state, local serving/build commands, Pages caching policy, and the intended unified GitHub Actions pipeline.

The documentation also records an important current-state fact: there is not yet a checked-in Actions workflow. The unified build/deploy workflow remains an upcoming milestone rather than an undocumented assumption.

**Milestone:** the project now has an explicit technical handbook and a consistent strategy for avoiding stale Pages assets.


### PR #10 — Wretched Demesne becomes playable on the web

**September 28, 2026.**

With the shared Scenario 01 runtime in place, the next milestone was to replace Wretched Demesne's placeholder page with an actual play surface. The browser UI deliberately remains a renderer: it loads the canonical MVP dataset and drives the shared runtime rather than maintaining a web-specific copy of the rules.

The first playable interface exposes crew selection, expedition resources, discovered rooms, hand/cards, searching, exploration, enemies, combat, the objective/inventory, enemy/end-turn processing, retreat/extraction and the expedition log. It is intentionally utilitarian enough to reveal gameplay and data problems before we spend time polishing presentation.

The Pages asset version was bumped as part of the change so the new game does not depend on a hard refresh to replace the old placeholder.

**Milestone:** Scenario 01 can now be exercised end-to-end through GitHub Pages using the same shared runtime intended to support the other targets.


### PR #11 - Unified three-format review build

**September 28, 2026.**

The first Game Director review needs to evaluate the game rather than just the browser implementation, so we brought the other two DODGE targets forward. The Wretched Demesne page now exposes a Print-and-Play PDF and a Tabletop Simulator ZIP alongside the playable web version.

Both review artifacts come from the same canonical Scenario 01 MVP dataset used by the web runtime. The PDF is intentionally text-first and printable; the TTS package uses native notecards and includes the canonical source and prototype-assumption note. These are review artifacts, not final visual production.

**Milestone:** Scenario 01 is now available for review in all three intended forms - Web, PnP, and TTS - without creating independent gameplay definitions.


### PR #12 — Align Wretched Demesne with official DODGE 0.2.0

**Merged September 28, 2026.**

Once official DODGE 0.2.0 was available, we migrated Wretched rather than allowing the implementation to become a historical fork. The new `game/wretched-demesne/dodge/history/wretched-demesne.dodge.v0.2.json` declares DODGE 0.2.0, formally identifies the lossless GDD sidecar and source authority, and adds neutral component profiles. The v0.1 document remains for traceability.

This establishes an ongoing project rule: **Wretched Demesne and its Web/PnP/TTS pipeline must remain compliant with the official DODGE specification.** DODGE changes require deliberate conformance review/migration rather than target-specific workarounds.

**Milestone:** DODGE conformance is now a maintained project constraint.

PR: https://github.com/jmbjr/TheFountain/pull/12


---

## Wretched adopts DODGE 0.2.1 as the working rules model

### PR #14 — Adopt DODGE 0.2.1 for Wretched Demesne

**Opened September 28, 2026.**

After using Scenario 01 to pressure-test the DODGE 0.2.1 draft, we identified four requirements for Wretched adoption: deterministic timing/effect lifetime, explicit subject/resource ownership, atomic transformation semantics, and a clear boundary between unresolved topology generation and materialized runtime topology. Those requirements were captured in DODGE issue #21 and incorporated into the 0.2.1 draft.

PR #14 moves Wretched onto that model. The active working document is now `game/wretched-demesne/dodge/wretched-demesne.dodge.v0.2.1.json`, with representative rules/resources, timing, ownership, spider transformation, topology, Scenario 01 and campaign semantics promoted out of the generic sidecar boundary. Scenario 01 now points to the 0.2.1 document as its DODGE authority, while older DODGE documents remain for traceability.

The governing DODGE specification is still under `draft/v0.2.1`, so this milestone is deliberately a **working adoption**, not a claim of official 0.2.1 conformance. When DODGE publishes `official/v0.2.1/`, Wretched must revalidate the document, semantic rules, resolver and exporters against that exact revision.

No unresolved design question was silently answered during the migration: prose-only semantics remain non-executable, physical corpse/chrysalis supply quantities remain unresolved, and the provisional Medic deck-size inconsistency remains a Wretched data issue.

**Milestone:** DODGE becomes the intended neutral rules/state/topology model for Scenario 01, not only its component-inventory contract.

PR: https://github.com/jmbjr/TheFountain/pull/14


## Beta PnP becomes dimensionally DODGE-driven

Following the first successful Scenario 01 PnP smoke test and DODGE issue #23, Wretched now declares its standard gameplay cards as poker-size components (2.5 × 3.5 in) in the DODGE 0.2.1 document. The Beta PnP exporter resolves those normative dimensions from DODGE instead of owning card size itself. This is the first physical-output gate toward the next Wretched stable release; room/tile sizing and unresolved physical supply quantities remain explicit follow-up decisions rather than exporter inventions.


### PR #17 — DODGE Health representation laboratory

**Opened September 28, 2026.**

DODGE issue #25 formalized a missing separation between semantic game state and the physical or digital mechanism used to display and manipulate it. Wretched now exercises that model directly in the Beta PnP pipeline: one neutral Health definition can be exported as individual Health tokens, a numbered track with marker, or a crew-reference-card marker track. Separate DODGE export contracts select the alternatives without copying or overriding crew Health values.

The Beta build produces all three PnP variants through the same exporter so they can be compared as implementation choices. Stable remains unchanged. This is an explicit DODGE 0.2.1 release-gating experiment, not a final physical-design decision; the selected representation can change after Implementor and Design Lead review without changing the underlying Health rules.

**Milestone:** Wretched demonstrates selectable physical representations of one semantic state while retaining a single DODGE source of truth.

PR: https://github.com/jmbjr/TheFountain/pull/17


### PR #18 — One bundled Beta PnP packet and efficient card imposition

**Opened September 28, 2026.**

DODGE issue #27 clarified that export profiles may include representation candidates as `alternatives`: multiple implementations can be bundled into one prototype/review artifact without duplicating the base game or implying simultaneous gameplay. Wretched's Beta PnP profile now uses that model to include all three Health experiments in one PDF.

The card imposition was also rebuilt from the proven Digitropolis approach. Standard WD cards now declare 63 × 88 mm MTG-size physical dimensions, are imposed adjacently in a portrait US Letter 3×3 grid with no inter-card gutters, and include subtle rounded-corner cutting guides. Compatible card categories are packed continuously instead of forcing category page breaks.

The Beta page and generated PDF now expose the Git source hash so stale Pages deployments can be identified directly. Stable remains unchanged.

**Milestone:** one DODGE-driven Beta PnP artifact can carry multiple representation experiments while using efficient, verifiable physical output.


### PR #19 — Deterministic 3×3 PnP card imposition

**Opened September 28, 2026.**

The first bundled PnP pass still allowed ReportLab Platypus to paginate card rows, which could yield six cards instead of the intended nine. The card-sheet renderer now follows Digitropolis more directly: each portrait Letter sheet is one fixed 3×3 canvas-level imposition with adjacent DODGE-sized cards, shared cut guides, and rounded-corner guides. This is a PnP target correction; DODGE semantics are unchanged.

**Milestone:** PnP card capacity is now deterministic from physical card and paper dimensions rather than document-flow pagination.


### PR #25 — Beta TTS Scenario 01 target

**Merged September 28, 2026.**

The first Wretched DODGE 0.2.1 Tabletop Simulator export deliberately organizes the table by gameplay role rather than flattening every component into one deck. Each crew has its own starter deck; Encounter, Salvage, unexplored Rooms, Cave Mouth and Crew References are separate card groups. Enemy types, corpses and chrysalises use separate supply bags. The three Health representation experiments are also separate labeled supplies so Implementor review can compare them without treating them as simultaneous game state. Generated TTS saves and texture assets carry the source Git revision.

**Milestone:** Wretched gains a DODGE-driven Beta TTS target with rational gameplay groupings and all three Health representation alternatives.

PR: https://github.com/jmbjr/TheFountain/pull/25


### PRs #20–#23 and #26–#30 — Make Beta releases identifiable and PnP builds stable

**Merged September 28, 2026.**

The Beta review channel exposed two operational problems that mattered enough to preserve in the project history: a reviewer needed to know exactly which Git revision was on screen, and exact 63 × 88 mm 3×3 card sheets were sensitive to implicit ReportLab frame behavior. Several small corrective PRs converged on durable rules rather than changing game data.

The Beta page, build manifest and PnP filename now identify the human/source merge SHA rather than the later bot-generated artifact commit. Generated commits are prevented from recursively becoming new release identities. The PnP exporter uses an explicit zero-padding ReportLab frame, preserving the DODGE card dimensions and 0.20 in target margins, and CI now compile-checks the exporter and guards the exact 3×3 geometry/frame implementation before generation.

The intermediate failures in this sequence—malformed workflow text, a literal escaped newline in Python, and a half-applied SimpleDocTemplate-to-BaseDocTemplate change—were useful evidence that release mechanics themselves need executable invariants. Those checks are now part of the pipeline rather than institutional memory.

**Milestone:** a Beta artifact can be cross-referenced to its source merge, and the user-verified 3×3 PnP layout is protected by CI invariants.

PRs: #20, #21, #22, #23, #26, #28, #29, #30

### PR #31 — One source revision, one Beta release bundle

**Opened September 28, 2026.**

PnP and TTS initially had separate workflows, which allowed their source hashes to drift. This milestone replaces them with one non-bot Beta release build. A single source merge SHA drives the visible BUILD stamp, PnP PDF, TTS save, generated TTS assets and manifests.

The TTS review deliverable is now a hash-stamped ZIP containing the generated save JSON and its generated assets, with a direct Beta-page download link. The manifest remains available for traceability. The ZIP is packaging only: it does not introduce another game definition, and both targets still originate from the same DODGE/Scenario sources.

**Milestone:** the intended DODGE release relationship is explicit in automation: one neutral source revision generates matching PnP and TTS review artifacts together.

PR: https://github.com/jmbjr/TheFountain/pull/31


### PR #32 — Make the TTS ZIP self-describing

**Opened September 28, 2026.**

The unified Beta release made the TTS ZIP the reviewer-facing artifact, which made the separate manifest link on the Beta page unnecessary. The build manifest remains available to automation, but the page now presents only the useful review downloads and Stable navigation.

A copy of that metadata now travels inside every TTS ZIP as `manifest.json`, including the manifest format version, DODGE version, full source Git SHA, ZIP artifact name and TTS save name. This keeps a downloaded package traceable even after it has been separated from GitHub Pages.

**Milestone:** TTS review packages are self-identifying without exposing build plumbing in the player-facing UI.


---

## Wretched Beta becomes a deterministic playtest laboratory

### PRs #34–#35 — Connected-room navigation and topology-aware enemy movement

**Merged September 29, 2026.**

The first Design Lead Beta feedback exposed a fundamental navigation gap: the crew could explore forward, but the browser did not provide a trustworthy way to traverse the cave back through already discovered rooms and ultimately return to the Cave Mouth after activating the Relay.

PR #34 made discovered-room connectivity explicit shared runtime state. Exploration now creates bidirectional edges, movement is restricted to connected discovered rooms, and the objective loop can legitimately return through the cave to extraction. PR #35 then moved enemy navigation onto the same graph: enemy movement uses shortest paths over materialized cave connections rather than target-specific or implicit room order.

A successful Beta playthrough subsequently reached the Relay, returned to Cave Mouth, extracted, and completed Scenario 01. That playtest demonstrated that the repaired navigation/extraction loop is achievable; it was not treated as proof that every Scenario 01 rule was already correct.

**Milestone:** crew movement, enemy pathfinding and extraction now share one explicit runtime topology.

PRs: https://github.com/jmbjr/TheFountain/pull/34 and https://github.com/jmbjr/TheFountain/pull/35

### PR #37 — Seeded deterministic replay

**Merged September 29, 2026.**

Manual playtests were becoming valuable enough that reproducing a strange run by memory was no longer acceptable. Wretched therefore gained an explicit seeded random stream and a semantic action-dispatch boundary.

The `wretched-replay.v1` format records a seed, crew and ordered actions, with optional exact state after each action. A fresh runtime can execute the file from the beginning and stop at the first rejected/nonsensical action or exact-state mismatch. This turns a playthrough into a repeatable regression case rather than a one-off anecdote.

**Milestone:** Wretched playtests can be deterministic, replayable and state-verifiable.

PR: https://github.com/jmbjr/TheFountain/pull/37

### PR #38 — Beta records and replays its own tests

**Merged September 29, 2026.**

The deterministic harness became part of the normal Beta play surface. A player can choose a visible test seed, play normally through semantic recorded actions, export the session as JSON, and later load that file into a fresh game for exact replay/state verification.

This closes the loop between human exploratory testing and automated regression evidence: interesting manual sessions can be preserved immediately without hand-authoring a test script.

**Milestone:** the Beta browser is now both a playable implementation and a deterministic test-case recorder.

PR: https://github.com/jmbjr/TheFountain/pull/38

### Replay discovery — the entrance-branch topology hack

A recorded `quick-test-001` playthrough appeared at first to reveal a serious navigation bug: after deep exploration and backtracking, Whispering Dead End seemed to jump directly back to Cave Mouth.

The replay showed something more interesting. The player had walked all the way back to Cave Mouth and then selected **Explore**. Under the current topology rules, exploration attaches the newly revealed room to the crew's current room. The runtime therefore legitimately created a second branch directly from Cave Mouth. The apparent teleport was legal graph movement.

The confusing part was the UI: **Discovered Path** rendered rooms in discovery order with arrows between them, falsely presenting that ordering as connectivity. The incident was preserved under `bugs/001-entrance-branch-topology-hack.md` because it is simultaneously a useful regression case, a visualization defect, and an example of emergent topology strategy that may deserve design review.

### PR #42 — Render the cave graph rather than discovery order

**Merged September 29, 2026.**

Issue #39 corrected the misleading map exposed by the replay. Beta now derives its topology display from the runtime `state.connections` graph. Every displayed edge is a real connection; branches are explicit; the current room remains identifiable; and enemy, corpse and chrysalis annotations remain available.

Regression coverage preserves the exact branched shape that exposed the problem: Cave Mouth may connect independently to Bone Pit and Whispering Dead End without inventing an edge between those branch rooms.

**Milestone:** the Beta map now reports the same topology that movement and enemy pathfinding actually use.

PR: https://github.com/jmbjr/TheFountain/pull/42


### PRs #42, #45, #49 and #51 — Topology becomes observable, deterministic, and policy-driven

**September 29–30, 2026.**

A deterministic Beta replay exposed what first looked like a navigation or map corruption bug. The old map renderer had been drawing room discovery order as though it were connectivity, hiding the fact that the runtime had legitimately materialized branches when the player backtracked and explored from an earlier room. PR #42 changed the Beta map to render the actual runtime graph; PR #45 then fixed release cache identity so a new BUILD could not silently execute a stale renderer.

Once the real graph was visible, replay diagnostics made a second behavior obvious: repeated Explore actions could turn a room whose canonical data declared two connections into a five-way hub. PR #49 first separated the two player intents—**Move follows an existing edge; Explore creates a new edge from the current room**—and removed targetless movement that silently chose the first neighbor.

PR #51 closes the implementation hole conservatively without throwing away the emergent design possibility. Scenario 01 now declares a prototype topology exploration-capacity policy. The default `declared` policy treats each room's `connections` value as its exploration capacity; the shared runtime rejects further exploration once that degree is reached. The alternative `unbounded` policy deliberately restores over-capacity branching, proving that non-Euclidean topology can be an authored rule rather than an engine bug. Design Lead issue #50 asks whether and how Wretched should intentionally exploit stranger topology.

This sequence also sharpened the DODGE boundary. Source/GDD intent remains losslessly preserved in the sidecar; normalized executable topology policy belongs in neutral DODGE/canonical semantics; room connection capacity is canonical room data; and the concrete discovered graph is runtime materialized state. The current Scenario 01 policy is explicitly a prototype assumption pending Design Lead review rather than a premature DODGE vocabulary decision.

**Milestone:** deterministic replay turned a confusing UI symptom into an inspectable topology model, then turned an accidental exploit into a configurable design capability while restoring safe default behavior.

PRs: #42, #45, #49, #51. Design decision: issue #50.


### Issue #52 — The BUILD stamp was not yet an atomic Web release

**September 30, 2026.**

The topology-capacity replay produced a second-order infrastructure discovery. A refreshed Beta page showed the new PR #51 BUILD identity, yet a newly started expedition rendered an empty hand, missing actions/path/log, while End Turn still advanced the game and the exported replay contained a populated hand, room deck and log. The runtime state and its presentation could not both have come coherently from the displayed revision.

Inspection showed that PR #45 had correctly source-keyed the Beta entry module but its static imports still used mutable canonical URLs. The visible BUILD therefore proved the entry revision, not the revision of the complete ES-module/data graph. That undermined deterministic replay as an acceptance test because a current renderer could potentially execute an older cached engine.

Issue #52 tightens the invariant: a Beta Web release is now generated as a complete `beta/web/<source-sha>/` tree containing the renderer, shared Wretched runtime modules and canonical Scenario JSON. Relative dependencies remain inside that immutable tree. Canonical `src/` and `game/` files remain the source of truth; the build-addressed tree is deployment output only.

**Milestone:** build identity moves from a stamped entry URL to an atomic executable release. This restores the premise needed for deterministic browser/replay testing: the SHA on screen identifies the code and data actually participating in the run.


### PRs #53–#58 — Making the atomic release real, and learning to debug the pipeline

**September 30, 2026.**

Issue #52 identified the architectural requirement, but implementing it exposed several assumptions that had been hidden while the Beta used mutable source URLs. PR #53 created the first source-addressed Web tree: renderer, shared runtime modules and canonical Scenario data were copied together under `beta/web/<source-sha>/`. The visible BUILD and PnP/TTS artifacts used that same human/source SHA, while the later bot commit remained deployment bookkeeping.

The first published atomic build then failed to open the expedition with `Unable to load canonical MVP data: 404`. The generated JSON existed; the path semantics were wrong. We had treated `fetch("../game/...")` as though it were relative to the importing renderer. In a browser, a plain relative fetch is document-relative. PR #54 moved that responsibility into the shared loader by resolving the supplied path with `new URL(path, import.meta.url)`. This made the loader's own module URL the explicit base and kept canonical data inside the SHA-addressed release.

The next several CI failures were not independent mysteries; they exposed weak spots in how we were reasoning about the release. PR #55 updated a stale preflight guard that still required the old `?build=<SHA>` entry form. PR #56 fixed an embedded Python assertion that received the literal string `${WEB_DIR}` because it lived inside a quoted shell heredoc; the robust solution was to pass the value through the environment. PR #57 corrected the path assertion itself: because `model.js` performs `new URL(..., import.meta.url)`, the path must be reasoned from `web/<SHA>/wretched/model.js`, where `../game/...` reaches the sibling game directory.

The final failure had no Python traceback at all. The assertion had actually passed; `bash -e` stopped on the following silent `grep -q`. Inspecting the exact checked-in HTML revealed the deeper generator bug. After the first atomic release, `index.html` already contained `./web/<OLD_SHA>/renderers/wretched-beta-web.js`. The workflow's rewrite only recognized the original `../../src/...?...build=...` source form, so later releases generated a new tree but silently left HTML pointing at the old one. PR #58 made the entry rewrite idempotent by targeting the semantic module-script entry regardless of its previous SHA. CI then passed.

This back-and-forth changed our debugging rule. When release plumbing fails, do not immediately patch the closest-looking assertion. First identify the last command known to have succeeded and the exact command that returned nonzero; inspect the current checked-in generated state as well as the source template; then classify whether the problem is source, generation, reference resolution, release identity, cache atomicity, assertion logic or deployment. In particular, silent `grep -q` failures under `set -e` are expected to produce almost no diagnostic output.

It also established a reusable release invariant for future games: **one human/source revision produces one source-addressed executable Web graph and matching non-Web artifacts; all references are explicit and module/data resolution is tested from the code that actually performs it; generation must be repeatable when the repository already contains the previous generated release.**

**Milestone:** the Wretched Beta release pipeline became an atomic, source-identifiable, repeatable three-target build, and the troubleshooting lessons were promoted into reusable architecture rather than left buried in CI logs.

PRs: #53, #54, #55, #56, #57, #58. Root cause thread: issue #52.

### PR #60 — Verify the runtime, not just the intended path

**September 30, 2026.**

After #58 passed CI, the published Beta still produced the same canonical-data 404. This time the exact generated release was inspected file-by-file. The SHA-addressed Scenario JSON existed, the renderer passed the expected `../game/...` reference, but the generated `wretched/model.js` still called plain `fetch(url)`. The module-relative `new URL(path, import.meta.url)` behavior described during #54 had never actually landed in the source loader. Later CI checks had therefore validated the geometry of the intended module-relative path without validating that the runtime used that resolution mechanism.

PR #60 made the runtime boundary real: the shared loader now constructs the data URL against `import.meta.url` before fetching and drops the obsolete manually versioned default query string. The resulting Beta release, BUILD `352ed31bdb6c`, was then tested successfully on both mobile and PC through the normal `/wretched-demesne/beta/` route.

The previously captured multi-path/over-capacity replay was also loaded against this coherent build. It was rejected at step 8 on the attempted `Explore`, as expected under the default `declared` exploration-capacity policy. That provides an acceptance check for both the repaired release boundary and the topology regression that originally drove this investigation.

**Lesson:** a CI assertion can accidentally prove an architectural assumption rather than executed behavior. For critical release boundaries, inspect or exercise the generated runtime mechanism itself in addition to checking that the destination path exists.

**Milestone:** the atomic Web release is now browser-verified across mobile and PC, and the historical topology-abuse replay fails at the expected semantic boundary.

PR: #60.



---

## Replay provenance, linear topology, and immutable Version Lab

### PRs #91–#93 — Make rule changes reproducible across builds

**Merged September 30, 2026.**

A Design Lead replay exposed an ambiguity in the provisional cave topology model. Scenario 01 now deliberately uses one outgoing Explore origin per room, producing a single linear cave while the broader topology design is resolved separately with the Design Lead. This is an interim executable constraint, not a claim that future Wretched topology must be linear.

That change also demonstrated why deterministic replay needs build provenance. PR #92 stamps new replay JSON with the full source Git SHA, reports replay/current versions on verification failure, and allows saved replay states to remain inspectable even when the current runtime rejects the historical action sequence. Inspection-only fallback does not silently bless incompatible state or permit takeover.

PR #93 adds the Wretched Version Lab. The ordinary Beta URL remains current-only, while the Lab can launch retained immutable SHA-addressed Beta builds and run a selected replay with the current, selected, or recorded runtime. Older/Newer and midpoint selection provide a simple manual compatibility/bisect workflow. Release automation now retains future web builds instead of deleting the previous SHA directory; retention begins with the Version Lab release, so older builds are reconstructed only when there is a concrete need.

**Milestone:** replay failures can now be tied to a source revision, inspected without discarding useful evidence, and reproduced against retained historical runtimes without turning those runtimes into a second source of truth.

PRs: https://github.com/jmbjr/TheFountain/pull/91, https://github.com/jmbjr/TheFountain/pull/92, https://github.com/jmbjr/TheFountain/pull/93


---

## Scenario 01 becomes source-aware and historically debuggable

### PRs #91–#93 — Linear topology, replay provenance, and Version Lab

**Merged September 30, 2026.**

Replay testing exposed two different problems that initially looked like one. First, the prototype's earlier graph-capacity interpretation let Cave Mouth originate Explore more than once. The current Scenario 01 design intent is simpler: each room may originate Explore exactly once, producing one linear cave. PR #91 implemented that explicit **single-origin** policy and left the broader topology model unresolved for Design Lead issue #90 rather than inventing future branching semantics.

Second, a newly generated replay could fail after a runtime change without identifying which source build had created it. PR #92 therefore stamped new replay exports with the source Git SHA and made replay failures report replay/current build identity. Saved states from an unverifiable replay remain useful for inspection, but are clearly unverified and cannot be taken over under the current runtime.

PR #93 completed the debugging architecture with **Version Lab**. Beta releases are now retained as immutable SHA-addressed web runtimes, the normal Beta URL still means newest/current, and the Lab can route a replay to Current, its recorded build, a manually selected build, or a midpoint for compatibility/bisect investigation. Historical retention begins with this release; older generated trees had already been deleted and will only be reconstructed if a specific investigation needs them.

These changes sharpened an important distinction: a replay may be valid under its originating build even when its actions no longer conform to the current build.

**Milestone:** Scenario 01 now has an explicit interim linear topology policy, replay files carry source provenance, and future Beta builds form an immutable compatibility history without changing the normal newest-Beta workflow.

The next convergence phase is the DODGE 0.2.1 runtime-semantic audit. The shared resolver already feeds Web and PnP; remaining procedural mechanics will be classified one coherent mechanic at a time as DODGE-expressible semantics, canonical Scenario data, genuine DODGE blockers, or legitimate engine implementation details. TTS remains paused until Web/PnP convergence is satisfactory.


## Authoritative Design Lead refresh and preserved reference variant

### Issues #99–#104 — Capture the new design before changing the executable reference

**October 1, 2026.**

Five new Design Lead documents were preserved as authoritative source issues #99–#103. They introduce Backpack and Character Sheet/Inventory direction and replace the earlier generated-cave topology direction with predetermined hidden scenario topology. Issue #104 collects the apparent hand-model inconsistency and asks whether the paired short/full Backpack and Character Sheet documents are superseding versions or independently authoritative.

The implementation does not choose between conflicting source statements. The existing playable Scenario 01 variant remains a useful DODGE 0.2.1 reference while its mechanic-by-mechanic semantic audit continues. After that audit, the clarified new requirements will receive a light DODGE compatibility/boundary audit before implementation. Genuine DODGE gaps are raised upstream rather than patched with Wretched-only semantics; the revised design can then become another DODGE-derived variant, providing a practical test of the requirements → DODGE → resolver → targets workflow.

PR #105 continued that audit by removing encounter-ID gameplay branching in favor of canonical structured effects. The room-setup audit follows the same ownership rule for room-specific setup facts.


## Multi-game source layout

Refactored authored source under `game/<game-id>/`, preserving Wretched Scenario 01 as the reference scenario, reserving Wretched Scenario 02, moving the original Fountain prototype into its own namespace, and creating a clean GURPS/DODGE incubation namespace. Added descriptor-based game/scenario discovery while leaving historical generated Beta builds untouched.


## DIRPS onboarding reset and G0 scaffold

### PR replacement for #162 — make the second game honest about its maturity

**October 11, 2026.**

The first DIRPS pull request was a useful stress test of the new multi-game layout, but review exposed an important process gap. The scaffold looked similar to Wretched and the repository CI was green, yet the DIRPS DODGE document itself had never been validated against the exact DODGE 0.2.1 schema. It also proposed a broad set of RPG-shaped future concepts before Scenario 01 had exercised them. The result was good architectural thinking without the evidence chain that made Wretched a real DODGE reference implementation.

That failure mode drove three repository/tooling changes before DIRPS continued: DODGE gained a versioned implementation golden path; TheFountain gained `docs/ADDING_A_GAME.md`; and TheFountain CI gained generic registered-game conformance discovery. Those changes made maturity explicit rather than inferred from directory shape or an unrelated green workflow.

DIRPS was then rebased from current `main` as an explicit **G0 — Scaffold**. The old reserved `game/gurps/` namespace was replaced by `game/dirps/`, keeping GURPS Lite as an external rules reference rather than the implementation identity. Scenario 01, *The Missing Courier*, preserves the useful source, compatibility audit, provisional DODGE working document, and proto sidecar from the original experiment, but it now makes no schema/core/runtime/target conformance claim.

The proto sidecar was also reclassified. Dice resolution, derived values, expression graphs, lookup tables, procedure-local context, reaction timing, secret state, RPG actor/skill organization, resolution traces, and replay history are now recorded as **suspected** gaps. They follow the progression `suspected → exercised → candidate`; none is a DODGE 0.2.2 proposal until Scenario 01 actually proves the need through the shared validation/resolver/runtime path with evidence.

**Milestone:** a second game can now enter TheFountain honestly at G0 without being mistaken for a conforming implementation, and the repository has a deterministic process for advancing it through G1–G7.

The next DIRPS convergence inventory remains issue #163.


## DIRPS Scenario 01 reaches G1 schema validity

**October 11, 2026.**

DIRPS Scenario 01, *The Missing Courier*, advanced from the PR #166 G0 scaffold to **G1 — Schema-valid** using the generic registered-game conformance path. The exact CI-pinned DODGE source is commit `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`, with `draft/v0.2.1/schemas/dodge.schema.v0.2.1.json` as the candidate schema.

Exact schema validation exposed the expected structural defect across all eight actor value definitions: `st`, `dx`, `iq`, `ht`, `hit-points`, `fatigue`, `stunned`, and `unconscious` lacked required `owner_scope` and `persistence_scope`. The redundant general `scope: actor` declarations were replaced with explicit `owner_scope: actor` and `persistence_scope: scenario`. Because persistence beyond this bounded tutorial is not yet established, each value records that post-scenario persistence remains unresolved rather than inventing campaign semantics at G1.

The registry now declares G1, causing `tools/validate_registered_dodge.py` to validate DIRPS instead of intentionally skipping it. This transition makes no G2 core-valid, semantic-profile, resolver, runtime, replay, target, or proto-promotion claim. Issue #163 remains the convergence inventory; G2 is next.


## Conformance CI records exact candidate source identity

**October 11, 2026.**

Review of DIRPS PR #168 found that the generic conformance workflow was candidate-specific but used GitHub's default pull-request synthetic merge checkout. That proved the candidate merged with the current base, but it did not literally prove the PR-head SHA required by the G1 handoff.

The repository now treats source identity as part of conformance evidence. Pull-request conformance checks out the exact PR head, reports the TheFountain SHA being validated, and asserts that the checkout matches the expected head before running the registered-game pipeline. Push/main and manual runs continue to use the triggering `github.sha`. The onboarding guide, review process, and technical architecture record the same invariant so future maturity reviews do not infer exact-head evidence from a synthetic merge run.

This closes the repository-level provenance gap discovered in TheFountain issue #169; it does not change DODGE semantics or raise DIRPS beyond G1.


## DIRPS Scenario 01 reaches G2 core validity

**October 11, 2026.**

DIRPS Scenario 01 advanced from the merged PR #168 G1 baseline to **G2 — Core-valid** by auditing the candidate against every DODGE 0.2.1 `DODGE_SPEC.md` §15.3 base rule and conditional group. The exact DODGE revision remains `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`.

The G2 audit found two real G1-era core gaps. The tutorial turn used unnamed legacy choice options, so it now uses stable named `choice_options`. The scenario also declared a prose-only end condition; because §15.3 requires deterministic end-condition evaluation, that executable declaration was removed rather than inventing completion state. Completion intent remains preserved in the prose objective and Scenario 01 source for later formalization.

The durable evidence record is `game/dirps/docs/g2-core-validation.md`. It records PASS/N/A for all twelve base checks plus the representation, target-content, invocation, and requirements/modifiers/choices/equipment conditional groups. `tests/test_dirps_g2_core.py` makes those applicability assumptions executable and includes negative fixtures for missing refs, face-slot mismatch, procedure cycles, duplicate scene IDs, wrong-kind rule refs, invalid defaults, prose-only end conditions, and duplicate choice IDs.

The repository onboarding/review docs now require this check-by-check G2 evidence format, closing TheFountain issue #170's documentation gap. No DIRPS semantic profile, resolver, executable dice, replay system, target, UI, or proto promotion was added. **G3 — Semantic-valid** is next.


## DIRPS Scenario 01 reaches G3 semantic validity

**October 11, 2026.**

Starting from merged PR #171 and current `main`, DIRPS Scenario 01 advanced from **G2 — Core-valid** to **G3 — Semantic-valid** at the DODGE source stage. The exact DODGE revision remains `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`.

The G3 audit separated generic DODGE core rules from game-owned implications. DIRPS now declares `dirps@0.1.0` through the DODGE 0.2.1 validation lifecycle, backed by `tools/dirps_semantic_validation.py`. The profile validates canonical PC build consistency, explicit actor initialization, DIRPS action/procedure meaning, tutorial action-choice synchronization, concrete combat-opponent presence, target-duration duplication, source/proto provenance, and the boundary between authoritative GURPS mechanics and provisional Scenario 01 composition.

The durable evidence record is `game/dirps/docs/g3-semantic-validation.md`. It also records what G3 deliberately does **not** claim: social/environmental encounter execution, active defense, damage/injury, recovery execution, deterministic scenario completion, dice terms, replay, or resolved semantics. Those remain future-gate concerns; all proto-sidecar concepts remain `suspected`.

No neutral resolver, resolved-game validator, executable dice/runtime, replay machinery, target, UI, or proto promotion was added. **G4 — Resolved** is next.


## Semantic validator version identity is enforced generically

**October 11, 2026.**

Independent review of DIRPS G3 exposed a reusable TheFountain orchestration gap: the generic DODGE conformance runner loaded a declared `semantic_validator` source without checking that its source `version` matched the required profile `version`. DODGE 0.2.1 §15.1 already requires version-mismatched validators to hard-fail.

The generic `profile_modules()` path now rejects a source/profile version mismatch before importing the validator module. A focused regression test proves the mismatch fails before module loading, while matching profiles continue through the existing lifecycle. This fixes TheFountain #174 as part of PR #172 without adding DIRPS-specific runner logic or expanding the G3 tranche into G4.


## DIRPS Scenario 01 reaches G4 neutral resolution

**October 11, 2026.**

Starting from accepted/merged G3 PR #172, DIRPS Scenario 01 advanced to **G4 — Resolved** on the same pinned DODGE 0.2.1 revision, `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`.

TheFountain now registers `tools/resolve_dirps_dodge.py` as the one DIRPS neutral resolver. It consumes the already G3-valid DODGE/scenario/sidecar sources and produces `dirps-resolved-game.v1`: source/provenance metadata, canonical scenario identity and ordered encounters, concrete selected scene instances, the canonical PC ST/DX/IQ/HT build plus additional actor state, skills/equipment, normalized rules/actions/procedures, target duration, and preserved proto material.

The existing `dirps@0.1.0` profile now declares both `source` and `resolved-game` stages. Resolved-stage validation compares the exact model back to the authoritative inputs and rejects dropped or invented semantics. `tests/test_dirps_resolution.py` adds perturbation evidence for canonical PC values and encounter ordering, provenance preservation, proto preservation, and visible failure on missing required semantics.

No executable dice, RNG, success/failure resolution, reaction/damage runtime, replay, divergence detection, target, or proto promotion was added. All proto entries remain `suspected`. **G5 — Executable** is next.


## DIRPS Scenario 01 reaches bounded G5 execution

**October 11, 2026.**

Starting from accepted/merged G4 PR #175, DIRPS Scenario 01 advanced to **G5 — Executable** for one deliberately narrow mechanic on the pinned DODGE 0.2.1 revision `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`.

`tools/dirps_runtime.py` now consumes only `dirps-resolved-game.v1` and executes `attempt-skill → success-roll` using an explicitly selected resolved character skill plus supplied deterministic die terms. The 3d6/sum/lte/output contract comes from the preserved DIRPS proto sidecar. A new sidecar `g5_execution_bindings.attempt-skill` declaration owns the otherwise-missing relationship between runtime `skill_ref`, the resolved character skill value, and the effective target; the runtime does not hard-code a skill target or reread authored source.

`dirps-execution-result.v1` records action/procedure identity, effective target, all die terms, total, success/failure, margin, and an explicit authority chain: authoritative GURPS rule identity, provisional DIRPS proto-binding identity, and provisional Scenario 01 target data with `prototype_assumption` character provenance. The G5 binding now limits the simplified binary comparator to effective targets 4..16; out-of-domain targets fail visibly rather than approximating unimplemented edge semantics. Single-record re-evaluation detects inconsistent recorded evidence, including provenance tampering, without introducing a generalized session replay framework. Perturbation tests change the prototype Tracking value through the scenario source + DODGE extension → G4 resolver path and prove the runtime follows the changed resolved value.

Actual runtime evidence moves `dice_resolution`, `procedure_context`, `actor_character_model`, `skill_model`, and `resolution_trace` from `suspected` to `exercised`. None becomes a DODGE candidate. Derived/modifier semantics and immutable replay/session history remain `suspected`.

No RNG, full skill/default system, social/environmental/combat/recovery runtime, complete scenario completion, Web/CLI/PnP/TTS target, or target manifest was added. G6 remains out of scope.


## DIRPS Scenario 01 reaches G6 with a thin debug target

**October 11, 2026.**

Starting from accepted/merged G5 PR #176, DIRPS Scenario 01 advanced to **G6 — Targeted** on the pinned DODGE 0.2.1 revision `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`.

The first target is intentionally a Python debug CLI, `tools/dirps_debug_target.py`, because the accepted DIRPS resolver/runtime are Python while the mature Wretched Web implementation uses its own JavaScript runtime stack. Choosing the CLI avoids either duplicating gameplay rules in a browser client or introducing a new server/build bridge merely to satisfy G6.

The runtime now exposes `describe_attempt_skill()` so targets can inspect the already-accepted executable capability, resolved actors/skills, dice contract, target domain, and provenance without reconstructing those semantics. The CLI calls that inspection API and `execute_attempt_skill()`, passes successful runtime result objects through unchanged, and turns runtime failures into visible error views without guessing outcomes.

Target tests prove the full source → DODGE → resolver → runtime → target perturbation path, inject fake runtime results to prove no target-side recomputation, smoke-test the registered CLI entry point, expose all three G5 authority layers, and verify unsupported mechanics are absent from the target surface. The target is registered through the existing `generated_targets` map.

The debug CLI does not use DODGE's export-contract/target-manifest model, so no fake manifest was introduced. No proto concept changes maturity at G6. No Web client, generated RNG, additional RPG mechanics, or G7 reference claim was added.
