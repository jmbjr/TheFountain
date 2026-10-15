# DIRPS G7 — reference validation

Phase J is the whole-system convergence audit for **Scenario 01: The Missing Courier**.

It adds no gameplay mechanic and does not change the accepted runtime contracts. Its purpose is to decide whether the accumulated G1-G6 + Phase A-I evidence is coherent enough for DIRPS to serve as a second DODGE 0.2.1 reference implementation.

## Baseline

- Phase I accepted/merged PR: #187.
- Phase I final head: `bdb396932ddfbb5e6ea92f13a452dcfde72cbc47`.
- Phase I merge SHA: `fbc2a560cfb2b55a24dfa3627e81a20cde0df3fb`.
- Phase I accepted exact-head CI: **38655115162**.
- Phase J branch baseline: post-merge `main` at `00c43f749e301e3993a6725dc61c3b58d049d36e`.
- DODGE 0.2.1 remains pinned by TheFountain CI to `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`.
- Normative schema: `draft/v0.2.1/schemas/dodge.schema.v0.2.1.json`.
- Formal status in this branch is a **G7 — Reference candidate** pending independent review.

Exact-head Phase J CI identity is recorded in PR #188 / #178 / #163 after the final literal candidate passes. This file intentionally does not embed a self-invalidating candidate SHA.

## G7 meaning

The selected DODGE implementation guide defines G7 as enough **validation, perturbation, runtime, replay/evidence, and target experience to serve as a conformance reference**.

G7 does not mean:

- the full GURPS ruleset is implemented;
- every RPG-shaped proto gap is promoted to DODGE;
- every possible target exists;
- intentionally unsupported rules become supported.

The reference claim is bounded to this explicit Scenario 01 scope.

## Phase J roadmap audit

| #178 Phase J criterion | Result | Evidence |
|---|---|---|
| Scenario 01 executes every mechanic it still claims | PASS | executable-claims matrix below; `tests/test_dirps_g7.py`; accepted Phase A-G tests |
| Source authority paths are singular and auditable | PASS | authority matrix below; G3/G4 validation; Phase A-G perturbation/drift tests |
| Schema/core/source/resolved validation remains green | PASS candidate | G1/G2/G3/G4 docs + generic registered-game conformance on final head |
| Runtime semantics are target-neutral | PASS | `tools/dirps_runtime.py`; debug CLI + Web both consume the same resolved/runtime path |
| Perturbation tests cover canonical facts and important rules bindings | PASS | G4/G6 + Phase A-G/H drift/perturbation inventory below |
| Random/result evidence is deterministic/inspectable | PASS | Phase A seeded/supplied terms, Phase E seeded combat, Phase H step evidence |
| Full-session replay/divergence behavior is tested | PASS | `dirps-session-history.v1`; `tests/test_dirps_phase_h.py` |
| At least one target consumes the same runtime semantics | PASS | debug CLI and real browser/Pyodide target |
| Unsupported semantics fail visibly | PASS | Phase B-G negative tests, Phase H source/divergence failures, browser fatal/error surface |
| Proto concepts have evidence-backed maturity states | PASS | proto audit below |
| Candidate DODGE proposals are limited to genuinely reusable concepts | PASS | **no DIRPS proto is promoted**; all remain `not-yet-candidate` |
| Wretched remains green | PASS candidate | final exact-head conformance must retain Wretched schema/source/resolver/manifests/PnP/TTS |
| Whole-system documentation accurately reflects implemented vs unsupported behavior | PASS candidate | this audit + README/ROADMAP/TECHNICAL/HISTORY/scenario metadata updates |

## Executable-claims matrix

The implementation guide requires a project-owned matrix distinguishing prose claims from executable mechanics.

| Scenario claim | Owning source | Normalized / bridge semantics | Runtime evidence | Tests |
|---|---|---|---|---|
| ordinary Tracking success roll with situational modifier | canonical Roadside action/context + GURPS Lite success-roll rules | DODGE `attempt-skill` / `success-roll` + Phase A proto bindings | effective target, deterministic 3d6 result, critical class, trace | `test_dirps_phase_a.py`, `test_dirps_phase_b.py` |
| investigation consequence changes scenario state | canonical Roadside state contract/consequences | DODGE state/effects + Phase B orchestration | `dirps-encounter-result.v1` | `test_dirps_phase_b.py` |
| social/reaction-oriented interaction | canonical Frightened Witness action/modifier/consequences + GURPS Lite reaction rules | Phase C lookup table + runtime binding | `dirps-social-encounter-result.v1` / nested reaction result | `test_dirps_phase_c.py` |
| environmental challenge with clear consequences | canonical Washed-Out Path action/modifier/consequences + GURPS Lite success-roll rules | DODGE `attempt-attribute` + Phase D bridge | `dirps-environment-encounter-result.v1` | `test_dirps_phase_d.py` |
| attack, active defense, damage, injury, state change | canonical Bandit Scout bounded assumptions + GURPS Lite combat rules | DODGE actor state plus Phase E reaction/derived/expression/lookup/damage bridges | `dirps-combat-exchange-result.v1` | `test_dirps_phase_e.py` |
| next-turn consciousness / stun recovery when required | canonical bounded recovery order + GURPS Lite HT rules | DODGE state/effects + Phase F recovery bridge | `dirps-recovery-result.v1` | `test_dirps_phase_f.py` |
| canonical ordered progression and deterministic success/failure completion | canonical `scenario.encounters` + `progression.completion` | DODGE values/conditions/effects/objective/end conditions + narrow Phase G bridge | `dirps-scenario-progression-result.v1` | `test_dirps_phase_g.py` |
| every random result preserved for replay | accepted runtime result records | Phase H session-history contract | exact random inputs, hashes, traces, transition records | `test_dirps_phase_h.py` |
| full run reproducible / first divergence visible | canonical initial state + resolved semantic identity | `dirps-session-history.v1` | complete success/failure replay and fail-first divergence | `test_dirps_phase_h.py` |
| player can use the scenario in a browser without a second rules engine | same resolved/runtime/replay semantics | thin Python Web adapter + pinned Pyodide transport | runtime-described actions/state/result/provenance/history | `test_dirps_phase_i.py`, `dirps-web-smoke.mjs` |

