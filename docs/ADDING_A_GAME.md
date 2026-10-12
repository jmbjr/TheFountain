# Adding a Game to TheFountain

This is the repository-specific onboarding guide for adding a new game or a major new game implementation to TheFountain.

It assumes the implementation targets DODGE and follows the portable lifecycle defined by the DODGE implementation guide:

- `jmbjr/DODGE/draft/v0.2.1/IMPLEMENTATION_GUIDE.md` for DODGE 0.2.1;
- `PROCESSES.md` for TheFountain's implementation principles;
- this document for exact TheFountain paths, files, CI expectations, and reference implementations.

The short version is:

```text
source / rules / GDD
        ↓
compatibility audit
        ↓
game/<game-id>/ + scenario source
        ↓
DODGE document
        ↓
candidate-specific schema/core validation
        ↓
game semantic validation
        ↓
one neutral resolver
        ↓
resolved-game validation
        ↓
one executable vertical slice
        ↓
deterministic / negative / perturbation evidence
        ↓
one target
        ↓
whole-system audit
```

Do not skip a gate because another game in the repository already passes it.

---

## 1. Before writing code

Read these first:

1. the exact DODGE version you intend to target;
2. that version's JSON Schemas;
3. the DODGE implementation guide for that version;
4. `PROCESSES.md`;
5. `game/README.md`;
6. the Wretched Demesne reference implementation only as an architectural example.

For DODGE 0.2.1, the current portable guide is:

```text
jmbjr/DODGE/draft/v0.2.1/IMPLEMENTATION_GUIDE.md
```

Wretched Scenario 01 is the mature TheFountain reference, but **copy its architecture, not its game semantics**.

Useful reference files:

```text
game/wretched-demesne/game.json
game/wretched-demesne/dodge/wretched-demesne.dodge.v0.2.1.json
game/wretched-demesne/scenarios/scenario-01/scenario.json
tools/validate_wretched_dodge.py
tools/wretched_semantic_validation.py
tools/resolve_wretched_dodge.py
tests/test_wretched_validation.py
tests/wretched-runtime.test.mjs
.github/workflows/dodge-conformance.yml
```

---

## 2. Use the DODGE maturity gates

TheFountain uses the non-normative maturity vocabulary from the DODGE 0.2.1 implementation guide:

| Gate | Meaning in TheFountain |
|---|---|
| **G0 — Scaffold** | Game namespace, source material, compatibility audit, and initial DODGE work exist. |
| **G1 — Schema-valid** | The candidate DODGE document validates against the exact selected DODGE schema. |
| **G2 — Core-valid** | Full generic DODGE core checks pass for the candidate. |
| **G3 — Semantic-valid** | Candidate-specific semantic validation passes. |
| **G4 — Resolved** | One neutral resolver produces a resolved model and resolved validation passes. |
| **G5 — Executable** | At least one bounded mechanic executes from the resolved model. |
| **G6 — Targeted** | At least one target consumes the resolved/runtime semantics. |
| **G7 — Reference** | The implementation has enough validation, perturbation, replay/evidence, and target experience to serve as a reference. |

These are review labels, not DODGE schema fields.

Every new game PR should state the highest gate it actually reaches.

CI evidence must also identify the TheFountain source revision actually validated. For pull requests that require exact-head evidence, the conformance workflow must check out `github.event.pull_request.head.sha` (or otherwise prove that literal source identity); GitHub's default synthetic merge ref is useful merge-compatibility evidence but is not exact PR-head evidence. A named candidate PASS only supports a maturity claim when it is tied to the source SHA that the workflow actually validated.

Do not use vague labels such as "prototype" as a substitute for saying which gate is complete.


### G2 evidence contract

G2 is not satisfied by schema success or by a single opaque "core valid" label. Review the exact selected DODGE version's `DODGE_SPEC.md` §15.3 and `IMPLEMENTATION_GUIDE.md` §9 check by check.

Until a reusable DODGE-owned core validator covers the selected contract, record a candidate evidence matrix with one row for every §15.3 base item and every conditional group:

```text
Check: <§15.3 item / conditional group>
Applicability: PASS | N/A
Evidence: <validator/test/file/fixture>
Notes: <why N/A or what invariant is proven>
```

The G2 record must include the exact DODGE revision/version and exact TheFountain candidate SHA. It must distinguish unconditional checks from conditional groups such as representations, target content configuration, invocations, and requirements/modifiers/choices/equipment. For invariants that need behavioral proof, include negative fixtures showing invalid candidates are rejected.

