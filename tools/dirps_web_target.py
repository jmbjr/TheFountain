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



def _fact(label, value):
    return {"label": label, "value": copy.deepcopy(value)}


def _roll_section(title, roll, *, target_label):
    target = roll.get("target") or {}
    evidence = roll.get("random_evidence") or {}
    outcome = roll.get("outcome") or {}
    target_ref = target.get("skill_ref") or target.get("attribute_ref")
    facts = []
    if target_ref is not None:
        facts.append(_fact(target_label, target_ref))
    if target.get("base_target") is not None:
        facts.append(_fact("Base", target.get("base_target")))
    if target.get("modifier_total") is not None:
        facts.append(_fact("Modifier", target.get("modifier_total")))
    effective = target.get("effective_target")
    if effective is not None:
        facts.append(_fact("Effective target", effective))
    elif roll.get("target") is not None and not isinstance(roll.get("target"), dict):
        facts.append(_fact("Target", roll.get("target")))
    if evidence.get("total") is not None:
        facts.append(_fact("Roll", evidence.get("total")))
    facts.extend(
        [
            _fact("Result", outcome.get("classification")),
            _fact("Success", outcome.get("success")),
            _fact("Margin", outcome.get("margin")),
        ]
    )
    modifiers = [
        {
            "amount": copy.deepcopy(row.get("amount")),
            "reason": row.get("reason"),
        }
        for row in target.get("modifiers", [])
        if isinstance(row, dict)
    ]
    return {
        "title": title,
        "facts": facts,
        "modifiers": modifiers,
    }


def _simple_roll_section(title, roll, *, subject_label=None, subject=None):
    evidence = roll.get("random_evidence") or {}
    outcome = roll.get("outcome") or {}
    facts = []
    if subject_label and subject is not None:
        facts.append(_fact(subject_label, subject))
    if roll.get("base_ht") is not None:
        facts.append(_fact("Base HT", roll.get("base_ht")))
    if roll.get("modifier") is not None:
        facts.append(_fact("Modifier", roll.get("modifier")))
    if roll.get("target") is not None:
        facts.append(_fact("Target", roll.get("target")))
    if evidence.get("total") is not None:
        facts.append(_fact("Roll", evidence.get("total")))
    facts.extend(
        [
            _fact("Result", outcome.get("classification")),
            _fact("Success", outcome.get("success")),
            _fact("Margin", outcome.get("margin")),
        ]
    )
    return {"title": title, "facts": facts, "modifiers": []}