### Claims intentionally not made

The presence of a value, skill, item, or proto idea does not by itself make it an executable Scenario 01 claim.

In particular:

- Area Knowledge and First Aid exist on Rook but Scenario 01 does not claim to exercise them.
- The basic first-aid kit is character inventory but has no executable use in this bounded scenario.
- broader GURPS combat, skill defaults, advantages/disadvantages, long-term healing, death checks, campaign persistence, GM-only state, and secret checks are not claimed.
- long-term waking after the scout becomes unconscious remains explicitly unsupported.

## Authority-path audit

The reference architecture remains:

```text
external GURPS Lite rule authority
          +
canonical Scenario 01 provisional facts
          +
DODGE 0.2.1 normalized semantics
          +
DIRPS proto sidecar only for genuine DODGE gaps
          ↓
DIRPS source semantic validation
          ↓
one neutral resolver
          ↓
dirps-resolved-game.v1
          ↓
resolved-game validation
          ↓
target-neutral Python runtime
          ↓
Phase H replay/evidence
          ↓
debug CLI / browser target
```

Important authority paths:

| Fact / semantic | Authority | Guard against shadow authority |
|---|---|---|
| PC ST/DX/IQ/HT, skills, equipment | canonical scenario, checked against DODGE scene/extension bindings | G3 contradictions + G4 PC perturbation |
| encounter order | canonical `scenario.encounters` | Phase G order perturbation changes runtime progression |
| contextual modifiers | canonical scenario fact with external rule locator where applicable | Phase A/D perturbation and provenance checks |
| success-roll mechanics / HT / combat rules | GURPS Lite external reference + normalized/sidecar bindings | binding validation and rule/source traces |
| actor state/value vocabulary, conditions/effects/end conditions | DODGE document | source + resolved semantic validation |
| reaction table / expression / damage/recovery orchestration gaps | validated DIRPS sidecar | binding-drift tests before execution |
| completion interpretation | canonical `progression.completion` aligned with DODGE conditions/effects/end conditions | Phase G trigger/effect/condition drift tests |
| replay source identity | resolved scene/rules/scenario/runtime + complete sidecar | Phase H pre-step source-identity drift tests |
| action availability | runtime `describe_scenario()` | targets consume the runtime output; target source tests forbid private gameplay literals |

No target is an independent gameplay authority.

## Validation/conformance evidence

### G1 — exact schema

The registered DIRPS DODGE document is validated against the pinned 0.2.1 schema by the generic conformance workflow.

### G2 — complete core validation

`g2-core-validation.md` contains the §15.3 evidence matrix for unconditional and conditional groups. The final G7 candidate must rerun the candidate itself through registered-game conformance; historical G2 evidence alone is not sufficient.

### G3 — source semantic validation

`dirps@0.1.0` source validation rejects authority/provenance drift, character/skill/equipment contradictions, actor-state binding problems, action/procedure mismatches, and phase-specific bridge drift.

### G4 — resolved semantic validation

One resolver, `tools/resolve_dirps_dodge.py`, produces `dirps-resolved-game.v1`. Resolved validation rejects dropped/invented semantics and preserves canonical source/provenance plus unresolved proto material.

## Deterministic / negative / perturbation inventory

Reference quality relies on all three evidence classes rather than snapshots alone.

### Deterministic

- G5 known supplied-dice success/failure.
- Phase A supplied and seeded 3d6 evidence.
- Phase B-D replay from exact recorded random evidence.
- Phase E seeded combat + replay.
- Phase F deterministic ordered checks + replay.
- Phase G deterministic success/failure terminal states.
- Phase H complete success/failure sessions and state hashes.
- Phase I deterministic browser seed preserved in the real browser smoke.

### Negative

