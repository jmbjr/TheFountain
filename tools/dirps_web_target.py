#!/usr/bin/env python3
"""Thin player-facing Web target adapter for DIRPS Scenario 01.

This target owns presentation shaping only. Resolution, action availability,
random evidence, state mutation, progression, completion, and replay remain
owned by the accepted DIRPS resolver/runtime path.
"""
from __future__ import annotations

import copy
import json

from game_registry import ROOT
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
PRESENTATION_FORMAT = "dirps-web-presentation.v1"
PRESENTATION_PATH = (
    ROOT
    / "game"
    / "dirps"
    / "scenarios"
    / "scenario-01"
    / "export-contracts"
    / "web-presentation.json"
)
_RESOLVED = None
_PRESENTATION = None


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


def _presentation_contract():
    global _PRESENTATION
    if _PRESENTATION is None:
        contract = json.loads(PRESENTATION_PATH.read_text())
        if contract.get("format") != PRESENTATION_FORMAT:
            raise ValueError(
                f"DIRPS Web presentation contract must use {PRESENTATION_FORMAT}"
            )
        _PRESENTATION = contract
    return copy.deepcopy(_PRESENTATION)


def _presentation_view(scenario, characters, contract):
    scenario_copy = contract.get("scenario") or {}
    encounter_copy = {}
    current_ref = (scenario.get("progress") or {}).get("current_encounter")
    if current_ref and current_ref != "complete":
        encounter_copy = copy.deepcopy(
            (contract.get("encounters") or {}).get(current_ref, {})
        )

    action_copy = []
    action_presentation = contract.get("actions") or {}
    for action in scenario.get("available_actions", []):
        phrasing = action_presentation.get(action.get("id"), {})
        action_copy.append(
            {
                "id": action.get("id"),
                "actor_ref": action.get("actor_ref"),
                "label": phrasing.get("label")
                or action.get("label")
                or action.get("name")
                or action.get("id"),
            }
        )

    character = characters[0] if characters else {}
    return {
        "scenario": {
            "title": scenario_copy.get("title") or scenario.get("title"),
            "player_name": character.get("name"),
            "player_role": scenario_copy.get("player_role"),
            "premise": scenario_copy.get("premise") or scenario.get("premise"),
            "objective": scenario_copy.get("objective"),
            "scope_note": scenario_copy.get("scope_note"),
        },
        "encounter": encounter_copy,
        "available_actions": action_copy,
    }


def inspect_web_target(
    resolved,
    history=None,
    *,
    presentation_contract=None,
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
    characters = _character_view(resolved)
    contract = (
        _presentation_contract()
        if presentation_contract is None
        else copy.deepcopy(presentation_contract)
    )
    presentation = _presentation_view(scenario, characters, contract)
    return {
        "target": {
            "id": TARGET_ID,
            "format": TARGET_FORMAT,
            "kind": TARGET_KIND,
        },
        "status": "complete" if replay["complete"] else "ready",
        "scenario": scenario,
        "presentation": presentation,
        "characters": characters,
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
