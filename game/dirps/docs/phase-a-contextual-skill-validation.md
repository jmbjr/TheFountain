# DIRPS Scenario 01 — Phase A contextual skill-check evidence

This is the durable evidence contract for **Phase A — Make ordinary skill checks useful** from TheFountain issue #178.

Phase A is gameplay expansion inside the accepted **G6 — Targeted** implementation. It is not a new maturity gate and does not claim G7.

- Baseline current main / fresh branch base: `6681cb0ecf0172d82b5de223b6dc2a5fd6227028`
- Accepted G6 PR: #177
- G6 accepted head: `1a3203efd6acf556843915e46249354f7f280b57`
- G6 merge SHA: `98f67282a07a0a3dca4bec893d20b1e6a39f8310`
- DODGE version: `0.2.1`
- DODGE revision pinned by TheFountain CI: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- Runtime: `tools/dirps_runtime.py`
- Resolved model: `dirps-resolved-game.v1`
- Gameplay roadmap: #178
- Maturity tracker: #163

## Phase A scope

Phase A extends the accepted success-roll runtime so a check can be contextual rather than only an unmodified skill target.

The bounded playable mechanic is:

```text
resolved actor skill
+ source-owned situational modifiers
→ effective target
→ supplied or deterministic generated 3d6 evidence
→ success/failure + margin
→ critical classification
→ provenance-rich execution result
```

The first canonical context is `roadside-tracks-tracking`.

This tranche deliberately stops before Phase B. It does not apply investigation consequences, mutate scenario progress, reveal information, or advance the encounter.

## Authority split

Phase A has one explicit authority path.

### External rules authority

`gurps-lite` remains authoritative for the applicable success-roll mechanics.

The executable sidecar binding records stable source locators for:

- modifier application / effective skill: `p. 2, Modifiers and Effective Skill`;
- critical success/failure: `p. 2, Critical Success and Failure`.

The runtime interprets the sidecar's declared rule table. It does not maintain a second hard-coded set of critical thresholds.

### Scenario authority

`scenario-01-source` owns the prototype gameplay tuning for the Roadside Tracks check:

```text
context: roadside-tracks-tracking
skill: tracking
modifier: -2
authority: provisional
provenance: prototype_assumption
```

The `-2` value is explicitly a Scenario 01 prototype assumption. It is **not** represented as a GURPS rule value.

### DIRPS proto authority

`dirps-proto` remains provisional executable authority for the bridge DODGE 0.2.1 cannot express first-class:

- named contextual-check input;
- modifier aggregation into effective target;
- critical-result classification contract;
- deterministic generated-random evidence contract;
- expanded structured result/trace.

## Canonical contextual-check shape

Scenario 01 now carries:

```json
{
  "contextual_checks": {
    "roadside-tracks-tracking": {
      "encounter_ref": "roadside-tracks",
      "action_ref": "attempt-skill",
      "skill_ref": "tracking",
      "provenance": "prototype_assumption",
      "modifiers": [
        {
          "id": "roadside-tracks-tutorial-difficulty",
          "amount": -2,
          "source_ref": "scenario-01-source",
          "authority": "provisional",
          "provenance": "prototype_assumption"
        }
      ]
    }
  }
}
```

The semantic profile validates the encounter/action/skill references, modifier identities, integer amounts, source/authority/provenance, and the current minimum rollable effective target before resolution.

The neutral resolver copies `contextual_checks` losslessly into `resolved.scenario.contextual_checks`.

## Effective target

The runtime executes the declared Phase A policy:

```text
base_target = resolved character skill
modifier_total = sum(resolved contextual modifier amounts)
effective_target = base_target + modifier_total
```

The binding declares a minimum effective target of 3. A lower target fails visibly rather than being rolled.

No caller or target is allowed to supply arbitrary modifier values to `execute_contextual_skill()`; the runtime selects them from the resolved context.

## Random evidence

Phase A supports two mutually exclusive evidence modes.

### Supplied terms

The accepted G5 explicit terms path remains supported.

### Deterministic generated terms

Phase A adds a runtime-owned deterministic generator:

```text
algorithm: sha256-rejection-v1
input: recorded seed
output: ordered die terms
```

The algorithm uses SHA-256 bytes with rejection sampling so die faces are not produced by biased modulo reduction.

The execution record preserves:

- evidence kind;
- algorithm id;
- seed;
- individual die terms;
- total.

The same resolved model + seed reproduces the same terms and result.

This is deterministic random evidence, not a session-history system.

## Critical classification

The sidecar declares the bounded critical-result classifier from the external rules authority.

Critical success:

- roll at most 4;
- roll 5 with effective target at least 15;
- roll 6 with effective target at least 16.

Critical failure:

- roll 18;
- roll 17 when effective target is at most 15;
- a roll at least 10 greater than effective target.

Explicit ordinary-failure boundary:

- roll 17 with effective target at least 16.

The runtime interprets those sidecar rows generically through `_rule_matches()`; the numeric thresholds are not duplicated in the target.

Phase A classifies the result but does not implement critical-success or critical-failure **consequences**. Those remain unsupported until a scenario phase actually needs them.