- malformed/missing semantic source facts fail validation;
- invalid actors/actions/dice/random-input shapes fail visibly;
- unsupported active defense and bounded-combat repetition fail;
- unsupported/out-of-order/post-terminal scenario actions fail without caller mutation;
- Phase H corrupted hashes/random evidence/source identity fail at the earliest applicable boundary;
- browser bootstrap/request/page failures expose the fatal target surface and fail CI.

### Perturbation / drift

- canonical PC values/skills propagate through resolution/runtime/target evidence;
- canonical encounter order perturbation changes progression;
- contextual modifiers change effective targets;
- Broadsword skill perturbation changes attack resolution;
- reaction/binding/table/expression/combat/recovery bridge drift is rejected;
- terminal trigger/effect/condition drift is rejected before misleading completion;
- Phase H scene/proto semantic drift invalidates replay before step execution.

## Replay/evidence audit

Phase H is the reference replay spine:

```text
accepted initial state
→ declared action + exact random evidence
→ accepted Phase G transition
→ before/after canonical JSON SHA-256
→ exact resolution trace
→ copy-on-append session
→ re-execute every step
→ fail first inconsistent step
```

The replay source identity covers the resolved `scene` and complete resolved `proto_sidecar` in addition to DODGE identity/rules/scenario/runtime state.

This is intentionally target-neutral. The browser consumes the same history contract rather than defining a browser save/replay dialect.

## Target audit

Two registered targets exist:

1. **debug CLI** — low-level reference consumer for runtime capability/result inspection;
2. **Web** — player-facing target using pinned Pyodide to execute the repository's existing Python validator/resolver/runtime in-browser.

The Phase I headless Chromium smoke proves the real transport:

```text
local HTTP checkout
→ /dirps/
→ JS module
→ pinned Pyodide
→ browser fetch/mount of repository files
→ Python imports
→ resolve()
→ runtime describe
→ action click
→ Phase H append/result
→ DOM evidence
```

Neither target owns gameplay rules.

## Unsupported-scope audit

A reference implementation must be trustworthy about what it does **not** implement.

Canonical progression explicitly rejects:

- skipping/reordering outside canonical order;
- repeating an already-resolved encounter;
- continuing after a terminal outcome;
- long-term recovery after the scout becomes unconscious.

Additional intentionally unsupported scope includes broader combat, long-term healing/death, skill defaults, campaign persistence, and hidden/GM-only state.

Unsupported behavior is not guessed by targets.

## Proto maturity audit

Current sidecar state:

| Proto concept | Phase J assessment |
|---|---|
| `dice_resolution` | exercised / not-yet-candidate |
| `derived_values` | exercised / not-yet-candidate |
| `expressions` | exercised / not-yet-candidate |
| `lookup_tables` | exercised / not-yet-candidate |
| `procedure_context` | exercised / not-yet-candidate |
| `reaction_timing` | exercised / not-yet-candidate |
| `actor_character_model` | exercised / not-yet-candidate |
| `skill_model` | exercised / not-yet-candidate |
| `resolution_trace` | exercised / not-yet-candidate |
| `damage_injury` | exercised / not-yet-candidate |
| `replay_session_history` | exercised / not-yet-candidate |
| `visibility_and_secret_state` | suspected / not-yet-candidate |

### Upstream proposal decision

**No DIRPS proto concept is promoted to DODGE in Phase J.**

The concepts above have strong one-game execution evidence, but the project does not yet have enough independent cross-game reuse evidence to justify claiming that any particular DIRPS-private shape is the reusable neutral contract DODGE should adopt.

That restraint is part of the G7 result, not a failure to converge.

Future upstream proposals should compare this DIRPS evidence with Wretched or a third implementation before promotion.

## Whole-system documentation audit

Phase J updates:

- `game/dirps/game.json` — G7/reference candidate registry state;
- canonical Scenario 01 metadata — accepted A-I scope + explicit unsupported remainder;
- DODGE metadata — current conformance claim;
- this G7 validation record;
- `game/dirps/README.md`;
- Scenario 01 README;
- compatibility audit;
- historical G6 note;
- root README;
- TECHNICAL;
- ROADMAP;
- HISTORY;
- #178 and #163.

`PROCESSES.md` does not change because Phase J applies the existing onboarding/review process rather than discovering a new reusable workflow.

## G7 candidate conclusion

The accumulated implementation now satisfies the repository/DODGE meaning of a bounded reference candidate:

- exact selected DODGE version and schema;
- complete candidate-level core evidence;
- source + resolved semantic validation;
- one neutral resolver;
- all bounded Scenario 01 mechanic claims executed;
- source authority guarded by negative/perturbation evidence;
- deterministic inspectable random/result evidence;
- complete session replay/divergence behavior;
- two targets over the same runtime, including real browser transport evidence;
- explicit unsupported scope;
- conservative proto maturity with zero premature upstream promotions;
- retained Wretched regression evidence.

Independent review still decides whether this candidate is **accepted G7 — Reference**.
