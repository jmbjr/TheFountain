# DIRPS Phase H — full session history / replay validation

Phase H keeps DIRPS at **G6 — Targeted** while moving from Phase G's one-transition re-evaluation to a complete deterministic audit of Scenario 01, **The Missing Courier**.

## Baseline

- TheFountain baseline: Phase G merge `41689202b7224c5c548121f978c241908896225f`.
- Accepted Phase G PR: #185, final head `93b22d52ab4995fed61aa308b09c0b5c8d302c44`.
- DODGE contract: **0.2.1** at the exact revision pinned by TheFountain CI, `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`.
- Formal maturity remains **G6**. Phase H is gameplay/runtime evidence, not G7.

## Authority

Phase H does not add new gameplay semantics.

```text
canonical Scenario 01 + DODGE 0.2.1 + DIRPS proto orchestration
→ dirps-resolved-game.v1
→ accepted Phase G scenario runtime
→ dirps-scenario-progression-result.v1 transition records
→ Phase H immutable/copy-on-append session evidence
→ deterministic full-session replay
```

The session layer never decides encounter order, mechanics, consequences, or terminal outcomes. Each step is produced by `execute_scenario_action()`, preserving the accepted Phase G record unchanged.

DODGE 0.2.1 has no first-class immutable session/replay sequence that fits this evidence contract. The representation therefore remains in the declared `replay_session_history` proto gap. Phase H provides enough real DIRPS execution evidence to advance that concept from **suspected** to **exercised**, while keeping it **not-yet-candidate** until broader reusable evidence exists.

## Session contract

The new record identity is `dirps-session-history.v1`.

A session contains:

- a resolved semantic source identity using `sha256-canonical-json-v1`;
- the exact accepted full-scenario initial runtime snapshot;
- its canonical JSON SHA-256 hash;
- an ordered `steps` sequence.

Each step preserves:

- contiguous `sequence`;
- `declared_action.action_id`;
- `declared_action.actor_ref`;
- exact Phase G `random_inputs` as `random_evidence`;
- `state_before_hash`;
- `state_after_hash`;
- exact Phase G `resolution_trace`;
- the complete unchanged `dirps-scenario-progression-result.v1` transition record.

The source identity hashes the declared resolved semantic fields needed to reproduce the session: game/scenario/document identity, source declarations, rules, scenario, runtime states, the Phase G progression binding, and the Phase H history binding. A replay against materially different resolved semantics fails before step execution.

## Append-only behavior

`create_scenario_session_history()` creates the zero-step session from the accepted `scenario-01-playable-initial` snapshot.

`append_scenario_session_step()` is copy-on-append:

1. replay and validate the existing history;
2. reject if the existing history is divergent or already terminal;
3. execute the declared action through the accepted Phase G runtime;
4. create one evidence step;
5. return a deep-copied history with the new step appended.

The caller's prior history object is never mutated. Existing step order or evidence cannot be silently rewritten by the append API.

## Full-session replay

`replay_scenario_session_history()` begins from the recorded initial state and checks steps in sequence.

For every step it verifies:

1. contiguous sequence identity;
2. declared action identity;
3. exact preserved random inputs;
4. before-state continuity and hash;
5. recorded after-state hash;
6. recorded Phase G resolution trace;
7. re-execution through `execute_scenario_action()`;
8. exact equality of the recomputed Phase G transition record.

Divergence raises an error naming the first inconsistent step. Later inconsistent evidence is not examined first.

A caller may replay a partial history for inspection. `require_complete=True` additionally requires the terminal Scenario 01 state.

## Evidence

`tests/test_dirps_phase_h.py` proves:

- session creation starts from the accepted full-scenario initial state;
- append is copy-on-append and leaves earlier history values unchanged;
- every step contains action, random, state-hash, trace, and complete transition evidence;
- a deterministic five-step success run replays to `success`;
- a deterministic four-step failure run replays to `failure`;
- final replay state/hash equals the terminal transition evidence;
- tampered random evidence reports the first inconsistent step;
- tampered state hashes report the exact inconsistent step;
- resolved semantic source drift is rejected before replay;
- a tampered prior history cannot be appended to;
- terminal histories reject further append;
- partial histories are distinguishable from complete histories;
- Phase H sidecar binding drift fails source semantic resolution;
- resolved Phase H binding drift fails at runtime;
- `replay_session_history` is exactly `exercised / not-yet-candidate`.

The named CI evidence line is:

```text
PASS dirps/scenario-01: Phase H full session history and replay
```

## Proto maturity decision

Phase H changes one proto maturity state:

```text
replay_session_history:
  suspected → exercised
  candidate_for_dodge: not-yet-candidate
```

Reason: Scenario 01 now executes the proposed concept end-to-end through shared resolved/runtime semantics with positive, negative, deterministic, continuity, and divergence evidence.

It is not promoted to candidate because this is still one game's exercised contract and has not yet demonstrated enough cross-game/generalized evidence for upstream DODGE standardization.

## Explicit deferrals

Phase H does not implement:

- save-file packaging or migration;
- a player-facing replay UI;
- target-specific history semantics;
- long-term healing/unconscious recovery;
- broader combat;
- Phase I Web presentation;
- G7 reference promotion.

Exact-head CI identity is recorded in the Phase H pull request and trackers after the final literal PR head passes. It is intentionally not embedded here because changing this document would create a new head and stale that evidence.
