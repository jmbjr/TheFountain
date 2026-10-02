# Implementation Process

This document is the working adapter between game-domain leadership and implementation. It describes the process we want to reuse when moving from a Design Lead's requirements to a DODGE-backed playable game.

It is deliberately not a project history. `HISTORY.md` records what happened; this file records the practices we want to repeat.

## Roles and authority

### Design Lead
Owns intended player experience, game rules, terminology, creative direction, and unresolved design decisions. Source material may be prose, diagrams, PDFs, spreadsheets, issue comments, or playtest feedback.

### Integration / Implementation Lead
Owns convergence: deciding what is ready to implement, keeping scope visible, testing builds, relaying domain clarifications, and deciding when a candidate is ready to promote.

### Implementation
Translates requirements into canonical game data, DODGE semantics, shared runtime behavior, validation, tests, and target artifacts. Implementation must expose ambiguity rather than silently inventing game design.

No implementation target is allowed to become an independent source of game truth.

## The core pipeline

```text
Design requirements / GDD
        |
        v
lossless source sidecar
        |
        +--> clarification / design issues
        |
        v
canonical scenario data + DODGE document
        |
        v
schema + semantic validation
        |
        v
shared resolver
        |
        v
neutral resolved game
        |
        +--> shared runtime / replay
        +--> Web
        +--> Print-and-Play
        +--> Tabletop Simulator
        +--> simulations / future targets
```

The important boundary is the neutral resolved game. Targets own presentation and packaging. They do not own gameplay rules, component membership, balance values, or scenario-specific exceptions.

## 1. Ingest requirements losslessly

Start with the complete Design Lead source, even when it is large or internally inconsistent. Preserve it in a lossless sidecar or equivalent source representation before normalizing it.

Do not discard facts merely because DODGE cannot yet express them. Do not silently reconcile contradictions. Record provenance and authority so later implementation can distinguish:

- authoritative design intent;
- provisional scenario assumptions needed to make a prototype playable;
- normalized DODGE semantics;
- target-only presentation choices;
- unresolved questions.

When documents disagree, open a focused clarification issue and record which source is authoritative after the Design Lead answers.

## 2. Perform a compatibility audit before implementation

Before building a new scenario or major design revision, inventory the requirements against the exact DODGE version being targeted.

Classify every meaningful requirement:

1. **Already expressible in DODGE** — model it with existing neutral semantics.
2. **Canonical game/scenario fact** — keep it in canonical data referenced by DODGE.
3. **Not expressible in DODGE** — raise a DODGE blocker or specification issue. Do not create a private game-specific DSL to get around the gap.
4. **Legitimate engine detail** — keep the algorithm in runtime code, with the semantic inputs coming from neutral data.
5. **Presentation/target detail** — keep it in the export contract or target renderer.

The output should be a bounded checklist, not an informal list of things to discover later.

## 3. Define the executable scenario contract

Before substantial runtime work, make explicit what the scenario claims to execute.

Specify at minimum:

- selected scenario/variant;
- setup and start state;
- actors and player-count scope;
- resources and limits;
- action costs and targeting;
- topology/materialization rules;
- card/item/room/encounter semantics;
- enemy behavior;
- timing and temporary effects;
- win, retreat, and loss conditions;
- component collections and representations.

Prose-only semantics must be labeled as such. A UI or card must not imply that a behavior is implemented when the runtime ignores it.

For revised designs, prefer a new scenario/variant over silently rewriting a preserved reference implementation. Scenario 1 can remain a reproducible reference while Scenario 2 implements the revised design.

## 4. Get one thin end-to-end slice working

Build the smallest playable vertical slice through the intended architecture:

```text
canonical source
-> DODGE
-> resolver
-> runtime
-> one target
```

The purpose is to test understanding and architecture, not to declare conformance. Early prototypes are allowed to contain explicit provisional assumptions.

Once the slice works, add the other targets through the same resolved source. Do not copy the prototype's game logic into each exporter.

## 5. Iterate through data, not target patches

Playtesting will reveal misunderstandings and design changes. Prefer changing canonical data or neutral semantics and regenerating targets.

For each requested tweak, ask:

- Is this a design fact?
- Is it a DODGE semantic?
- Is it runtime machinery?
- Is it presentation only?
- Does it expose an ambiguity that needs the Design Lead?

Avoid “just make Web do this” fixes when PnP/TTS would then describe a different game.

## 6. Use perturbation tests to prove authority

A test that merely reproduces today's expected value can pass while the value remains hardcoded.

