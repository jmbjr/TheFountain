# DIRPS Scenario 01 — Phase E bounded combat evidence

This is the durable evidence contract for **Phase E — Bounded combat vertical slice** from TheFountain issue #178.

DIRPS remains **G6 — Targeted**. Phase E adds one deliberately narrow combat exchange without attempting to encode the full GURPS combat system.

- Fresh branch base / current main at start: `3dde8480745ef80bef8425c6eec81e786eb4d0ba`
- Accepted Phase D PR: #182
- Phase D accepted head: `c8bfdebb5cb2dcb88a20827804a6684aa4618a2c`
- Phase D merge SHA: `c3e6bbbdeec1e5a8f70cedccb92d3d16c302b5ea`
- DODGE version: `0.2.1`
- Pinned DODGE revision: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- Combat record: `dirps-combat-exchange-result.v1`
- Attack record: `dirps-attack-result.v1`
- Active-defense record: `dirps-active-defense-result.v1`
- Damage record: `dirps-damage-result.v1`

## Bounded playable path

Phase E supports exactly one exchange:

```text
Rook attacks with Broadsword
→ 3d6 attack roll vs resolved Broadsword skill
→ on ordinary success: one bandit Dodge reaction
→ on failed defense: ST10 swing/cutting damage
→ armor DR
→ cutting injury
→ HP mutation
→ major-wound stun when applicable
→ mark future consciousness check when HP <= 0
```

A critical attack bypasses the defense window.

The critical-damage split is authoritative and explicit:

- attack total **3**: do **not** roll damage; use maximum damage from the matched ST/weapon profile;
- other supported critical hits: bypass defense but roll damage normally.

A failed attack stops before defense/damage.

The combat snapshot is one-exchange bounded. After the exchange its revision changes from `0` to `1`, and no further Phase E action is offered.

## Authority split

### Canonical Scenario 01

Scenario 01 owns the provisional combat setup:

- Rook is the attacker.
- The bandit scout is the target.
- Rook uses the resolved Broadsword skill/equipment.
- The supported attack mode is broadsword swing/cutting.
- The bandit is initially conscious and not stunned.
- The bandit is aware of the attack.
- Encumbrance penalty, passive defense, and armor DR are scenario-owned prototype inputs.
- The slice permits one exchange.

Opponent attribute/state values are canonical prototype facts and remain perturbable. Semantic validation requires the DODGE scene/runtime snapshot to match those canonical values instead of freezing them in runtime code.

### GURPS Lite authority

The registered `gurps-lite` source remains authoritative for:

- weapon-skill attack rolls and critical-hit defense bypass;
- active-defense timing and Dodge;
- Basic Speed / Move / Dodge derivation;
- defense-roll auto-success/failure boundaries;
- ST-based basic weapon damage;
- Broadsword swing/cutting damage;
- armor DR;
- cutting injury multiplier;
- HP injury;
- major-wound stun;
- the beginning-of-turn consciousness-check requirement at HP <= 0.

Stable source locators live in the Phase E sidecar contracts.

### DODGE 0.2.1

DODGE continues to own normalized actor state/value definitions and the neutral resolved actor instances.

Phase E adds a neutral runtime snapshot for the target actor:

```text
hit-points
stunned
unconscious
consciousness-check-required
```

Every actor-scoped DODGE value remains explicitly initialized on every scene actor, preserving the accepted source-profile invariant.

The new `consciousness-check-required` binding is provisional DIRPS execution bookkeeping: it records a future rule obligation but does not execute the HT roll.

### DIRPS sidecar

DODGE 0.2.1 does not provide one first-class RPG combat contract for:

- active-defense reaction windows;
- arithmetic derived-value graphs;
- ST-to-damage lookup;
- weapon damage profile;
- damage-type injury conversion;
- one coherent attack/defense/damage/injury result.

Phase E therefore exercises explicit target-neutral sidecar contracts:

- `phase_e_combat_bindings`;
- `phase_e_expressions`;
- `phase_e_derived_values`;
- `phase_e_lookup_tables`;
- `damage_injury` proto evidence.

Targets do not own these rules.

## Attack resolution

The attack target is the resolved player-character Broadsword skill.

