#!/usr/bin/env python3
"""Bounded DIRPS G5 execution runtime.

This module consumes only an accepted `dirps-resolved-game.v1` model.
It currently executes exactly one path:

    attempt-skill -> success-roll -> supplied 3d6 evidence

It does not own canonical game data, generate randomness, or implement G6 targets.
"""
from __future__ import annotations

import copy


RESULT_FORMAT = "dirps-execution-result.v1"
ACTION_REF = "attempt-skill"
PROCEDURE_REF = "success-roll"
DICE_PROTO_REF = "dice_resolution"


class ExecutionError(ValueError):
    pass


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ExecutionError(f"{label} is required")
    return value


def _actor(resolved, actor_ref):
    scene = _require_mapping(resolved.get("scene"), "resolved scene")
    for row in scene.get("instances", []):
        if row.get("id") == actor_ref:
            return row
    raise ExecutionError(f"actor is not available in resolved scene: {actor_ref}")


def _dice_contract(resolved):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    specs = _require_mapping(sidecar.get("proto_specs"), "resolved proto_specs")
    spec = _require_mapping(specs.get(DICE_PROTO_REF), "dice_resolution proto contract")
    if spec.get("status") != "exercised":
        raise ExecutionError("dice_resolution proto contract must be exercised for G5 execution")

    shape = _require_mapping(spec.get("proposed_shape"), "dice_resolution proposed_shape")
    randomizer = _require_mapping(shape.get("randomizer"), "dice_resolution randomizer")
    comparator = _require_mapping(shape.get("comparator"), "dice_resolution comparator")

    if randomizer.get("kind") != "dice-pool":
        raise ExecutionError("G5 success roll requires a dice-pool randomizer")
    count = randomizer.get("count")
    sides = randomizer.get("sides")
    if not isinstance(count, int) or count <= 0:
        raise ExecutionError("dice_resolution randomizer count must be a positive integer")
    if not isinstance(sides, int) or sides < 2:
        raise ExecutionError("dice_resolution randomizer sides must be an integer >= 2")
    if randomizer.get("combine") != "sum":
        raise ExecutionError("G5 success roll requires dice combine=sum")
    if comparator.get("op") != "lte" or comparator.get("target_ref") != "effective-target":
        raise ExecutionError("G5 success roll requires lte comparison against effective-target")

    required_outputs = {"rolled_terms", "total", "success", "margin"}
    outputs = set(shape.get("outputs") or [])
    if not required_outputs.issubset(outputs):
        raise ExecutionError(
            f"dice_resolution outputs must include {sorted(required_outputs)}"
        )
    return {
        "id": shape.get("id"),
        "kind": randomizer["kind"],
        "count": count,
        "sides": sides,
        "combine": randomizer["combine"],
        "comparator": copy.deepcopy(comparator),
    }


def _execution_path(resolved):
    if resolved.get("format") != "dirps-resolved-game.v1":
        raise ExecutionError("DIRPS G5 runtime requires dirps-resolved-game.v1")

    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    if ACTION_REF not in (scenario.get("action_refs") or []):
        raise ExecutionError(f"action is not available in resolved scenario: {ACTION_REF}")

    rules = _require_mapping(resolved.get("rules"), "resolved rules")
    actions = _require_mapping(rules.get("actions"), "resolved actions")
    procedures = _require_mapping(rules.get("procedures"), "resolved procedures")
    action = _require_mapping(actions.get(ACTION_REF), f"resolved action {ACTION_REF}")
    if action.get("procedure_ref") != PROCEDURE_REF:
        raise ExecutionError(
            f"{ACTION_REF} must resolve procedure {PROCEDURE_REF}, got {action.get('procedure_ref')!r}"
        )
    procedure = _require_mapping(
        procedures.get(PROCEDURE_REF), f"resolved procedure {PROCEDURE_REF}"
    )
    return scenario, action, procedure


def _effective_target(actor, skill_ref):
    character = _require_mapping(
        actor.get("character"), f"actor {actor.get('id')} resolved character"
    )
    skills = _require_mapping(
        character.get("skills"), f"actor {actor.get('id')} resolved character skills"
    )
    if skill_ref not in skills:
        raise ExecutionError(
            f"required resolved skill target is missing for actor {actor.get('id')}: {skill_ref}"
        )
    target = skills[skill_ref]
    if not isinstance(target, int) or isinstance(target, bool):
        raise ExecutionError(
            f"resolved skill target must be an integer: {skill_ref}={target!r}"
        )
    return target


