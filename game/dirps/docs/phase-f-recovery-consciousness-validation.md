# DIRPS Scenario 01 — Phase F recovery / consciousness evidence

This is the durable evidence contract for **Phase F — Recovery / consciousness** from TheFountain issue #178.

Phase F is gameplay expansion inside the accepted **G6 — Targeted** implementation. It does not claim G7.

- Fresh branch base / current main at start: `09b1f0328695fd7170fc4a31c1d7a7f99f8f4f80`
- Accepted Phase E PR: #183
- Phase E accepted head: `ec0aa62f0bf2f46c23ca038783a4086704a4f333`
- Phase E merge SHA: `461d088e7c03c72b169e7de9b67f32a5854b1b29`
- DODGE version: `0.2.1`
- DODGE revision pinned by TheFountain CI: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- Resolved model: `dirps-resolved-game.v1`
- Phase E combat record: `dirps-combat-exchange-result.v1`
- Phase F check record: `dirps-ht-check-result.v1`
- Phase F turn record: `dirps-recovery-result.v1`
- Target recovery view: `dirps-debug-recovery-target.v1`
- Gameplay roadmap: #178
- Maturity tracker: #163

## Phase F playable slice

Phase F resolves the injury obligations left by Phase E using the **same neutral combat runtime state**:

```text
Phase E post-combat state
→ next-turn start
→ if HP <= 0 and consciousness-check-required:
     basic-HT stay-conscious check
→ if still conscious and stunned:
     basic-HT physical-stun recovery check
→ normalized state effects
→ exact before/after combat state + delta
→ deterministic recovery record
→ thin debug target continuation
```

This is deliberately not a healing system.

## Authority path

### GURPS Lite

The registered `gurps-lite` source remains authoritative for the two bounded Phase F mechanics:

1. **Stay conscious at HP <= 0** — at the beginning of the actor's turn, roll against basic HT, modified by applicable Strong/Weak Will; failure means unconsciousness and success permits the current turn.
2. **Physical-stun recovery** — on the next turn, roll against basic HT; success ends stun and failure leaves the actor stunned.

The sidecar stores stable locators for those rules.

Phase F uses the accepted 3d6/success-roll evidence machinery for the HT rolls, but the branch consequences above come from the recovery binding rather than target code.

### Canonical Scenario 01

Scenario 01 owns only the bounded orchestration facts that are not external rules:

- the supported actor is the bandit scout;
- the action id/label used by the tutorial slice;
- timing is `next-turn-start`;
- check order is `consciousness → stun-recovery`;
- the Strong/Weak Will modifier is provisionally assumed to be `0`;
- long-term recovery from unconsciousness is unsupported in this bounded scenario slice.

The `0` modifier is a perturbable `prototype_assumption`, not a GURPS constant.

### DODGE 0.2.1

Phase F reuses the standard actor state already carried by Phase E:

- `hit-points`;
- `stunned`;
- `unconscious`;
- `consciousness-check-required`.

It adds only normalized structured `set` effects for the state transitions Phase F can produce:

- set `unconscious = true`;
- clear the provisional stay-conscious obligation after unconsciousness;
- clear `stunned` after successful recovery.

No parallel recovery-state model is created.

### DIRPS sidecar

DODGE 0.2.1 already has the state and effect vocabulary needed by Phase F, but it does not provide the RPG-specific orchestration for two ordered conditional HT checks.

The sidecar therefore adds:

`phase_f_recovery_bindings.bandit-scout`

It binds:

- actor/action/procedure;
- next-turn timing;
- check order;
- source of canonical HT;
- accepted `dice_resolution` contract;
- accepted Phase A `critical_resolution` contract;
- accepted Phase A `random_evidence` contract;
- state refs;
- effect refs;
- rule source/locators;
- result identities;
- explicit unsupported long-term recovery.

The accepted G5 / Phase A / B / C / D / E binding subtrees remain unchanged.

## Phase E state continuity

Phase F does not create a fresh initial state.