For migrated semantics, deliberately change the canonical identity/value in a test and verify runtime behavior follows it. Examples:

- change a spawn enemy;
- change a threshold;
- change a start room;
- change an extraction condition;
- change an effect amount;
- change a required item.

This proves that data is authoritative rather than coincidentally matching a literal in the engine.

Also test negative cases: missing required normalized semantics should fail validation instead of silently falling back to historical defaults.

## 7. Audit the whole system before convergence

Do not rely indefinitely on finding one hardcoded mechanic at a time.

After the first iterative implementation phase, perform a bounded whole-system semantic audit across:

- canonical scenario data;
- DODGE document and sidecars;
- resolver;
- runtime/model;
- renderer/action dispatch;
- tests and replay;
- every exporter;
- CI/release seams.

Classify findings into:
- duplicate/hardcoded executable semantics;
- declared but unimplemented behavior;
- timing/state/end-condition gaps;
- target/resolver parity problems;
- genuine DODGE/design blockers;
- legitimate engine machinery.

Create one master convergence issue with all findings and a proposed PR decomposition. That issue becomes the inventory. New work maps to it; genuinely new findings are added with an explanation of why the audit missed them.

This prevents a sequence of tiny PRs from hiding whether the project is 10% or 90% complete.

## 8. Batch fixes by architectural concern

Do not default to one PR per literal. Group related findings where they share an ownership boundary or runtime abstraction.

Good batches include:

- compatibility fallbacks and aliases;
- action execution/cost/target binding;
- timed card effects and equipment;
- room/search/encounter conditions;
- crew abilities;
- enemy AI/status/end conditions;
- target-manifest parity.

A PR should still be small enough to review and perturb. “Coherent” is more important than “tiny.”

After each conformance PR:
1. run unit/perturbation tests;
2. run DODGE validation;
3. build the relevant targets;
4. update the master audit checklist;
5. feed reusable conformance lessons back to the DODGE conformance guide.

## 9. Preserve deterministic evidence

Record source Git identity in generated builds and replay files. Generated artifact commits are not new gameplay versions.

Keep old executable Beta builds immutable when practical. A replay has two separate questions:

- Does it reproduce under its originating build?
- Does it conform to the current build?

Saved snapshots after replay divergence are inspection evidence, not proof that later actions reproduced.

## 10. Separate Beta convergence from Stable

Beta is the integration and convergence environment. Stable is preserved for Design Lead review and should not be mutated by ongoing implementation.

Promote only after the declared gate is satisfied:
- schema and semantic validation;
- shared resolver;
- runtime-state and topology conformance;
- deterministic inventory;
- target parity;
- scenario acceptance playtest;
- blockers resolved or explicitly deferred;
- exact DODGE revision recorded.

## Scenario 2 starting checklist

When the revised Wretched design becomes Scenario 2, start here rather than copying Scenario 1 code:

- [ ] Identify the authoritative Design Lead sources and preserve them losslessly.
- [ ] Resolve contradictory sources through explicit clarification.
- [ ] Audit every requirement against the current DODGE spec before coding.
- [ ] Create a bounded compatibility/conformance issue.
- [ ] Define Scenario 2's executable scope, including multiplayer, topology, card availability, Backpack, enemy AI, and timing.
- [ ] Represent Scenario 2 as canonical data / DODGE configuration rather than overwriting Scenario 1.
- [ ] Produce the neutral resolved Scenario 2 model.
- [ ] Build the thinnest shared-runtime vertical slice.
- [ ] Add perturbation tests immediately for every promoted semantic.
- [ ] Generate targets from the same resolved source.
- [ ] Run a whole-system audit before calling the scenario converged.
- [ ] Promote only through the declared release gate.

## Rules of thumb

**Preserve before normalizing.** Source fidelity lets us recover from misunderstandings.

**Ask before inventing.** Ambiguity belongs with the Design Lead, not hidden in runtime code.

**Normalize once.** Resolver/runtime/exporters should not independently interpret the same rule.

**Fail loudly at authority boundaries.** Missing required semantics are errors, not invitations to resurrect historical defaults.

**Perturb, don't merely snapshot.** A changed input proving changed behavior is stronger evidence than a test of today's constant.

**Audit in bulk before declaring convergence.** Iteration discovers the domain; the whole-system audit establishes the remaining scope.

**Keep variants reproducible.** A new design should be a new scenario/variant when preserving the old one helps comparison, replay, and process learning.

**Targets render; they do not design.** Web, PnP, TTS, and future targets consume the game. They do not define it.