def _resolution_explanation(record):
    if not isinstance(record, dict):
        return None
    mechanic = record.get("mechanic_result")
    if not isinstance(mechanic, dict):
        return None

    result_format = mechanic.get("format")
    explanation = {
        "format": result_format,
        "sections": [],
        "consequence": None,
        "state_change": copy.deepcopy(mechanic.get("state_delta") or []),
    }

    if result_format == "dirps-encounter-result.v1":
        roll = mechanic.get("skill_resolution") or {}
        explanation["title"] = "Skill check"
        explanation["sections"].append(
            _roll_section("Check", roll, target_label="Skill")
        )
        explanation["consequence"] = (mechanic.get("consequence") or {}).get(
            "information_text"
        )

    elif result_format == "dirps-social-encounter-result.v1":
        reaction = mechanic.get("reaction_resolution") or {}
        evidence = reaction.get("random_evidence") or {}
        explanation["title"] = "Reaction roll"
        explanation["sections"].append(
            {
                "title": "Reaction",
                "facts": [
                    _fact("Roll", evidence.get("raw_total")),
                    _fact("Modifier", reaction.get("modifier_total")),
                    _fact("Modified total", reaction.get("modified_total")),
                    _fact("Reaction", mechanic.get("reaction")),
                ],
                "modifiers": [],
            }
        )
        explanation["consequence"] = (mechanic.get("consequence") or {}).get(
            "information_text"
        )

    elif result_format == "dirps-environment-encounter-result.v1":
        roll = mechanic.get("attribute_resolution") or {}
        explanation["title"] = "Attribute check"
        explanation["sections"].append(
            _roll_section("Check", roll, target_label="Attribute")
        )
        explanation["consequence"] = (mechanic.get("consequence") or {}).get(
            "consequence_text"
        )

    elif result_format == "dirps-combat-exchange-result.v1":
        explanation["title"] = "Combat exchange"
        attack = mechanic.get("attack_resolution") or {}
        explanation["sections"].append(
            _simple_roll_section(
                "Rook attacks",
                attack,
                subject_label="Skill",
                subject=attack.get("skill_ref"),
            )
        )

        defense = mechanic.get("defense_resolution")
        if isinstance(defense, dict):
            explanation["sections"].append(
                _simple_roll_section(
                    "Bandit defends",
                    defense,
                    subject_label="Defense",
                    subject=defense.get("kind"),
                )
            )

        damage = mechanic.get("damage_resolution")
        if isinstance(damage, dict):
            damage_facts = [
                _fact("Basic damage", damage.get("basic_damage")),
                _fact("Armor DR", damage.get("armor_dr")),
                _fact("Penetrating damage", damage.get("penetrating_damage")),
                _fact("Injury", damage.get("injury")),
            ]
            explanation["sections"].append(
                {"title": "Damage and injury", "facts": damage_facts, "modifiers": []}
            )

        injury = mechanic.get("injury_effects") or {}
        explanation["sections"].append(
            {
                "title": "Bandit condition",
                "facts": [
                    _fact("HP remaining", injury.get("remaining_hp")),
                    _fact("Major wound", injury.get("major_wound")),
                    _fact("Stunned", injury.get("stunned")),
                    _fact("Unconscious", injury.get("unconscious")),
                    _fact(
                        "Consciousness check required",
                        injury.get("consciousness_check_required"),
                    ),
                ],
                "modifiers": [],
            }
        )
        branch_text = {
            "attack-missed": "Rook's attack missed; no defense or damage roll followed.",
            "defended": "The bandit successfully defended; no damage was applied.",
            "hit": "Rook's attack got through and the recorded injury was applied.",
        }
        explanation["consequence"] = branch_text.get(mechanic.get("outcome_branch"))

    elif result_format == "dirps-recovery-result.v1":
        explanation["title"] = "Recovery checks"
        consciousness = mechanic.get("consciousness_check")
        if isinstance(consciousness, dict):
            explanation["sections"].append(
                _simple_roll_section("Consciousness", consciousness)
            )
        stun = mechanic.get("stun_recovery_check")
        if isinstance(stun, dict):
            explanation["sections"].append(
                _simple_roll_section("Stun recovery", stun)
            )
        outcome = mechanic.get("outcome") or {}
        explanation["sections"].append(
            {
                "title": "Resulting condition",
                "facts": [
                    _fact("Can act normally", outcome.get("can_act_normally")),
                    _fact(
                        "Consciousness check still required",
                        outcome.get("consciousness_check_required"),
                    ),
                ],
                "modifiers": [],
            }
        )
        explanation["skipped_checks"] = copy.deepcopy(
            mechanic.get("skipped_checks") or []
        )

    else:
        explanation["title"] = "Resolved action"
        explanation["sections"].append(
            {
                "title": "Runtime result",
                "facts": [_fact("Result format", result_format)],
                "modifiers": [],
            }
        )

    progression = record.get("progression") or {}
    explanation["progression"] = {
        "advanced_to": copy.deepcopy(progression.get("advanced_to")),
        "terminal": copy.deepcopy(progression.get("terminal")),
        "outcome": copy.deepcopy(progression.get("outcome")),
    }
    return explanation

def _transition_view(scenario, latest, contract, resolution_explanation):
    if not isinstance(latest, dict):
        return None
    progression = latest.get("progression") or {}
    from_encounter = latest.get("encounter_ref")
    from_step = latest.get("step")
    to_encounter = progression.get("advanced_to")
    to_step = (scenario.get("progress") or {}).get("step")
    if not all(isinstance(value, str) and value for value in (
        from_encounter, from_step, to_encounter, to_step
    )):
        return None

    key = f"{from_encounter}:{from_step}->{to_encounter}:{to_step}"
    copy_row = (contract.get("transitions") or {}).get(key)
    if not isinstance(copy_row, dict):
        return None

    if progression.get("terminal"):
        outcome_text = progression.get("conclusion_text")
    else:
        outcome_text = (
            (resolution_explanation or {}).get("consequence")
            if isinstance(resolution_explanation, dict)
            else None
        )
    return {
        "key": key,
        "from_encounter": from_encounter,
        "from_step": from_step,
        "to_encounter": to_encounter,
        "to_step": to_step,
        "outcome_text": copy.deepcopy(outcome_text),
        "bridge_text": copy_row.get("bridge_text"),
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
    resolution_explanation = _resolution_explanation(latest)
    transition = _transition_view(
        scenario, latest, contract, resolution_explanation
    )
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
        "resolution_explanation": resolution_explanation,
        "transition": transition,
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
