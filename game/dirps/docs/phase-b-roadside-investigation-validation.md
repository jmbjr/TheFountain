# DIRPS Scenario 01 — Phase B Roadside Tracks investigation evidence

This is the durable evidence contract for **Phase B — Roadside Tracks investigation encounter** from TheFountain issue #178.

Phase B is gameplay expansion inside the accepted **G6 — Targeted** implementation. It does not claim G7.

- Fresh branch base / current main at start: `271e29c5f2498ccd0773aa542a1e6f46a81ff06e`
- Accepted Phase A PR: #179
- Phase A accepted head: `c82c3f441accf94a998a17e95f2c8d51751d0579`
- Phase A merge SHA: `b36818890eb33ac7b7d9c6927a8185f4c8d45f66`
- DODGE version: `0.2.1`
- DODGE revision pinned by TheFountain CI: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- Resolved model: `dirps-resolved-game.v1`
- Phase A skill record: `dirps-execution-result.v2`
- Phase B encounter record: `dirps-encounter-result.v1`
- Target encounter view: `dirps-debug-encounter-target.v1`
- Gameplay roadmap: #178
- Maturity tracker: #163

## Phase B playable slice

The bounded encounter path is:

```text
fresh neutral Scenario 01 runtime state
→ Roadside Tracks exposes investigate-tracks
→ runtime executes roadside-tracks-tracking through Phase A
→ success/failure branch selects ordered normalized DODGE effects
→ effects mutate neutral scenario state
→ result preserves skill evidence + before/after state + state delta
→ debug CLI displays the same runtime result/state
```

This is the first DIRPS tranche in which a player choice changes scenario state.

Phase B intentionally stops after resolving Roadside Tracks. It does not automatically activate or resolve Frightened Witness. Broader encounter-order progression remains Phase G.

## Authority path

### Canonical Scenario 01

`scenario-01-source` owns the provisional Roadside Tracks gameplay facts:

- initial encounter state;
- one valid investigation action;
- action label and actor;
- the Phase A contextual-check binding;
- success consequence values;
- failure consequence values;
- player-readable information text.

These remain prototype scenario facts, not GURPS mechanics.

### DODGE 0.2.1

Phase B uses standard DODGE semantics rather than a new state proto.

The DODGE document normalizes the canonical Roadside facts as:

- scenario-owned `rules.values`;
- `scenario.initial_state`;
- `runtime_states.scenario-01-initial`;
- structured `set` effects.

The neutral state refs are:

```text
roadside-tracks-status
roadside-tracks-outcome
roadside-tracks-information
```

Initial values:

```text
status      = ready
outcome     = unresolved
information = undiscovered
```

Success:

```text
status      = resolved
outcome     = success
information = clear-trail
```

Failure:

```text
status      = resolved
outcome     = failure
information = trail-inconclusive
```

DIRPS source semantic validation derives the expected DODGE value domains, initial bindings, runtime snapshot, and effect values from canonical Scenario 01. A canonical change without matching normalized DODGE semantics is rejected before resolution.

### GURPS Lite / Phase A

Phase B does not add a new GURPS rule.

The investigation check is the accepted Phase A contextual Tracking check:

```text
roadside-tracks-tracking
→ attempt-skill
→ success-roll
→ dirps-execution-result.v2
```

The nested skill record retains the Phase A external-rule authority and random evidence.

### DIRPS sidecar

The sidecar owns only the DODGE-0.2.1 procedure-context gap that is still not first-class:

`phase_b_encounter_bindings.roadside-tracks`

It binds:

- encounter id;
- action id;
- actor;
- Phase A context ref;
- initial runtime-state ref;
- the required `ready` state;
- success effect refs;
- failure effect refs;
- nested skill record format;
- encounter record format.

The sidecar does **not** duplicate the consequence values. Those are canonical Scenario 01 facts normalized into DODGE effects.

## Neutral resolution

`tools/resolve_dirps_dodge.py` now additionally preserves:

- DODGE `runtime_states`;
- scenario `initial_state`.

The existing resolved `scenario.encounters` copy already preserves the canonical Phase B action/consequence contract.

Resolved semantic validation requires all three to remain exact.

## Runtime state

`create_runtime_state(resolved, encounter_ref=...)` creates a fresh copy of the resolved DODGE runtime snapshot.

The Phase B runtime validates:

- scenario identity;
- revision shape;
- event-list shape;
- unique scenario-subject bindings;
- referenced DODGE value definitions;
- owner scope;
- authority agreement;
- declared enum/type domains.

The runtime never creates a second target-owned state model.

The initial snapshot uses revision `"0"`. A successful encounter resolution increments it to `"1"`.

## Action availability

`describe_investigation()` exposes encounter state plus the available semantic action.

At the initial state:

```text
investigate-tracks
```

is available.

After either success or failure, `roadside-tracks-status = resolved` and the available-action list is empty.

A second attempt fails visibly.

## Execution

`execute_investigation()` accepts:

- resolved model;
- neutral runtime state;
- encounter ref;
- action id;
- actor ref;
- either explicit die terms or a deterministic seed.