Random evidence uses the existing accepted 3d6 machinery.

The attack result preserves:

- target;
- all die terms;
- total;
- success/failure;
- margin;
- critical classification;
- action/procedure identity;
- random/critical contract refs.

Attack critical success bypasses the defense window.

An attack total of exactly 3 additionally triggers the GURPS Lite maximum-damage rule. The runtime derives the maximum from the matched ST damage profile plus weapon add, records no damage random evidence, and then applies DR/cutting injury/state normally. Other supported critical successes still roll damage normally.

Attack failure or critical failure ends the exchange without damage.

## Reaction timing and active defense

Phase E is the first real evidence for `reaction_timing`.

The declared reaction window is:

```text
trigger: successful noncritical attack
responder: attacked bandit
eligible defenses: Dodge only
order: attack → defense → damage
```

The runtime will not accept Parry, Block, or another responder.

For the bounded scout, total Dodge defense is derived from:

```text
floor((DX + HT) / 4)
- encumbrance penalty
+ passive defense
```

The default canonical values produce defense target 5.

Defense evidence preserves the derived target, expression/dependency trace, rule locator, all 3d6 terms, total, success/failure, and margin.

A defense roll of 3 or 4 succeeds automatically; 17 or 18 fails.

## Damage and injury

The supported attacker remains ST10.

The authoritative bounded ST lookup returns:

```text
ST 10 swing → 1d
```

Broadsword swing/cutting adds +1, producing:

```text
basic damage = max(1, 1d + 1)
penetrating damage = max(0, basic damage - DR)
cutting injury = penetrating + floor(penetrating / 2)
```

The lookup intentionally has no fallback approximation. A different attacker ST fails visibly until that table is deliberately expanded.

Damage evidence preserves:

- attacker ST;
- matched lookup row;
- resolution mode (`rolled` or `automatic-maximum`);
- damage random evidence only when a damage roll actually occurs;
- weapon add;
- basic damage;
- armor DR;
- penetrating damage;
- damage type;
- final injury;
- rule/derived-expression trace.

For attack total 3, `random_evidence` is null and the trace records the authoritative critical maximum-damage rule plus the derived maximum dice total.

## Critical attack total 3

GURPS Lite's ordinary attack rule distinguishes a roll of exactly 3 from other critical hits.

For the bounded default attack:

```text
ST10 swing = 1d
Broadsword swing/cut = +1
maximum basic damage = 6 + 1 = 7
DR0 → penetrating 7
cutting injury = 7 + floor(7/2) = 10
bandit HP 10 → 0
```

Therefore the supported roll-3 branch:

- bypasses active defense;
- consumes no damage RNG evidence;
- emits `resolution_mode: automatic-maximum`;
- emits `random_evidence: null`;
- produces basic damage 7 / injury 10 on the default profile;
- sets stunned and `consciousness-check-required` while leaving unconsciousness for Phase F.

The existing total-4 critical branch remains distinct: it bypasses defense but uses a normal damage roll.

Both branches are covered by deterministic replay evidence.

## Injury state

On a hit, injury subtracts from target HP.

A single injury greater than half defender HT marks the target stunned.

If remaining HP is zero or below, Phase E sets:

`consciousness-check-required = true`

but leaves:

`unconscious = false`

because the actual beginning-of-turn HT consciousness check belongs to **Phase F**.

The result explicitly records:

- remaining HP;
- major-wound flag;
- stunned;
- consciousness-check requirement;
- unconscious state;
- deferred recovery phase and timing.

Phase E does not execute knockdown position, death checks, bleeding, shock penalties, hit locations, or recovery.

## Expressions and derived values

Phase E is the first runtime execution evidence for the existing proto gaps:

- `expressions`;
- `derived_values`.

The runtime supports only the bounded pure operators required here:

- literal;
- ref;
- add;
- subtract;
- divide;
- floor.

Unknown operators or unresolved references fail visibly.

The two executed derived values are:

1. bandit Dodge target;
2. cutting injury.

Both remain `not-yet-candidate`.

## Lookup tables

The existing `lookup_tables` proto remains exercised.

Phase E adds one authoritative bounded ST10 swing-damage table.