Its input must be the same Phase E combat snapshot after at least one combat-state revision.

The canonical roll-3 Phase E critical path can leave:

```text
hit-points                    = 0
stunned                       = true
unconscious                   = false
consciousness-check-required  = true
revision                      = 1
```

That exact object is a valid Phase F input.

The runtime rejects:

- revision 0 initial combat state;
- `consciousness-check-required = true` while HP > 0;
- a conscious actor at HP <= 0 with the obligation missing;
- an unconscious actor that still carries the stay-conscious obligation.

## Check ordering

Phase F executes checks in declared order.

### 1. Consciousness

If the actor is conscious, HP <= 0, and the obligation flag is true:

```text
target = canonical HT + canonical/provisional Strong/Weak Will modifier
roll 3d6
success → actor remains conscious for this turn
failure → unconscious = true
          consciousness-check-required = false
```

**Important:** success does **not** clear `consciousness-check-required`.

While the actor stays at HP <= 0 and remains conscious, the rule obligation persists into a later turn. This preserves the repeated beginning-of-turn check rather than treating one success as permanent recovery.

### 2. Physical-stun recovery

Only if the actor remains conscious and is stunned:

```text
target = canonical HT
roll 3d6
success → stunned = false
failure → stunned remains true
```

If consciousness fails first, the stun check is skipped.

If the actor is not stunned, the stun check is skipped.

## Explicit unsupported boundary

If the actor is already unconscious, Phase F offers no recovery action and reports:

`long-term-unconscious-recovery`

as unsupported.

This tranche does not implement:

- hourly waking checks;
- natural healing;
- First Aid healing;
- hospitalization;
- death checks;
- bleeding;
- whole-scenario time progression.

Those mechanics are not required to satisfy the bounded Scenario 01 Phase F milestone.

## Random evidence

Phase F accepts either:

- explicit 3d6 terms for each executed check; or
- one deterministic root seed.

Generated sub-rolls derive labels from the root seed:

```text
<seed>:phase-f:consciousness
<seed>:phase-f:stun-recovery
```

Each `dirps-ht-check-result.v1` preserves:

- check identity;
- base HT;
- modifier;
- effective target;
- random evidence kind;
- algorithm/seed when generated;
- individual die terms;
- total;
- classification;
- success/failure;
- margin;
- recovery-rule source trace;
- `dice_resolution_ref`;
- `critical_resolution_ref`;
- `random_evidence_ref`.

Those three reuse refs are executable dependencies, not documentation-only labels. The runtime validates them against the accepted Phase A success-roll binding before any recovery HT roll.

Unused-check dice fail visibly rather than being silently ignored.

## Phase F dice/critical reuse refs

Independent review identified that Phase F was calling the accepted Phase A dice/critical helpers while declaring only the random-evidence dependency.

The Phase F bridge now explicitly pins:

```text
dice_resolution_ref     = dice_resolution
critical_resolution_ref = phase_a_execution_bindings.attempt-skill.critical_resolution
random_evidence_ref     = phase_a_execution_bindings.attempt-skill.random_evidence
```

Semantic validation rejects any drift in those refs before resolution. Runtime binding validation checks the same refs against the accepted Phase A binding before an HT roll, and each HT-check trace records all three.

Focused regressions perturb the dice and critical reuse refs independently and prove that both fail visibly before resolution.

## Recovery record

`dirps-recovery-result.v1` preserves:

- encounter/action/actor;
- timing;
- declared resolution order;
- random mode;
- consciousness result or skip;
- stun-recovery result or skip;
- exact before state;
- exact after state;
- ordered state delta;
- final unconscious/stunned/obligation state;
- whether the actor can act normally this turn;
- binding/source trace;
- canonical HT trace;
- canonical modifier provenance.

A successful consciousness roll followed by successful stun recovery can yield:

```text
HP = 0
unconscious = false
stunned = false
consciousness-check-required = true
can_act_normally = true
```

