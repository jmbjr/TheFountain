# DIRPS Scenario 01 — Phase D Washed-Out Path evidence

Phase D implements the roadmap's bounded environmental challenge while DIRPS remains **G6 — Targeted**.

## Baseline

- fresh branch base: `456e75e0d7f61b6c83ffe566432fbb08d8784ada`
- Phase C accepted/merged PR: #181
- Phase C final head: `50d64a897d832551c8ecce278f462df43fb4628d`
- Phase C merge SHA: `7b5520fa6cfc320903633473057a87a8d90f1018`
- DODGE: 0.2.1 at CI-pinned revision `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`

## Playable slice

```text
fresh Washed-Out Path runtime state
→ cross-washed-out-path
→ `attempt-attribute → success-roll`
→ resolved PC DX
→ canonical environmental modifier
→ authoritative success-roll / critical rules + 3d6 evidence
→ success or failure
→ ordered DODGE set effects
→ crossed or detour-required neutral progress
→ thin debug target
```

## Authority

Canonical Scenario 01 owns the provisional environmental facts: the crossing action, DX selection, obstacle modifier, and branch consequences.

The canonical PC build owns Rook's DX value.

GURPS Lite remains authoritative for success rolls, modifiers/effective target, and critical classification.

DODGE 0.2.1 owns the normalized scenario values, runtime-state snapshot, and structured effects.

The DIRPS sidecar owns only the executable bridge: resolved primary-attribute target selection, accepted success-roll machinery reuse, runtime-state ref, and ordered effect refs.

## State

Initial:

```text
status   = ready
outcome  = unresolved
progress = not-crossed
```

Success:

```text
status   = resolved
outcome  = success
progress = crossed
```

Failure:

```text
status   = resolved
outcome  = failure
progress = detour-required
```

Both branch results persist in neutral runtime state for later Phase G progression. Phase D does not itself advance encounter order.

## Attribute resolution

The bounded check is `washed-out-path-dx`, executed through the distinct authoritative DODGE action `attempt-attribute → success-roll`. This keeps the accepted `attempt-skill` contracts unchanged while accurately identifying an attribute test.

Baseline:

- canonical DX = 11;
- provisional obstacle modifier = -1;
- effective target = 10.

`dirps-attribute-result.v1` preserves actor, attribute, context, base target, modifiers, effective target, 3d6 evidence, classification, success/failure, margin, rule trace, target provenance, and binding provenance.

`dirps-environment-encounter-result.v1` wraps that roll with the canonical consequence and exact before/after state plus ordered state delta.

## Replay and evidence

`replay_environment_challenge()` re-executes from recorded state and supplied terms/seed and requires exact whole-record equality.

`tests/test_dirps_phase_d.py` covers:

- initial state/action;
- success/crossed path;
- failure/detour-required path;
- one-shot availability;
- deterministic seeded replay;
- state-delta tampering;
- canonical DX perturbation;
- canonical modifier perturbation;
- stale canonical/DODGE consequence normalization;
- normalized canonical + DODGE + sidecar consequence perturbation reaching runtime state;
- target-source binding drift;
- inherited critical/random binding drift;
- `attempt-attribute` authority drift;
- conservative proto status;
- generic target dispatch;
- target anti-hardcoding;
- actual CLI execution.

Named evidence:

```text
PASS dirps/scenario-01: Phase D Washed-Out Path environmental challenge
PASS dirps/scenario-01: Phase D debug target consumes environmental runtime
```

## Proto review

No new proto concept is promoted.

Phase D reuses already-exercised dice resolution, procedure context, character model, and resolution trace. Attribute targeting is a bounded DIRPS bridge over the existing canonical/resolved character attributes, not a new generic proto proposal.

`reaction_timing` and `replay_session_history` remain suspected. Phase C's `lookup_tables` remains exercised/not-yet-candidate.

## Deferred

Phase D does not implement combat, injury, recovery, automatic encounter progression, session history, Web presentation, or G7.

The next roadmap tranche after independent Phase D acceptance is **Phase E — bounded combat vertical slice**.
