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
    describe_attempt_skill,
    describe_investigation,
    execute_attempt_skill,
    execute_investigation,
)
from resolve_dirps_dodge import resolve


TARGET_ID = "dirps-debug-cli"
TARGET_FORMAT = "dirps-debug-cli-target.v1"
TARGET_KIND = "debug-cli"
ENCOUNTER_TARGET_FORMAT = "dirps-debug-encounter-target.v1"


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
            view = _investigation_input_error_view(
                resolved,
                args.encounter,
                "--skill belongs to the legacy direct-skill mode",
            )
        elif args.action is None:
            view = inspect_investigation_target(
                resolved,
                encounter_ref=args.encounter,
            )
        elif args.actor is None:
            view = _investigation_input_error_view(
                resolved,
                args.encounter,
                "encounter execution requires --actor",
            )
        elif (args.dice is None) == (args.seed is None):
            view = _investigation_input_error_view(
                resolved,
                args.encounter,
                "encounter execution requires exactly one of --dice or --seed",
            )
        else:
            view = execute_investigation_target(
                resolved,
                encounter_ref=args.encounter,
                action_id=args.action,
                actor_ref=args.actor,
                dice_terms=args.dice,
                random_seed=args.seed,
            )
    else:
        legacy_extras = [args.action is not None, args.seed is not None]
        supplied = [args.actor is not None, args.skill is not None, args.dice is not None]
        if any(legacy_extras):
            view = _input_error_view(
                resolved,
                "--action/--seed require --encounter",
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