A `PASS ... schema` line is G1 evidence only. G2 requires complete §15.3 evidence for the candidate itself. N/A is acceptable only when the feature is genuinely absent and the evidence makes that absence auditable so later additions cannot silently reuse stale evidence.

---

## 3. Create the game namespace

Each game lives under:

```text
game/<game-id>/
```

Minimum recommended structure:

```text
game/<game-id>/
├── game.json
├── README.md
├── dodge/
│   └── <game>-<scenario>.dodge.v<version>.json
├── sidecars/
├── docs/
│   └── compatibility-audit.md
└── scenarios/
    └── <scenario-id>/
        ├── README.md
        ├── scenario.json
        └── export-contracts/
```

Optional directories may be added when the game needs them, but the source-of-truth boundary must remain obvious.

Generated Web/PnP/TTS artifacts do **not** belong under `game/`.

---

## 4. Register the game

Create:

```text
game/<game-id>/game.json
```

The immediate child directory name must match the descriptor's `id`.

A typical scenario descriptor looks like:

```json
{
  "registry_version": "1",
  "id": "my-game",
  "title": "My Game",
  "status": "incubating",
  "scenarios": {
    "scenario-01": {
      "title": "Scenario 01",
      "status": "scaffold",
      "dodge": "dodge/my-game-scenario-01.dodge.v0.2.1.json",
      "source": "scenarios/scenario-01/scenario.json",
      "sidecars": [
        "sidecars/my-game.sidecar.v0.1.json"
      ]
    }
  }
}
```

The exact scenario status vocabulary is repository-owned, but it should not imply more maturity than the implementation has actually demonstrated.

`tools/game_registry.py` discovers `game/*/game.json`.

Adding a game must not require adding a central `if game == ...` list merely to make the namespace visible.

---

## 5. Preserve source authority first

Before normalization, inventory the inputs.

Examples:

- GDD;
- rules PDF;
- spreadsheets;
- card/entity catalogs;
- issue decisions;
- prototype assumptions;
- external rules references.

For every important input, classify it as:

- authoritative;
- derived;
- provisional;
- reference.

Do not silently reconcile contradictory sources.

Preserve unsupported semantics in a declared sidecar or equivalent source rather than dropping them.

A game-specific sidecar is a bridge for information DODGE does not yet normalize. It must not become an unvalidated private rules engine.

---

## 6. Write a bounded compatibility audit

Create:

```text
game/<game-id>/docs/compatibility-audit.md
```

Audit only the mechanics required by the first bounded scenario.

Use at least these classifications:

| Requirement | Classification | Treatment |
|---|---|---|
| already expressible in selected DODGE | DODGE | normalize it |
| canonical game/scenario fact | canonical source | reference it |
| not cleanly expressible | candidate gap | sidecar/extension, do not hide in target |
| implementation algorithm | runtime | data-driven algorithm only |
| target-only detail | target | export contract/renderer |

The audit may identify future DODGE gaps, but treat them as **suspected** until the scenario actually exercises them.

Do not design an entire future DODGE revision before building the first vertical slice.

---

## 7. Define a small executable Scenario 01

The first scenario should be deliberately small.

Its purpose is to test the architecture, not to encode the full game.

Document:

- setup;
- actors;
- player-count scope;
- mutable values/resources;
- available actions;
- procedure/phase ordering;
- objects/collections;
- objective;
- win/loss/retreat conditions;
- the exact mechanics the scenario claims to exercise.

Create an executable-claims table in the scenario README or compatibility audit.

Example:

| Claimed mechanic | Canonical source | DODGE binding | Runtime | Test |
|---|---|---|---|---|
| skill check | scenario/rules | action/procedure | ✅ / ❌ | ✅ / ❌ |
| interaction | scenario | invocation/action | ✅ / ❌ | ✅ / ❌ |
| attack | rules | action/procedure | ✅ / ❌ | ✅ / ❌ |
| defense/reaction | rules/proto | procedure | ✅ / ❌ | ✅ / ❌ |
| injury/state change | rules | effect/procedure | ✅ / ❌ | ✅ / ❌ |

This prevents a descriptive scenario from being mistaken for an executable one.

A prose-only procedure is not an executable mechanic.

---

## 8. Keep one canonical authority path

Every executable fact should have one authority path.

Avoid this:

