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

We also added `game/WRETCHED_SCENARIO01_MVP.md`, which records the assumptions and target explicitly. The core acceptance goal is for a playtest to exercise exploration, the five-card hand, three-action turns, searching and loot, firearm ammo and Noise, global Threat, enemy activation, Spider Corpses, feeding, chrysalis/evolution, voluntary retreat, the objective chain, extraction, and both win and loss.

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

Once official DODGE 0.2.0 was available, we migrated Wretched rather than allowing the implementation to become a historical fork. The new `game/wretched-demesne.dodge.v0.2.json` declares DODGE 0.2.0, formally identifies the lossless GDD sidecar and source authority, and adds neutral component profiles. The v0.1 document remains for traceability.

This establishes an ongoing project rule: **Wretched Demesne and its Web/PnP/TTS pipeline must remain compliant with the official DODGE specification.** DODGE changes require deliberate conformance review/migration rather than target-specific workarounds.

**Milestone:** DODGE conformance is now a maintained project constraint.

PR: https://github.com/jmbjr/TheFountain/pull/12


---

## Wretched adopts DODGE 0.2.1 as the working rules model

### PR #14 — Adopt DODGE 0.2.1 for Wretched Demesne

**Opened September 28, 2026.**

After using Scenario 01 to pressure-test the DODGE 0.2.1 draft, we identified four requirements for Wretched adoption: deterministic timing/effect lifetime, explicit subject/resource ownership, atomic transformation semantics, and a clear boundary between unresolved topology generation and materialized runtime topology. Those requirements were captured in DODGE issue #21 and incorporated into the 0.2.1 draft.

PR #14 moves Wretched onto that model. The active working document is now `game/wretched-demesne.dodge.v0.2.1.json`, with representative rules/resources, timing, ownership, spider transformation, topology, Scenario 01 and campaign semantics promoted out of the generic sidecar boundary. Scenario 01 now points to the 0.2.1 document as its DODGE authority, while older DODGE documents remain for traceability.

The governing DODGE specification is still under `draft/v0.2.1`, so this milestone is deliberately a **working adoption**, not a claim of official 0.2.1 conformance. When DODGE publishes `official/v0.2.1/`, Wretched must revalidate the document, semantic rules, resolver and exporters against that exact revision.

No unresolved design question was silently answered during the migration: prose-only semantics remain non-executable, physical corpse/chrysalis supply quantities remain unresolved, and the provisional Medic deck-size inconsistency remains a Wretched data issue.

**Milestone:** DODGE becomes the intended neutral rules/state/topology model for Scenario 01, not only its component-inventory contract.

PR: https://github.com/jmbjr/TheFountain/pull/14


## Beta PnP becomes dimensionally DODGE-driven

Following the first successful Scenario 01 PnP smoke test and DODGE issue #23, Wretched now declares its standard gameplay cards as poker-size components (2.5 × 3.5 in) in the DODGE 0.2.1 document. The Beta PnP exporter resolves those normative dimensions from DODGE instead of owning card size itself. This is the first physical-output gate toward the next Wretched stable release; room/tile sizing and unresolved physical supply quantities remain explicit follow-up decisions rather than exporter inventions.
