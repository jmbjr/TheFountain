#!/usr/bin/env python3
"""Thin G6 debug-CLI target for DIRPS Scenario 01.

The target owns only CLI interaction and presentation. All executable gameplay
semantics come from the accepted DIRPS resolver/runtime path.
"""
from __future__ import annotations

import argparse
import json

from dirps_runtime import ExecutionError, describe_attempt_skill, execute_attempt_skill
from resolve_dirps_dodge import resolve


TARGET_ID = "dirps-debug-cli"
TARGET_FORMAT = "dirps-debug-cli-target.v1"
TARGET_KIND = "debug-cli"


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
    parser.add_argument(
        "--dice",
        nargs="+",
        type=int,
        help="Explicit die terms. Runtime semantics determine the required count/range.",
    )
    args = parser.parse_args()

    resolved = resolve()
    supplied = [args.actor is not None, args.skill is not None, args.dice is not None]
    if not any(supplied):
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