That is intentional: the actor passed this turn's stay-conscious roll but must check again on a later turn while HP remains <= 0.

## Replay

`replay_recovery()` re-executes from the recorded `state_before`.

It reuses:

- the recorded root seed; or
- recorded supplied terms for each check that actually executed.

Whole-record equality is required.

State/result tampering therefore diverges.

This remains one-record deterministic replay, not append-only `replay_session_history`.

## Target support

Phase F adds a continuation mode to the existing debug CLI.

Runtime-facing target APIs:

- `inspect_recovery_target()`;
- `execute_recovery_target()`.

The target requires an explicit post-combat state. It does not fabricate one.

CLI shape:

```bash
python tools/dirps_debug_target.py \
  --recovery \
  --encounter <encounter> \
  --state-json '<post-combat-state-json>'
```

Execution with supplied evidence:

```bash
python tools/dirps_debug_target.py \
  --recovery \
  --encounter <encounter> \
  --action <action> \
  --actor <actor> \
  --state-json '<post-combat-state-json>' \
  --consciousness-dice <terms...> \
  --stun-dice <terms...>
```

or use `--seed <seed>`.

The target owns argument/state transport and JSON presentation only.

It contains no bandit/recovery/check/state-effect gameplay literals.

## Deterministic, negative, and perturbation evidence

`tests/test_dirps_phase_f.py` proves:

1. a real Phase E HP0/stunned/check-required state flows directly into Phase F;
2. recovery capability exposes both required checks and canonical HT targets;
3. consciousness success + stun success clears stun but preserves the HP<=0 consciousness obligation;
4. a later turn still offers the consciousness action;
5. failed consciousness sets unconscious and clears only the stay-conscious obligation;
6. failed consciousness skips stun recovery;
7. successful consciousness + failed stun recovery leaves the actor stunned;
8. positive-HP major-wound state runs stun recovery without a consciousness roll;
9. a state with no pending recovery has no action and execution fails;
10. long-term unconscious recovery fails visibly as unsupported;
11. Phase E revision-0 initial state is rejected;
12. inconsistent HP/obligation state is rejected without mutation;
13. dice supplied for a skipped check are rejected without mutating caller state;
14. seeded recovery is deterministic;
15. recovery replay reproduces the whole record;
16. state tampering causes replay divergence;
17. changing the canonical Strong/Weak Will modifier changes the consciousness target/outcome;
18. changing canonical bandit HT with matching normalized DODGE state changes both HT targets;
19. sidecar recovery-order drift fails before resolution;
20. target inspection/execution consumes the same post-combat state;
21. fake runtime result pass-through proves the target does not recompute recovery;
22. target source contains no Phase F gameplay literals;
23. the real CLI continues a real Phase E state through Phase F;
24. proto maturity remains conservative.

Named evidence:

```text
PASS dirps/scenario-01: Phase F recovery and consciousness
PASS dirps/scenario-01: Phase F debug target consumes recovery runtime
```

## Proto maturity review

No new proto concept changes maturity in Phase F.

Already exercised / `not-yet-candidate`:

- `dice_resolution`;
- `procedure_context`;
- `actor_character_model`;
- `skill_model`;
- `resolution_trace`;
- `lookup_tables`;
- `reaction_timing`;
- `derived_values`;
- `expressions`;
- `damage_injury`.

Still `suspected`:

- `visibility_and_secret_state`;
- `replay_session_history`.

Why no promotion:

- next-turn recovery uses existing procedure-context/result machinery rather than a new generic representation;
- actor state/effects are already standard DODGE semantics;
- one recovery record still is not a multi-step immutable session history.

## Explicitly deferred to Phase G+

Phase F does not add:

- encounter progression/order;
- scenario completion;
- success/failure end-state semantics;
- long-term unconscious recovery;
- healing;
- append-only full-session history;
- Web target;
- G7 reference claims.

The next roadmap tranche after independent Phase F acceptance is **Phase G — Scenario progression and completion**.
