#!/usr/bin/env python3
"""Thin G6 debug-CLI target for DIRPS Scenario 01.

The target owns only CLI interaction and presentation. All executable gameplay
semantics come from the accepted DIRPS resolver/runtime path.
"""
from __future__ import annotations

import argparse
import json

from dirps_runtime import (
    ExecutionError,
    create_runtime_state,
    create_social_runtime_state,
    create_environment_runtime_state,
    create_combat_runtime_state,
    describe_attempt_skill,
    describe_investigation,
    describe_social_interaction,
    describe_environment_challenge,
    describe_combat_exchange,
    encounter_runtime_kind,
    execute_attempt_skill,
    execute_investigation,
    execute_social_interaction,
    execute_environment_challenge,
    execute_combat_exchange,
)
from resolve_dirps_dodge import resolve


TARGET_ID = "dirps-debug-cli"
TARGET_FORMAT = "dirps-debug-cli-target.v1"
TARGET_KIND = "debug-cli"
ENCOUNTER_TARGET_FORMAT = "dirps-debug-encounter-target.v1"
SOCIAL_TARGET_FORMAT = "dirps-debug-social-target.v1"
ENVIRONMENT_TARGET_FORMAT = "dirps-debug-environment-target.v1"
COMBAT_TARGET_FORMAT = "dirps-debug-combat-target.v1"


def inspect_target(resolved, *, runtime_describe=describe_attempt_skill):
    """Return presentation-ready runtime capability data without executing."""
    capability = runtime_describe(resolved)
    return {
        "target": {
            "id": TARGET_ID,
            "format": TARGET_FORMAT,
            "kind": TARGET_KIND,
        },
        "status": "ready",
        "scenario": capability["scenario"],
        "capability": capability,
    }