def _require_actor_available(resolved, actor):
    state = _require_mapping(actor.get("state"), f"actor {actor.get('id')} state")
    rules = _require_mapping(resolved.get("rules"), "resolved rules")
    action = rules["actions"][ACTION_REF]
    condition_refs = action.get("condition_refs") or []
    if condition_refs != ["actor-conscious"]:
        raise ExecutionError(
            "G5 bounded runtime only supports the accepted actor-conscious attempt-skill condition"
        )
    conscious = (rules.get("conditions") or {}).get("actor-conscious")
    if not isinstance(conscious, dict):
        raise ExecutionError("actor-conscious condition is missing")
    if (
        conscious.get("op") != "eq"
        or (conscious.get("left") or {}).get("ref") != "unconscious"
        or ((conscious.get("left") or {}).get("subject") or {}).get("relative")
        != "current-actor"
        or conscious.get("right") is not False
    ):
        raise ExecutionError("actor-conscious semantics are unsupported or malformed")
    if state.get("unconscious") is not False:
        raise ExecutionError(f"action {ACTION_REF} is unavailable: actor is unconscious")


def _validate_terms(terms, contract):
    if not isinstance(terms, (list, tuple)):
        raise ExecutionError("dice terms must be an ordered list")
    if len(terms) != contract["count"]:
        raise ExecutionError(
            f"dice evidence must contain exactly {contract['count']} terms"
        )
    validated = []
    for index, value in enumerate(terms):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ExecutionError(f"die term {index} must be an integer")
        if value < 1 or value > contract["sides"]:
            raise ExecutionError(
                f"die term {index}={value} is outside 1..{contract['sides']}"
            )
        validated.append(value)
    return validated


def execute_attempt_skill(resolved, *, actor_ref, skill_ref, dice_terms):
    """Execute the bounded G5 attempt-skill path from one resolved model."""
    _, action, procedure = _execution_path(resolved)
    actor = _actor(resolved, actor_ref)
    _require_actor_available(resolved, actor)
    effective_target = _effective_target(actor, skill_ref)
    dice = _dice_contract(resolved)
    terms = _validate_terms(dice_terms, dice)

    total = sum(terms)
    success = total <= effective_target
    margin = effective_target - total

    action_source_ref = action.get("source_ref")
    procedure_source_ref = procedure.get("source_ref")
    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    action_source = _require_mapping(
        sources.get(action_source_ref), f"action source {action_source_ref}"
    )
    procedure_source = _require_mapping(
        sources.get(procedure_source_ref), f"procedure source {procedure_source_ref}"
    )

    # No modifier/default/derived-stat machinery is claimed here. The effective
    # target is the exact selected skill level already carried by G4.
    return {
        "format": RESULT_FORMAT,
        "mechanic": "ordinary-success-roll",
        "input": {
            "actor_ref": actor_ref,
            "skill_ref": skill_ref,
        },
        "semantic_path": {
            "action_ref": ACTION_REF,
            "procedure_ref": PROCEDURE_REF,
        },
        "target": {
            "kind": "resolved-character-skill",
            "skill_ref": skill_ref,
            "effective_target": effective_target,
            "modifier_path": "unsupported-in-g5-bounded-slice",
        },
        "random_evidence": {
            "kind": "supplied-dice-terms",
            "proto_ref": DICE_PROTO_REF,
            "randomizer_id": dice["id"],
            "dice_kind": dice["kind"],
            "sides": dice["sides"],
            "terms": terms,
            "total": total,
        },
        "outcome": {
            "success": success,
            "margin": margin,
        },
        "trace": {
            "action": {
                "ref": ACTION_REF,
                "source_ref": action_source_ref,
                "authority": action.get("authority"),
            },
            "procedure": {
                "ref": PROCEDURE_REF,
                "source_ref": procedure_source_ref,
                "authority": procedure.get("authority"),
            },
            "sources": {
                action_source_ref: copy.deepcopy(action_source),
                procedure_source_ref: copy.deepcopy(procedure_source),
            },
        },
        "state_delta": [],
    }


def replay_attempt_skill(resolved, record):
    """Re-evaluate one execution record and fail on any divergence."""
    if not isinstance(record, dict) or record.get("format") != RESULT_FORMAT:
        raise ExecutionError("record is not a DIRPS G5 execution result")
    inputs = _require_mapping(record.get("input"), "record input")
    evidence = _require_mapping(record.get("random_evidence"), "record random_evidence")
    recomputed = execute_attempt_skill(
        resolved,
        actor_ref=inputs.get("actor_ref"),
        skill_ref=inputs.get("skill_ref"),
        dice_terms=evidence.get("terms"),
    )
    if recomputed != record:
        raise ExecutionError("execution record divergence detected")
    return recomputed
