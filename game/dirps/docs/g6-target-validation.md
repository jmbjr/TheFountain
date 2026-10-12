# DIRPS Scenario 01 — G6 target evidence

This is the durable G6 target contract for the first DIRPS target consumer.

- Baseline: accepted/merged G5 PR #176
- G5 accepted head: `9df7ca690f06ba73942f163867e421aca37d5913`
- G5 merge SHA: `ae3b624d235c7832790ef3eea408b789c45fd8f5`
- G6 branch base: `fbce97f00e2bfc38e6f84451bfa989e3a289291c`
- DODGE version: `0.2.1`
- DODGE revision pinned by TheFountain CI: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- Target type: debug CLI
- Target entry point: `tools/dirps_debug_target.py`
- Resolved model: `dirps-resolved-game.v1`
- Runtime: `tools/dirps_runtime.py`
- G7 status: intentionally not claimed

## Why a CLI target

The accepted DIRPS runtime is Python. The existing mature Wretched Web target uses a separate JavaScript runtime stack.

Forcing a browser target at G6 would therefore require either:

- duplicating the accepted DIRPS execution semantics in JavaScript; or
- introducing a new browser/server/build bridge whose complexity is unrelated to proving the target boundary.

The debug CLI is the thinner honest target. It directly consumes the accepted resolver/runtime and exposes the execution evidence without adding a second gameplay engine.

## Architecture

The target follows:

```text
Scenario 01 source
→ DODGE 0.2.1
→ dirps@0.1.0 source validation
→ tools/resolve_dirps_dodge.py
→ dirps-resolved-game.v1
→ dirps@0.1.0 resolved-game validation
→ tools/dirps_runtime.py
→ tools/dirps_debug_target.py
→ JSON debug presentation
```

The target calls:

- `describe_attempt_skill(resolved)` for target-neutral capability inspection;
- `execute_attempt_skill(resolved, ...)` for execution.

The target never computes a roll result itself.

## Target registration

Scenario 01 uses the repository's existing `generated_targets` descriptor map:

```json
{
  "generated_targets": {
    "debug-cli": "../../tools/dirps_debug_target.py"
  }
}
```

No parallel DIRPS-only target registry was introduced.

The field name is historical; for this source-controlled debug target the registered value is the target entry point rather than a generated artifact directory.

## DODGE export-contract / manifest status

This debug CLI does **not** use the DODGE export-contract/target-manifest model.

DODGE 0.2.1 Step 12 allows a small debug/CLI target once the neutral boundary works. Step 13 applies the export-contract/manifest lifecycle **when a target uses that model**.

Therefore:

- Scenario 01 declares no DIRPS export contract at G6;
- the generic G6 manifest loop has no DIRPS contract to resolve;
- no fake target manifest is emitted;
- G6 acceptance is project-defined target-consumption evidence plus retained DODGE lifecycle evidence.

## Runtime capability inspection

`describe_attempt_skill(resolved)` exposes the already-accepted runtime semantics for target consumption:

- scenario identity;
- executable action/procedure identity;
- resolved actors;
- resolved character skill choices;
- effective-target source kind;
- supported target domain;
- modifier policy;
- explicit dice/random-evidence contract;
- result scope;
- no-state-mutation policy;
- authoritative/provisional provenance layers.

This helper adds no new game rule. It is a target-neutral inspection of the same binding and dice contracts already enforced by G5.

## Target-owned responsibilities

The debug target owns only:

- CLI argument parsing;
- selected actor id;
- selected skill id;
- entered die values;
- debug JSON formatting;
- mapping `ExecutionError` to a visible error object;
- target identity/format labels.

Those are presentation / interaction-adaptation concerns.

## Runtime-owned responsibilities

The target delegates all executable semantics to the runtime, including:

- which action/procedure is executable;
- actor availability;
- skill lookup;
- effective target;
- supported target domain;
- dice count/sides;
- total;
- success/failure;
- margin;
- source authority/provenance;
- state delta.

The target adapter does not contain the semantic literals `attempt-skill`, `success-roll`, `tracking`, `gurps-lite`, `dirps-proto`, `scenario-01-source`, `prototype_assumption`, or the 4/16 target bounds.

## Target views

Inspection mode:

```bash
python tools/dirps_debug_target.py
```

returns scenario identity plus the runtime-described executable capability, actors, skills, dice contract, target domain, and provenance.

Execution mode accepts explicit user-selected actor/skill/die inputs:

```bash
python tools/dirps_debug_target.py --actor <actor> --skill <skill> --dice <terms...>
```

The runtime determines whether those inputs are legal. The target does not know or enforce the gameplay-specific die count/domain itself.

A successful target view contains the exact runtime execution object unchanged under `execution`.

A runtime failure produces:

```json
{
  "status": "error",
  "error": {
    "type": "ExecutionError",
    "message": "..."
  }
}
```

and no guessed `execution` result.

## Perturbation evidence

`tests/test_dirps_target.py` changes the canonical Tracking value through the full authority path:

```text
scenario source
→ DODGE character extension
→ G4 resolver
→ G5 runtime
→ G6 target
```

With the same supplied roll, the displayed effective target and outcome change with the source.

This proves the target does not contain a copied `Tracking = 12` fact.

## No-recomputation evidence

A focused test injects a fake runtime result containing deliberately unusual target/total/margin values.

The target returns that same object by identity and displays those runtime-provided values unchanged.

A separate capability test injects a fake runtime description with unusual action/procedure, dice, domain, actor, and skill values; the target exposes the injected capability unchanged.

Together these prove the target is adapting runtime output, not re-deriving gameplay.

## Error evidence

Focused target tests verify visible runtime errors for:

- effective target outside the accepted G5 domain;
- malformed dice evidence;
- missing skill;
- unavailable actor.

The target returns no execution outcome in those cases.

It does not translate an error into a guessed success/failure result.

## Provenance display evidence

A successful target result exposes all three accepted G5 authority layers:

1. `gurps-lite` — authoritative action/procedure semantics;
2. `dirps-proto` — provisional execution binding;
3. `scenario-01-source` — provisional target value with `prototype_assumption` character provenance.

The target passes the runtime trace through intact.

## G6 boundary / unsupported mechanics

The target offers only the runtime-described bounded success-roll capability.

It does not expose or implement:

- attack;
- active defense;
- damage/injury;
- recovery;
- social/reaction resolution;
- environmental consequences;
- critical-result consequences;
- situational modifiers;
- skill defaults;
- generated/derived targets;
- generated RNG;
- a turn loop;
- scenario completion;
- persistent game state;
- session-history replay.

A source-level regression also checks the target module for forbidden private gameplay literals.

## State

The G5 mechanic is non-mutating, so G6 invents no persistent game state.

The CLI's selected actor, selected skill, and entered dice are target-owned interaction state only.

The runtime result continues to report an empty `state_delta`.

## Tests

`tests/test_dirps_target.py` proves:

1. inspection exposes runtime-described scenario/capability/actors/skills;
2. a successful target execution comes from the real G5 runtime;
3. source perturbation reaches the target;
4. fake runtime execution output is passed through unchanged;
5. fake capability metadata is passed through unchanged;
6. out-of-domain errors remain visible errors;
7. malformed dice errors remain visible errors;
8. missing-skill errors remain visible errors;
9. unavailable-actor errors remain visible errors;
10. all three authority layers are exposed;
11. the target source contains no private gameplay literals;
12. unsupported mechanics are absent from the offered target surface.

The positive test emits:

```text
PASS dirps/scenario-01: debug-cli target consumes DIRPS runtime
```

## Proto maturity after G6

No proto concept advances merely because a target displays it.

The five G5 concepts remain `exercised` and `not-yet-candidate`:

- `dice_resolution`;
- `procedure_context`;
- `actor_character_model`;
- `skill_model`;
- `resolution_trace`.

The untouched concepts remain `suspected`:

- `derived_values`;
- `expressions`;
- `lookup_tables`;
- `reaction_timing`;
- `visibility_and_secret_state`;
- `replay_session_history`.

The proto sidecar itself is unchanged by G6.

## Why G7 is not claimed

G6 proves one target consumes the accepted resolved/runtime semantics.

G7 still requires a whole-system reference-quality assessment. Scenario 01 still has intentionally unimplemented mechanics and does not yet execute all of its broader tutorial claims.

No G7 work is included in this tranche.