def execute_target(
    resolved,
    *,
    actor_ref,
    skill_ref,
    dice_terms,
    runtime_execute=execute_attempt_skill,
    runtime_describe=describe_attempt_skill,
):
    """Adapt one runtime execution result for the debug target.

    The returned execution object is the runtime object itself. This adapter
    intentionally does not recompute target, dice, outcome, margin, or trace.
    """
    view = inspect_target(resolved, runtime_describe=runtime_describe)
    view["selection"] = {
        "actor_ref": actor_ref,
        "skill_ref": skill_ref,
        "dice_terms": list(dice_terms) if isinstance(dice_terms, (list, tuple)) else dice_terms,
    }
    try:
        execution = runtime_execute(
            resolved,
            actor_ref=actor_ref,
            skill_ref=skill_ref,
            dice_terms=dice_terms,
        )
    except ExecutionError as exc:
        view["status"] = "error"
        view["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        return view

    view["status"] = "ok"
    view["execution"] = execution
    return view


def inspect_investigation_target(
    resolved,
    *,
    encounter_ref,
    state=None,
    runtime_create=create_runtime_state,
    runtime_describe=describe_investigation,
):
    """Present one runtime-described stateful encounter without owning gameplay."""
    runtime_state = (
        runtime_create(resolved, encounter_ref=encounter_ref)
        if state is None
        else state
    )
    capability = runtime_describe(
        resolved,
        runtime_state,
        encounter_ref=encounter_ref,
    )
    return {
        "target": {
            "id": TARGET_ID,
            "format": ENCOUNTER_TARGET_FORMAT,
            "kind": TARGET_KIND,
        },
        "status": "ready",
        "encounter": capability["encounter"],
        "runtime_state": runtime_state,
        "capability": capability,
    }


def execute_investigation_target(
    resolved,
    *,
    encounter_ref,
    action_id,
    actor_ref,
    dice_terms=None,
    random_seed=None,
    state=None,
    runtime_create=create_runtime_state,
    runtime_describe=describe_investigation,
    runtime_execute=execute_investigation,
):
    """Pass one target selection to the Phase B runtime and return its record."""
    view = inspect_investigation_target(
        resolved,
        encounter_ref=encounter_ref,
        state=state,
        runtime_create=runtime_create,
        runtime_describe=runtime_describe,
    )
    view["selection"] = {
        "encounter_ref": encounter_ref,
        "action_id": action_id,
        "actor_ref": actor_ref,
        "dice_terms": (
            list(dice_terms) if isinstance(dice_terms, (list, tuple)) else dice_terms
        ),
        "random_seed": random_seed,
    }
    try:
        record = runtime_execute(
            resolved,
            view["runtime_state"],
            encounter_ref=encounter_ref,
            action_id=action_id,
            actor_ref=actor_ref,
            dice_terms=dice_terms,
            random_seed=random_seed,
        )
    except ExecutionError as exc:
        view["status"] = "error"
        view["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        return view

    view["status"] = "ok"
    view["execution"] = record
    view["runtime_state"] = record["state_after"]
    # Keep target capability in lockstep with the post-action runtime state.
    # Availability/state semantics remain runtime-owned: the target asks the
    # runtime description path again rather than reconstructing them here.
    view["capability"] = runtime_describe(
        resolved,
        view["runtime_state"],
        encounter_ref=encounter_ref,
    )
    view["encounter"] = view["capability"]["encounter"]
    return view


def inspect_social_target(
    resolved,
    *,
    encounter_ref,
    state=None,
    runtime_create=create_social_runtime_state,
    runtime_describe=describe_social_interaction,
):
    """Present one runtime-described social encounter without owning gameplay."""
    runtime_state = (
        runtime_create(resolved, encounter_ref=encounter_ref)
        if state is None
        else state
    )
    capability = runtime_describe(
        resolved,
        runtime_state,
        encounter_ref=encounter_ref,
    )
    return {
        "target": {
            "id": TARGET_ID,
            "format": SOCIAL_TARGET_FORMAT,
            "kind": TARGET_KIND,
        },
        "status": "ready",
        "encounter": capability["encounter"],
        "runtime_state": runtime_state,
        "capability": capability,
    }


def execute_social_target(
    resolved,
    *,
    encounter_ref,
    action_id,
    actor_ref,
    dice_terms=None,
    random_seed=None,
    state=None,
    runtime_create=create_social_runtime_state,
    runtime_describe=describe_social_interaction,
    runtime_execute=execute_social_interaction,
):
    """Pass one target selection to the Phase C runtime and return its record."""
    view = inspect_social_target(
        resolved,
        encounter_ref=encounter_ref,
        state=state,
        runtime_create=runtime_create,
        runtime_describe=runtime_describe,
    )
    view["selection"] = {
        "encounter_ref": encounter_ref,
        "action_id": action_id,
        "actor_ref": actor_ref,
        "dice_terms": (
            list(dice_terms) if isinstance(dice_terms, (list, tuple)) else dice_terms
        ),
        "random_seed": random_seed,
    }
    try:
        record = runtime_execute(
            resolved,
            view["runtime_state"],
            encounter_ref=encounter_ref,
            action_id=action_id,
            actor_ref=actor_ref,
            dice_terms=dice_terms,
            random_seed=random_seed,
        )
    except ExecutionError as exc:
        view["status"] = "error"
        view["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        return view

    view["status"] = "ok"
    view["execution"] = record
    view["runtime_state"] = record["state_after"]
    view["capability"] = runtime_describe(
        resolved,
        view["runtime_state"],
        encounter_ref=encounter_ref,
    )
    view["encounter"] = view["capability"]["encounter"]
    return view


def inspect_environment_target(
    resolved, *, encounter_ref, state=None,
    runtime_create=create_environment_runtime_state,
    runtime_describe=describe_environment_challenge,
):
    runtime_state = runtime_create(resolved, encounter_ref=encounter_ref) if state is None else state
    capability = runtime_describe(resolved, runtime_state, encounter_ref=encounter_ref)
    return {
        "target": {"id": TARGET_ID, "format": ENVIRONMENT_TARGET_FORMAT, "kind": TARGET_KIND},
        "status": "ready",
        "encounter": capability["encounter"],
        "runtime_state": runtime_state,
        "capability": capability,
    }


def execute_environment_target(
    resolved, *, encounter_ref, action_id, actor_ref,
    dice_terms=None, random_seed=None, state=None,
    runtime_create=create_environment_runtime_state,
    runtime_describe=describe_environment_challenge,
    runtime_execute=execute_environment_challenge,
):
    view = inspect_environment_target(
        resolved, encounter_ref=encounter_ref, state=state,
        runtime_create=runtime_create, runtime_describe=runtime_describe,
    )
    view["selection"] = {
        "encounter_ref": encounter_ref, "action_id": action_id, "actor_ref": actor_ref,
        "dice_terms": list(dice_terms) if isinstance(dice_terms, (list, tuple)) else dice_terms,
        "random_seed": random_seed,
    }
    try:
        record = runtime_execute(
            resolved, view["runtime_state"], encounter_ref=encounter_ref,
            action_id=action_id, actor_ref=actor_ref,
            dice_terms=dice_terms, random_seed=random_seed,
        )
    except ExecutionError as exc:
        view["status"] = "error"
        view["error"] = {"type": type(exc).__name__, "message": str(exc)}
        return view
    view["status"] = "ok"
    view["execution"] = record
    view["runtime_state"] = record["state_after"]
    view["capability"] = runtime_describe(resolved, view["runtime_state"], encounter_ref=encounter_ref)
    view["encounter"] = view["capability"]["encounter"]
    return view


def inspect_combat_target(
    resolved,
    *,
    encounter_ref,
    state=None,
    runtime_create=create_combat_runtime_state,
    runtime_describe=describe_combat_exchange,
):
    runtime_state = (
        runtime_create(resolved, encounter_ref=encounter_ref)
        if state is None
        else state
    )
    capability = runtime_describe(
        resolved, runtime_state, encounter_ref=encounter_ref
    )
    return {
        "target": {
            "id": TARGET_ID,
            "format": COMBAT_TARGET_FORMAT,
            "kind": TARGET_KIND,
        },
        "status": "ready",
        "encounter": capability["encounter"],
        "runtime_state": runtime_state,
        "capability": capability,
    }


def execute_combat_target(
    resolved,
    *,
    encounter_ref,
    action_id,
    actor_ref,
    target_ref,
    defense_kind,
    attack_terms=None,
    defense_terms=None,
    damage_terms=None,
    random_seed=None,
    state=None,
    runtime_create=create_combat_runtime_state,
    runtime_describe=describe_combat_exchange,
    runtime_execute=execute_combat_exchange,
):
    view = inspect_combat_target(
        resolved,
        encounter_ref=encounter_ref,
        state=state,
        runtime_create=runtime_create,
        runtime_describe=runtime_describe,
    )
    view["selection"] = {
        "encounter_ref": encounter_ref,
        "action_id": action_id,
        "actor_ref": actor_ref,
        "target_ref": target_ref,
        "defense_kind": defense_kind,
        "attack_terms": (
            list(attack_terms) if isinstance(attack_terms, (list, tuple)) else attack_terms
        ),
        "defense_terms": (
            list(defense_terms) if isinstance(defense_terms, (list, tuple)) else defense_terms
        ),
        "damage_terms": (
            list(damage_terms) if isinstance(damage_terms, (list, tuple)) else damage_terms
        ),
        "random_seed": random_seed,
    }
    try:
        record = runtime_execute(
            resolved,
            view["runtime_state"],
            encounter_ref=encounter_ref,
            action_id=action_id,
            actor_ref=actor_ref,
            target_ref=target_ref,
            defense_kind=defense_kind,
            attack_terms=attack_terms,
            defense_terms=defense_terms,
            damage_terms=damage_terms,
            random_seed=random_seed,
        )
    except ExecutionError as exc:
        view["status"] = "error"
        view["error"] = {"type": type(exc).__name__, "message": str(exc)}
        return view
    view["status"] = "ok"
    view["execution"] = record
    view["runtime_state"] = record["state_after"]
    view["capability"] = runtime_describe(
        resolved, view["runtime_state"], encounter_ref=encounter_ref
    )
    view["encounter"] = view["capability"]["encounter"]
    return view


def inspect_encounter_target(resolved, *, encounter_ref, state=None):
    """Dispatch encounter inspection by runtime-owned encounter kind."""
    kind = encounter_runtime_kind(resolved, encounter_ref)
    if kind == "investigation":
        return inspect_investigation_target(
            resolved, encounter_ref=encounter_ref, state=state
        )
    if kind == "social":
        return inspect_social_target(
            resolved, encounter_ref=encounter_ref, state=state
        )
    if kind == "environment":
        return inspect_environment_target(
            resolved, encounter_ref=encounter_ref, state=state
        )
    if kind == "combat":
        return inspect_combat_target(
            resolved, encounter_ref=encounter_ref, state=state
        )
    raise ExecutionError(f"unsupported encounter runtime kind: {kind}")


def execute_encounter_target(
    resolved,
    *,
    encounter_ref,
    action_id,
    actor_ref,
    dice_terms=None,
    random_seed=None,
    state=None,
    target_ref=None,
    defense_kind=None,
    attack_terms=None,
    defense_terms=None,
    damage_terms=None,
):
    """Dispatch encounter execution by runtime-owned encounter kind."""
    kind = encounter_runtime_kind(resolved, encounter_ref)
    if kind == "investigation":
        return execute_investigation_target(
            resolved,
            encounter_ref=encounter_ref,
            action_id=action_id,
            actor_ref=actor_ref,
            dice_terms=dice_terms,
            random_seed=random_seed,
            state=state,
        )
    if kind == "social":
        return execute_social_target(
            resolved,
            encounter_ref=encounter_ref,
            action_id=action_id,
            actor_ref=actor_ref,
            dice_terms=dice_terms,
            random_seed=random_seed,
            state=state,
        )
    if kind == "environment":
        return execute_environment_target(
            resolved,
            encounter_ref=encounter_ref,
            action_id=action_id,
            actor_ref=actor_ref,
            dice_terms=dice_terms,
            random_seed=random_seed,
            state=state,
        )
    if kind == "combat":
        return execute_combat_target(
            resolved,
            encounter_ref=encounter_ref,
            action_id=action_id,
            actor_ref=actor_ref,
            target_ref=target_ref,
            defense_kind=defense_kind,
            attack_terms=attack_terms,
            defense_terms=defense_terms,
            damage_terms=damage_terms,
            random_seed=random_seed,
            state=state,
        )
    raise ExecutionError(f"unsupported encounter runtime kind: {kind}")


def _encounter_input_error_view(resolved, encounter_ref, message):
    try:
        view = inspect_encounter_target(resolved, encounter_ref=encounter_ref)
    except ExecutionError as exc:
        return {
            "target": {
                "id": TARGET_ID,
                "format": ENCOUNTER_TARGET_FORMAT,
                "kind": TARGET_KIND,
            },
            "status": "error",
            "encounter": {"id": encounter_ref},
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }
    view["status"] = "error"
    view["error"] = {
        "type": "TargetInputError",
        "message": message,
    }
    return view


def _investigation_input_error_view(resolved, encounter_ref, message):
    view = inspect_investigation_target(resolved, encounter_ref=encounter_ref)
    view["status"] = "error"
    view["error"] = {
        "type": "TargetInputError",
        "message": message,
    }
    return view


def _input_error_view(resolved, message):
    view = inspect_target(resolved)
    view["status"] = "error"
    view["error"] = {
        "type": "TargetInputError",
        "message": message,
    }
    return view


def main():
    parser = argparse.ArgumentParser(
        description="Inspect or execute the bounded DIRPS Scenario 01 debug target."
    )
    parser.add_argument("--actor", help="Resolved actor id to execute.")
    parser.add_argument("--skill", help="Resolved skill id to execute.")
    parser.add_argument("--encounter", help="Resolved encounter id to inspect/execute.")
    parser.add_argument("--action", help="Encounter action id to execute.")
    parser.add_argument("--seed", help="Deterministic runtime random seed.")
    parser.add_argument("--target", help="Resolved combat target actor id.")
    parser.add_argument("--defense", help="Selected active-defense id.")
    parser.add_argument("--attack-dice", nargs="+", type=int, help="Explicit attack-roll die terms.")
    parser.add_argument("--defense-dice", nargs="+", type=int, help="Explicit defense-roll die terms.")
    parser.add_argument("--damage-dice", nargs="+", type=int, help="Explicit damage-roll die terms.")
    parser.add_argument(
        "--dice",
        nargs="+",
        type=int,
        help="Explicit die terms. Runtime semantics determine the required count/range.",
    )
    args = parser.parse_args()

    resolved = resolve()

    if args.encounter is not None:
        if args.skill is not None:
            view = _encounter_input_error_view(
                resolved,
                args.encounter,
                "--skill belongs to the legacy direct-skill mode",
            )
        elif args.action is None:
            view = inspect_encounter_target(
                resolved,
                encounter_ref=args.encounter,
            )
        elif args.actor is None:
            view = _encounter_input_error_view(
                resolved,
                args.encounter,
                "encounter execution requires --actor",
            )
        else:
            try:
                kind = encounter_runtime_kind(resolved, args.encounter)
            except ExecutionError as exc:
                view = _encounter_input_error_view(
                    resolved, args.encounter, str(exc)
                )
            else:
                if kind == "combat":
                    supplied_combat = any(
                        value is not None
                        for value in (args.attack_dice, args.defense_dice, args.damage_dice)
                    )
                    if args.target is None or args.defense is None:
                        view = _encounter_input_error_view(
                            resolved,
                            args.encounter,
                            "combat execution requires --target and --defense",
                        )
                    elif args.seed is None and args.attack_dice is None:
                        view = _encounter_input_error_view(
                            resolved,
                            args.encounter,
                            "combat execution requires --seed or --attack-dice",
                        )
                    elif args.seed is not None and supplied_combat:
                        view = _encounter_input_error_view(
                            resolved,
                            args.encounter,
                            "combat execution cannot mix --seed with explicit combat dice",
                        )
                    else:
                        view = execute_encounter_target(
                            resolved,
                            encounter_ref=args.encounter,
                            action_id=args.action,
                            actor_ref=args.actor,
                            target_ref=args.target,
                            defense_kind=args.defense,
                            attack_terms=args.attack_dice,
                            defense_terms=args.defense_dice,
                            damage_terms=args.damage_dice,
                            random_seed=args.seed,
                        )
                elif any(
                    value is not None
                    for value in (
                        args.target,
                        args.defense,
                        args.attack_dice,
                        args.defense_dice,
                        args.damage_dice,
                    )
                ):
                    view = _encounter_input_error_view(
                        resolved,
                        args.encounter,
                        "combat-specific inputs require a combat encounter",
                    )
                elif (args.dice is None) == (args.seed is None):
                    view = _encounter_input_error_view(
                        resolved,
                        args.encounter,
                        "encounter execution requires exactly one of --dice or --seed",
                    )
                else:
                    view = execute_encounter_target(
                        resolved,
                        encounter_ref=args.encounter,
                        action_id=args.action,
                        actor_ref=args.actor,
                        dice_terms=args.dice,
                        random_seed=args.seed,
                    )
    else:
        legacy_extras = [
            args.action is not None,
            args.seed is not None,
            args.target is not None,
            args.defense is not None,
            args.attack_dice is not None,
            args.defense_dice is not None,
            args.damage_dice is not None,
        ]
        supplied = [args.actor is not None, args.skill is not None, args.dice is not None]
        if any(legacy_extras):
            view = _input_error_view(
                resolved,
                "encounter/combat-specific inputs require --encounter",
            )
        elif not any(supplied):
            view = inspect_target(resolved)
        elif not all(supplied):
            view = _input_error_view(
                resolved,
                "execution requires --actor, --skill, and --dice together",
            )
        else:
            view = execute_target(
                resolved,
                actor_ref=args.actor,
                skill_ref=args.skill,
                dice_terms=args.dice,
            )

    print(json.dumps(view, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