```text
scenario.json       DX = 11
DODGE scene state   DX = 11
runtime default     DX = 11
```

Prefer:

```text
canonical scenario/source
        ↓
DODGE references/selects it
        ↓
resolver
        ↓
runtime
```

If duplication is unavoidable, the game semantic validator must enforce consistency.

For important migrated semantics, add a perturbation test:

```text
change canonical input
→ resolve again
→ assert runtime/resolved output changed
```

A passing snapshot is not enough to prove authority.

---

## 9. Build the DODGE document

Create the DODGE document under the game namespace.

For example:

```text
game/<game-id>/dodge/<game>-scenario-01.dodge.v0.2.1.json
```

Use the **exact** selected DODGE schema.

Do not infer field shapes from:

- memory;
- another DODGE version;
- a different game;
- a similar field name.

### Hard gate: G1

Before claiming any DODGE conformance:

> validate the candidate document itself against the exact schema for the selected DODGE version.

For 0.2.1:

```text
jmbjr/DODGE/draft/v0.2.1/schemas/dodge.schema.v0.2.1.json
```

A repository-wide green CI badge is not enough.

---

## 10. Declare the conformance pipeline; CI discovers it

TheFountain now discovers registered DODGE-backed scenarios through:

```text
tools/validate_registered_dodge.py
```

The workflow no longer needs one hardcoded block per game for the standard DODGE lifecycle.

For an active scenario, add a repository-specific resolver declaration to `game.json`:

```json
{
  "conformance": {
    "maturity": "G4",
    "resolver": "tools/resolve_my_game_dodge.py"
  }
}
```

The resolver path is repository-root-relative and must point to a Python module exposing:

```python
def resolve_context(context, export_contract_path=None):
    ...
```

Game/application semantic validators are **not** listed again in `game.json`. Declare them in the DODGE document using `validation.required_profiles` and a `semantic_validator` source. The required profile version must exactly match the referenced semantic-validator source `version`; the generic conformance runner hard-fails a mismatch before importing or invoking the validator. The referenced validator module must expose the TheFountain hooks:

```python
def validate_source_context(context):
    return []  # or error strings

def validate_resolved_context(context):
    return []  # or error strings
```

The context contains the discovered game/scenario config, parsed DODGE document, canonical scenario source when present, and—at the resolved stage—the exact resolved model.

The generic runner now performs, for every discovered active DODGE scenario:

```text
exact-version DODGE schema
→ export-contract schema(s)
→ declared semantic source profile(s)
→ declared neutral resolver
→ declared semantic resolved-game profile(s)
→ resolved target-manifest schema(s) for G6/G7 scenarios
```

A DODGE-backed scenario without a conformance declaration is an error unless it is explicitly `planned` or `scaffold`. A `G0` conformance declaration is also explicitly skipped.

### Test discovery

Python tests are discovered by:

```text
tests/test_*.py
```

Runtime JavaScript tests are discovered by:

```text
tests/*-runtime.test.mjs
```

Adding tests that follow those conventions does not require editing the workflow.

### Important

A green CI result now means the generic runner discovered the registered active DODGE scenarios present in that checkout and ran their declared standard conformance stages. Still inspect the named PASS/SKIP lines when reviewing maturity claims.

The DIRPS scaffold failure mode that motivated this work—green CI validating Wretched while never reading the new DIRPS DODGE document—is now structurally blocked once DIRPS is registered as an active conformance candidate.

---

## 11. Add candidate-specific semantic validation

Schema/core validity cannot know game-domain completeness.

Create a game-owned semantic validator when the game has domain implications that DODGE core cannot infer.

Recommended pattern:

```text
tools/<game>_semantic_validation.py
tests/test_<game>_validation.py
```

Examples of game-owned contracts:

- a capability implies an executable invocation;
- a tutorial encounter claiming combat actually binds to combat semantics;
- a domain field references a valid entity;
- duplicated unavoidable facts agree;
- scenario-required collections are complete;
- a game-specific extension has the expected shape.

Declare required validation profiles in the DODGE document when appropriate for the selected DODGE version.

### Hard gate: G3

Do not resolve or generate targets when required semantic validation fails.

---

## 12. Build one neutral resolver

Recommended pattern:

```text
tools/resolve_<game>_dodge.py
```

The resolver should:

1. start from the DODGE document;
2. follow declared source references;
3. preserve authority/provenance;
4. select the intended scenario/scene;
5. resolve canonical entities and semantic collections;
6. expose unresolved/prose-only semantics honestly;
7. produce one neutral resolved model.