It is deliberately **not** a complete GURPS ST damage table. Unsupported ST values fail instead of extrapolating.

## New damage/injury proto evidence

Phase E adds `damage_injury` as an exercised DIRPS gap record because DODGE 0.2.1 has typed state/effects but no first-class combat profile that composes:

```text
weapon/ST damage
→ DR
→ penetrating damage
→ damage type
→ injury multiplier
→ HP/state thresholds
```

The concept remains `not-yet-candidate`.

## Random evidence and replay

Combat can use either:

- explicit attack/defense/damage die terms; or
- one deterministic root seed.

Generated evidence derives separate deterministic seeds for attack, defense, and damage.

The combat record preserves the overall random mode and every executed nested roll.

`replay_combat_exchange()` re-executes from recorded `state_before` and recorded random evidence. Whole-record equality is required.

State/result tampering therefore diverges.

This remains one-record deterministic replay, not append-only `replay_session_history`.

## Target support

The generic encounter dispatcher now recognizes runtime kind:

`combat`

The debug target adds:

- `inspect_combat_target()`;
- `execute_combat_target()`;
- `dirps-debug-combat-target.v1`.

CLI execution with supplied evidence:

```bash
python tools/dirps_debug_target.py \
  --encounter <encounter> \
  --action <action> \
  --actor <actor> \
  --target <target> \
  --defense <defense> \
  --attack-dice <3 terms> \
  --defense-dice <3 terms> \
  --damage-dice <damage terms>
```

or use `--seed <seed>`.

The target contains no bandit, Broadsword, Dodge, HP, stun, or damage-rule literals.

It passes runtime selections/results/state through and asks the runtime to re-describe post-action availability.

## Deterministic, negative, and perturbation evidence

`tests/test_dirps_phase_e.py` covers:

1. exact initial target state;
2. runtime-described attack/defense/damage capability;
3. attack miss stopping before defense/damage;
4. successful defense stopping before damage;
5. undefended hit → cutting injury → HP loss;
6. major wound → stunned;
7. HP 0 → future consciousness check required, not automatic unconsciousness;
8. critical attack bypassing defense;
9. unsupported Parry rejected;
10. one-exchange bound;
11. deterministic seeded combat and replay;
12. tampered injury evidence divergence;
13. Broadsword-skill perturbation changing attack outcome;
14. defender-DX perturbation changing derived Dodge/outcome;
15. armor-DR perturbation changing injury;
16. unsupported attacker ST failing the bounded lookup;
17. reaction-window binding drift rejected;
18. expression drift rejected;
19. precise proto maturity;
20. generic target dispatch;
21. fake runtime result pass-through;
22. target anti-hardcoding;
23. real CLI combat execution.

Named evidence:

```text
PASS dirps/scenario-01: Phase E bounded combat exchange
PASS dirps/scenario-01: Phase E debug target consumes combat runtime
```

## Proto maturity after Phase E

Already exercised / not-yet-candidate:

- `dice_resolution`;
- `procedure_context`;
- `actor_character_model`;
- `skill_model`;
- `resolution_trace`;
- `lookup_tables`.

Newly exercised / not-yet-candidate in Phase E:

- `reaction_timing`;
- `derived_values`;
- `expressions`;
- `damage_injury`.

Still suspected:

- `visibility_and_secret_state`;
- `replay_session_history`.

## Explicit unsupported combat surface

Phase E visibly does not support:

- Parry;
- Block;
- multiple active defenses;
- multiple attacks/exchanges;
- other weapons or attack modes;
- attacker ST outside the declared ST10 damage row;
- hit locations;
- knockdown position;
- armor beyond the scenario-provided numeric DR input;
- shock penalties;
- bleeding;
- death checks;
- critical-hit special tables;
- the future HT consciousness/recovery roll.

## Phase F handoff

Phase E may leave the bandit with:

- reduced/zero HP;
- `stunned = true`;
- `consciousness-check-required = true`;
- `unconscious = false`.

That state is the input for **Phase F — Recovery / consciousness**.

Phase F, not this PR, owns the required HT recovery/consciousness checks and resulting unconscious/recovered state.