## Record versioning / compatibility

The accepted G5 evidence contract remains **immutable**:

`g5_execution_bindings.attempt-skill → dirps-execution-result.v1`

and continues to back:

```python
execute_attempt_skill(...)
replay_attempt_skill(...)
describe_attempt_skill(...)
```

Phase A does not redefine that identity. Its expanded contextual contract lives separately at:

`phase_a_execution_bindings.attempt-skill → dirps-execution-result.v2`

and backs:

```python
execute_contextual_skill(...)
replay_contextual_skill(...)
describe_contextual_skill(...)
```

This separation is intentional because Phase A adds required structure that is not compatible with the accepted v1 record shape: contextual modifier evidence, expanded effective-target trace, generated-random metadata, and critical classification.

Replay APIs reject the other record version explicitly:

- v1 presented to the Phase A replay path is identified as a legacy G5 record;
- v2 presented to the legacy G5 replay path is identified as a Phase A record.

A version mismatch is therefore **not** reported as generic record divergence/tampering.

## Runtime APIs

Existing unmodified compatibility path:

```python
execute_attempt_skill(resolved, actor_ref=..., skill_ref=..., dice_terms=...)
```

New Phase A contextual path:

```python
describe_contextual_skill(resolved)
execute_contextual_skill(
    resolved,
    actor_ref=...,
    context_ref=...,
    dice_terms=... | random_seed=...
)
```

Re-evaluation:

```python
replay_contextual_skill(resolved, record)
```

The contextual replay path reuses recorded supplied terms or the recorded generated seed and rejects any divergent record.

## Result evidence

`dirps-execution-result.v2` is the Phase A contextual record identity. It records:

- actor;
- selected skill;
- optional context ref;
- base target;
- ordered modifier rows;
- modifier total;
- effective target;
- modifier-rule source/authority/locator;
- individual die terms;
- generated-random algorithm and seed when used;
- total;
- success Boolean;
- margin;
- critical classification;
- critical-rule source/authority/locator;
- action/procedure/binding/target provenance;
- empty state delta.

Phase A remains non-mutating.

## Deterministic, negative, and perturbation evidence

`tests/test_dirps_phase_a.py` proves:

1. Roadside Tracking resolves from base 12 plus canonical -2 modifier to effective target 10;
2. modifier provenance stays provisional / prototype-assumption while the modifier rule remains externally authoritative;
3. changing the canonical modifier from -2 to -1 flows through source → resolver → runtime and changes target/margin;
4. corrupting modifier authority/source fails before resolution;
5. a contextual effective target below 3 fails before runtime;
6. a recorded seed produces deterministic 3d6 evidence;
7. changing the seed changes the preserved evidence;
8. generated evidence re-evaluates deterministically and seed tampering diverges;
9. supplied and generated evidence are mutually exclusive and one is required;
10. rolls 3/4 classify critical success;
11. roll 5 uses the effective-target 15 boundary;
12. roll 6 uses the effective-target 16 boundary;
13. roll 18 is always critical failure;
14. roll 17 uses the effective-target 16 ordinary-failure boundary;
15. a roll 10 greater than effective target classifies critical failure;
16. capability inspection exposes contextual checks, RNG contract, modifier policy, and critical contract;
17. proto maturity remains conservative;
18. accepted G5 records still emit/replay as `dirps-execution-result.v1`;
19. contextual Phase A records emit/replay as `dirps-execution-result.v2`;
20. v1/v2 cross-replay is rejected as an explicit version-contract mismatch rather than generic divergence.

The positive test emits:

```text
PASS dirps/scenario-01: Phase A contextual skill check
```

Retained G4/G5/G6 tests continue to guard resolution, the original success-roll API, and target pass-through.

## Proto maturity review

Phase A reassessed `derived_values` and `expressions` as required by #178.

Neither is promoted.

`derived_values` remains `suspected` because Phase A does not implement its proposed generic derived-value/dependency/recompute shape. It performs one bounded effective-target calculation inside the DIRPS execution binding.

`expressions` remains `suspected` because no reusable arithmetic expression graph is implemented.

The five already-exercised concepts remain:

- `dice_resolution`;
- `procedure_context`;
- `actor_character_model`;
- `skill_model`;
- `resolution_trace`.

All remain `not-yet-candidate`.

`replay_session_history` remains `suspected`; one-record deterministic re-evaluation is still not immutable session history.

## Target status

Phase A intentionally changes runtime semantics before adding presentation.

The accepted G6 debug CLI remains the thin target consumer and its capability inspection automatically exposes the runtime-described contextual/RNG/critical contract.

This tranche does **not** add target controls for choosing contextual checks or generated RNG. Player-facing encounter interaction belongs to the later gameplay/target phases.

## Explicitly deferred to Phase B+

Phase A does not add:

- Roadside Tracks encounter state;
- investigation choices/consequences;
- discovered information;
- scenario progress mutation;
- social resolution;
- environmental consequences;
- combat;
- recovery;
- scenario completion;
- full session history;
- Web presentation.

The next roadmap tranche is **Phase B — Roadside Tracks investigation encounter** after independent Phase A acceptance.
