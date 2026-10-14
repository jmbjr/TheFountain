# DIRPS Phase G — scenario progression / completion validation

Phase G keeps DIRPS at **G6 — Targeted** while connecting the accepted Phase A-F mechanics into one bounded start-to-finish run of Scenario 01, **The Missing Courier**.

## Baseline

- TheFountain branch baseline: current `main` at Phase G start, `0eb00a1d32a80c50bd1af20e4f99bfcd7f28fa37`.
- Prior accepted gameplay tranche: PR #184, final head `f25fb0bc3721910e0e0d22017ad147e2d6ea6829`, merge `456b05fd9f303b12b97619baed689e4bf3a8ec64`.
- DODGE contract: **0.2.1** at the exact revision pinned by TheFountain CI, `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`.
- Formal maturity remains **G6**. Phase G is gameplay convergence, not G7.

## Authority

The authority path remains singular:

```text
canonical Scenario 01
→ DODGE 0.2.1
→ DIRPS source semantic validation
→ neutral resolver
→ dirps-resolved-game.v1
→ resolved-game validation
→ DIRPS runtime
→ targets
```

Scenario 01 owns the encounter order and the bounded interpretation of scenario success/failure. DODGE owns the neutral progress values, conditions, effects, runtime-state snapshot, objective completion reference, and win/loss end conditions that 0.2.1 already supports. The DIRPS proto sidecar only bridges a completed mechanic result to the relevant normalized progress effect because DODGE 0.2.1 does not provide the procedure-local orchestration needed to dispatch across these four heterogeneous encounter runtimes.

No target owns or recomputes Phase G gameplay semantics.

## Neutral scenario state

Full play begins from `runtime_states.scenario-01-playable-initial`. The accepted Phase B-F runtime-state definitions remain unchanged and are composed into the new full-scenario snapshot together with:

- `scenario-progress-status`;
- `scenario-current-encounter`;
- `scenario-progress-step`;
- `scenario-outcome`;
- `scenario-completion-information`.

The canonical order is:

1. `roadside-tracks`;
2. `frightened-witness`;
3. `washed-out-path`;
4. `bandit-scout`.

Information/outcome bindings produced by earlier encounters remain in the full neutral state after progression.

## Completion semantics

The final bounded Bandit Scout result determines the tutorial end state:

- if the scout is no longer able to act normally after the supported combat/recovery path, the scenario records `success`, `courier-fate-established`, satisfies `scenario-success`, and matches `missing-courier-success`;
- if the scout remains able to act normally, the scenario records `failure`, `courier-fate-unresolved`, satisfies `scenario-failure`, and matches `missing-courier-failure`.

These are Scenario 01 prototype semantics, not GURPS rules.

## Runtime and record compatibility

Phase G adds new scenario-level APIs:

- `create_scenario_runtime_state()`;
- `describe_scenario()`;
- `execute_scenario_action()`;
- `replay_scenario_progression()`.

The new record identity is `dirps-scenario-progression-result.v1`. Accepted Phase A-F result identities and payloads are nested unchanged rather than rewritten in place.

Phase G maintains a scenario-global revision while each accepted mechanic receives its original phase-local state/revision contract. This keeps the old bounded runtimes compatible and prevents the new progression layer from redefining their records.

One-record Phase G replay re-executes the selected mechanic and progression transition and rejects divergence. It is deliberately **not** an append-only multi-step session-history contract.

## Negative / perturbation evidence

`tests/test_dirps_phase_g.py` proves:

- only the current canonical encounter exposes an action;
- out-of-order, post-completion, and unsupported-input branches fail visibly without mutating caller state;
- Roadside/Witness/Path information and consequences remain in the unified state;
- deterministic supplied random evidence can play the scenario to both success and failure;
- one Phase G record replays identically and tampering diverges;
- swapping the middle encounters in the canonical source changes the next runtime encounter after Roadside, proving the runtime follows canonical order rather than a copied target/runtime order;
- DODGE objective/end-state drift and sidecar bridge drift fail semantic resolution;
- `replay_session_history` remains `suspected` / `not-yet-candidate`;
- accepted nested Phase E/F record identities remain unchanged.

## Proto maturity

Phase G promotes no proto concept.

Scenario progress, conditions, effects, objectives, end conditions, and typed state are already standard DODGE 0.2.1 semantics. The sidecar bridge is bounded DIRPS orchestration evidence, not a new generic semantic proposal. Full immutable session history remains deferred to Phase H.

## Explicit deferrals

Phase G does not implement:

- append-only full-session replay/history;
- save/load session packaging;
- long-term unconscious recovery, healing, first aid, or death checks;
- broader combat;
- player-facing Web presentation;
- G7 reference-quality promotion.

Exact-head CI identity and the final run are recorded in the Phase G pull request and issues #178/#163 after the final literal PR head is validated. They are intentionally not embedded here because changing this file would create a new head and invalidate that evidence.
