#!/usr/bin/env python3
"""Thin player-facing Web target adapter for DIRPS Scenario 01.

This target owns presentation shaping only. Resolution, action availability,
random evidence, state mutation, progression, completion, and replay remain
owned by the accepted DIRPS resolver/runtime path.
"""
from __future__ import annotations

import copy
import json

from dirps_runtime import (
    ExecutionError,
    append_scenario_session_step,
    create_scenario_session_history,
    describe_scenario,
    replay_scenario_session_history,
)
from resolve_dirps_dodge import resolve


TARGET_ID = "dirps-web"
TARGET_FORMAT = "dirps-web-target.v1"
TARGET_KIND = "web"
_RESOLVED = None


def _character_view(resolved):
    scene = resolved.get("scene") or {}
    characters = []
    for instance in scene.get("instances", []):
        character = instance.get("character")
        if not isinstance(character, dict):
            continue
        characters.append(
            {
                "id": instance.get("id"),
                "name": instance.get("name"),
                "state": copy.deepcopy(instance.get("state", {})),
                "primary_attributes": copy.deepcopy(
                    character.get("primary_attributes", {})
                ),
                "skills": copy.deepcopy(character.get("skills", {})),
                "equipment": copy.deepcopy(character.get("equipment", [])),
                "provenance": character.get("provenance"),
            }
        )
    return characters


def inspect_web_target(
    resolved,
    history=None,
    *,
    runtime_create=create_scenario_session_history,
    runtime_replay=replay_scenario_session_history,
    runtime_describe=describe_scenario,
):
    """Return presentation-ready data derived from accepted runtime semantics."""
    session = runtime_create(resolved) if history is None else copy.deepcopy(history)
    replay = runtime_replay(resolved, session, require_complete=False)
    scenario = runtime_describe(resolved, replay["final_state"])
    latest = (
        copy.deepcopy(session["steps"][-1]["transition_record"])
        if session.get("steps")
        else None
    )
    return {
        "target": {
            "id": TARGET_ID,
            "format": TARGET_FORMAT,
            "kind": TARGET_KIND,
        },
        "status": "complete" if replay["complete"] else "ready",
        "scenario": scenario,
        "characters": _character_view(resolved),
        "history": session,
        "history_summary": {
            "format": session.get("format"),
            "steps": len(session.get("steps", [])),
            "source_identity": copy.deepcopy(session.get("source_identity")),
            "final_state_hash": replay.get("final_state_hash"),
        },
        "latest_execution": latest,
    }


def execute_web_target(
    resolved,
    history,
    *,
    action_id,
    actor_ref,
    random_seed,
    runtime_append=append_scenario_session_step,
    runtime_replay=replay_scenario_session_history,
    runtime_describe=describe_scenario,
):
    """Pass one browser selection to Phase H append/replay without recomputing it."""
    before = copy.deepcopy(history)
    try:
        updated = runtime_append(
            resolved,
            before,
            action_id=action_id,
            actor_ref=actor_ref,
            random_inputs={"random_seed": random_seed},
        )
    except ExecutionError as exc:
        view = inspect_web_target(
            resolved,
            before,
            runtime_replay=runtime_replay,
            runtime_describe=runtime_describe,
        )
        view["status"] = "error"
        view["selection"] = {
            "action_id": action_id,
            "actor_ref": actor_ref,
            "random_seed": random_seed,
        }
        view["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        return view

    view = inspect_web_target(
        resolved,
        updated,
        runtime_replay=runtime_replay,
        runtime_describe=runtime_describe,
    )
    view["selection"] = {
        "action_id": action_id,
        "actor_ref": actor_ref,
        "random_seed": random_seed,
    }
    return view


def _resolved():
    global _RESOLVED
    if _RESOLVED is None:
        _RESOLVED = resolve()
    return _RESOLVED


def web_bootstrap_json():
    return json.dumps(inspect_web_target(_resolved()), separators=(",", ":"))


def web_execute_json(history_json, action_id, actor_ref, random_seed):
    history = json.loads(history_json)
    return json.dumps(
        execute_web_target(
            _resolved(),
            history,
            action_id=action_id,
            actor_ref=actor_ref,
            random_seed=random_seed,
        ),
        separators=(",", ":"),
    )


if __name__ == "__main__":
    print(json.dumps(inspect_web_target(resolve()), indent=2))