It does **not** accept consequence values or arbitrary modifier values.

The function:

1. validates the Phase B bridge;
2. validates current neutral runtime state;
3. validates encounter/action/actor availability;
4. calls `execute_contextual_skill()`;
5. maps the nested Boolean success to the declared `success` or `failure` consequence branch;
6. resolves the branch's ordered DODGE effect refs;
7. applies only normalized DODGE `set` effects;
8. increments runtime-state revision;
9. emits one encounter evidence record.

Critical success uses the success consequence. Critical failure uses the failure consequence. Phase B does not invent separate critical encounter consequences.

## Encounter evidence

`dirps-encounter-result.v1` contains:

- encounter/action/actor identity;
- outcome branch;
- complete nested `dirps-execution-result.v2`;
- canonical consequence record;
- exact state before;
- exact state after;
- ordered state delta;
- encounter-action provenance;
- sidecar bridge provenance;
- consequence source authority;
- ordered DODGE effect refs.

Each state-delta row records:

- effect ref;
- operation;
- state ref;
- scenario subject;
- before value;
- after value;
- source ref;
- authority.

This is one stateful encounter record, not session history.

## Replay

`replay_investigation()` re-executes the encounter from the recorded `state_before`.

It reuses:

- the recorded seed for generated evidence; or
- recorded explicit terms for supplied evidence.

The recomputed encounter record must equal the recorded object exactly.

Tampered state deltas, consequences, nested evidence, or state snapshots therefore diverge.

`replay_session_history` remains `suspected`: Phase B does not create an append-only multi-step scenario history.

## Target support

The existing G6/direct-skill target behavior remains intact.

Phase B adds a separate debug encounter view:

`dirps-debug-encounter-target.v1`

Target functions:

- `inspect_investigation_target()`;
- `execute_investigation_target()`.

CLI mode:

```bash
python tools/dirps_debug_target.py \
  --encounter <encounter-ref> \
  --action <action-id> \
  --actor <actor-ref> \
  --dice <terms...>
```

or:

```bash
python tools/dirps_debug_target.py \
  --encounter <encounter-ref> \
  --action <action-id> \
  --actor <actor-ref> \
  --seed <seed>
```

Providing `--encounter` without `--action` inspects available runtime-described actions.

The target does not contain Roadside/action/consequence IDs. It receives those from input/runtime data and passes the encounter record through unchanged. After successful execution it asks `describe_investigation()` again using `record.state_after`, so the returned `runtime_state`, `capability.state`, and `capability.available_actions` describe one consistent post-action state. Rejected execution keeps the original pre-action state/capability.

## Deterministic, negative, and perturbation evidence

`tests/test_dirps_phase_b.py` proves:

1. fresh neutral runtime state is exactly the DODGE initial snapshot;
2. the Roadside investigation action is available only while state is `ready`;
3. a successful Tracking check mutates status/outcome/information through ordered DODGE effects;
4. a failed Tracking check produces a different meaningful state consequence;
5. resolved Roadside cannot be executed twice;
6. rejected repeat attempts do not mutate caller state;
7. an invalid action fails without mutation;
8. malformed runtime-state enum values fail visibly;
9. seeded encounter execution is deterministic;
10. the stateful encounter record replays exactly;
11. tampered state-delta evidence diverges;
12. changing canonical consequence data without matching DODGE normalization is rejected;
13. changing canonical + normalized DODGE consequence data changes runtime state;
14. no new proto concept is promoted;
15. the target inspects and executes the same neutral state/runtime path;
16. successful and failed target executions refresh capability from post-action runtime state and expose no stale available action;
17. rejected target execution keeps the unchanged pre-action capability/state;
18. fake encounter results and post-action runtime-described capability are passed through rather than recomputed in target code;
19. target source contains no Phase B gameplay literals;
20. the actual registered CLI executes the encounter end-to-end.

Named evidence:

```text
PASS dirps/scenario-01: Phase B Roadside investigation encounter
PASS dirps/scenario-01: Phase B debug target consumes encounter runtime
```

## Proto maturity review

Phase B uses standard DODGE 0.2.1 values, scenario initial state, runtime state, and structured effects.

Therefore no new proto concept is promoted.

Existing exercised concepts remain:

- `dice_resolution`;
- `procedure_context`;
- `actor_character_model`;
- `skill_model`;
- `resolution_trace`.

All remain `not-yet-candidate`.

Still `suspected` include:

- `derived_values`;
- `expressions`;
- `lookup_tables`;
- `reaction_timing`;
- `visibility_and_secret_state`;
- `replay_session_history`.

In particular:

- public Roadside information does not exercise hidden/visibility semantics;
- one stateful encounter replay does not exercise full session-history semantics.

## Explicitly deferred to Phase C+

Phase B does not add:

- Frightened Witness social/reaction resolution;
- automatic transition into the next encounter;
- Washed-Out Path consequences;
- combat;
- recovery;
- whole-scenario completion;
- append-only session history;
- Web presentation;
- G7 reference claims.

The next roadmap tranche after independent Phase B acceptance is **Phase C — Frightened Witness social encounter**.