Example resolved identity:

```text
<game>-resolved-game.v1
```

The exact format is game-owned unless later standardized by DODGE.

Do not build separate Web/PnP/TTS interpretations of the game.

### Hard gate: G4

Validate the exact resolved model before runtime or target generation.

---

## 13. Implement one executable vertical mechanic

Do not attempt the entire game at once.

Choose one mechanic that crosses the full architecture:

```text
canonical source
→ DODGE
→ validation
→ resolver
→ runtime
→ result/state evidence
```

Examples:

- draw and resolve one card;
- perform one skill check;
- execute one attack;
- enter one hazardous room;
- equip/use one item.

For rules-heavy games, a CLI/debug harness is acceptable as the first runtime surface.

The first goal is to prove the neutral semantic path, not visual polish.

### Hard gate: G5

At least one mechanic must execute from the resolved model rather than from target-specific literals.

---

## 14. Add deterministic, negative, and perturbation tests

Use all three.

### Deterministic

Given the same declared inputs and random evidence/seed, reproduce the same result/state transition.

### Negative

Remove or corrupt a required semantic fact and prove validation rejects it before runtime.

### Perturbation

Change an authoritative input and prove resolved/runtime behavior follows it.

These tests are especially important when migrating from a prose rules source because they prove the runtime is following the neutral source rather than historical code constants.

---

## 15. Add replay or resolution evidence when the game needs it

Not every game needs the exact Wretched replay format.

But if the game depends on:

- random resolution;
- teaching/explanation;
- source-rule traceability;
- deterministic debugging;
- session continuation;

then preserve enough evidence to inspect or reproduce the result.

Wretched's replay system is a reference for the architectural property:

> current-build output must be reproducible under its originating build, and rejected actions must not mutate state or append replay history.

Copy the invariant, not necessarily the file format.

---

## 16. Add one target only after the neutral boundary works

A first target may be:

- Web;
- CLI/debug;
- PnP;
- TTS;
- simulation;
- another project-specific adapter.

The target must consume the resolved/runtime model.

It may own:

- layout;
- typography;
- transforms;
- platform IDs;
- interaction adaptation;
- packaging.

It must not own:

- canonical stats;
- scenario objectives;
- collection membership;
- domain validation fixes;
- fallback rules.

### Hard gate: G6

A target passes only when its gameplay behavior comes from the resolved/runtime semantics.

---

## 17. Add export contracts/manifests when applicable

If the target uses the DODGE target-contract model:

```text
game/<game-id>/scenarios/<scenario-id>/export-contracts/
```

The target contract may choose:

- supported forms/features;
- representation selection;
- presentation grouping;
- target-owned variants;
- explicit noncanonical playtest quantities.

It may not redefine the game.

Where a resolved target manifest is emitted, validate it against the exact DODGE manifest schema and preserve validation evidence.

---

## 18. Do not promote speculative DODGE gaps too early

Use this progression:

```text
suspected
→ exercised
→ candidate
```

**Suspected**  
The source suggests a missing neutral concept.

**Exercised**  
The bounded scenario actually needs it.

**Candidate**  
A target-neutral representation is implemented, validated, executed, and supported by evidence; it appears reusable beyond the originating game.

Only candidate-level concepts should normally become upstream DODGE proposals.

A sidecar may preserve all three states, but implementation should focus on the minimum exercised subset.

---

## 19. First-PR guidance

The first PR for a new game does not need to reach G6 or G7.

It may intentionally be a G0 scaffold.

But the PR description should say that explicitly.

A useful first-PR template:

```text
Goal:
- establish <game> namespace
- preserve source authority
- define bounded Scenario 01
- complete compatibility audit

Maturity:
- G0 Scaffold

Not yet claimed:
- schema conformance
- semantic validation
- resolver
- runtime
- target parity
```

If the PR claims G1 or higher, the corresponding gate must be executable in CI.

---

## 20. Definition of ready for a reference implementation

A new game is comparable to Wretched as a DODGE reference implementation when:

- [ ] exact DODGE schema validation passes;
- [ ] full generic DODGE core checks pass;
- [ ] game-owned semantic validation passes;
- [ ] one neutral resolver exists;
- [ ] resolved-game validation passes;
- [ ] canonical facts have one authority path;
- [ ] perturbation tests prove that authority path;
- [ ] one bounded scenario executes its claimed mechanics;
- [ ] random/state evidence is inspectable where relevant;
- [ ] at least one target consumes the resolved/runtime model;
- [ ] target code does not redefine gameplay semantics;
- [ ] unresolved semantics fail visibly rather than being guessed;
- [ ] only exercised generic gaps are proposed upstream.

That is roughly G7.

---

## 21. Whole-system convergence audit

After the first working vertical slice, perform a bounded audit across:

- canonical scenario source;
- DODGE document;
- sidecars/extensions;
- semantic validator;
- resolver;
- resolved model;
- runtime;
- replay/evidence;
- tests;
- target adapters;
- CI;
- generated artifacts.

Classify findings into:

- duplicated/hardcoded semantics;
- declared but unimplemented mechanics;
- missing timing/state/end conditions;
- source-authority conflicts;
- target/resolver parity gaps;
- genuine DODGE gaps;
- legitimate runtime machinery;
- presentation-only work.

Create one convergence issue containing the inventory.

This is the point where the implementation moves from iterative discovery toward reference quality.

---

## 22. Reference implementation map

### Wretched Demesne — mature reference

Use Wretched to understand the complete architecture:

```text
game/wretched-demesne/
tools/wretched_semantic_validation.py
tools/resolve_wretched_dodge.py
tools/validate_wretched_dodge.py
tests/test_wretched_validation.py
tests/wretched-runtime.test.mjs
```

Wretched demonstrates:

- source/sidecar authority;
- DODGE normalization;
- semantic validation;
- neutral resolution;
- deterministic replay;
- perturbation testing;
- Web/PnP/TTS target convergence.

It also contains historical complexity. Do not assume every Wretched-specific concept should be copied into another game.

### DODGE 52-card example — small complete reference

Use:

```text
jmbjr/DODGE/draft/v0.2.1/examples/standard-52-card-deck/
```

for a much smaller complete source → validate → resolve → target-contract example.

### DODGE validation lifecycle example

Use:

```text
jmbjr/DODGE/draft/v0.2.1/examples/validation-lifecycle/
```

to understand why a core-valid document can still be rejected by a game semantic profile.

---

## 23. Generic conformance discovery

TheFountain has both generic game discovery and generic standard DODGE conformance discovery.

`tools/game_registry.py` discovers game/scenario descriptors.

`tools/validate_registered_dodge.py` discovers every scenario with a DODGE document and uses:

- the document's own `dodge_version` to select the exact checked-out DODGE version root;
- the DODGE `validation.required_profiles` declaration to discover semantic validators;
- the scenario's small `conformance.resolver` declaration to discover the neutral resolver;
- scenario export-contract declarations to validate resolved target manifests.

The descriptor contains no arbitrary shell commands.

Runtime and game-specific regression tests remain normal repository tests and are discovered by filename convention.

A remaining upstream tooling opportunity is a reusable DODGE-owned implementation of every generic section 15.3 core semantic check. TheFountain's generic runner guarantees exact schema/profile/resolver/manifest discovery; it does not claim that a missing upstream generic core-validator executable has been invented locally.

---

## 24. Operational checklist

When a new game arrives with only a rules document/GDD and loose direction, follow this order:

```text
[ ] Read DODGE implementation guide + selected spec/schema
[ ] Create game namespace + game.json
[ ] Preserve source authority
[ ] Write bounded compatibility audit
[ ] Define small Scenario 01 + executable claims
[ ] Create canonical scenario data
[ ] Create DODGE document
[ ] Add conformance declaration so generic CI discovers the candidate
[ ] Pass G1
[ ] Pass full core checks / G2
[ ] Create game semantic validator
[ ] Add negative tests
[ ] Pass G3
[ ] Create one neutral resolver
[ ] Create resolved validator
[ ] Add perturbation tests
[ ] Pass G4
[ ] Execute one full mechanic
[ ] Add deterministic evidence
[ ] Pass G5
[ ] Complete bounded scenario claims
[ ] Add one target
[ ] Pass G6
[ ] Run whole-system convergence audit
[ ] Promote only exercised generic DODGE gaps
[ ] Reach G7 only when evidence supports it
```

The objective is deterministic implementation progress, not merely a familiar-looking directory tree.

A fresh contributor or ChatGPT session should be able to follow this guide from source material to a defensible DODGE implementation without relying on undocumented knowledge from the Wretched development history.
