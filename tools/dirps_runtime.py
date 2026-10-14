#!/usr/bin/env python3
"""Bounded DIRPS execution runtime.

This module consumes only an accepted `dirps-resolved-game.v1` model.
It executes the accepted success-roll path plus the bounded Phase A-G
investigation, social, environmental, combat, recovery, and scenario-progression
slices over neutral resolved semantics and DODGE runtime state/effects.

It does not own canonical scenario facts or target presentation.
"""
from __future__ import annotations

import copy
import hashlib
import math


BINDING_ID = "attempt-skill"
RNG_ALGORITHM = "sha256-rejection-v1"
PHASE_B_RESULT_FORMAT = "dirps-encounter-result.v1"
PHASE_C_REACTION_FORMAT = "dirps-reaction-result.v1"
PHASE_C_RESULT_FORMAT = "dirps-social-encounter-result.v1"
PHASE_D_ATTRIBUTE_RESULT_FORMAT = "dirps-attribute-result.v1"
PHASE_D_RESULT_FORMAT = "dirps-environment-encounter-result.v1"
PHASE_E_ATTACK_FORMAT = "dirps-attack-result.v1"
PHASE_E_DEFENSE_FORMAT = "dirps-active-defense-result.v1"
PHASE_E_DAMAGE_FORMAT = "dirps-damage-result.v1"
PHASE_E_RESULT_FORMAT = "dirps-combat-exchange-result.v1"
PHASE_F_CHECK_FORMAT = "dirps-ht-check-result.v1"
PHASE_F_RESULT_FORMAT = "dirps-recovery-result.v1"
PHASE_G_RESULT_FORMAT = "dirps-scenario-progression-result.v1"


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


def _execution_binding(resolved):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    bindings = _require_mapping(
        sidecar.get("phase_a_execution_bindings"),
        "resolved phase_a_execution_bindings"
    )
    binding = _require_mapping(
        bindings.get(BINDING_ID), f"execution binding {BINDING_ID}"
    )

    if (
        binding.get("actor_input") != "actor_ref"
        or binding.get("target_input") != "skill_ref"
        or binding.get("context_input") != "context_ref"
    ):
        raise ExecutionError("attempt-skill runtime input binding is unsupported or malformed")
    if not binding.get("action_ref") or not binding.get("procedure_ref"):
        raise ExecutionError("attempt-skill action/procedure binding is incomplete")
    if binding.get("dice_resolution_ref") != "dice_resolution":
        raise ExecutionError("attempt-skill dice-resolution binding is unsupported or malformed")
    if binding.get("target_source") != {
        "kind": "resolved-character-skill",
        "path": "scene.instances[].character.skills",
    }:
        raise ExecutionError("attempt-skill target source is unsupported or malformed")
    if binding.get("context_source") != {
        "kind": "resolved-scenario-contextual-check",
        "path": "scenario.contextual_checks",
    }:
        raise ExecutionError("attempt-skill context source is unsupported or malformed")

    effective = _require_mapping(
        binding.get("effective_target"), "attempt-skill effective-target binding"
    )
    if (
        effective.get("from") != "selected-skill-level-plus-context-modifiers"
        or effective.get("modifier_policy") != "sum-resolved-context-modifiers"
        or effective.get("minimum") != 3
        or effective.get("below_minimum") != "error"
        or effective.get("rule_source_ref") != "gurps-lite"
        or effective.get("rule_locator") != "p. 2, Modifiers and Effective Skill"
    ):
        raise ExecutionError("attempt-skill effective-target binding is unsupported or malformed")

    critical = _require_mapping(
        binding.get("critical_resolution"), "attempt-skill critical-resolution binding"
    )
    if (
        critical.get("rule_source_ref") != "gurps-lite"
        or critical.get("rule_locator") != "p. 2, Critical Success and Failure"
        or critical.get("classifications")
        != ["critical-success", "success", "failure", "critical-failure"]
    ):
        raise ExecutionError("attempt-skill critical-resolution binding is unsupported or malformed")

    random_evidence = _require_mapping(
        binding.get("random_evidence"), "attempt-skill random-evidence binding"
    )
    generated = _require_mapping(
        random_evidence.get("generated"), "attempt-skill generated random-evidence binding"
    )
    if (
        random_evidence.get("supplied_terms") != {"supported": True}
        or generated.get("supported") is not True
        or generated.get("seed_required") is not True
        or generated.get("algorithm") != RNG_ALGORITHM
    ):
        raise ExecutionError("attempt-skill random-evidence binding is unsupported or malformed")

    if binding.get("binding_source_ref") != "dirps-proto":
        raise ExecutionError("attempt-skill binding provenance source is unsupported or malformed")
    if binding.get("target_provenance") != {
        "source_ref": "scenario-01-source",
        "character_provenance": "prototype_assumption",
        "canonical_path": "player_character.skills",
        "context_source_ref": "scenario-01-source",
        "context_path": "contextual_checks",
    }:
        raise ExecutionError("attempt-skill target provenance is unsupported or malformed")
    if binding.get("result_scope") != "success-failure-margin-and-critical-classification":
        raise ExecutionError("attempt-skill result scope is unsupported or malformed")
    if binding.get("result_format") != "dirps-execution-result.v2":
        raise ExecutionError("Phase A attempt-skill result format is unsupported")
    if binding.get("state_mutation") != "none":
        raise ExecutionError("bounded attempt-skill must not declare state mutation")
    return binding


def _legacy_g5_binding(resolved):
    """Return and validate the immutable accepted G5/v1 execution binding."""
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    bindings = _require_mapping(
        sidecar.get("g5_execution_bindings"), "resolved g5_execution_bindings"
    )
    binding = _require_mapping(
        bindings.get(BINDING_ID), f"G5 execution binding {BINDING_ID}"
    )
    if (
        binding.get("actor_input") != "actor_ref"
        or binding.get("target_input") != "skill_ref"
    ):
        raise ExecutionError(
            "attempt-skill runtime input binding is unsupported or malformed"
        )
    if not binding.get("action_ref") or not binding.get("procedure_ref"):
        raise ExecutionError("attempt-skill action/procedure binding is incomplete")
    if binding.get("dice_resolution_ref") != "dice_resolution":
        raise ExecutionError(
            "attempt-skill dice-resolution binding is unsupported or malformed"
        )
    if binding.get("target_source") != {
        "kind": "resolved-character-skill",
        "path": "scene.instances[].character.skills",
    }:
        raise ExecutionError("attempt-skill target source is unsupported or malformed")
    effective = binding.get("effective_target")
    if effective != {
        "from": "selected-skill-level",
        "modifier_policy": "unsupported",
        "supported_domain": {"minimum": 4, "maximum": 16},
        "outside_domain": "error",
    }:
        raise ExecutionError(
            "attempt-skill effective-target binding is unsupported or malformed"
        )
    if binding.get("binding_source_ref") != "dirps-proto":
        raise ExecutionError(
            "attempt-skill binding provenance source is unsupported or malformed"
        )
    if binding.get("target_provenance") != {
        "source_ref": "scenario-01-source",
        "character_provenance": "prototype_assumption",
        "canonical_path": "player_character.skills",
    }:
        raise ExecutionError(
            "attempt-skill target provenance is unsupported or malformed"
        )
    if binding.get("result_scope") != "binary-success-and-margin-only":
        raise ExecutionError("attempt-skill result scope is unsupported or malformed")
    if binding.get("result_format") != "dirps-execution-result.v1":
        raise ExecutionError("attempt-skill result format is unsupported")
    if binding.get("state_mutation") != "none":
        raise ExecutionError("bounded G5 attempt-skill must not declare state mutation")
    return binding

def _dice_contract(resolved, binding):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    specs = _require_mapping(sidecar.get("proto_specs"), "resolved proto_specs")
    proto_ref = binding.get("dice_resolution_ref")
    spec = _require_mapping(specs.get(proto_ref), f"{proto_ref} proto contract")
    if spec.get("status") != "exercised":
        raise ExecutionError(f"{proto_ref} proto contract must be exercised")

    shape = _require_mapping(spec.get("proposed_shape"), f"{proto_ref} proposed_shape")
    randomizer = _require_mapping(shape.get("randomizer"), "dice_resolution randomizer")
    comparator = _require_mapping(shape.get("comparator"), "dice_resolution comparator")

    if randomizer.get("kind") != "dice-pool":
        raise ExecutionError("success roll requires a dice-pool randomizer")
    count = randomizer.get("count")
    sides = randomizer.get("sides")
    if not isinstance(count, int) or count <= 0:
        raise ExecutionError("dice_resolution randomizer count must be a positive integer")
    if not isinstance(sides, int) or sides < 2:
        raise ExecutionError("dice_resolution randomizer sides must be an integer >= 2")
    if randomizer.get("combine") != "sum":
        raise ExecutionError("success roll requires dice combine=sum")
    if comparator.get("op") != "lte" or comparator.get("target_ref") != "effective-target":
        raise ExecutionError("success roll requires lte comparison against effective-target")

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
        raise ExecutionError("DIRPS runtime requires dirps-resolved-game.v1")

    binding = _execution_binding(resolved)
    action_ref = binding.get("action_ref")
    procedure_ref = binding.get("procedure_ref")

    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    if action_ref not in (scenario.get("action_refs") or []):
        raise ExecutionError(f"action is not available in resolved scenario: {action_ref}")

    rules = _require_mapping(resolved.get("rules"), "resolved rules")
    actions = _require_mapping(rules.get("actions"), "resolved actions")
    procedures = _require_mapping(rules.get("procedures"), "resolved procedures")
    action = _require_mapping(actions.get(action_ref), f"resolved action {action_ref}")
    if action.get("procedure_ref") != procedure_ref:
        raise ExecutionError(
            f"{action_ref} must resolve procedure {procedure_ref}, got {action.get('procedure_ref')!r}"
        )
    procedure = _require_mapping(
        procedures.get(procedure_ref), f"resolved procedure {procedure_ref}"
    )
    return binding, scenario, action, procedure


def _legacy_execution_path(resolved):
    if resolved.get("format") != "dirps-resolved-game.v1":
        raise ExecutionError("DIRPS G5 runtime requires dirps-resolved-game.v1")

    binding = _legacy_g5_binding(resolved)
    action_ref = binding.get("action_ref")
    procedure_ref = binding.get("procedure_ref")

    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    if action_ref not in (scenario.get("action_refs") or []):
        raise ExecutionError(f"action is not available in resolved scenario: {action_ref}")

    rules = _require_mapping(resolved.get("rules"), "resolved rules")
    actions = _require_mapping(rules.get("actions"), "resolved actions")
    procedures = _require_mapping(rules.get("procedures"), "resolved procedures")
    action = _require_mapping(actions.get(action_ref), f"resolved action {action_ref}")
    if action.get("procedure_ref") != procedure_ref:
        raise ExecutionError(
            f"{action_ref} must resolve procedure {procedure_ref}, got {action.get('procedure_ref')!r}"
        )
    procedure = _require_mapping(
        procedures.get(procedure_ref), f"resolved procedure {procedure_ref}"
    )
    return binding, scenario, action, procedure


def _resolved_skill(actor, skill_ref, binding):
    target_source = binding.get("target_source") or {}
    if target_source.get("kind") != "resolved-character-skill":
        raise ExecutionError("runtime does not support this target source kind")

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


def _legacy_effective_target(actor, skill_ref, binding):
    target = _resolved_skill(actor, skill_ref, binding)
    effective = _require_mapping(
        binding.get("effective_target"), "legacy G5 effective-target binding"
    )
    if effective.get("from") != "selected-skill-level":
        raise ExecutionError("legacy G5 effective-target source is unsupported")
    if effective.get("modifier_policy") != "unsupported":
        raise ExecutionError("legacy G5 modifier policy must remain unsupported")

    domain = _require_mapping(
        effective.get("supported_domain"), "legacy G5 supported target domain"
    )
    minimum = domain.get("minimum")
    maximum = domain.get("maximum")
    if (
        not isinstance(minimum, int)
        or not isinstance(maximum, int)
        or minimum > maximum
    ):
        raise ExecutionError("legacy G5 supported target domain is malformed")
    if target < minimum or target > maximum:
        raise ExecutionError(
            f"resolved skill target {target} is outside supported G5 domain {minimum}..{maximum}"
        )
    return target


def _contextual_check(resolved, context_ref, binding):
    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    checks = _require_mapping(
        scenario.get("contextual_checks"), "resolved scenario contextual_checks"
    )
    check = _require_mapping(
        checks.get(context_ref), f"resolved contextual check {context_ref}"
    )
    if check.get("action_ref") != binding["action_ref"]:
        raise ExecutionError(
            f"contextual check {context_ref} does not bind action {binding['action_ref']}"
        )
    skill_ref = check.get("skill_ref")
    if not isinstance(skill_ref, str) or not skill_ref:
        raise ExecutionError(f"contextual check {context_ref} has no skill_ref")
    modifiers = check.get("modifiers")
    if not isinstance(modifiers, list) or not modifiers:
        raise ExecutionError(f"contextual check {context_ref} has no resolved modifiers")
    return check, skill_ref, copy.deepcopy(modifiers)


def _validated_modifiers(resolved, modifiers, binding):
    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    target_provenance = _require_mapping(
        binding.get("target_provenance"), "attempt-skill target provenance"
    )
    expected_source_ref = target_provenance.get("context_source_ref")
    expected_provenance = target_provenance.get("character_provenance")

    rows = []
    seen = set()
    for index, modifier in enumerate(modifiers):
        row = _require_mapping(modifier, f"contextual modifier {index}")
        modifier_id = row.get("id")
        if not isinstance(modifier_id, str) or not modifier_id:
            raise ExecutionError(f"contextual modifier {index} requires id")
        if modifier_id in seen:
            raise ExecutionError(f"duplicate contextual modifier id: {modifier_id}")
        seen.add(modifier_id)

        amount = row.get("amount")
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ExecutionError(f"contextual modifier {modifier_id} amount must be integer")
        if row.get("source_ref") != expected_source_ref:
            raise ExecutionError(
                f"contextual modifier {modifier_id} source_ref disagrees with execution binding"
            )
        source = _require_mapping(
            sources.get(row.get("source_ref")),
            f"contextual modifier source {row.get('source_ref')}",
        )
        if row.get("authority") != source.get("authority"):
            raise ExecutionError(
                f"contextual modifier {modifier_id} authority disagrees with source"
            )
        if row.get("provenance") != expected_provenance:
            raise ExecutionError(
                f"contextual modifier {modifier_id} provenance disagrees with execution binding"
            )
        rows.append(copy.deepcopy(row))
    return rows


def _effective_target(actor, skill_ref, modifiers, binding):
    effective = _require_mapping(
        binding.get("effective_target"), "attempt-skill effective-target binding"
    )
    if effective.get("from") != "selected-skill-level-plus-context-modifiers":
        raise ExecutionError("runtime does not support this effective-target source")
    if effective.get("modifier_policy") != "sum-resolved-context-modifiers":
        raise ExecutionError("runtime does not support this modifier policy")

    base_target = _resolved_skill(actor, skill_ref, binding)
    modifier_total = sum(row["amount"] for row in modifiers)
    target = base_target + modifier_total
    minimum = effective.get("minimum")
    if not isinstance(minimum, int):
        raise ExecutionError("attempt-skill effective-target minimum is malformed")
    if target < minimum:
        raise ExecutionError(
            f"effective target {target} is below minimum rollable target {minimum}"
        )
    return {
        "base_target": base_target,
        "modifier_total": modifier_total,
        "effective_target": target,
    }


def _require_actor_available(resolved, actor, action_ref):
    state = _require_mapping(actor.get("state"), f"actor {actor.get('id')} state")
    rules = _require_mapping(resolved.get("rules"), "resolved rules")
    action = rules["actions"][action_ref]
    condition_refs = action.get("condition_refs") or []
    if condition_refs != ["actor-conscious"]:
        raise ExecutionError(
            "bounded runtime only supports the accepted actor-conscious attempt-skill condition"
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
        raise ExecutionError(f"action {action_ref} is unavailable: actor is unconscious")


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


def _generated_terms(seed, contract, binding):
    generated = _require_mapping(
        (binding.get("random_evidence") or {}).get("generated"),
        "generated random-evidence binding",
    )
    algorithm = generated.get("algorithm")
    if algorithm != RNG_ALGORITHM:
        raise ExecutionError(f"unsupported deterministic RNG algorithm: {algorithm}")
    if seed is None or isinstance(seed, bool):
        raise ExecutionError("generated dice evidence requires a non-boolean seed")
    seed_text = str(seed)

    terms = []
    counter = 0
    sides = contract["sides"]
    limit = 256 - (256 % sides)
    while len(terms) < contract["count"]:
        digest = hashlib.sha256(
            f"dirps:{algorithm}:{seed_text}:{counter}".encode("utf-8")
        ).digest()
        counter += 1
        for value in digest:
            if value >= limit:
                continue
            terms.append((value % sides) + 1)
            if len(terms) == contract["count"]:
                break
    return terms, {
        "kind": "generated-seeded-dice-terms",
        "algorithm": algorithm,
        "seed": seed_text,
    }


def _random_terms(*, dice_terms, random_seed, contract, binding):
    if dice_terms is not None and random_seed is not None:
        raise ExecutionError("provide either supplied dice terms or random_seed, not both")
    if dice_terms is None and random_seed is None:
        raise ExecutionError("dice evidence requires supplied terms or random_seed")
    if random_seed is not None:
        terms, generator = _generated_terms(random_seed, contract, binding)
        return terms, generator
    terms = _validate_terms(dice_terms, contract)
    return terms, {"kind": "supplied-dice-terms"}


def _rule_matches(rule, total, effective_target):
    if "roll_max" in rule and not total <= rule["roll_max"]:
        return False
    if "roll" in rule and total != rule["roll"]:
        return False
    if (
        "minimum_effective_target" in rule
        and effective_target < rule["minimum_effective_target"]
    ):
        return False
    if (
        "maximum_effective_target" in rule
        and effective_target > rule["maximum_effective_target"]
    ):
        return False
    if (
        "roll_minus_effective_target_minimum" in rule
        and total - effective_target < rule["roll_minus_effective_target_minimum"]
    ):
        return False
    return True


def _critical_classification(total, effective_target, binding):
    contract = _require_mapping(
        binding.get("critical_resolution"), "critical-resolution binding"
    )

    critical_success = contract.get("critical_success")
    critical_failure = contract.get("critical_failure")
    ordinary_failure = contract.get("ordinary_failure")
    if not isinstance(critical_success, list) or not isinstance(critical_failure, list):
        raise ExecutionError("critical-resolution rules are malformed")
    if not isinstance(ordinary_failure, list):
        raise ExecutionError("ordinary-failure critical boundary is malformed")

    if any(_rule_matches(rule, total, effective_target) for rule in critical_success):
        return "critical-success", True
    if any(_rule_matches(rule, total, effective_target) for rule in critical_failure):
        return "critical-failure", False
    if any(_rule_matches(rule, total, effective_target) for rule in ordinary_failure):
        return "failure", False

    success = total <= effective_target
    return ("success" if success else "failure"), success


def _sources_for_execution(resolved, action, procedure, binding):
    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    action_source_ref = action.get("source_ref")
    procedure_source_ref = procedure.get("source_ref")
    binding_source_ref = binding.get("binding_source_ref")
    target_provenance = _require_mapping(
        binding.get("target_provenance"), "attempt-skill target provenance"
    )
    target_source_ref = target_provenance.get("source_ref")

    action_source = _require_mapping(
        sources.get(action_source_ref), f"action source {action_source_ref}"
    )
    procedure_source = _require_mapping(
        sources.get(procedure_source_ref), f"procedure source {procedure_source_ref}"
    )
    binding_source = _require_mapping(
        sources.get(binding_source_ref), f"binding source {binding_source_ref}"
    )
    target_source = _require_mapping(
        sources.get(target_source_ref), f"target source {target_source_ref}"
    )
    return {
        "action_ref": action_source_ref,
        "procedure_ref": procedure_source_ref,
        "binding_ref": binding_source_ref,
        "target_ref": target_source_ref,
        "action": action_source,
        "procedure": procedure_source,
        "binding": binding_source,
        "target": target_source,
        "target_provenance": target_provenance,
    }


def describe_attempt_skill(resolved):
    """Describe the immutable accepted G5/v1 capability for G6 consumers."""
    binding, scenario, action, procedure = _legacy_execution_path(resolved)
    dice = _dice_contract(resolved, binding)
    source_info = _sources_for_execution(resolved, action, procedure, binding)

    scene = _require_mapping(resolved.get("scene"), "resolved scene")
    actors = []
    for row in scene.get("instances", []):
        character = row.get("character")
        skills = character.get("skills") if isinstance(character, dict) else None
        actors.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "skills": copy.deepcopy(skills) if isinstance(skills, dict) else {},
                "character_provenance": (
                    character.get("provenance") if isinstance(character, dict) else None
                ),
            }
        )

    return {
        "mechanic": "ordinary-success-roll",
        "semantic_path": {
            "action_ref": binding["action_ref"],
            "procedure_ref": binding["procedure_ref"],
        },
        "scenario": {
            "id": resolved.get("scenario_id"),
            "name": scenario.get("name"),
        },
        "inputs": {
            "actor": binding["actor_input"],
            "target": binding["target_input"],
            "random_evidence": "dice_terms",
        },
        "target": {
            "kind": binding["target_source"]["kind"],
            "supported_domain": copy.deepcopy(
                binding["effective_target"]["supported_domain"]
            ),
            "modifier_policy": binding["effective_target"]["modifier_policy"],
            "outside_domain": binding["effective_target"]["outside_domain"],
        },
        "dice": {
            "proto_ref": binding["dice_resolution_ref"],
            "randomizer_id": dice["id"],
            "kind": dice["kind"],
            "count": dice["count"],
            "sides": dice["sides"],
            "combine": dice["combine"],
            "comparator": copy.deepcopy(dice["comparator"]),
        },
        "result_format": binding["result_format"],
        "result_scope": binding["result_scope"],
        "state_mutation": binding["state_mutation"],
        "actors": actors,
        "trace": {
            "action": {
                "source_ref": source_info["action_ref"],
                "authority": action.get("authority"),
            },
            "procedure": {
                "source_ref": source_info["procedure_ref"],
                "authority": procedure.get("authority"),
            },
            "execution_binding": {
                "source_ref": source_info["binding_ref"],
                "authority": source_info["binding"].get("authority"),
            },
            "effective_target": {
                "source_ref": source_info["target_ref"],
                "authority": source_info["target"].get("authority"),
                "character_provenance": source_info["target_provenance"].get(
                    "character_provenance"
                ),
                "canonical_path": source_info["target_provenance"].get(
                    "canonical_path"
                ),
            },
            "sources": {
                source_info["action_ref"]: copy.deepcopy(source_info["action"]),
                source_info["procedure_ref"]: copy.deepcopy(source_info["procedure"]),
                source_info["binding_ref"]: copy.deepcopy(source_info["binding"]),
                source_info["target_ref"]: copy.deepcopy(source_info["target"]),
            },
        },
    }


def describe_contextual_skill(resolved):
    """Describe the Phase A/v2 contextual capability without executing it."""
    binding, scenario, action, procedure = _execution_path(resolved)
    dice = _dice_contract(resolved, binding)
    source_info = _sources_for_execution(resolved, action, procedure, binding)

    scene = _require_mapping(resolved.get("scene"), "resolved scene")
    actors = []
    for row in scene.get("instances", []):
        character = row.get("character")
        skills = character.get("skills") if isinstance(character, dict) else None
        actors.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "skills": copy.deepcopy(skills) if isinstance(skills, dict) else {},
                "character_provenance": (
                    character.get("provenance") if isinstance(character, dict) else None
                ),
            }
        )

    effective = binding["effective_target"]
    return {
        "mechanic": "ordinary-success-roll",
        "semantic_path": {
            "action_ref": binding["action_ref"],
            "procedure_ref": binding["procedure_ref"],
        },
        "scenario": {
            "id": resolved.get("scenario_id"),
            "name": scenario.get("name"),
        },
        "inputs": {
            "actor": binding["actor_input"],
            "target": binding["target_input"],
            "context": binding["context_input"],
            "random_evidence": ["dice_terms", "random_seed"],
        },
        "target": {
            "kind": binding["target_source"]["kind"],
            "modifier_policy": effective["modifier_policy"],
            "supported_domain": {
                "minimum": effective["minimum"],
                "maximum": None,
            },
            "below_minimum": effective["below_minimum"],
            "rule_source_ref": effective["rule_source_ref"],
            "rule_locator": effective["rule_locator"],
        },
        "contextual_checks": copy.deepcopy(scenario.get("contextual_checks", {})),
        "dice": {
            "proto_ref": binding["dice_resolution_ref"],
            "randomizer_id": dice["id"],
            "kind": dice["kind"],
            "count": dice["count"],
            "sides": dice["sides"],
            "combine": dice["combine"],
            "comparator": copy.deepcopy(dice["comparator"]),
            "random_evidence": copy.deepcopy(binding["random_evidence"]),
        },
        "critical_resolution": copy.deepcopy(binding["critical_resolution"]),
        "result_format": binding["result_format"],
        "result_scope": binding["result_scope"],
        "state_mutation": binding["state_mutation"],
        "actors": actors,
        "trace": {
            "action": {
                "source_ref": source_info["action_ref"],
                "authority": action.get("authority"),
            },
            "procedure": {
                "source_ref": source_info["procedure_ref"],
                "authority": procedure.get("authority"),
            },
            "execution_binding": {
                "source_ref": source_info["binding_ref"],
                "authority": source_info["binding"].get("authority"),
            },
            "effective_target": {
                "source_ref": source_info["target_ref"],
                "authority": source_info["target"].get("authority"),
                "character_provenance": source_info["target_provenance"].get(
                    "character_provenance"
                ),
                "canonical_path": source_info["target_provenance"].get("canonical_path"),
                "context_source_ref": source_info["target_provenance"].get(
                    "context_source_ref"
                ),
                "context_path": source_info["target_provenance"].get("context_path"),
            },
            "sources": {
                source_info["action_ref"]: copy.deepcopy(source_info["action"]),
                source_info["procedure_ref"]: copy.deepcopy(source_info["procedure"]),
                source_info["binding_ref"]: copy.deepcopy(source_info["binding"]),
                source_info["target_ref"]: copy.deepcopy(source_info["target"]),
            },
        },
    }


def _execute_attempt_skill(
    resolved,
    *,
    actor_ref,
    skill_ref,
    context_ref,
    modifiers,
    dice_terms,
    random_seed,
):
    binding, _, action, procedure = _execution_path(resolved)
    action_ref = binding["action_ref"]
    procedure_ref = binding["procedure_ref"]
    actor = _actor(resolved, actor_ref)
    _require_actor_available(resolved, actor, action_ref)

    validated_modifiers = _validated_modifiers(resolved, modifiers, binding)
    target = _effective_target(actor, skill_ref, validated_modifiers, binding)
    dice = _dice_contract(resolved, binding)
    terms, evidence_kind = _random_terms(
        dice_terms=dice_terms,
        random_seed=random_seed,
        contract=dice,
        binding=binding,
    )

    total = sum(terms)
    classification, success = _critical_classification(
        total, target["effective_target"], binding
    )
    margin = target["effective_target"] - total

    source_info = _sources_for_execution(resolved, action, procedure, binding)
    character = _require_mapping(
        actor.get("character"), f"actor {actor_ref} resolved character"
    )
    character_provenance = character.get("provenance")
    if character_provenance != source_info["target_provenance"].get(
        "character_provenance"
    ):
        raise ExecutionError(
            "resolved character provenance disagrees with the execution binding"
        )

    effective_contract = binding["effective_target"]
    critical_contract = binding["critical_resolution"]
    input_row = {
        "actor_ref": actor_ref,
        "skill_ref": skill_ref,
    }
    if context_ref is not None:
        input_row["context_ref"] = context_ref

    random_evidence = {
        **evidence_kind,
        "proto_ref": binding["dice_resolution_ref"],
        "randomizer_id": dice["id"],
        "dice_kind": dice["kind"],
        "sides": dice["sides"],
        "terms": terms,
        "total": total,
    }

    return {
        "format": binding["result_format"],
        "mechanic": "ordinary-success-roll",
        "result_scope": binding["result_scope"],
        "input": input_row,
        "semantic_path": {
            "action_ref": action_ref,
            "procedure_ref": procedure_ref,
        },
        "target": {
            "kind": binding["target_source"]["kind"],
            "skill_ref": skill_ref,
            "base_target": target["base_target"],
            "modifiers": copy.deepcopy(validated_modifiers),
            "modifier_total": target["modifier_total"],
            "effective_target": target["effective_target"],
            "modifier_policy": effective_contract["modifier_policy"],
            "supported_domain": {
                "minimum": effective_contract["minimum"],
                "maximum": None,
            },
        },
        "random_evidence": random_evidence,
        "outcome": {
            "classification": classification,
            "success": success,
            "margin": margin,
        },
        "trace": {
            "action": {
                "ref": action_ref,
                "source_ref": source_info["action_ref"],
                "authority": action.get("authority"),
            },
            "procedure": {
                "ref": procedure_ref,
                "source_ref": source_info["procedure_ref"],
                "authority": procedure.get("authority"),
            },
            "execution_binding": {
                "ref": f"proto_sidecar.phase_a_execution_bindings.{BINDING_ID}",
                "source_ref": source_info["binding_ref"],
                "authority": source_info["binding"].get("authority"),
            },
            "effective_target": {
                "actor_ref": actor_ref,
                "skill_ref": skill_ref,
                "base_value": target["base_target"],
                "modifier_total": target["modifier_total"],
                "value": target["effective_target"],
                "target_source_ref": source_info["target_ref"],
                "target_authority": source_info["target"].get("authority"),
                "character_provenance": character_provenance,
                "canonical_path": (
                    f"{source_info['target_provenance'].get('canonical_path')}.{skill_ref}"
                ),
                "context_ref": context_ref,
                "modifier_rule_source_ref": effective_contract["rule_source_ref"],
                "modifier_rule_authority": (
                    resolved["sources"][effective_contract["rule_source_ref"]].get(
                        "authority"
                    )
                ),
                "modifier_rule_locator": effective_contract["rule_locator"],
                "modifiers": copy.deepcopy(validated_modifiers),
            },
            "critical_resolution": {
                "classification": classification,
                "source_ref": critical_contract["rule_source_ref"],
                "authority": (
                    resolved["sources"][critical_contract["rule_source_ref"]].get(
                        "authority"
                    )
                ),
                "rule_locator": critical_contract["rule_locator"],
            },
            "random_evidence": {
                "kind": random_evidence["kind"],
                "algorithm": random_evidence.get("algorithm"),
                "seed": random_evidence.get("seed"),
                "terms": copy.deepcopy(terms),
            },
            "sources": {
                source_info["action_ref"]: copy.deepcopy(source_info["action"]),
                source_info["procedure_ref"]: copy.deepcopy(source_info["procedure"]),
                source_info["binding_ref"]: copy.deepcopy(source_info["binding"]),
                source_info["target_ref"]: copy.deepcopy(source_info["target"]),
            },
        },
        "state_delta": [],
    }


def execute_attempt_skill(resolved, *, actor_ref, skill_ref, dice_terms):
    """Execute the immutable accepted G5/v1 unmodified success-roll contract."""
    binding, _, action, procedure = _legacy_execution_path(resolved)
    action_ref = binding["action_ref"]
    procedure_ref = binding["procedure_ref"]
    actor = _actor(resolved, actor_ref)
    _require_actor_available(resolved, actor, action_ref)
    effective_target = _legacy_effective_target(actor, skill_ref, binding)
    dice = _dice_contract(resolved, binding)
    terms = _validate_terms(dice_terms, dice)

    total = sum(terms)
    success = total <= effective_target
    margin = effective_target - total

    source_info = _sources_for_execution(resolved, action, procedure, binding)
    character = _require_mapping(
        actor.get("character"), f"actor {actor_ref} resolved character"
    )
    character_provenance = character.get("provenance")
    if character_provenance != source_info["target_provenance"].get(
        "character_provenance"
    ):
        raise ExecutionError(
            "resolved character provenance disagrees with the G5 target provenance binding"
        )

    return {
        "format": binding["result_format"],
        "mechanic": "ordinary-success-roll",
        "result_scope": binding["result_scope"],
        "input": {
            "actor_ref": actor_ref,
            "skill_ref": skill_ref,
        },
        "semantic_path": {
            "action_ref": action_ref,
            "procedure_ref": procedure_ref,
        },
        "target": {
            "kind": binding["target_source"]["kind"],
            "skill_ref": skill_ref,
            "effective_target": effective_target,
            "modifier_policy": binding["effective_target"]["modifier_policy"],
            "supported_domain": copy.deepcopy(
                binding["effective_target"]["supported_domain"]
            ),
        },
        "random_evidence": {
            "kind": "supplied-dice-terms",
            "proto_ref": binding["dice_resolution_ref"],
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
                "ref": action_ref,
                "source_ref": source_info["action_ref"],
                "authority": action.get("authority"),
            },
            "procedure": {
                "ref": procedure_ref,
                "source_ref": source_info["procedure_ref"],
                "authority": procedure.get("authority"),
            },
            "execution_binding": {
                "ref": f"proto_sidecar.g5_execution_bindings.{BINDING_ID}",
                "source_ref": source_info["binding_ref"],
                "authority": source_info["binding"].get("authority"),
            },
            "effective_target": {
                "actor_ref": actor_ref,
                "skill_ref": skill_ref,
                "value": effective_target,
                "source_ref": source_info["target_ref"],
                "authority": source_info["target"].get("authority"),
                "character_provenance": character_provenance,
                "canonical_path": (
                    f"{source_info['target_provenance'].get('canonical_path')}.{skill_ref}"
                ),
            },
            "sources": {
                source_info["action_ref"]: copy.deepcopy(source_info["action"]),
                source_info["procedure_ref"]: copy.deepcopy(source_info["procedure"]),
                source_info["binding_ref"]: copy.deepcopy(source_info["binding"]),
                source_info["target_ref"]: copy.deepcopy(source_info["target"]),
            },
        },
        "state_delta": [],
    }

def execute_contextual_skill(
    resolved,
    *,
    actor_ref,
    context_ref,
    dice_terms=None,
    random_seed=None,
):
    """Execute one source-owned contextual skill check from resolved semantics."""
    binding = _execution_binding(resolved)
    _, skill_ref, modifiers = _contextual_check(resolved, context_ref, binding)
    return _execute_attempt_skill(
        resolved,
        actor_ref=actor_ref,
        skill_ref=skill_ref,
        context_ref=context_ref,
        modifiers=modifiers,
        dice_terms=dice_terms,
        random_seed=random_seed,
    )


def replay_attempt_skill(resolved, record):
    """Re-evaluate one accepted G5/v1 record and reject other record versions."""
    binding = _legacy_g5_binding(resolved)
    if not isinstance(record, dict):
        raise ExecutionError("record is not a DIRPS execution result")
    record_format = record.get("format")
    if record_format == "dirps-execution-result.v2":
        raise ExecutionError(
            "dirps-execution-result.v2 is a Phase A record, not a legacy G5/v1 record"
        )
    if record_format != binding["result_format"]:
        raise ExecutionError(
            f"unsupported DIRPS execution record format for G5 replay: {record_format!r}"
        )
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


def replay_contextual_skill(resolved, record):
    """Re-evaluate one Phase A/v2 contextual record from its recorded evidence."""
    binding = _execution_binding(resolved)
    if not isinstance(record, dict):
        raise ExecutionError("record is not a DIRPS execution result")
    record_format = record.get("format")
    if record_format == "dirps-execution-result.v1":
        raise ExecutionError(
            "dirps-execution-result.v1 is a legacy G5 record, not a Phase A/v2 record"
        )
    if record_format != binding["result_format"]:
        raise ExecutionError(
            f"unsupported DIRPS execution record format for Phase A replay: {record_format!r}"
        )
    inputs = _require_mapping(record.get("input"), "record input")
    evidence = _require_mapping(record.get("random_evidence"), "record random_evidence")
    kwargs = {
        "resolved": resolved,
        "actor_ref": inputs.get("actor_ref"),
        "context_ref": inputs.get("context_ref"),
    }
    if evidence.get("kind") == "generated-seeded-dice-terms":
        kwargs["random_seed"] = evidence.get("seed")
    elif evidence.get("kind") == "supplied-dice-terms":
        kwargs["dice_terms"] = evidence.get("terms")
    else:
        raise ExecutionError("record random evidence kind is unsupported")

    recomputed = execute_contextual_skill(**kwargs)
    if recomputed != record:
        raise ExecutionError("execution record divergence detected")
    return recomputed



def _phase_b_binding(resolved, encounter_ref):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    bindings = _require_mapping(
        sidecar.get("phase_b_encounter_bindings"),
        "resolved phase_b_encounter_bindings",
    )
    binding = _require_mapping(
        bindings.get(encounter_ref), f"Phase B encounter binding {encounter_ref}"
    )
    if binding.get("encounter_ref") != encounter_ref:
        raise ExecutionError("Phase B encounter binding identity is malformed")
    if binding.get("skill_result_format") != "dirps-execution-result.v2":
        raise ExecutionError("Phase B requires Phase A/v2 skill evidence")
    if binding.get("result_format") != PHASE_B_RESULT_FORMAT:
        raise ExecutionError("Phase B encounter result format is unsupported")
    if binding.get("binding_source_ref") != "dirps-proto":
        raise ExecutionError("Phase B encounter binding source is malformed")
    if binding.get("consequence_source_ref") != "scenario-01-source":
        raise ExecutionError("Phase B consequence source is malformed")
    if not isinstance(binding.get("required_state"), list):
        raise ExecutionError("Phase B required_state must be a list")
    consequences = _require_mapping(
        binding.get("consequences"), "Phase B consequence bindings"
    )
    if set(consequences) != {"success", "failure"}:
        raise ExecutionError("Phase B must bind success and failure consequences")
    for branch in ("success", "failure"):
        effect_refs = (consequences.get(branch) or {}).get("effect_refs")
        if not isinstance(effect_refs, list) or not effect_refs:
            raise ExecutionError(
                f"Phase B {branch} consequence must declare ordered effect_refs"
            )
    return binding


def _encounter(resolved, encounter_ref):
    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    for row in scenario.get("encounters", []):
        if isinstance(row, dict) and row.get("id") == encounter_ref:
            return row
    raise ExecutionError(f"encounter is not available in resolved scenario: {encounter_ref}")


def _encounter_action(encounter, action_id):
    for row in encounter.get("actions", []):
        if isinstance(row, dict) and row.get("id") == action_id:
            return row
    raise ExecutionError(
        f"action is not available in encounter {encounter.get('id')}: {action_id}"
    )


def _state_binding_index(state):
    bindings = state.get("bindings")
    if not isinstance(bindings, list):
        raise ExecutionError("runtime state bindings must be a list")
    index = {}
    for row in bindings:
        binding = _require_mapping(row, "runtime state binding")
        ref = binding.get("ref")
        subject = binding.get("subject")
        if not isinstance(ref, str) or not ref:
            raise ExecutionError("runtime state binding ref is required")
        if subject != {"relative": "scenario"}:
            raise ExecutionError(
                f"Phase B runtime state binding {ref} must target the scenario subject"
            )
        if ref in index:
            raise ExecutionError(f"duplicate runtime state binding: {ref}")
        index[ref] = binding
    return index


def _validate_state_value(definition, value, ref):
    value_type = definition.get("type")
    if value_type == "enum":
        if value not in (definition.get("enum_values") or []):
            raise ExecutionError(
                f"runtime state value {ref}={value!r} is outside declared enum_values"
            )
    elif value_type == "boolean":
        if not isinstance(value, bool):
            raise ExecutionError(f"runtime state value {ref} must be boolean")
    elif value_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ExecutionError(f"runtime state value {ref} must be integer")
    elif value_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ExecutionError(f"runtime state value {ref} must be numeric")
    elif value_type == "string":
        if not isinstance(value, str):
            raise ExecutionError(f"runtime state value {ref} must be string")
    else:
        raise ExecutionError(f"unsupported runtime state value type for {ref}: {value_type}")


def validate_runtime_state(resolved, state):
    """Validate the neutral DODGE runtime-state subset used by Phase B."""
    if not isinstance(state, dict):
        raise ExecutionError("runtime state must be an object")
    if state.get("scenario_ref") != resolved.get("scenario_id"):
        raise ExecutionError("runtime state scenario_ref disagrees with resolved scenario")
    if not isinstance(state.get("revision"), str):
        raise ExecutionError("runtime state revision must be a string")
    try:
        int(state["revision"])
    except ValueError as exc:
        raise ExecutionError("runtime state revision must be an integer string") from exc
    events = state.get("events")
    if not isinstance(events, list):
        raise ExecutionError("runtime state events must be a list")

    definitions = _require_mapping(
        (resolved.get("rules") or {}).get("values"), "resolved value definitions"
    )
    index = _state_binding_index(state)
    for ref, row in index.items():
        definition = _require_mapping(
            definitions.get(ref), f"runtime state value definition {ref}"
        )
        if definition.get("owner_scope") != "scenario":
            raise ExecutionError(
                f"Phase B runtime state value {ref} must be scenario-owned"
            )
        if row.get("authority") != definition.get("authority"):
            raise ExecutionError(
                f"runtime state binding {ref} authority disagrees with value definition"
            )
        _validate_state_value(definition, row.get("value"), ref)
    return index


def create_runtime_state(resolved, *, encounter_ref="roadside-tracks"):
    """Create a fresh neutral runtime-state snapshot from resolved DODGE."""
    binding = _phase_b_binding(resolved, encounter_ref)
    states = _require_mapping(resolved.get("runtime_states"), "resolved runtime_states")
    source = _require_mapping(
        states.get(binding.get("runtime_state_ref")),
        f"runtime state {binding.get('runtime_state_ref')}",
    )
    state = copy.deepcopy(source)
    validate_runtime_state(resolved, state)
    return state


def _state_value(state_index, ref):
    row = state_index.get(ref)
    if not isinstance(row, dict):
        raise ExecutionError(f"required runtime state binding is missing: {ref}")
    return row.get("value")


def _phase_b_ready(resolved, state, binding):
    index = validate_runtime_state(resolved, state)
    for requirement in binding.get("required_state", []):
        row = _require_mapping(requirement, "Phase B state requirement")
        if _state_value(index, row.get("ref")) != row.get("value"):
            return False
    return True


def describe_investigation(resolved, state, *, encounter_ref):
    """Describe available Phase B encounter actions from neutral runtime state."""
    binding = _phase_b_binding(resolved, encounter_ref)
    encounter = _encounter(resolved, encounter_ref)
    action = _encounter_action(encounter, binding.get("action_id"))
    ready = _phase_b_ready(resolved, state, binding)

    state_contract = _require_mapping(
        encounter.get("state_contract"), f"encounter {encounter_ref} state_contract"
    )
    refs = _require_mapping(
        state_contract.get("refs"), f"encounter {encounter_ref} state refs"
    )
    index = validate_runtime_state(resolved, state)
    current_state = {
        role: _state_value(index, ref)
        for role, ref in refs.items()
    }

    return {
        "encounter": {
            "id": encounter_ref,
            "type": encounter.get("type"),
            "purpose": encounter.get("purpose"),
        },
        "runtime_state_revision": state.get("revision"),
        "state": current_state,
        "available_actions": [
            {
                "id": action.get("id"),
                "label": action.get("label"),
                "actor_ref": action.get("actor_ref"),
                "action_ref": action.get("action_ref"),
                "context_ref": action.get("context_ref"),
                "source_ref": action.get("source_ref"),
                "authority": action.get("authority"),
                "provenance": action.get("provenance"),
            }
        ]
        if ready
        else [],
        "skill_capability": describe_contextual_skill(resolved),
        "result_format": binding.get("result_format"),
    }


def _apply_set_effect(resolved, state, state_index, effect_ref):
    effects = _require_mapping(
        (resolved.get("rules") or {}).get("effects"), "resolved effects"
    )
    effect = _require_mapping(effects.get(effect_ref), f"resolved effect {effect_ref}")
    if effect.get("op") != "set":
        raise ExecutionError(
            f"Phase B only supports normalized set effects, got {effect.get('op')!r}"
        )
    if effect.get("subject") != {"relative": "scenario"}:
        raise ExecutionError(f"Phase B effect {effect_ref} must target scenario state")
    if effect.get("source_ref") != "scenario-01-source":
        raise ExecutionError(f"Phase B effect {effect_ref} has wrong source authority")
    if effect.get("authority") != "provisional":
        raise ExecutionError(f"Phase B effect {effect_ref} must remain provisional")

    target_ref = effect.get("target_ref")
    binding = state_index.get(target_ref)
    if not isinstance(binding, dict):
        raise ExecutionError(
            f"Phase B effect {effect_ref} target binding is missing: {target_ref}"
        )
    definitions = _require_mapping(
        (resolved.get("rules") or {}).get("values"), "resolved value definitions"
    )
    definition = _require_mapping(
        definitions.get(target_ref), f"value definition {target_ref}"
    )
    new_value = effect.get("value")
    _validate_state_value(definition, new_value, target_ref)
    before = binding.get("value")
    binding["value"] = copy.deepcopy(new_value)
    return {
        "effect_ref": effect_ref,
        "op": "set",
        "ref": target_ref,
        "subject": {"relative": "scenario"},
        "before": copy.deepcopy(before),
        "after": copy.deepcopy(new_value),
        "source_ref": effect.get("source_ref"),
        "authority": effect.get("authority"),
    }


def execute_investigation(
    resolved,
    state,
    *,
    encounter_ref,
    action_id,
    actor_ref,
    dice_terms=None,
    random_seed=None,
):
    """Resolve one Phase B investigation action and apply neutral DODGE effects."""
    binding = _phase_b_binding(resolved, encounter_ref)
    encounter = _encounter(resolved, encounter_ref)
    action = _encounter_action(encounter, action_id)
    if action_id != binding.get("action_id"):
        raise ExecutionError(
            f"action is not bound for Phase B encounter {encounter_ref}: {action_id}"
        )
    if actor_ref != binding.get("actor_ref") or actor_ref != action.get("actor_ref"):
        raise ExecutionError(
            f"actor {actor_ref} is not eligible for encounter action {action_id}"
        )
    if action.get("action_ref") != binding.get("action_ref"):
        raise ExecutionError("encounter action disagrees with Phase B action_ref")
    if action.get("context_ref") != binding.get("context_ref"):
        raise ExecutionError("encounter action disagrees with Phase B context_ref")

    before = copy.deepcopy(state)
    if not _phase_b_ready(resolved, before, binding):
        raise ExecutionError(
            f"encounter action {action_id} is unavailable in current runtime state"
        )

    skill_resolution = execute_contextual_skill(
        resolved,
        actor_ref=actor_ref,
        context_ref=binding["context_ref"],
        dice_terms=dice_terms,
        random_seed=random_seed,
    )
    if skill_resolution.get("format") != binding.get("skill_result_format"):
        raise ExecutionError("Phase B received an unexpected nested skill-result format")

    branch = "success" if skill_resolution["outcome"]["success"] else "failure"
    consequence = _require_mapping(
        (action.get("consequences") or {}).get(branch),
        f"encounter consequence {branch}",
    )
    effect_refs = binding["consequences"][branch]["effect_refs"]

    after = copy.deepcopy(before)
    state_index = validate_runtime_state(resolved, after)
    delta = [
        _apply_set_effect(resolved, after, state_index, effect_ref)
        for effect_ref in effect_refs
    ]
    after["revision"] = str(int(after["revision"]) + 1)
    validate_runtime_state(resolved, after)

    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    bridge_source = _require_mapping(
        sources.get(binding["binding_source_ref"]), "Phase B binding source"
    )
    consequence_source = _require_mapping(
        sources.get(binding["consequence_source_ref"]),
        "Phase B consequence source",
    )

    return {
        "format": binding["result_format"],
        "encounter_ref": encounter_ref,
        "action_id": action_id,
        "actor_ref": actor_ref,
        "outcome_branch": branch,
        "skill_resolution": skill_resolution,
        "consequence": copy.deepcopy(consequence),
        "state_before": before,
        "state_after": after,
        "state_delta": delta,
        "trace": {
            "encounter_action": {
                "encounter_ref": encounter_ref,
                "action_id": action_id,
                "source_ref": action.get("source_ref"),
                "authority": action.get("authority"),
                "provenance": action.get("provenance"),
            },
            "execution_binding": {
                "ref": f"proto_sidecar.phase_b_encounter_bindings.{encounter_ref}",
                "source_ref": binding["binding_source_ref"],
                "authority": bridge_source.get("authority"),
            },
            "consequence_source": {
                "source_ref": binding["consequence_source_ref"],
                "authority": consequence_source.get("authority"),
                "effect_refs": copy.deepcopy(effect_refs),
            },
            "nested_skill_result_format": binding["skill_result_format"],
        },
    }


def replay_investigation(resolved, record):
    """Deterministically re-evaluate one Phase B stateful encounter record."""
    if not isinstance(record, dict):
        raise ExecutionError("encounter record must be an object")
    if record.get("format") != PHASE_B_RESULT_FORMAT:
        raise ExecutionError(
            f"unsupported Phase B encounter record format: {record.get('format')!r}"
        )
    skill = _require_mapping(
        record.get("skill_resolution"), "encounter record skill_resolution"
    )
    evidence = _require_mapping(
        skill.get("random_evidence"), "encounter record random_evidence"
    )
    kwargs = {
        "resolved": resolved,
        "state": copy.deepcopy(record.get("state_before")),
        "encounter_ref": record.get("encounter_ref"),
        "action_id": record.get("action_id"),
        "actor_ref": record.get("actor_ref"),
    }
    if evidence.get("kind") == "generated-seeded-dice-terms":
        kwargs["random_seed"] = evidence.get("seed")
    elif evidence.get("kind") == "supplied-dice-terms":
        kwargs["dice_terms"] = evidence.get("terms")
    else:
        raise ExecutionError("encounter record random evidence kind is unsupported")

    recomputed = execute_investigation(**kwargs)
    if recomputed != record:
        raise ExecutionError("encounter record divergence detected")
    return recomputed


def _phase_c_binding(resolved, encounter_ref):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    bindings = _require_mapping(
        sidecar.get("phase_c_social_bindings"),
        "resolved phase_c_social_bindings",
    )
    binding = _require_mapping(
        bindings.get(encounter_ref), f"Phase C social binding {encounter_ref}"
    )
    if binding.get("encounter_ref") != encounter_ref:
        raise ExecutionError("Phase C social binding identity is malformed")
    if binding.get("procedure_ref") != "reaction-roll":
        raise ExecutionError("Phase C social binding must use reaction-roll")
    if binding.get("reaction_result_format") != PHASE_C_REACTION_FORMAT:
        raise ExecutionError("Phase C reaction-result format is unsupported")
    if binding.get("result_format") != PHASE_C_RESULT_FORMAT:
        raise ExecutionError("Phase C social encounter result format is unsupported")
    if binding.get("binding_source_ref") != "dirps-proto":
        raise ExecutionError("Phase C social binding source is malformed")
    if binding.get("consequence_source_ref") != "scenario-01-source":
        raise ExecutionError("Phase C social consequence source is malformed")
    if not isinstance(binding.get("required_state"), list):
        raise ExecutionError("Phase C required_state must be a list")

    modifier_source = _require_mapping(
        binding.get("modifier_source"), "Phase C reaction-modifier source binding"
    )
    if modifier_source != {
        "kind": "encounter-action-reaction-modifiers",
        "path": "scenario.encounters[].actions[].reaction_modifiers",
    }:
        raise ExecutionError(
            "Phase C reaction-modifier source binding is unsupported or malformed"
        )

    random_evidence = _require_mapping(
        binding.get("random_evidence"), "Phase C random-evidence binding"
    )
    randomizer = _require_mapping(
        random_evidence.get("randomizer"), "Phase C randomizer"
    )
    if randomizer != {
        "kind": "dice-pool",
        "count": 3,
        "sides": 6,
        "combine": "sum",
    }:
        raise ExecutionError("Phase C reaction roll requires the declared 3d6 sum randomizer")
    generated = _require_mapping(
        random_evidence.get("generated"), "Phase C generated random-evidence binding"
    )
    if (
        random_evidence.get("supplied_terms") != {"supported": True}
        or generated.get("supported") is not True
        or generated.get("seed_required") is not True
        or generated.get("algorithm") != RNG_ALGORITHM
    ):
        raise ExecutionError("Phase C random-evidence binding is malformed")

    consequences = _require_mapping(
        binding.get("consequences"), "Phase C consequence bindings"
    )
    expected_categories = {
        "disastrous",
        "very-bad",
        "bad",
        "poor",
        "neutral",
        "good",
        "very-good",
        "excellent",
    }
    if set(consequences) != expected_categories:
        raise ExecutionError("Phase C must bind every declared reaction category")
    for category, row in consequences.items():
        effect_refs = (row or {}).get("effect_refs")
        if not isinstance(effect_refs, list) or not effect_refs:
            raise ExecutionError(
                f"Phase C {category} consequence must declare ordered effect_refs"
            )
    return binding


def _phase_c_lookup_table(resolved, table_ref):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    tables = _require_mapping(
        sidecar.get("phase_c_lookup_tables"),
        "resolved phase_c_lookup_tables",
    )
    table = _require_mapping(tables.get(table_ref), f"Phase C lookup table {table_ref}")
    if table.get("source_ref") != "gurps-lite":
        raise ExecutionError("Phase C reaction table must use gurps-lite authority")
    if table.get("authority") != "authoritative":
        raise ExecutionError("Phase C reaction table must remain authoritative")
    if table.get("rule_locator") != "p. 3, Reaction Table":
        raise ExecutionError("Phase C reaction table source locator is unsupported")
    rows = table.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ExecutionError("Phase C reaction table rows are required")
    return table


def _phase_c_reaction_modifiers(action):
    modifiers = action.get("reaction_modifiers")
    if not isinstance(modifiers, list) or not modifiers:
        raise ExecutionError("Phase C social action requires reaction modifiers")
    rows = []
    seen = set()
    for index, modifier in enumerate(modifiers):
        row = _require_mapping(modifier, f"reaction modifier {index}")
        modifier_id = row.get("id")
        if not isinstance(modifier_id, str) or not modifier_id:
            raise ExecutionError(f"reaction modifier {index} requires id")
        if modifier_id in seen:
            raise ExecutionError(f"duplicate reaction modifier id: {modifier_id}")
        seen.add(modifier_id)
        amount = row.get("amount")
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ExecutionError(f"reaction modifier {modifier_id} amount must be integer")
        if row.get("source_ref") != "scenario-01-source":
            raise ExecutionError(
                f"reaction modifier {modifier_id} must come from scenario-01-source"
            )
        if row.get("authority") != "provisional":
            raise ExecutionError(
                f"reaction modifier {modifier_id} must remain provisional"
            )
        if row.get("provenance") != "prototype_assumption":
            raise ExecutionError(
                f"reaction modifier {modifier_id} provenance is unsupported"
            )
        if row.get("rule_source_ref") != "gurps-lite":
            raise ExecutionError(
                f"reaction modifier {modifier_id} rule authority must be gurps-lite"
            )
        if row.get("rule_locator") != "p. 3, Reaction Modifiers":
            raise ExecutionError(
                f"reaction modifier {modifier_id} source locator is unsupported"
            )
        rows.append(copy.deepcopy(row))
    return rows


def _lookup_reaction_category(table, modified_total):
    matches = []
    for row in table.get("rows", []):
        when = _require_mapping(row.get("when"), "reaction lookup range")
        minimum = when.get("min")
        maximum = when.get("max")
        if minimum is not None and modified_total < minimum:
            continue
        if maximum is not None and modified_total > maximum:
            continue
        matches.append(row)
    if len(matches) != 1:
        raise ExecutionError(
            f"reaction lookup must match exactly one row for {modified_total}, got {len(matches)}"
        )
    return matches[0]


def _phase_c_ready(resolved, state, binding):
    index = validate_runtime_state(resolved, state)
    for requirement in binding.get("required_state", []):
        row = _require_mapping(requirement, "Phase C state requirement")
        if _state_value(index, row.get("ref")) != row.get("value"):
            return False
    return True


def create_social_runtime_state(resolved, *, encounter_ref="frightened-witness"):
    """Create the bounded neutral runtime snapshot used by Phase C."""
    binding = _phase_c_binding(resolved, encounter_ref)
    states = _require_mapping(resolved.get("runtime_states"), "resolved runtime_states")
    source = _require_mapping(
        states.get(binding.get("runtime_state_ref")),
        f"runtime state {binding.get('runtime_state_ref')}",
    )
    state = copy.deepcopy(source)
    validate_runtime_state(resolved, state)
    return state


def describe_social_interaction(resolved, state, *, encounter_ref):
    """Describe the Phase C witness interaction from neutral runtime state."""
    binding = _phase_c_binding(resolved, encounter_ref)
    encounter = _encounter(resolved, encounter_ref)
    action = _encounter_action(encounter, binding.get("action_id"))
    ready = _phase_c_ready(resolved, state, binding)

    state_contract = _require_mapping(
        encounter.get("state_contract"), f"encounter {encounter_ref} state_contract"
    )
    refs = _require_mapping(
        state_contract.get("refs"), f"encounter {encounter_ref} state refs"
    )
    index = validate_runtime_state(resolved, state)
    current_state = {role: _state_value(index, ref) for role, ref in refs.items()}
    table = _phase_c_lookup_table(resolved, binding.get("lookup_table_ref"))

    procedure = _require_mapping(
        (resolved.get("rules") or {}).get("procedures", {}).get(binding["procedure_ref"]),
        f"resolved procedure {binding['procedure_ref']}",
    )

    return {
        "encounter": {
            "id": encounter_ref,
            "type": encounter.get("type"),
            "purpose": encounter.get("purpose"),
        },
        "runtime_state_revision": state.get("revision"),
        "state": current_state,
        "available_actions": [
            {
                "id": action.get("id"),
                "label": action.get("label"),
                "actor_ref": action.get("actor_ref"),
                "procedure_ref": action.get("procedure_ref"),
                "reaction_modifiers": copy.deepcopy(action.get("reaction_modifiers", [])),
                "source_ref": action.get("source_ref"),
                "authority": action.get("authority"),
                "provenance": action.get("provenance"),
            }
        ]
        if ready
        else [],
        "reaction_capability": {
            "procedure_ref": binding["procedure_ref"],
            "procedure_source_ref": procedure.get("source_ref"),
            "procedure_authority": procedure.get("authority"),
            "random_evidence": copy.deepcopy(binding["random_evidence"]),
            "lookup_table_ref": binding["lookup_table_ref"],
            "lookup_table": copy.deepcopy(table),
            "reaction_result_format": binding["reaction_result_format"],
        },
        "result_format": binding["result_format"],
    }


def _execute_reaction_roll(
    resolved,
    *,
    encounter_ref,
    action,
    actor_ref,
    binding,
    dice_terms=None,
    random_seed=None,
):
    modifiers = _phase_c_reaction_modifiers(action)
    randomizer = binding["random_evidence"]["randomizer"]
    contract = {
        "count": randomizer["count"],
        "sides": randomizer["sides"],
    }
    terms, evidence_kind = _random_terms(
        dice_terms=dice_terms,
        random_seed=random_seed,
        contract=contract,
        binding=binding,
    )
    raw_total = sum(terms)
    modifier_total = sum(row["amount"] for row in modifiers)
    modified_total = raw_total + modifier_total
    table = _phase_c_lookup_table(resolved, binding["lookup_table_ref"])
    matched = _lookup_reaction_category(table, modified_total)
    category = matched.get("value")

    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    rule_source = _require_mapping(sources.get("gurps-lite"), "gurps-lite source")
    scenario_source = _require_mapping(
        sources.get("scenario-01-source"), "scenario-01 source"
    )
    bridge_source = _require_mapping(
        sources.get(binding["binding_source_ref"]), "Phase C binding source"
    )

    return {
        "format": binding["reaction_result_format"],
        "mechanic": "reaction-roll",
        "input": {
            "encounter_ref": encounter_ref,
            "action_id": action.get("id"),
            "actor_ref": actor_ref,
        },
        "procedure_ref": binding["procedure_ref"],
        "modifiers": modifiers,
        "modifier_total": modifier_total,
        "random_evidence": {
            **evidence_kind,
            "dice_kind": randomizer["kind"],
            "sides": randomizer["sides"],
            "terms": terms,
            "raw_total": raw_total,
        },
        "modified_total": modified_total,
        "reaction": category,
        "lookup": {
            "table_ref": binding["lookup_table_ref"],
            "matched_row": copy.deepcopy(matched),
        },
        "trace": {
            "procedure": {
                "ref": binding["procedure_ref"],
                "source_ref": "gurps-lite",
                "authority": rule_source.get("authority"),
                "rule_locator": "p. 3, Reaction Rolls / Reaction Table",
            },
            "reaction_modifiers": {
                "rule_source_ref": "gurps-lite",
                "rule_authority": rule_source.get("authority"),
                "rule_locator": "p. 3, Reaction Modifiers",
                "scenario_source_ref": "scenario-01-source",
                "scenario_authority": scenario_source.get("authority"),
            },
            "lookup_table": {
                "source_ref": table.get("source_ref"),
                "authority": table.get("authority"),
                "rule_locator": table.get("rule_locator"),
            },
            "execution_binding": {
                "ref": f"proto_sidecar.phase_c_social_bindings.{encounter_ref}",
                "source_ref": binding["binding_source_ref"],
                "authority": bridge_source.get("authority"),
            },
        },
    }


def execute_social_interaction(
    resolved,
    state,
    *,
    encounter_ref,
    action_id,
    actor_ref,
    dice_terms=None,
    random_seed=None,
):
    """Execute one bounded Phase C social/reaction encounter."""
    binding = _phase_c_binding(resolved, encounter_ref)
    encounter = _encounter(resolved, encounter_ref)
    action = _encounter_action(encounter, action_id)

    if action_id != binding.get("action_id"):
        raise ExecutionError(
            f"action is not bound for Phase C encounter {encounter_ref}: {action_id}"
        )
    if actor_ref != binding.get("actor_ref") or actor_ref != action.get("actor_ref"):
        raise ExecutionError(
            f"actor {actor_ref} is not eligible for social action {action_id}"
        )
    if action.get("procedure_ref") != binding.get("procedure_ref"):
        raise ExecutionError("social action disagrees with Phase C procedure_ref")

    before = copy.deepcopy(state)
    if not _phase_c_ready(resolved, before, binding):
        raise ExecutionError(
            f"social action {action_id} is unavailable in current runtime state"
        )

    reaction_resolution = _execute_reaction_roll(
        resolved,
        encounter_ref=encounter_ref,
        action=action,
        actor_ref=actor_ref,
        binding=binding,
        dice_terms=dice_terms,
        random_seed=random_seed,
    )
    category = reaction_resolution["reaction"]
    consequence = _require_mapping(
        (action.get("consequences") or {}).get(category),
        f"social consequence {category}",
    )
    effect_refs = binding["consequences"][category]["effect_refs"]

    after = copy.deepcopy(before)
    state_index = validate_runtime_state(resolved, after)
    delta = [
        _apply_set_effect(resolved, after, state_index, effect_ref)
        for effect_ref in effect_refs
    ]
    after["revision"] = str(int(after["revision"]) + 1)
    validate_runtime_state(resolved, after)

    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    bridge_source = _require_mapping(
        sources.get(binding["binding_source_ref"]), "Phase C binding source"
    )
    consequence_source = _require_mapping(
        sources.get(binding["consequence_source_ref"]),
        "Phase C consequence source",
    )

    return {
        "format": binding["result_format"],
        "encounter_ref": encounter_ref,
        "action_id": action_id,
        "actor_ref": actor_ref,
        "reaction_resolution": reaction_resolution,
        "reaction": category,
        "consequence": copy.deepcopy(consequence),
        "state_before": before,
        "state_after": after,
        "state_delta": delta,
        "trace": {
            "encounter_action": {
                "encounter_ref": encounter_ref,
                "action_id": action_id,
                "source_ref": action.get("source_ref"),
                "authority": action.get("authority"),
                "provenance": action.get("provenance"),
            },
            "execution_binding": {
                "ref": f"proto_sidecar.phase_c_social_bindings.{encounter_ref}",
                "source_ref": binding["binding_source_ref"],
                "authority": bridge_source.get("authority"),
            },
            "consequence_source": {
                "source_ref": binding["consequence_source_ref"],
                "authority": consequence_source.get("authority"),
                "effect_refs": copy.deepcopy(effect_refs),
            },
            "nested_reaction_result_format": binding["reaction_result_format"],
        },
    }


def replay_social_interaction(resolved, record):
    """Deterministically re-evaluate one Phase C social encounter record."""
    if not isinstance(record, dict):
        raise ExecutionError("social encounter record must be an object")
    if record.get("format") != PHASE_C_RESULT_FORMAT:
        raise ExecutionError(
            f"unsupported Phase C social record format: {record.get('format')!r}"
        )
    reaction = _require_mapping(
        record.get("reaction_resolution"), "social record reaction_resolution"
    )
    evidence = _require_mapping(
        reaction.get("random_evidence"), "social record random_evidence"
    )
    kwargs = {
        "resolved": resolved,
        "state": copy.deepcopy(record.get("state_before")),
        "encounter_ref": record.get("encounter_ref"),
        "action_id": record.get("action_id"),
        "actor_ref": record.get("actor_ref"),
    }
    if evidence.get("kind") == "generated-seeded-dice-terms":
        kwargs["random_seed"] = evidence.get("seed")
    elif evidence.get("kind") == "supplied-dice-terms":
        kwargs["dice_terms"] = evidence.get("terms")
    else:
        raise ExecutionError("social record random evidence kind is unsupported")

    recomputed = execute_social_interaction(**kwargs)
    if recomputed != record:
        raise ExecutionError("social encounter record divergence detected")
    return recomputed


def encounter_runtime_kind(resolved, encounter_ref):
    """Return the runtime-owned interaction kind for a supported encounter."""
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    if encounter_ref in (sidecar.get("phase_b_encounter_bindings") or {}):
        return "investigation"
    if encounter_ref in (sidecar.get("phase_c_social_bindings") or {}):
        return "social"
    if encounter_ref in (sidecar.get("phase_d_environment_bindings") or {}):
        return "environment"
    if encounter_ref in (sidecar.get("phase_e_combat_bindings") or {}):
        return "combat"
    raise ExecutionError(f"encounter has no supported runtime binding: {encounter_ref}")


def _phase_d_binding(resolved, encounter_ref):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    bindings = _require_mapping(
        sidecar.get("phase_d_environment_bindings"),
        "resolved phase_d_environment_bindings",
    )
    binding = _require_mapping(
        bindings.get(encounter_ref), f"Phase D environment binding {encounter_ref}"
    )
    expected_target_source = {
        "kind": "resolved-character-primary-attribute",
        "path": "scene.instances[].character.primary_attributes",
    }
    if binding.get("encounter_ref") != encounter_ref:
        raise ExecutionError("Phase D environment binding identity is malformed")
    if binding.get("action_ref") != "attempt-attribute" or binding.get("procedure_ref") != "success-roll":
        raise ExecutionError("Phase D environment binding must use attempt-attribute -> success-roll")
    if binding.get("target_source") != expected_target_source:
        raise ExecutionError("Phase D attribute target-source binding is unsupported or malformed")
    if binding.get("attribute_result_format") != PHASE_D_ATTRIBUTE_RESULT_FORMAT:
        raise ExecutionError("Phase D attribute result format is unsupported")
    if binding.get("result_format") != PHASE_D_RESULT_FORMAT:
        raise ExecutionError("Phase D encounter result format is unsupported")
    if binding.get("binding_source_ref") != "dirps-proto":
        raise ExecutionError("Phase D binding source is malformed")
    if binding.get("target_source_ref") != "scenario-01-source":
        raise ExecutionError("Phase D target source is malformed")
    if binding.get("consequence_source_ref") != "scenario-01-source":
        raise ExecutionError("Phase D consequence source is malformed")
    if binding.get("critical_resolution_ref") != "phase_a_execution_bindings.attempt-skill.critical_resolution":
        raise ExecutionError("Phase D critical-resolution reuse binding is malformed")
    if binding.get("random_evidence_ref") != "phase_a_execution_bindings.attempt-skill.random_evidence":
        raise ExecutionError("Phase D random-evidence reuse binding is malformed")
    if binding.get("dice_resolution_ref") != "dice_resolution":
        raise ExecutionError("Phase D dice-resolution reuse binding is malformed")
    expected_effective_target = {
        "from": "selected-attribute-level-plus-context-modifiers",
        "modifier_policy": "sum-resolved-context-modifiers",
        "minimum": 3,
        "below_minimum": "error",
        "rule_source_ref": "gurps-lite",
        "rule_locator": "p. 2, Success Rolls; Modifiers and Effective Skill",
    }
    if binding.get("effective_target") != expected_effective_target:
        raise ExecutionError("Phase D effective-target binding is malformed")
    consequences = _require_mapping(binding.get("consequences"), "Phase D consequences")
    if set(consequences) != {"success", "failure"}:
        raise ExecutionError("Phase D must bind success and failure consequences")
    return binding


def create_environment_runtime_state(resolved, *, encounter_ref):
    binding = _phase_d_binding(resolved, encounter_ref)
    states = _require_mapping(resolved.get("runtime_states"), "resolved runtime_states")
    source = _require_mapping(
        states.get(binding.get("runtime_state_ref")),
        f"runtime state {binding.get('runtime_state_ref')}",
    )
    state = copy.deepcopy(source)
    validate_runtime_state(resolved, state)
    return state


def _phase_d_context(resolved, encounter_ref, binding):
    encounter = _encounter(resolved, encounter_ref)
    action = _encounter_action(encounter, binding.get("action_id"))
    if action.get("actor_ref") != binding.get("actor_ref"):
        raise ExecutionError("Phase D encounter actor disagrees with binding")
    if action.get("action_ref") != binding.get("action_ref"):
        raise ExecutionError("Phase D encounter action_ref disagrees with binding")
    if action.get("context_ref") != binding.get("context_ref"):
        raise ExecutionError("Phase D encounter context_ref disagrees with binding")
    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    checks = _require_mapping(scenario.get("contextual_checks"), "resolved contextual_checks")
    check = _require_mapping(
        checks.get(binding.get("context_ref")), "Phase D contextual check"
    )
    if check.get("encounter_ref") != encounter_ref or check.get("action_ref") != binding.get("action_ref"):
        raise ExecutionError("Phase D contextual check identity is malformed")
    attribute_ref = check.get("attribute_ref")
    if not isinstance(attribute_ref, str) or not attribute_ref:
        raise ExecutionError("Phase D contextual check requires attribute_ref")
    modifiers = check.get("modifiers")
    if not isinstance(modifiers, list) or not modifiers:
        raise ExecutionError("Phase D contextual check requires modifiers")
    return encounter, action, check, attribute_ref, copy.deepcopy(modifiers)


def _phase_d_attribute_resolution(
    resolved, *, actor_ref, encounter_ref, dice_terms=None, random_seed=None
):
    binding = _phase_d_binding(resolved, encounter_ref)
    encounter, action, check, attribute_ref, modifiers = _phase_d_context(
        resolved, encounter_ref, binding
    )
    actor = _actor(resolved, actor_ref)
    _require_actor_available(resolved, actor, binding["action_ref"])
    character = _require_mapping(actor.get("character"), f"actor {actor_ref} character")
    attributes = _require_mapping(
        character.get("primary_attributes"), f"actor {actor_ref} primary_attributes"
    )
    base_target = attributes.get(attribute_ref)
    if not isinstance(base_target, int) or isinstance(base_target, bool):
        raise ExecutionError(f"Phase D attribute {attribute_ref} is unavailable or non-integer")

    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    validated_modifiers = []
    seen = set()
    for index, modifier in enumerate(modifiers):
        row = _require_mapping(modifier, f"Phase D modifier {index}")
        modifier_id = row.get("id")
        if not isinstance(modifier_id, str) or not modifier_id or modifier_id in seen:
            raise ExecutionError("Phase D modifier ids must be unique non-empty strings")
        seen.add(modifier_id)
        if not isinstance(row.get("amount"), int) or isinstance(row.get("amount"), bool):
            raise ExecutionError(f"Phase D modifier {modifier_id} amount must be integer")
        if row.get("source_ref") != binding.get("target_source_ref"):
            raise ExecutionError(f"Phase D modifier {modifier_id} source_ref disagrees with binding")
        source = _require_mapping(sources.get(row.get("source_ref")), "Phase D modifier source")
        if row.get("authority") != source.get("authority"):
            raise ExecutionError(f"Phase D modifier {modifier_id} authority disagrees with source")
        if row.get("provenance") != character.get("provenance"):
            raise ExecutionError(f"Phase D modifier {modifier_id} provenance disagrees with character")
        validated_modifiers.append(copy.deepcopy(row))

    effective = _require_mapping(binding.get("effective_target"), "Phase D effective target")
    if effective.get("from") != "selected-attribute-level-plus-context-modifiers":
        raise ExecutionError("Phase D effective-target source is unsupported")
    if effective.get("modifier_policy") != "sum-resolved-context-modifiers":
        raise ExecutionError("Phase D modifier policy is unsupported")
    modifier_total = sum(row["amount"] for row in validated_modifiers)
    effective_target = base_target + modifier_total
    minimum = effective.get("minimum")
    if not isinstance(minimum, int) or effective_target < minimum:
        raise ExecutionError("Phase D effective target is below the supported minimum")

    phase_a = _execution_binding(resolved)
    if binding["dice_resolution_ref"] != phase_a.get("dice_resolution_ref"):
        raise ExecutionError(
            "Phase F roll dice_resolution_ref disagrees with the accepted Phase A binding"
        )
    if binding["critical_resolution_ref"] != (
        "phase_a_execution_bindings.attempt-skill.critical_resolution"
    ):
        raise ExecutionError(
            "Phase F roll critical_resolution_ref is unsupported or malformed"
        )
    _require_mapping(
        phase_a.get("critical_resolution"),
        "Phase F roll referenced Phase A critical_resolution",
    )
    if binding["random_evidence_ref"] != (
        "phase_a_execution_bindings.attempt-skill.random_evidence"
    ):
        raise ExecutionError(
            "Phase F roll random_evidence_ref is unsupported or malformed"
        )
    _require_mapping(
        phase_a.get("random_evidence"),
        "Phase F roll referenced Phase A random_evidence",
    )
    dice = _dice_contract(resolved, phase_a)
    terms, evidence_kind = _random_terms(
        dice_terms=dice_terms,
        random_seed=random_seed,
        contract=dice,
        binding=phase_a,
    )
    total = sum(terms)
    classification, success = _critical_classification(total, effective_target, phase_a)
    margin = effective_target - total
    critical = _require_mapping(phase_a.get("critical_resolution"), "Phase A critical contract")

    return {
        "format": binding["attribute_result_format"],
        "mechanic": "attribute-success-roll",
        "input": {
            "actor_ref": actor_ref,
            "attribute_ref": attribute_ref,
            "context_ref": binding["context_ref"],
        },
        "semantic_path": {
            "action_ref": binding["action_ref"],
            "procedure_ref": binding["procedure_ref"],
        },
        "target": {
            "kind": binding["target_source"]["kind"],
            "attribute_ref": attribute_ref,
            "base_target": base_target,
            "modifiers": validated_modifiers,
            "modifier_total": modifier_total,
            "effective_target": effective_target,
            "modifier_policy": effective["modifier_policy"],
        },
        "random_evidence": {
            **evidence_kind,
            "proto_ref": binding["dice_resolution_ref"],
            "randomizer_id": dice["id"],
            "dice_kind": dice["kind"],
            "sides": dice["sides"],
            "terms": terms,
            "total": total,
        },
        "outcome": {
            "classification": classification,
            "success": success,
            "margin": margin,
        },
        "trace": {
            "attribute_target": {
                "actor_ref": actor_ref,
                "attribute_ref": attribute_ref,
                "base_value": base_target,
                "character_provenance": character.get("provenance"),
                "canonical_path": f"player_character.attributes.{attribute_ref}",
                "source_ref": binding["target_source_ref"],
                "authority": sources[binding["target_source_ref"]].get("authority"),
            },
            "effective_target": {
                "modifier_total": modifier_total,
                "value": effective_target,
                "rule_source_ref": effective["rule_source_ref"],
                "rule_authority": sources[effective["rule_source_ref"]].get("authority"),
                "rule_locator": effective["rule_locator"],
                "modifiers": copy.deepcopy(validated_modifiers),
            },
            "critical_resolution": {
                "classification": classification,
                "source_ref": critical["rule_source_ref"],
                "authority": sources[critical["rule_source_ref"]].get("authority"),
                "rule_locator": critical["rule_locator"],
            },
            "execution_binding": {
                "ref": f"proto_sidecar.phase_d_environment_bindings.{encounter_ref}",
                "source_ref": binding["binding_source_ref"],
                "authority": sources[binding["binding_source_ref"]].get("authority"),
            },
        },
        "state_delta": [],
    }


def describe_environment_challenge(resolved, state, *, encounter_ref):
    binding = _phase_d_binding(resolved, encounter_ref)
    encounter, action, check, attribute_ref, modifiers = _phase_d_context(
        resolved, encounter_ref, binding
    )
    index = validate_runtime_state(resolved, state)
    ready = all(
        _state_value(index, row.get("ref")) == row.get("value")
        for row in binding.get("required_state", [])
    )
    refs = _require_mapping(
        _require_mapping(encounter.get("state_contract"), "Phase D state_contract").get("refs"),
        "Phase D state refs",
    )
    return {
        "encounter": {"id": encounter_ref, "type": encounter.get("type"), "purpose": encounter.get("purpose")},
        "runtime_state_revision": state.get("revision"),
        "state": {role: _state_value(index, ref) for role, ref in refs.items()},
        "available_actions": [{
            "id": action.get("id"),
            "label": action.get("label"),
            "actor_ref": action.get("actor_ref"),
            "action_ref": action.get("action_ref"),
            "context_ref": action.get("context_ref"),
            "source_ref": action.get("source_ref"),
            "authority": action.get("authority"),
            "provenance": action.get("provenance"),
        }] if ready else [],
        "check": {
            "attribute_ref": attribute_ref,
            "modifiers": copy.deepcopy(modifiers),
            "procedure_ref": binding["procedure_ref"],
            "target_source": copy.deepcopy(binding["target_source"]),
        },
        "result_format": binding["result_format"],
    }


def execute_environment_challenge(
    resolved, state, *, encounter_ref, action_id, actor_ref,
    dice_terms=None, random_seed=None
):
    binding = _phase_d_binding(resolved, encounter_ref)
    encounter, action, check, attribute_ref, modifiers = _phase_d_context(
        resolved, encounter_ref, binding
    )
    if action_id != binding.get("action_id"):
        raise ExecutionError(f"action is not bound for Phase D encounter {encounter_ref}: {action_id}")
    if actor_ref != binding.get("actor_ref"):
        raise ExecutionError(f"actor {actor_ref} is not eligible for Phase D encounter")
    before = copy.deepcopy(state)
    index = validate_runtime_state(resolved, before)
    if not all(
        _state_value(index, row.get("ref")) == row.get("value")
        for row in binding.get("required_state", [])
    ):
        raise ExecutionError(f"encounter action {action_id} is unavailable in current runtime state")

    attribute_resolution = _phase_d_attribute_resolution(
        resolved,
        actor_ref=actor_ref,
        encounter_ref=encounter_ref,
        dice_terms=dice_terms,
        random_seed=random_seed,
    )
    branch = "success" if attribute_resolution["outcome"]["success"] else "failure"
    consequence = _require_mapping(
        (action.get("consequences") or {}).get(branch),
        f"Phase D {branch} consequence",
    )
    effect_refs = binding["consequences"][branch]["effect_refs"]
    after = copy.deepcopy(before)
    after_index = validate_runtime_state(resolved, after)
    delta = [_apply_set_effect(resolved, after, after_index, ref) for ref in effect_refs]
    after["revision"] = str(int(after["revision"]) + 1)
    validate_runtime_state(resolved, after)
    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    return {
        "format": binding["result_format"],
        "encounter_ref": encounter_ref,
        "action_id": action_id,
        "actor_ref": actor_ref,
        "outcome_branch": branch,
        "attribute_resolution": attribute_resolution,
        "consequence": copy.deepcopy(consequence),
        "state_before": before,
        "state_after": after,
        "state_delta": delta,
        "trace": {
            "encounter_action": {
                "encounter_ref": encounter_ref,
                "action_id": action_id,
                "source_ref": action.get("source_ref"),
                "authority": action.get("authority"),
                "provenance": action.get("provenance"),
            },
            "execution_binding": {
                "ref": f"proto_sidecar.phase_d_environment_bindings.{encounter_ref}",
                "source_ref": binding["binding_source_ref"],
                "authority": sources[binding["binding_source_ref"]].get("authority"),
            },
            "consequence_source": {
                "source_ref": binding["consequence_source_ref"],
                "authority": sources[binding["consequence_source_ref"]].get("authority"),
                "effect_refs": copy.deepcopy(effect_refs),
            },
            "nested_attribute_result_format": binding["attribute_result_format"],
        },
    }


def replay_environment_challenge(resolved, record):
    if not isinstance(record, dict) or record.get("format") != PHASE_D_RESULT_FORMAT:
        raise ExecutionError("unsupported Phase D environmental record format")
    resolution = _require_mapping(record.get("attribute_resolution"), "Phase D attribute_resolution")
    evidence = _require_mapping(resolution.get("random_evidence"), "Phase D random_evidence")
    kwargs = {
        "resolved": resolved,
        "state": copy.deepcopy(record.get("state_before")),
        "encounter_ref": record.get("encounter_ref"),
        "action_id": record.get("action_id"),
        "actor_ref": record.get("actor_ref"),
    }
    if evidence.get("kind") == "generated-seeded-dice-terms":
        kwargs["random_seed"] = evidence.get("seed")
    elif evidence.get("kind") == "supplied-dice-terms":
        kwargs["dice_terms"] = evidence.get("terms")
    else:
        raise ExecutionError("Phase D random evidence kind is unsupported")
    recomputed = execute_environment_challenge(**kwargs)
    if recomputed != record:
        raise ExecutionError("environment encounter record divergence detected")
    return recomputed


def _phase_e_binding(resolved, encounter_ref):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    bindings = _require_mapping(
        sidecar.get("phase_e_combat_bindings"), "resolved phase_e_combat_bindings"
    )
    binding = _require_mapping(
        bindings.get(encounter_ref), f"Phase E combat binding {encounter_ref}"
    )
    if binding.get("encounter_ref") != encounter_ref:
        raise ExecutionError("Phase E combat binding identity is malformed")
    expected_scalar = {
        "action_id": "strike-bandit-scout",
        "attacker_ref": "pc",
        "target_ref": "bandit-scout",
        "action_ref": "attack",
        "procedure_ref": "attack-resolution",
        "skill_ref": "broadsword",
        "weapon_ref": "broadsword",
        "attack_mode": "swing-cut",
        "runtime_state_ref": "scenario-01-bandit-scout-initial",
        "required_revision": "0",
        "attack_random_evidence_ref": "phase_a_execution_bindings.attempt-skill.random_evidence",
        "attack_critical_resolution_ref": "phase_a_execution_bindings.attempt-skill.critical_resolution",
        "attack_result_format": PHASE_E_ATTACK_FORMAT,
        "result_format": PHASE_E_RESULT_FORMAT,
        "binding_source_ref": "dirps-proto",
        "scenario_source_ref": "scenario-01-source",
    }
    for key, expected in expected_scalar.items():
        if binding.get(key) != expected:
            raise ExecutionError(
                f"Phase E combat binding {key} is unsupported or malformed"
            )
    if binding.get("reaction_window") != {
        "trigger": "successful-noncritical-attack",
        "responder_ref": "bandit-scout",
        "eligible_defenses": ["dodge"],
        "resolution_order": "attack-then-defense-before-damage",
    }:
        raise ExecutionError("Phase E active-defense reaction window is unsupported or malformed")
    if binding.get("defense") != {
        "kind": "dodge",
        "target_expression_ref": "bandit-dodge-target",
        "random_evidence_ref": "phase_a_execution_bindings.attempt-skill.random_evidence",
        "rule_source_ref": "gurps-lite",
        "rule_locator": "p. 26, Defense / Dodging",
        "result_format": PHASE_E_DEFENSE_FORMAT,
    }:
        raise ExecutionError("Phase E Dodge binding is unsupported or malformed")
    if binding.get("damage") != {
        "strength_lookup_ref": "gurps-lite-st10-swing",
        "weapon_add": 1,
        "damage_type": "cutting",
        "minimum_basic_damage": 1,
        "armor_dr_source": "encounter.opponent.defense_assumptions.armor_dr",
        "injury_expression_ref": "cutting-injury",
        "rule_source_ref": "gurps-lite",
        "rule_locator": "pp. 18-19, Weapon Damage; pp. 26-28, Damage and Injury",
        "result_format": PHASE_E_DAMAGE_FORMAT,
        "critical_attack_total_three": {
            "attack_total": 3,
            "resolution": "automatic-maximum-profile-damage",
            "damage_random_evidence": "none",
            "rule_source_ref": "gurps-lite",
            "rule_locator": "Rolling to Attack / Critical Hits",
        },
    }:
        raise ExecutionError("Phase E damage binding is unsupported or malformed")
    if binding.get("injury_state") != {
        "hit_points_ref": "hit-points",
        "stunned_ref": "stunned",
        "unconscious_ref": "unconscious",
        "consciousness_check_required_ref": "consciousness-check-required",
        "major_wound_rule": "injury > defender.ht / 2",
        "consciousness_check_rule": "remaining_hp <= 0",
        "consciousness_check_timing": "next-turn-start",
        "recovery_phase": "Phase F",
    }:
        raise ExecutionError("Phase E injury-state binding is unsupported or malformed")
    return binding


def _phase_e_context(resolved, encounter_ref, binding):
    encounter = _encounter(resolved, encounter_ref)
    actions = encounter.get("actions")
    if not isinstance(actions, list) or len(actions) != 1:
        raise ExecutionError("Phase E bounded combat requires exactly one encounter action")
    action = _require_mapping(actions[0], "Phase E combat action")
    expected = {
        "id": binding["action_id"],
        "actor_ref": binding["attacker_ref"],
        "target_ref": binding["target_ref"],
        "action_ref": binding["action_ref"],
        "skill_ref": binding["skill_ref"],
        "weapon_ref": binding["weapon_ref"],
        "attack_mode": binding["attack_mode"],
        "source_ref": "scenario-01-source",
        "authority": "provisional",
        "provenance": "prototype_assumption",
        "supported_defense": "dodge",
    }
    for key, value in expected.items():
        if action.get(key) != value:
            raise ExecutionError(f"Phase E combat action {key} disagrees with binding")

    opponent = _require_mapping(encounter.get("opponent"), "Phase E opponent")
    if opponent.get("actor_ref") != binding["target_ref"]:
        raise ExecutionError("Phase E opponent actor_ref disagrees with combat target")
    assumptions = _require_mapping(
        opponent.get("defense_assumptions"), "Phase E defense assumptions"
    )
    if assumptions.get("aware_of_attack") is not True:
        raise ExecutionError("Phase E Dodge requires an aware defender")
    for ref in ("encumbrance_penalty", "armor_dr", "passive_defense"):
        value = assumptions.get(ref)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ExecutionError(f"Phase E defense assumption {ref} is malformed")
    if encounter.get("bounded_combat") != {"maximum_exchanges": 1}:
        raise ExecutionError("Phase E combat scope must remain one exchange")

    attacker = _actor(resolved, binding["attacker_ref"])
    defender = _actor(resolved, binding["target_ref"])
    character = _require_mapping(
        attacker.get("character"), "Phase E attacker resolved character"
    )
    skills = _require_mapping(character.get("skills"), "Phase E attacker skills")
    if binding["skill_ref"] not in skills:
        raise ExecutionError("Phase E Broadsword skill is missing")
    if binding["weapon_ref"] not in (character.get("equipment") or []):
        raise ExecutionError("Phase E Broadsword equipment is missing")
    _require_actor_available(resolved, attacker, binding["action_ref"])
    return encounter, action, opponent, attacker, defender


def _phase_e_expression(resolved, expression_ref):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    expressions = _require_mapping(
        sidecar.get("phase_e_expressions"), "resolved phase_e_expressions"
    )
    expression = _require_mapping(
        expressions.get(expression_ref), f"Phase E expression {expression_ref}"
    )
    if expression.get("source_ref") != "gurps-lite" or expression.get("authority") != "authoritative":
        raise ExecutionError(f"Phase E expression {expression_ref} lost rule authority")
    return expression


def _eval_phase_e_expression(node, values):
    node = _require_mapping(node, "Phase E expression node")
    if "literal" in node:
        value = node["literal"]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ExecutionError("Phase E expression literal must be numeric")
        return value
    if "ref" in node:
        ref = node["ref"]
        if ref not in values:
            raise ExecutionError(f"Phase E expression reference is unresolved: {ref}")
        return values[ref]

    op = node.get("op")
    if op == "floor":
        return math.floor(_eval_phase_e_expression(node.get("arg"), values))
    args = node.get("args")
    if not isinstance(args, list) or len(args) != 2:
        raise ExecutionError(f"Phase E expression {op!r} requires exactly two args")
    left = _eval_phase_e_expression(args[0], values)
    right = _eval_phase_e_expression(args[1], values)
    if op == "add":
        return left + right
    if op == "subtract":
        return left - right
    if op == "divide":
        if right == 0:
            raise ExecutionError("Phase E expression division by zero")
        return left / right
    raise ExecutionError(f"unsupported Phase E expression operator: {op!r}")


def _phase_e_derived_value(resolved, derived_ref, values):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    derived = _require_mapping(
        (sidecar.get("phase_e_derived_values") or {}).get(derived_ref),
        f"Phase E derived value {derived_ref}",
    )
    expression_ref = derived.get("expression_ref")
    expression = _phase_e_expression(resolved, expression_ref)
    result = _eval_phase_e_expression(expression, values)
    if derived.get("value_type") == "integer":
        if isinstance(result, bool) or int(result) != result:
            raise ExecutionError(f"Phase E derived value {derived_ref} must be integer")
        result = int(result)
    return result, {
        "derived_ref": derived_ref,
        "expression_ref": expression_ref,
        "dependencies": copy.deepcopy(derived.get("dependencies", [])),
        "recompute": derived.get("recompute"),
        "source_ref": expression.get("source_ref"),
        "authority": expression.get("authority"),
        "rule_locator": expression.get("rule_locator"),
    }


def _phase_e_damage_profile(resolved, lookup_ref, strength):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    table = _require_mapping(
        (sidecar.get("phase_e_lookup_tables") or {}).get(lookup_ref),
        f"Phase E damage lookup {lookup_ref}",
    )
    if table.get("source_ref") != "gurps-lite" or table.get("authority") != "authoritative":
        raise ExecutionError("Phase E damage lookup lost rule authority")
    matches = []
    for row in table.get("rows", []):
        when = _require_mapping(row.get("when"), "Phase E damage lookup range")
        if when.get("min") is not None and strength < when["min"]:
            continue
        if when.get("max") is not None and strength > when["max"]:
            continue
        matches.append(row)
    if len(matches) != 1:
        raise ExecutionError(
            f"Phase E bounded damage lookup has no unique row for ST {strength}"
        )
    value = _require_mapping(matches[0].get("value"), "Phase E damage lookup result")
    count = value.get("count")
    sides = value.get("sides")
    adds = value.get("adds")
    if (
        not isinstance(count, int) or count <= 0
        or not isinstance(sides, int) or sides < 2
        or not isinstance(adds, int) or isinstance(adds, bool)
    ):
        raise ExecutionError("Phase E damage lookup result is malformed")
    return copy.deepcopy(value), {
        "table_ref": lookup_ref,
        "matched_row": copy.deepcopy(matches[0]),
        "source_ref": table.get("source_ref"),
        "authority": table.get("authority"),
        "rule_locator": table.get("rule_locator"),
    }


def validate_combat_runtime_state(resolved, state, *, target_ref):
    if not isinstance(state, dict):
        raise ExecutionError("combat runtime state must be an object")
    if state.get("scenario_ref") != resolved.get("scenario_id"):
        raise ExecutionError("combat runtime state scenario_ref disagrees with resolved scenario")
    revision = state.get("revision")
    if not isinstance(revision, str):
        raise ExecutionError("combat runtime state revision must be a string")
    try:
        int(revision)
    except ValueError as exc:
        raise ExecutionError("combat runtime state revision must be an integer string") from exc
    if not isinstance(state.get("events"), list):
        raise ExecutionError("combat runtime state events must be a list")

    expected_refs = {
        "hit-points",
        "stunned",
        "unconscious",
        "consciousness-check-required",
    }
    definitions = _require_mapping(
        (resolved.get("rules") or {}).get("values"), "resolved value definitions"
    )
    index = {}
    for row in state.get("bindings", []):
        binding = _require_mapping(row, "combat runtime state binding")
        ref = binding.get("ref")
        if ref not in expected_refs:
            raise ExecutionError(f"unsupported Phase E combat state binding: {ref}")
        if binding.get("subject") != {"instance_ref": target_ref}:
            raise ExecutionError(
                f"Phase E combat state binding {ref} must target {target_ref}"
            )
        if binding.get("authority") != "provisional":
            raise ExecutionError(
                f"Phase E combat state binding {ref} must remain provisional"
            )
        if ref in index:
            raise ExecutionError(f"duplicate combat state binding: {ref}")
        definition = _require_mapping(
            definitions.get(ref), f"combat state value definition {ref}"
        )
        _validate_state_value(definition, binding.get("value"), ref)
        index[ref] = binding
    missing = sorted(expected_refs - set(index))
    if missing:
        raise ExecutionError(f"Phase E combat state is missing bindings: {missing}")
    return index


def create_combat_runtime_state(resolved, *, encounter_ref="bandit-scout"):
    binding = _phase_e_binding(resolved, encounter_ref)
    states = _require_mapping(resolved.get("runtime_states"), "resolved runtime_states")
    state = copy.deepcopy(
        _require_mapping(
            states.get(binding["runtime_state_ref"]),
            f"combat runtime state {binding['runtime_state_ref']}",
        )
    )
    validate_combat_runtime_state(resolved, state, target_ref=binding["target_ref"])
    return state


def _phase_e_random_terms(
    *,
    resolved,
    label,
    terms,
    random_seed,
    count,
    sides,
):
    phase_a = _execution_binding(resolved)
    contract = {"count": count, "sides": sides}
    if random_seed is not None:
        if terms is not None:
            raise ExecutionError("Phase E cannot mix supplied combat dice with random_seed")
        return _random_terms(
            dice_terms=None,
            random_seed=f"{random_seed}:{label}",
            contract=contract,
            binding=phase_a,
        )
    if terms is None:
        raise ExecutionError(f"Phase E requires {label} dice evidence")
    return _random_terms(
        dice_terms=terms,
        random_seed=None,
        contract=contract,
        binding=phase_a,
    )


def _phase_e_attack_roll(
    resolved,
    *,
    attacker,
    binding,
    attack_terms,
    random_seed,
):
    phase_a = _execution_binding(resolved)
    character = _require_mapping(attacker.get("character"), "Phase E attacker character")
    skills = _require_mapping(character.get("skills"), "Phase E attacker skills")
    target = skills.get(binding["skill_ref"])
    if not isinstance(target, int) or isinstance(target, bool) or target < 3:
        raise ExecutionError("Phase E attack skill target must be an integer >= 3")
    dice = _dice_contract(resolved, phase_a)
    terms, evidence_kind = _phase_e_random_terms(
        resolved=resolved,
        label="attack",
        terms=attack_terms,
        random_seed=random_seed,
        count=dice["count"],
        sides=dice["sides"],
    )
    total = sum(terms)
    classification, success = _critical_classification(total, target, phase_a)
    return {
        "format": binding["attack_result_format"],
        "skill_ref": binding["skill_ref"],
        "target": target,
        "random_evidence": {
            **evidence_kind,
            "dice_kind": dice["kind"],
            "sides": dice["sides"],
            "terms": terms,
            "total": total,
        },
        "outcome": {
            "classification": classification,
            "success": success,
            "margin": target - total,
        },
        "trace": {
            "action_ref": binding["action_ref"],
            "procedure_ref": binding["procedure_ref"],
            "rule_source_ref": "gurps-lite",
            "rule_authority": "authoritative",
            "random_evidence_ref": binding["attack_random_evidence_ref"],
            "critical_resolution_ref": binding["attack_critical_resolution_ref"],
        },
    }


def _phase_e_defense_roll(
    resolved,
    *,
    opponent,
    binding,
    defense_terms,
    random_seed,
):
    attrs = _require_mapping(opponent.get("attributes"), "Phase E opponent attributes")
    assumptions = _require_mapping(
        opponent.get("defense_assumptions"), "Phase E defense assumptions"
    )
    values = {
        "defender.dx": attrs.get("dx"),
        "defender.ht": attrs.get("ht"),
        "defender.encumbrance_penalty": assumptions.get("encumbrance_penalty"),
        "defender.passive_defense": assumptions.get("passive_defense"),
    }
    target, derived_trace = _phase_e_derived_value(
        resolved, "bandit-dodge", values
    )
    if not isinstance(target, int) or target < 0:
        raise ExecutionError("Phase E Dodge target must be a nonnegative integer")

    terms, evidence_kind = _phase_e_random_terms(
        resolved=resolved,
        label="defense",
        terms=defense_terms,
        random_seed=random_seed,
        count=3,
        sides=6,
    )
    total = sum(terms)
    if total <= 4:
        classification = "critical-success"
        success = True
    elif total >= 17:
        classification = "failure"
        success = False
    else:
        success = total <= target
        classification = "success" if success else "failure"
    return {
        "format": binding["defense"]["result_format"],
        "kind": binding["defense"]["kind"],
        "target": target,
        "random_evidence": {
            **evidence_kind,
            "dice_kind": "dice-pool",
            "sides": 6,
            "terms": terms,
            "total": total,
        },
        "outcome": {
            "classification": classification,
            "success": success,
            "margin": target - total,
        },
        "trace": {
            "reaction_window": copy.deepcopy(binding["reaction_window"]),
            "derived_target": derived_trace,
            "rule_source_ref": binding["defense"]["rule_source_ref"],
            "rule_authority": "authoritative",
            "rule_locator": binding["defense"]["rule_locator"],
            "random_evidence_ref": binding["defense"]["random_evidence_ref"],
        },
    }


def _phase_e_damage_result(
    resolved,
    *,
    attacker,
    opponent,
    binding,
    profile,
    lookup_trace,
    random_evidence,
    rolled_total,
    resolution_mode,
):
    assumptions = _require_mapping(
        opponent.get("defense_assumptions"), "Phase E defense assumptions"
    )
    armor_dr = assumptions.get("armor_dr")
    if not isinstance(armor_dr, int) or isinstance(armor_dr, bool) or armor_dr < 0:
        raise ExecutionError("Phase E armor DR must be a nonnegative integer")

    basic_damage = max(
        binding["damage"]["minimum_basic_damage"],
        rolled_total + profile["adds"] + binding["damage"]["weapon_add"],
    )
    penetrating = max(0, basic_damage - armor_dr)
    injury, injury_trace = _phase_e_derived_value(
        resolved,
        "cutting-injury",
        {"penetrating_damage": penetrating},
    )
    if not isinstance(injury, int) or injury < 0:
        raise ExecutionError("Phase E injury must be a nonnegative integer")

    attacker_state = _require_mapping(attacker.get("state"), "Phase E attacker state")
    strength = attacker_state.get("st")
    return {
        "format": binding["damage"]["result_format"],
        "strength": strength,
        "attack_mode": binding["attack_mode"],
        "damage_type": binding["damage"]["damage_type"],
        "resolution_mode": resolution_mode,
        "random_evidence": copy.deepcopy(random_evidence),
        "weapon_add": binding["damage"]["weapon_add"],
        "basic_damage": basic_damage,
        "armor_dr": armor_dr,
        "penetrating_damage": penetrating,
        "injury": injury,
        "trace": {
            "strength_lookup": lookup_trace,
            "injury_derived": injury_trace,
            "rule_source_ref": binding["damage"]["rule_source_ref"],
            "rule_authority": "authoritative",
            "rule_locator": binding["damage"]["rule_locator"],
        },
    }


def _phase_e_damage_roll(
    resolved,
    *,
    attacker,
    opponent,
    binding,
    damage_terms,
    random_seed,
):
    attacker_state = _require_mapping(attacker.get("state"), "Phase E attacker state")
    strength = attacker_state.get("st")
    if not isinstance(strength, int) or isinstance(strength, bool):
        raise ExecutionError("Phase E attacker ST must be an integer")
    profile, lookup_trace = _phase_e_damage_profile(
        resolved, binding["damage"]["strength_lookup_ref"], strength
    )
    terms, evidence_kind = _phase_e_random_terms(
        resolved=resolved,
        label="damage",
        terms=damage_terms,
        random_seed=random_seed,
        count=profile["count"],
        sides=profile["sides"],
    )
    rolled = sum(terms)
    return _phase_e_damage_result(
        resolved,
        attacker=attacker,
        opponent=opponent,
        binding=binding,
        profile=profile,
        lookup_trace=lookup_trace,
        random_evidence={
            **evidence_kind,
            "dice_kind": "dice-pool",
            "sides": profile["sides"],
            "terms": terms,
            "rolled_total": rolled,
        },
        rolled_total=rolled,
        resolution_mode="rolled",
    )


def _phase_e_maximum_damage(
    resolved,
    *,
    attacker,
    opponent,
    binding,
):
    rule = _require_mapping(
        binding["damage"].get("critical_attack_total_three"),
        "Phase E roll-3 critical damage rule",
    )
    if rule != {
        "attack_total": 3,
        "resolution": "automatic-maximum-profile-damage",
        "damage_random_evidence": "none",
        "rule_source_ref": "gurps-lite",
        "rule_locator": "Rolling to Attack / Critical Hits",
    }:
        raise ExecutionError("Phase E roll-3 critical damage rule is malformed")

    attacker_state = _require_mapping(attacker.get("state"), "Phase E attacker state")
    strength = attacker_state.get("st")
    if not isinstance(strength, int) or isinstance(strength, bool):
        raise ExecutionError("Phase E attacker ST must be an integer")
    profile, lookup_trace = _phase_e_damage_profile(
        resolved, binding["damage"]["strength_lookup_ref"], strength
    )
    maximum_rolled_total = profile["count"] * profile["sides"]
    result = _phase_e_damage_result(
        resolved,
        attacker=attacker,
        opponent=opponent,
        binding=binding,
        profile=profile,
        lookup_trace=lookup_trace,
        random_evidence=None,
        rolled_total=maximum_rolled_total,
        resolution_mode="automatic-maximum",
    )
    result["trace"]["critical_maximum_damage"] = {
        "attack_total": rule["attack_total"],
        "resolution": rule["resolution"],
        "random_damage_evidence": rule["damage_random_evidence"],
        "maximum_rolled_total": maximum_rolled_total,
        "rule_source_ref": rule["rule_source_ref"],
        "rule_authority": "authoritative",
        "rule_locator": rule["rule_locator"],
    }
    return result

def _combat_delta_row(ref, before, after, target_ref, source_ref, authority):
    return {
        "op": "set",
        "ref": ref,
        "subject": {"instance_ref": target_ref},
        "before": copy.deepcopy(before),
        "after": copy.deepcopy(after),
        "source_ref": source_ref,
        "authority": authority,
    }


def _apply_phase_e_injury(
    resolved,
    state,
    *,
    target_ref,
    opponent,
    binding,
    injury,
):
    after = copy.deepcopy(state)
    index = validate_combat_runtime_state(resolved, after, target_ref=target_ref)
    injury_state = binding["injury_state"]
    hp_ref = injury_state["hit_points_ref"]
    stunned_ref = injury_state["stunned_ref"]
    unconscious_ref = injury_state["unconscious_ref"]
    check_ref = injury_state["consciousness_check_required_ref"]

    hp_before = index[hp_ref]["value"]
    hp_after = hp_before - injury
    index[hp_ref]["value"] = hp_after
    delta = [
        _combat_delta_row(
            hp_ref,
            hp_before,
            hp_after,
            target_ref,
            "gurps-lite",
            "authoritative",
        )
    ] if injury else []

    ht = (_require_mapping(opponent.get("attributes"), "Phase E opponent attributes")).get("ht")
    if not isinstance(ht, int) or isinstance(ht, bool) or ht < 1:
        raise ExecutionError("Phase E defender HT must be a positive integer")

    major_wound = injury > (ht / 2)
    stunned_before = index[stunned_ref]["value"]
    stunned_after = bool(stunned_before or major_wound)
    if stunned_after != stunned_before:
        index[stunned_ref]["value"] = stunned_after
        delta.append(
            _combat_delta_row(
                stunned_ref,
                stunned_before,
                stunned_after,
                target_ref,
                "gurps-lite",
                "authoritative",
            )
        )

    check_before = index[check_ref]["value"]
    check_after = bool(check_before or hp_after <= 0)
    if check_after != check_before:
        index[check_ref]["value"] = check_after
        delta.append(
            _combat_delta_row(
                check_ref,
                check_before,
                check_after,
                target_ref,
                "dirps-proto",
                "provisional",
            )
        )

    # Phase E intentionally does not perform the beginning-of-turn HT check.
    if index[unconscious_ref]["value"] is not False:
        raise ExecutionError("Phase E does not support an already-unconscious defender")

    return after, delta, {
        "major_wound": major_wound,
        "stunned": stunned_after,
        "remaining_hp": hp_after,
        "consciousness_check_required": check_after,
        "unconscious": False,
        "deferred_recovery_phase": injury_state["recovery_phase"],
        "consciousness_check_timing": injury_state["consciousness_check_timing"],
    }


def describe_combat_exchange(resolved, state, *, encounter_ref):
    binding = _phase_e_binding(resolved, encounter_ref)
    encounter, action, opponent, attacker, defender = _phase_e_context(
        resolved, encounter_ref, binding
    )
    index = validate_combat_runtime_state(
        resolved, state, target_ref=binding["target_ref"]
    )
    ready = (
        state.get("revision") == binding["required_revision"]
        and index["unconscious"]["value"] is False
    )
    defense_values = {
        "defender.dx": opponent["attributes"]["dx"],
        "defender.ht": opponent["attributes"]["ht"],
        "defender.encumbrance_penalty": opponent["defense_assumptions"]["encumbrance_penalty"],
        "defender.passive_defense": opponent["defense_assumptions"]["passive_defense"],
    }
    defense_target, defense_trace = _phase_e_derived_value(
        resolved, "bandit-dodge", defense_values
    )
    damage_profile, damage_trace = _phase_e_damage_profile(
        resolved, binding["damage"]["strength_lookup_ref"], attacker["state"]["st"]
    )
    character = _require_mapping(attacker.get("character"), "Phase E attacker character")
    return {
        "encounter": {
            "id": encounter_ref,
            "type": encounter.get("type"),
            "purpose": encounter.get("purpose"),
        },
        "runtime_state_revision": state.get("revision"),
        "target_state": {ref: row["value"] for ref, row in index.items()},
        "available_actions": [
            {
                "id": action.get("id"),
                "label": action.get("label"),
                "actor_ref": action.get("actor_ref"),
                "target_ref": action.get("target_ref"),
                "action_ref": action.get("action_ref"),
                "skill_ref": action.get("skill_ref"),
                "weapon_ref": action.get("weapon_ref"),
                "attack_mode": action.get("attack_mode"),
                "supported_defense": action.get("supported_defense"),
                "source_ref": action.get("source_ref"),
                "authority": action.get("authority"),
                "provenance": action.get("provenance"),
            }
        ] if ready else [],
        "combat_capability": {
            "attack_target": character["skills"][binding["skill_ref"]],
            "reaction_window": copy.deepcopy(binding["reaction_window"]),
            "defense": {
                "kind": binding["defense"]["kind"],
                "target": defense_target,
                "trace": defense_trace,
            },
            "damage": {
                "strength": attacker["state"]["st"],
                "profile": damage_profile,
                "weapon_add": binding["damage"]["weapon_add"],
                "damage_type": binding["damage"]["damage_type"],
                "armor_dr": opponent["defense_assumptions"]["armor_dr"],
                "trace": damage_trace,
            },
            "injury_state": copy.deepcopy(binding["injury_state"]),
        },
        "result_format": binding["result_format"],
    }


def execute_combat_exchange(
    resolved,
    state,
    *,
    encounter_ref,
    action_id,
    actor_ref,
    target_ref,
    defense_kind="dodge",
    attack_terms=None,
    defense_terms=None,
    damage_terms=None,
    random_seed=None,
):
    binding = _phase_e_binding(resolved, encounter_ref)
    encounter, action, opponent, attacker, defender = _phase_e_context(
        resolved, encounter_ref, binding
    )
    if action_id != binding["action_id"]:
        raise ExecutionError(f"unsupported Phase E combat action: {action_id}")
    if actor_ref != binding["attacker_ref"] or target_ref != binding["target_ref"]:
        raise ExecutionError("Phase E combat actor/target selection is unsupported")
    if defense_kind not in binding["reaction_window"]["eligible_defenses"]:
        raise ExecutionError(f"unsupported Phase E active defense: {defense_kind}")
    if defense_kind != binding["defense"]["kind"]:
        raise ExecutionError("Phase E defense selection disagrees with binding")
    if random_seed is not None and any(
        terms is not None for terms in (attack_terms, defense_terms, damage_terms)
    ):
        raise ExecutionError("Phase E cannot mix supplied combat dice with random_seed")

    before = copy.deepcopy(state)
    index = validate_combat_runtime_state(
        resolved, before, target_ref=binding["target_ref"]
    )
    if before.get("revision") != binding["required_revision"]:
        raise ExecutionError("Phase E bounded combat supports exactly one exchange")
    if index["unconscious"]["value"] is not False:
        raise ExecutionError("Phase E target is already unconscious")

    attack = _phase_e_attack_roll(
        resolved,
        attacker=attacker,
        binding=binding,
        attack_terms=attack_terms,
        random_seed=random_seed,
    )
    attack_class = attack["outcome"]["classification"]
    attack_success = attack["outcome"]["success"]

    defense = None
    damage = None
    state_delta = []
    injury_effects = {
        "major_wound": False,
        "stunned": index["stunned"]["value"],
        "remaining_hp": index["hit-points"]["value"],
        "consciousness_check_required": index["consciousness-check-required"]["value"],
        "unconscious": index["unconscious"]["value"],
        "deferred_recovery_phase": binding["injury_state"]["recovery_phase"],
        "consciousness_check_timing": binding["injury_state"]["consciousness_check_timing"],
    }
    after = copy.deepcopy(before)

    if not attack_success:
        outcome_branch = "attack-missed"
        reaction_window = {
            "opened": False,
            "reason": "attack-failed",
            **copy.deepcopy(binding["reaction_window"]),
        }
    else:
        critical_hit = attack_class == "critical-success"
        reaction_window = {
            "opened": not critical_hit,
            "reason": "critical-hit-bypasses-defense" if critical_hit else "successful-attack",
            **copy.deepcopy(binding["reaction_window"]),
        }
        defended = False
        if not critical_hit:
            defense = _phase_e_defense_roll(
                resolved,
                opponent=opponent,
                binding=binding,
                defense_terms=defense_terms,
                random_seed=random_seed,
            )
            defended = defense["outcome"]["success"]
        if defended:
            outcome_branch = "defended"
        else:
            outcome_branch = "hit"
            attack_total = attack["random_evidence"]["total"]
            if attack_total == binding["damage"]["critical_attack_total_three"]["attack_total"]:
                damage = _phase_e_maximum_damage(
                    resolved,
                    attacker=attacker,
                    opponent=opponent,
                    binding=binding,
                )
            else:
                damage = _phase_e_damage_roll(
                    resolved,
                    attacker=attacker,
                    opponent=opponent,
                    binding=binding,
                    damage_terms=damage_terms,
                    random_seed=random_seed,
                )
            after, state_delta, injury_effects = _apply_phase_e_injury(
                resolved,
                after,
                target_ref=binding["target_ref"],
                opponent=opponent,
                binding=binding,
                injury=damage["injury"],
            )

    after["revision"] = str(int(before["revision"]) + 1)
    validate_combat_runtime_state(
        resolved, after, target_ref=binding["target_ref"]
    )
    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    return {
        "format": binding["result_format"],
        "encounter_ref": encounter_ref,
        "action_id": action_id,
        "actor_ref": actor_ref,
        "target_ref": target_ref,
        "outcome_branch": outcome_branch,
        "random_mode": (
            {"kind": "generated-seeded-combat", "seed": str(random_seed)}
            if random_seed is not None
            else {"kind": "supplied-combat-terms"}
        ),
        "attack_resolution": attack,
        "reaction_window": reaction_window,
        "defense_resolution": defense,
        "damage_resolution": damage,
        "injury_effects": injury_effects,
        "state_before": before,
        "state_after": after,
        "state_delta": state_delta,
        "trace": {
            "combat_binding": {
                "ref": f"proto_sidecar.phase_e_combat_bindings.{encounter_ref}",
                "source_ref": binding["binding_source_ref"],
                "authority": sources[binding["binding_source_ref"]].get("authority"),
            },
            "scenario_source": {
                "source_ref": binding["scenario_source_ref"],
                "authority": sources[binding["scenario_source_ref"]].get("authority"),
            },
            "attack_rule": {
                "action_ref": binding["action_ref"],
                "procedure_ref": binding["procedure_ref"],
                "source_ref": "gurps-lite",
                "authority": sources["gurps-lite"].get("authority"),
            },
        },
    }


def replay_combat_exchange(resolved, record):
    if not isinstance(record, dict) or record.get("format") != PHASE_E_RESULT_FORMAT:
        raise ExecutionError("unsupported Phase E combat record format")
    kwargs = {
        "resolved": resolved,
        "state": copy.deepcopy(record.get("state_before")),
        "encounter_ref": record.get("encounter_ref"),
        "action_id": record.get("action_id"),
        "actor_ref": record.get("actor_ref"),
        "target_ref": record.get("target_ref"),
        "defense_kind": (
            (record.get("defense_resolution") or {}).get("kind") or "dodge"
        ),
    }
    random_mode = _require_mapping(record.get("random_mode"), "Phase E random_mode")
    if random_mode.get("kind") == "generated-seeded-combat":
        kwargs["random_seed"] = random_mode.get("seed")
    elif random_mode.get("kind") == "supplied-combat-terms":
        attack = _require_mapping(
            record.get("attack_resolution"), "Phase E attack_resolution"
        )
        kwargs["attack_terms"] = (attack.get("random_evidence") or {}).get("terms")
        defense = record.get("defense_resolution")
        if isinstance(defense, dict):
            kwargs["defense_terms"] = (defense.get("random_evidence") or {}).get("terms")
        damage = record.get("damage_resolution")
        if isinstance(damage, dict):
            kwargs["damage_terms"] = (damage.get("random_evidence") or {}).get("terms")
    else:
        raise ExecutionError("unsupported Phase E combat random mode")

    recomputed = execute_combat_exchange(**kwargs)
    if recomputed != record:
        raise ExecutionError("combat exchange record divergence detected")
    return recomputed


def _phase_f_binding(resolved, encounter_ref):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    bindings = _require_mapping(
        sidecar.get("phase_f_recovery_bindings"),
        "resolved phase_f_recovery_bindings",
    )
    binding = _require_mapping(
        bindings.get(encounter_ref), f"Phase F recovery binding {encounter_ref}"
    )
    expected_scalars = {
        "encounter_ref": encounter_ref,
        "action_id": "resolve-bandit-next-turn",
        "actor_ref": "bandit-scout",
        "action_ref": "recover",
        "procedure_ref": "recovery-check",
        "timing": "next-turn-start",
        "minimum_state_revision": 1,
        "ht_source": "encounter.opponent.attributes.ht",
        "dice_resolution_ref": "dice_resolution",
        "critical_resolution_ref": "phase_a_execution_bindings.attempt-skill.critical_resolution",
        "random_evidence_ref": "phase_a_execution_bindings.attempt-skill.random_evidence",
        "long_term_unconscious_recovery": "unsupported",
        "check_result_format": PHASE_F_CHECK_FORMAT,
        "result_format": PHASE_F_RESULT_FORMAT,
        "binding_source_ref": "dirps-proto",
        "scenario_source_ref": "scenario-01-source",
    }
    for key, expected in expected_scalars.items():
        if binding.get(key) != expected:
            raise ExecutionError(
                f"Phase F recovery binding {key} is unsupported or malformed"
            )
    if binding.get("resolution_order") != ["consciousness", "stun-recovery"]:
        raise ExecutionError("Phase F recovery resolution order is unsupported")
    if binding.get("consciousness") != {
        "hit_points_ref": "hit-points",
        "check_required_ref": "consciousness-check-required",
        "unconscious_ref": "unconscious",
        "will_modifier_source": "encounter.post_combat_recovery.consciousness.will_modifier",
        "success_effect_refs": [],
        "failure_effect_refs": [
            "phase-f-bandit-set-unconscious",
            "phase-f-bandit-clear-consciousness-check-required",
        ],
        "rule_source_ref": "gurps-lite",
        "rule_locator": "p. 27, General Damage / Unconsciousness",
    }:
        raise ExecutionError("Phase F consciousness binding is unsupported or malformed")
    if binding.get("stun_recovery") != {
        "stunned_ref": "stunned",
        "unconscious_ref": "unconscious",
        "success_effect_refs": ["phase-f-bandit-clear-stunned"],
        "failure_effect_refs": [],
        "rule_source_ref": "gurps-lite",
        "rule_locator": "p. 27, Stunning; p. 26, Knockdown and Stunning",
    }:
        raise ExecutionError("Phase F stun-recovery binding is unsupported or malformed")

    phase_a = _execution_binding(resolved)
    if binding["dice_resolution_ref"] != phase_a.get("dice_resolution_ref"):
        raise ExecutionError(
            "Phase F dice_resolution_ref disagrees with the accepted Phase A binding"
        )
    if binding["critical_resolution_ref"] != (
        "phase_a_execution_bindings.attempt-skill.critical_resolution"
    ):
        raise ExecutionError(
            "Phase F critical_resolution_ref is unsupported or malformed"
        )
    _require_mapping(
        phase_a.get("critical_resolution"),
        "Phase F referenced Phase A critical_resolution",
    )
    if binding["random_evidence_ref"] != (
        "phase_a_execution_bindings.attempt-skill.random_evidence"
    ):
        raise ExecutionError(
            "Phase F random_evidence_ref is unsupported or malformed"
        )
    _require_mapping(
        phase_a.get("random_evidence"),
        "Phase F referenced Phase A random_evidence",
    )
    return binding


def _phase_f_context(resolved, encounter_ref, binding):
    encounter = _encounter(resolved, encounter_ref)
    recovery = _require_mapping(
        encounter.get("post_combat_recovery"), "Phase F post_combat_recovery"
    )
    action = _require_mapping(recovery.get("action"), "Phase F recovery action")
    expected_action = {
        "id": binding["action_id"],
        "actor_ref": binding["actor_ref"],
        "action_ref": binding["action_ref"],
        "source_ref": "scenario-01-source",
        "authority": "provisional",
        "provenance": "prototype_assumption",
    }
    for key, expected in expected_action.items():
        if action.get(key) != expected:
            raise ExecutionError(f"Phase F recovery action {key} disagrees with binding")
    if recovery.get("timing") != binding["timing"]:
        raise ExecutionError("Phase F canonical recovery timing disagrees with binding")
    if recovery.get("resolution_order") != binding["resolution_order"]:
        raise ExecutionError("Phase F canonical recovery order disagrees with binding")
    if recovery.get("long_term_unconscious_recovery") != "unsupported":
        raise ExecutionError("Phase F long-term unconscious recovery must remain unsupported")

    consciousness = _require_mapping(
        recovery.get("consciousness"), "Phase F consciousness assumptions"
    )
    modifier = consciousness.get("will_modifier")
    if not isinstance(modifier, int) or isinstance(modifier, bool):
        raise ExecutionError("Phase F consciousness will modifier must be an integer")
    if (
        consciousness.get("modifier_source_ref") != "scenario-01-source"
        or consciousness.get("authority") != "provisional"
        or consciousness.get("provenance") != "prototype_assumption"
    ):
        raise ExecutionError("Phase F consciousness modifier provenance is malformed")

    opponent = _require_mapping(encounter.get("opponent"), "Phase F opponent")
    attrs = _require_mapping(opponent.get("attributes"), "Phase F opponent attributes")
    ht = attrs.get("ht")
    if not isinstance(ht, int) or isinstance(ht, bool) or ht < 1:
        raise ExecutionError("Phase F opponent HT must be a positive integer")

    actor = _actor(resolved, binding["actor_ref"])
    actor_state = _require_mapping(actor.get("state"), "Phase F resolved actor state")
    if actor_state.get("ht") != ht:
        raise ExecutionError("Phase F resolved actor HT disagrees with canonical opponent HT")

    rules = _require_mapping(resolved.get("rules"), "resolved rules")
    recover_action = _require_mapping(
        (rules.get("actions") or {}).get(binding["action_ref"]),
        "Phase F recover DODGE action",
    )
    if recover_action.get("procedure_ref") != binding["procedure_ref"]:
        raise ExecutionError("Phase F recover action/procedure binding disagrees")
    if binding["procedure_ref"] not in (rules.get("procedures") or {}):
        raise ExecutionError("Phase F recovery procedure is missing")
    return encounter, recovery, action, opponent, actor, ht, modifier


def _phase_f_state_requirements(resolved, state, binding):
    index = validate_combat_runtime_state(
        resolved, state, target_ref=binding["actor_ref"]
    )
    revision = int(state["revision"])
    if revision < binding["minimum_state_revision"]:
        raise ExecutionError(
            "Phase F requires the post-combat runtime state from Phase E"
        )

    consciousness = binding["consciousness"]
    stun = binding["stun_recovery"]
    hp = index[consciousness["hit_points_ref"]]["value"]
    check_required = index[consciousness["check_required_ref"]]["value"]
    unconscious = index[consciousness["unconscious_ref"]]["value"]
    stunned = index[stun["stunned_ref"]]["value"]

    if unconscious and check_required:
        raise ExecutionError(
            "Phase F state is inconsistent: unconscious actor cannot retain stay-conscious obligation"
        )
    if check_required and hp > 0:
        raise ExecutionError(
            "Phase F state is inconsistent: consciousness check is required only at HP <= 0"
        )
    if hp <= 0 and not unconscious and not check_required:
        raise ExecutionError(
            "Phase F state is inconsistent: conscious actor at HP <= 0 is missing the consciousness obligation"
        )

    consciousness_needed = bool(hp <= 0 and check_required and not unconscious)
    stun_needed = bool(stunned and not unconscious)
    return index, {
        "hit_points": hp,
        "consciousness_check_required": check_required,
        "unconscious": unconscious,
        "stunned": stunned,
        "consciousness_needed": consciousness_needed,
        "stun_needed": stun_needed,
    }


def _phase_f_roll(
    resolved,
    *,
    label,
    ht,
    modifier,
    terms,
    random_seed,
    binding,
    rule,
):
    target = ht + modifier
    if target < 3:
        raise ExecutionError(
            f"Phase F {label} effective HT target {target} is below supported minimum 3"
        )
    phase_a = _execution_binding(resolved)
    dice = _dice_contract(resolved, phase_a)
    if random_seed is not None:
        if terms is not None:
            raise ExecutionError(
                f"Phase F {label} cannot mix supplied dice with random_seed"
            )
        rolled, evidence_kind = _random_terms(
            dice_terms=None,
            random_seed=f"{random_seed}:phase-f:{label}",
            contract={"count": dice["count"], "sides": dice["sides"]},
            binding=phase_a,
        )
    else:
        if terms is None:
            raise ExecutionError(f"Phase F requires {label} dice evidence")
        rolled, evidence_kind = _random_terms(
            dice_terms=terms,
            random_seed=None,
            contract={"count": dice["count"], "sides": dice["sides"]},
            binding=phase_a,
        )

    total = sum(rolled)
    classification, success = _critical_classification(total, target, phase_a)
    return {
        "format": binding["check_result_format"],
        "check": label,
        "base_ht": ht,
        "modifier": modifier,
        "target": target,
        "random_evidence": {
            **evidence_kind,
            "dice_kind": dice["kind"],
            "sides": dice["sides"],
            "terms": rolled,
            "total": total,
        },
        "outcome": {
            "classification": classification,
            "success": success,
            "margin": target - total,
        },
        "trace": {
            "rule_source_ref": rule["rule_source_ref"],
            "rule_authority": "authoritative",
            "rule_locator": rule["rule_locator"],
            "dice_resolution_ref": binding["dice_resolution_ref"],
            "critical_resolution_ref": binding["critical_resolution_ref"],
            "random_evidence_ref": binding["random_evidence_ref"],
        },
    }


def _apply_phase_f_effect(resolved, state, index, *, target_ref, effect_ref):
    effects = _require_mapping(
        (resolved.get("rules") or {}).get("effects"), "resolved effects"
    )
    effect = _require_mapping(effects.get(effect_ref), f"Phase F effect {effect_ref}")
    if effect.get("op") != "set":
        raise ExecutionError(f"Phase F effect {effect_ref} must use set")
    if effect.get("subject") != {"instance_ref": target_ref}:
        raise ExecutionError(f"Phase F effect {effect_ref} targets the wrong actor")
    target_state_ref = effect.get("target_ref")
    row = index.get(target_state_ref)
    if not isinstance(row, dict):
        raise ExecutionError(
            f"Phase F effect {effect_ref} target binding is missing: {target_state_ref}"
        )
    definitions = _require_mapping(
        (resolved.get("rules") or {}).get("values"), "resolved value definitions"
    )
    definition = _require_mapping(
        definitions.get(target_state_ref), f"Phase F value definition {target_state_ref}"
    )
    value = effect.get("value")
    _validate_state_value(definition, value, target_state_ref)
    if effect.get("source_ref") not in {"gurps-lite", "dirps-proto"}:
        raise ExecutionError(f"Phase F effect {effect_ref} has unsupported source")
    expected_authority = (
        "authoritative" if effect["source_ref"] == "gurps-lite" else "provisional"
    )
    if effect.get("authority") != expected_authority:
        raise ExecutionError(f"Phase F effect {effect_ref} authority is malformed")

    before = row.get("value")
    row["value"] = copy.deepcopy(value)
    return {
        "effect_ref": effect_ref,
        "op": "set",
        "ref": target_state_ref,
        "subject": {"instance_ref": target_ref},
        "before": copy.deepcopy(before),
        "after": copy.deepcopy(value),
        "source_ref": effect.get("source_ref"),
        "authority": effect.get("authority"),
    }


def describe_recovery(resolved, state, *, encounter_ref):
    binding = _phase_f_binding(resolved, encounter_ref)
    encounter, recovery, action, opponent, actor, ht, modifier = _phase_f_context(
        resolved, encounter_ref, binding
    )
    index, status = _phase_f_state_requirements(resolved, state, binding)

    if status["unconscious"]:
        availability = []
        unsupported = "long-term-unconscious-recovery"
    else:
        needed = status["consciousness_needed"] or status["stun_needed"]
        availability = [
            {
                "id": action.get("id"),
                "label": action.get("label"),
                "actor_ref": action.get("actor_ref"),
                "action_ref": action.get("action_ref"),
                "timing": recovery.get("timing"),
                "source_ref": action.get("source_ref"),
                "authority": action.get("authority"),
                "provenance": action.get("provenance"),
            }
        ] if needed else []
        unsupported = None

    return {
        "encounter": {
            "id": encounter_ref,
            "type": encounter.get("type"),
            "purpose": encounter.get("purpose"),
        },
        "runtime_state_revision": state.get("revision"),
        "target_state": {ref: row["value"] for ref, row in index.items()},
        "available_actions": availability,
        "check_plan": {
            "timing": binding["timing"],
            "resolution_order": copy.deepcopy(binding["resolution_order"]),
            "consciousness": {
                "required": status["consciousness_needed"],
                "base_ht": ht,
                "will_modifier": modifier,
                "target": ht + modifier,
                "rule_source_ref": binding["consciousness"]["rule_source_ref"],
                "rule_locator": binding["consciousness"]["rule_locator"],
            },
            "stun_recovery": {
                "required": status["stun_needed"] and not status["unconscious"],
                "base_ht": ht,
                "target": ht,
                "rule_source_ref": binding["stun_recovery"]["rule_source_ref"],
                "rule_locator": binding["stun_recovery"]["rule_locator"],
            },
        },
        "unsupported": unsupported,
        "result_format": binding["result_format"],
    }


def execute_recovery(
    resolved,
    state,
    *,
    encounter_ref,
    action_id,
    actor_ref,
    consciousness_terms=None,
    stun_terms=None,
    random_seed=None,
):
    binding = _phase_f_binding(resolved, encounter_ref)
    encounter, recovery, action, opponent, actor, ht, modifier = _phase_f_context(
        resolved, encounter_ref, binding
    )
    if action_id != binding["action_id"]:
        raise ExecutionError(f"unsupported Phase F recovery action: {action_id}")
    if actor_ref != binding["actor_ref"] or actor_ref != action.get("actor_ref"):
        raise ExecutionError("Phase F recovery actor selection is unsupported")
    if random_seed is not None and (
        consciousness_terms is not None or stun_terms is not None
    ):
        raise ExecutionError(
            "Phase F cannot mix supplied recovery dice with random_seed"
        )

    before = copy.deepcopy(state)
    index, status = _phase_f_state_requirements(resolved, before, binding)
    if status["unconscious"]:
        raise ExecutionError(
            "Phase F long-term recovery from unconsciousness is unsupported"
        )
    if not status["consciousness_needed"] and not status["stun_needed"]:
        raise ExecutionError("Phase F recovery action is unavailable in current state")
    if not status["consciousness_needed"] and consciousness_terms is not None:
        raise ExecutionError("Phase F consciousness dice were supplied for a skipped check")

    after = copy.deepcopy(before)
    after_index = validate_combat_runtime_state(
        resolved, after, target_ref=binding["actor_ref"]
    )
    delta = []
    consciousness_result = None
    stun_result = None
    skipped = []

    if status["consciousness_needed"]:
        consciousness_result = _phase_f_roll(
            resolved,
            label="consciousness",
            ht=ht,
            modifier=modifier,
            terms=consciousness_terms,
            random_seed=random_seed,
            binding=binding,
            rule=binding["consciousness"],
        )
        if not consciousness_result["outcome"]["success"]:
            for effect_ref in binding["consciousness"]["failure_effect_refs"]:
                delta.append(
                    _apply_phase_f_effect(
                        resolved,
                        after,
                        after_index,
                        target_ref=binding["actor_ref"],
                        effect_ref=effect_ref,
                    )
                )
            if stun_terms is not None:
                raise ExecutionError(
                    "Phase F stun-recovery dice were supplied after a failed consciousness check"
                )
            skipped.append(
                {
                    "check": "stun-recovery",
                    "reason": "actor-fell-unconscious",
                }
            )
        else:
            # The obligation persists while HP remains <= 0; there is no
            # success effect that clears consciousness-check-required.
            pass
    else:
        skipped.append(
            {
                "check": "consciousness",
                "reason": "consciousness-check-not-required",
            }
        )

    current_unconscious = after_index[binding["consciousness"]["unconscious_ref"]]["value"]
    current_stunned = after_index[binding["stun_recovery"]["stunned_ref"]]["value"]
    if not current_unconscious and current_stunned:
        stun_result = _phase_f_roll(
            resolved,
            label="stun-recovery",
            ht=ht,
            modifier=0,
            terms=stun_terms,
            random_seed=random_seed,
            binding=binding,
            rule=binding["stun_recovery"],
        )
        if stun_result["outcome"]["success"]:
            for effect_ref in binding["stun_recovery"]["success_effect_refs"]:
                delta.append(
                    _apply_phase_f_effect(
                        resolved,
                        after,
                        after_index,
                        target_ref=binding["actor_ref"],
                        effect_ref=effect_ref,
                    )
                )
    elif not current_unconscious:
        if stun_terms is not None:
            raise ExecutionError("Phase F stun-recovery dice were supplied for a skipped check")
        skipped.append(
            {
                "check": "stun-recovery",
                "reason": "actor-not-stunned",
            }
        )

    after["revision"] = str(int(before["revision"]) + 1)
    final_index, final_status = _phase_f_state_requirements(
        resolved, after, binding
    )
    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    return {
        "format": binding["result_format"],
        "encounter_ref": encounter_ref,
        "action_id": action_id,
        "actor_ref": actor_ref,
        "timing": binding["timing"],
        "resolution_order": copy.deepcopy(binding["resolution_order"]),
        "random_mode": (
            {"kind": "generated-seeded-recovery", "seed": str(random_seed)}
            if random_seed is not None
            else {"kind": "supplied-recovery-terms"}
        ),
        "consciousness_check": consciousness_result,
        "stun_recovery_check": stun_result,
        "skipped_checks": skipped,
        "outcome": {
            "unconscious": final_status["unconscious"],
            "stunned": final_status["stunned"],
            "consciousness_check_required": final_status[
                "consciousness_check_required"
            ],
            "can_act_normally": (
                not final_status["unconscious"] and not final_status["stunned"]
            ),
        },
        "state_before": before,
        "state_after": after,
        "state_delta": delta,
        "trace": {
            "recovery_binding": {
                "ref": f"proto_sidecar.phase_f_recovery_bindings.{encounter_ref}",
                "source_ref": binding["binding_source_ref"],
                "authority": sources[binding["binding_source_ref"]].get("authority"),
            },
            "scenario_source": {
                "source_ref": binding["scenario_source_ref"],
                "authority": sources[binding["scenario_source_ref"]].get("authority"),
            },
            "ht_source": {
                "path": binding["ht_source"],
                "value": ht,
                "source_ref": binding["scenario_source_ref"],
                "authority": sources[binding["scenario_source_ref"]].get("authority"),
            },
            "consciousness_modifier": {
                "value": modifier,
                "path": binding["consciousness"]["will_modifier_source"],
                "source_ref": recovery["consciousness"]["modifier_source_ref"],
                "authority": recovery["consciousness"]["authority"],
                "provenance": recovery["consciousness"]["provenance"],
            },
        },
    }


def replay_recovery(resolved, record):
    if not isinstance(record, dict) or record.get("format") != PHASE_F_RESULT_FORMAT:
        raise ExecutionError("unsupported Phase F recovery record format")
    kwargs = {
        "resolved": resolved,
        "state": copy.deepcopy(record.get("state_before")),
        "encounter_ref": record.get("encounter_ref"),
        "action_id": record.get("action_id"),
        "actor_ref": record.get("actor_ref"),
    }
    random_mode = _require_mapping(record.get("random_mode"), "Phase F random_mode")
    if random_mode.get("kind") == "generated-seeded-recovery":
        kwargs["random_seed"] = random_mode.get("seed")
    elif random_mode.get("kind") == "supplied-recovery-terms":
        consciousness = record.get("consciousness_check")
        stun = record.get("stun_recovery_check")
        if isinstance(consciousness, dict):
            kwargs["consciousness_terms"] = (
                consciousness.get("random_evidence") or {}
            ).get("terms")
        if isinstance(stun, dict):
            kwargs["stun_terms"] = (stun.get("random_evidence") or {}).get("terms")
    else:
        raise ExecutionError("unsupported Phase F recovery random mode")

    recomputed = execute_recovery(**kwargs)
    if recomputed != record:
        raise ExecutionError("recovery record divergence detected")
    return recomputed


def _phase_g_binding(resolved):
    sidecar = _require_mapping(resolved.get("proto_sidecar"), "resolved proto_sidecar")
    bindings = _require_mapping(
        sidecar.get("phase_g_progression_bindings"),
        "resolved phase_g_progression_bindings",
    )
    binding = _require_mapping(
        bindings.get("scenario-01"), "Phase G scenario progression binding"
    )
    if binding.get("scenario_ref") != "scenario-01":
        raise ExecutionError("Phase G scenario_ref is unsupported")
    if binding.get("runtime_state_ref") != "scenario-01-playable-initial":
        raise ExecutionError("Phase G playable runtime_state_ref is unsupported")
    if binding.get("encounter_order_source") != "scenario.encounters":
        raise ExecutionError("Phase G encounter-order source binding is malformed")
    if binding.get("progress_refs") != {
        "status": "scenario-progress-status",
        "current_encounter": "scenario-current-encounter",
        "step": "scenario-progress-step",
        "outcome": "scenario-outcome",
        "information": "scenario-completion-information",
    }:
        raise ExecutionError("Phase G progress refs are unsupported or malformed")
    if binding.get("phase_runtime_state_refs") != {
        "roadside-tracks": "scenario-01-initial",
        "frightened-witness": "scenario-01-frightened-witness-initial",
        "washed-out-path": "scenario-01-washed-out-path-initial",
        "bandit-scout": "scenario-01-bandit-scout-initial",
    }:
        raise ExecutionError("Phase G phase runtime-state bridge is malformed")
    if binding.get("advance_effect_refs") != {
        "frightened-witness": "phase-g-current-frightened-witness",
        "washed-out-path": "phase-g-current-washed-out-path",
        "bandit-scout": "phase-g-current-bandit-scout",
    }:
        raise ExecutionError("Phase G advance-effect bridge is malformed")
    if binding.get("recovery_effect_ref") != "phase-g-step-recovery":
        raise ExecutionError("Phase G recovery transition is malformed")
    if binding.get("terminal_effect_refs") != {
        "success": [
            "phase-g-status-complete",
            "phase-g-current-complete",
            "phase-g-step-complete",
            "phase-g-outcome-success",
            "phase-g-information-success",
        ],
        "failure": [
            "phase-g-status-complete",
            "phase-g-current-complete",
            "phase-g-step-complete",
            "phase-g-outcome-failure",
            "phase-g-information-failure",
        ],
    }:
        raise ExecutionError("Phase G terminal-effect bridge is malformed")
    if (
        binding.get("completion_condition_ref") != "scenario-success"
        or binding.get("failure_condition_ref") != "scenario-failure"
        or binding.get("result_format") != PHASE_G_RESULT_FORMAT
        or binding.get("binding_source_ref") != "dirps-proto"
        or binding.get("scenario_source_ref") != "scenario-01-source"
    ):
        raise ExecutionError("Phase G result/authority binding is malformed")

    states = _require_mapping(resolved.get("runtime_states"), "resolved runtime_states")
    for state_ref in [
        binding["runtime_state_ref"],
        *binding["phase_runtime_state_refs"].values(),
    ]:
        _require_mapping(states.get(state_ref), f"Phase G runtime state {state_ref}")
    effects = _require_mapping((resolved.get("rules") or {}).get("effects"), "resolved effects")
    effect_refs = list(binding["advance_effect_refs"].values())
    effect_refs.append(binding["recovery_effect_ref"])
    for rows in binding["terminal_effect_refs"].values():
        effect_refs.extend(rows)
    for effect_ref in effect_refs:
        _require_mapping(effects.get(effect_ref), f"Phase G effect {effect_ref}")
    conditions = _require_mapping(
        (resolved.get("rules") or {}).get("conditions"), "resolved conditions"
    )
    _require_mapping(
        conditions.get(binding["completion_condition_ref"]),
        "Phase G completion condition",
    )
    _require_mapping(
        conditions.get(binding["failure_condition_ref"]),
        "Phase G failure condition",
    )
    return binding


def _phase_g_validate_completion_contract(resolved, binding, completion):
    refs = binding["progress_refs"]
    expected = {
        "success": {
            "trigger": {
                "encounter_ref": "bandit-scout",
                "bandit_can_act_normally": False,
            },
            "state": {
                "status": "complete",
                "current_encounter": "complete",
                "step": "complete",
                "outcome": "success",
                "information": "courier-fate-established",
            },
            "condition_ref": binding["completion_condition_ref"],
            "end_condition": {
                "id": "missing-courier-success",
                "outcome": "win",
                "condition": binding["completion_condition_ref"],
                "priority": 1,
            },
        },
        "failure": {
            "trigger": {
                "encounter_ref": "bandit-scout",
                "bandit_can_act_normally": True,
            },
            "state": {
                "status": "complete",
                "current_encounter": "complete",
                "step": "complete",
                "outcome": "failure",
                "information": "courier-fate-unresolved",
            },
            "condition_ref": binding["failure_condition_ref"],
            "end_condition": {
                "id": "missing-courier-failure",
                "outcome": "loss",
                "condition": binding["failure_condition_ref"],
                "priority": 2,
            },
        },
    }
    effects = _require_mapping(
        (resolved.get("rules") or {}).get("effects"), "resolved effects"
    )
    conditions = _require_mapping(
        (resolved.get("rules") or {}).get("conditions"), "resolved conditions"
    )
    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    end_conditions = scenario.get("end_conditions")
    if not isinstance(end_conditions, list):
        raise ExecutionError("Phase G scenario end_conditions must be a list")

    for branch, expected_branch in expected.items():
        row = _require_mapping(
            completion.get(branch), f"Phase G canonical {branch} completion branch"
        )
        if row.get("trigger") != expected_branch["trigger"]:
            raise ExecutionError(
                f"Phase G canonical {branch} completion trigger is unsupported or drifted"
            )
        state = _require_mapping(
            row.get("state"), f"Phase G canonical {branch} terminal state"
        )
        if state != expected_branch["state"]:
            raise ExecutionError(
                f"Phase G canonical {branch} terminal state is unsupported or drifted"
            )
        if not isinstance(row.get("conclusion_text"), str) or not row.get(
            "conclusion_text"
        ):
            raise ExecutionError(
                f"Phase G canonical {branch} completion conclusion is missing"
            )

        expected_by_ref = {
            refs[role]: state[role]
            for role in ("status", "current_encounter", "step", "outcome", "information")
        }
        effect_refs = binding["terminal_effect_refs"].get(branch)
        if not isinstance(effect_refs, list):
            raise ExecutionError(
                f"Phase G {branch} terminal-effect bridge is malformed"
            )
        seen_targets = set()
        for effect_ref in effect_refs:
            effect = _require_mapping(
                effects.get(effect_ref), f"Phase G {branch} terminal effect {effect_ref}"
            )
            target_ref = effect.get("target_ref")
            if (
                effect.get("op") != "set"
                or effect.get("subject") != {"relative": "scenario"}
                or effect.get("source_ref") != binding["scenario_source_ref"]
                or effect.get("authority") != "provisional"
                or target_ref not in expected_by_ref
                or effect.get("value") != expected_by_ref.get(target_ref)
            ):
                raise ExecutionError(
                    f"Phase G {branch} terminal state/effect alignment drifted"
                )
            if target_ref in seen_targets:
                raise ExecutionError(
                    f"Phase G {branch} terminal effects duplicate state target {target_ref}"
                )
            seen_targets.add(target_ref)
        if seen_targets != set(expected_by_ref):
            raise ExecutionError(
                f"Phase G {branch} terminal effects do not cover canonical terminal state"
            )

        condition_ref = expected_branch["condition_ref"]
        condition = _require_mapping(
            conditions.get(condition_ref),
            f"Phase G {branch} terminal condition {condition_ref}",
        )
        if (
            condition.get("op") != "eq"
            or condition.get("left")
            != {"ref": refs["outcome"], "subject": {"relative": "scenario"}}
            or condition.get("right") != state["outcome"]
            or condition.get("source_ref") != binding["scenario_source_ref"]
            or condition.get("authority") != "provisional"
        ):
            raise ExecutionError(
                f"Phase G {branch} terminal state/condition alignment drifted"
            )

        matches = [
            end_condition
            for end_condition in end_conditions
            if isinstance(end_condition, dict)
            and end_condition.get("condition") == condition_ref
        ]
        if matches != [expected_branch["end_condition"]]:
            raise ExecutionError(
                f"Phase G {branch} end-condition bridge is unsupported or drifted"
            )


def _phase_g_progression(resolved, binding):
    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    progression = _require_mapping(
        scenario.get("progression"), "resolved Scenario 01 progression"
    )
    if (
        progression.get("source_ref") != binding["scenario_source_ref"]
        or progression.get("authority") != "provisional"
        or progression.get("provenance") != "prototype_assumption"
        or progression.get("runtime_state_ref") != binding["runtime_state_ref"]
    ):
        raise ExecutionError("Phase G canonical progression authority is malformed")
    order = [
        row.get("id")
        for row in scenario.get("encounters", [])
        if isinstance(row, dict) and row.get("id")
    ]
    if (
        len(order) != len(set(order))
        or not order
        or order[0] != "roadside-tracks"
        or order[-1] != "bandit-scout"
    ):
        raise ExecutionError("Phase G encounter order is unsupported or malformed")
    contract = _require_mapping(
        progression.get("state_contract"), "Phase G progress state_contract"
    )
    if contract.get("refs") != binding["progress_refs"]:
        raise ExecutionError("Phase G canonical/DODGE progress refs disagree")
    completion = _require_mapping(
        progression.get("completion"), "Phase G completion semantics"
    )
    if completion.get("objective_id") != "resolve-courier-mystery":
        raise ExecutionError("Phase G objective identity is unsupported")
    _phase_g_validate_completion_contract(resolved, binding, completion)
    return progression, order, completion


def _phase_g_terminal_branch(completion, *, encounter_ref, can_act_normally):
    if not isinstance(can_act_normally, bool):
        raise ExecutionError("Phase G terminal actor capability must be boolean")
    matches = []
    for branch in ("success", "failure"):
        row = _require_mapping(
            completion.get(branch), f"Phase G canonical {branch} completion branch"
        )
        trigger = _require_mapping(
            row.get("trigger"), f"Phase G canonical {branch} completion trigger"
        )
        if (
            trigger.get("encounter_ref") == encounter_ref
            and trigger.get("bandit_can_act_normally") is can_act_normally
        ):
            matches.append(branch)
    if len(matches) != 1:
        raise ExecutionError(
            "Phase G canonical completion trigger does not select exactly one terminal branch"
        )
    return matches[0]


def _phase_g_binding_key(row):
    subject = _require_mapping(row.get("subject"), "Phase G state binding subject")
    return row.get("ref"), tuple(sorted(subject.items()))


def validate_scenario_runtime_state(resolved, state):
    if not isinstance(state, dict):
        raise ExecutionError("Phase G scenario runtime state must be an object")
    binding = _phase_g_binding(resolved)
    progression, order, completion = _phase_g_progression(resolved, binding)
    if state.get("scenario_ref") != binding["scenario_ref"]:
        raise ExecutionError("Phase G scenario runtime state has wrong scenario_ref")
    revision = state.get("revision")
    if not isinstance(revision, str):
        raise ExecutionError("Phase G scenario runtime revision must be a string")
    try:
        revision_number = int(revision)
    except ValueError as exc:
        raise ExecutionError("Phase G scenario runtime revision must be an integer string") from exc
    if revision_number < 0:
        raise ExecutionError("Phase G scenario runtime revision cannot be negative")
    if state.get("events") != []:
        raise ExecutionError(
            "Phase G does not implement append-only session events; events must remain empty"
        )

    states = _require_mapping(resolved.get("runtime_states"), "resolved runtime_states")
    template = _require_mapping(
        states.get(binding["runtime_state_ref"]), "Phase G playable runtime template"
    )
    expected_rows = {}
    for row in template.get("bindings", []):
        key = _phase_g_binding_key(row)
        if key in expected_rows:
            raise ExecutionError("Phase G playable runtime template has duplicate bindings")
        expected_rows[key] = row

    actual_rows = {}
    for row in state.get("bindings", []):
        if not isinstance(row, dict):
            raise ExecutionError("Phase G state bindings must be objects")
        key = _phase_g_binding_key(row)
        if key in actual_rows:
            raise ExecutionError(f"Phase G duplicate runtime binding: {row.get('ref')}")
        actual_rows[key] = row
    if set(actual_rows) != set(expected_rows):
        raise ExecutionError("Phase G runtime state bindings do not match the playable template")

    definitions = _require_mapping(
        (resolved.get("rules") or {}).get("values"), "resolved value definitions"
    )
    index = {}
    for key, row in actual_rows.items():
        expected = expected_rows[key]
        ref = row.get("ref")
        if row.get("authority") != expected.get("authority"):
            raise ExecutionError(f"Phase G runtime binding {ref} authority drifted")
        definition = _require_mapping(
            definitions.get(ref), f"Phase G value definition {ref}"
        )
        _validate_state_value(definition, row.get("value"), ref)
        if ref in index:
            raise ExecutionError(f"Phase G runtime ref is ambiguous: {ref}")
        index[ref] = row

    refs = binding["progress_refs"]
    status = _state_value(index, refs["status"])
    current = _state_value(index, refs["current_encounter"])
    step = _state_value(index, refs["step"])
    outcome = _state_value(index, refs["outcome"])
    information = _state_value(index, refs["information"])
    if status == "in-progress":
        if current not in order:
            raise ExecutionError("Phase G current encounter is outside canonical order")
        if outcome != "undetermined" or information != "accumulating":
            raise ExecutionError("Phase G in-progress state cannot already have terminal outcome")
        if step not in {"action", "recovery"}:
            raise ExecutionError("Phase G in-progress step is unsupported")
        if step == "recovery" and current != "bandit-scout":
            raise ExecutionError("Phase G recovery step is only supported for bandit-scout")
    elif status == "complete":
        if current != "complete" or step != "complete":
            raise ExecutionError("Phase G terminal state must use complete encounter/step")
        if outcome == "success":
            expected_information = completion["success"]["state"]["information"]
        elif outcome == "failure":
            expected_information = completion["failure"]["state"]["information"]
        else:
            raise ExecutionError("Phase G terminal outcome must be success or failure")
        if information != expected_information:
            raise ExecutionError("Phase G terminal information disagrees with canonical completion")
    else:
        raise ExecutionError("Phase G scenario progress status is unsupported")
    return index


def create_scenario_runtime_state(resolved):
    binding = _phase_g_binding(resolved)
    states = _require_mapping(resolved.get("runtime_states"), "resolved runtime_states")
    state = copy.deepcopy(states[binding["runtime_state_ref"]])
    validate_scenario_runtime_state(resolved, state)
    return state


def _phase_g_project_state(resolved, state, *, encounter_ref, step):
    binding = _phase_g_binding(resolved)
    state_ref = binding["phase_runtime_state_refs"].get(encounter_ref)
    if not state_ref:
        raise ExecutionError(f"Phase G encounter has no phase runtime state: {encounter_ref}")
    states = _require_mapping(resolved.get("runtime_states"), "resolved runtime_states")
    template = _require_mapping(states.get(state_ref), f"Phase G phase state {state_ref}")
    full_rows = {_phase_g_binding_key(row): row for row in state["bindings"]}
    bindings = []
    for template_row in template.get("bindings", []):
        key = _phase_g_binding_key(template_row)
        row = full_rows.get(key)
        if not isinstance(row, dict):
            raise ExecutionError(
                f"Phase G unified state is missing phase binding: {template_row.get('ref')}"
            )
        bindings.append(copy.deepcopy(row))
    revision = template.get("revision", "0")
    if encounter_ref == "bandit-scout" and step == "recovery":
        revision = "1"
    return {
        "scenario_ref": binding["scenario_ref"],
        "bindings": bindings,
        "events": [],
        "revision": revision,
    }


def _phase_g_merge_mechanic_state(after, mechanic_state):
    rows = {_phase_g_binding_key(row): row for row in after["bindings"]}
    for row in mechanic_state.get("bindings", []):
        key = _phase_g_binding_key(row)
        target = rows.get(key)
        if not isinstance(target, dict):
            raise ExecutionError(
                f"Phase G mechanic result introduced unknown state binding: {row.get('ref')}"
            )
        target["value"] = copy.deepcopy(row.get("value"))


def _apply_phase_g_effect(resolved, state, state_index, effect_ref):
    effects = _require_mapping(
        (resolved.get("rules") or {}).get("effects"), "resolved effects"
    )
    effect = _require_mapping(effects.get(effect_ref), f"Phase G effect {effect_ref}")
    if (
        effect.get("op") != "set"
        or effect.get("subject") != {"relative": "scenario"}
        or effect.get("source_ref") != "scenario-01-source"
        or effect.get("authority") != "provisional"
    ):
        raise ExecutionError(f"Phase G effect is unsupported or malformed: {effect_ref}")
    target_ref = effect.get("target_ref")
    row = state_index.get(target_ref)
    if not isinstance(row, dict):
        raise ExecutionError(f"Phase G effect target is missing: {target_ref}")
    definitions = _require_mapping(
        (resolved.get("rules") or {}).get("values"), "resolved value definitions"
    )
    definition = _require_mapping(
        definitions.get(target_ref), f"Phase G value definition {target_ref}"
    )
    value = effect.get("value")
    _validate_state_value(definition, value, target_ref)
    before = copy.deepcopy(row.get("value"))
    row["value"] = copy.deepcopy(value)
    return {
        "effect_ref": effect_ref,
        "op": "set",
        "ref": target_ref,
        "subject": {"relative": "scenario"},
        "before": before,
        "after": copy.deepcopy(value),
        "source_ref": effect.get("source_ref"),
        "authority": effect.get("authority"),
    }


def _phase_g_condition_matches(resolved, state_index, condition_ref):
    conditions = _require_mapping(
        (resolved.get("rules") or {}).get("conditions"), "resolved conditions"
    )
    condition = _require_mapping(
        conditions.get(condition_ref), f"Phase G condition {condition_ref}"
    )
    left = _require_mapping(condition.get("left"), f"Phase G condition {condition_ref} left")
    if (
        condition.get("op") != "eq"
        or left.get("subject") != {"relative": "scenario"}
        or condition.get("source_ref") != "scenario-01-source"
        or condition.get("authority") != "provisional"
    ):
        raise ExecutionError(f"Phase G terminal condition is unsupported: {condition_ref}")
    ref = left.get("ref")
    row = state_index.get(ref)
    if not isinstance(row, dict):
        raise ExecutionError(f"Phase G terminal condition binding is missing: {ref}")
    return row.get("value") == condition.get("right")


def _phase_g_retained_state(resolved, state_index):
    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    retained = {}
    for encounter in scenario.get("encounters", []):
        if not isinstance(encounter, dict):
            continue
        encounter_ref = encounter.get("id")
        state_contract = encounter.get("state_contract")
        if isinstance(state_contract, dict):
            refs = _require_mapping(
                state_contract.get("refs"), f"Phase G {encounter_ref} state refs"
            )
            retained[encounter_ref] = {
                role: _state_value(state_index, ref)
                for role, ref in refs.items()
            }
    retained["bandit-scout"] = {
        ref: _state_value(state_index, ref)
        for ref in (
            "hit-points",
            "stunned",
            "unconscious",
            "consciousness-check-required",
        )
    }
    return retained


def describe_scenario(resolved, state):
    binding = _phase_g_binding(resolved)
    progression, order, completion = _phase_g_progression(resolved, binding)
    index = validate_scenario_runtime_state(resolved, state)
    refs = binding["progress_refs"]
    progress = {
        role: _state_value(index, ref)
        for role, ref in refs.items()
    }
    current = progress["current_encounter"]
    step = progress["step"]
    capability = None
    available_actions = []
    if progress["status"] == "in-progress":
        projected = _phase_g_project_state(
            resolved, state, encounter_ref=current, step=step
        )
        if current == "roadside-tracks":
            capability = describe_investigation(
                resolved, projected, encounter_ref=current
            )
        elif current == "frightened-witness":
            capability = describe_social_interaction(
                resolved, projected, encounter_ref=current
            )
        elif current == "washed-out-path":
            capability = describe_environment_challenge(
                resolved, projected, encounter_ref=current
            )
        elif current == "bandit-scout" and step == "action":
            capability = describe_combat_exchange(
                resolved, projected, encounter_ref=current
            )
        elif current == "bandit-scout" and step == "recovery":
            capability = describe_recovery(
                resolved, projected, encounter_ref=current
            )
        else:
            raise ExecutionError(
                f"Phase G has no supported runtime path for {current}/{step}"
            )
        available_actions = copy.deepcopy(capability.get("available_actions", []))

    return {
        "scenario_ref": binding["scenario_ref"],
        "title": _require_mapping(resolved.get("scenario"), "resolved scenario").get("name"),
        "runtime_state_revision": state.get("revision"),
        "encounter_order": copy.deepcopy(order),
        "progress": progress,
        "retained_state": _phase_g_retained_state(resolved, index),
        "available_actions": available_actions,
        "current_capability": capability,
        "completion": {
            "objective_id": completion.get("objective_id"),
            "success_condition_ref": binding["completion_condition_ref"],
            "failure_condition_ref": binding["failure_condition_ref"],
        },
        "unsupported": copy.deepcopy(progression.get("unsupported", [])),
        "result_format": binding["result_format"],
    }


def _phase_g_random_inputs(random_inputs, allowed):
    if random_inputs is None:
        return {}
    if not isinstance(random_inputs, dict):
        raise ExecutionError("Phase G random_inputs must be an object")
    unexpected = sorted(set(random_inputs) - set(allowed))
    if unexpected:
        raise ExecutionError(
            f"Phase G random_inputs contain unsupported keys: {unexpected}"
        )
    return copy.deepcopy(random_inputs)


def _phase_g_end_condition_id(resolved, condition_ref):
    scenario = _require_mapping(resolved.get("scenario"), "resolved scenario")
    matches = [
        row.get("id")
        for row in scenario.get("end_conditions", [])
        if isinstance(row, dict) and row.get("condition") == condition_ref
    ]
    if len(matches) != 1:
        raise ExecutionError(
            f"Phase G terminal condition must map to exactly one end condition: {condition_ref}"
        )
    return matches[0]


def execute_scenario_action(
    resolved,
    state,
    *,
    action_id,
    actor_ref,
    random_inputs=None,
):
    binding = _phase_g_binding(resolved)
    progression, order, completion = _phase_g_progression(resolved, binding)
    before = copy.deepcopy(state)
    description = describe_scenario(resolved, before)
    if description["progress"]["status"] != "in-progress":
        raise ExecutionError("Phase G scenario is already complete")
    actions = description["available_actions"]
    selected = next(
        (
            row
            for row in actions
            if row.get("id") == action_id and row.get("actor_ref") == actor_ref
        ),
        None,
    )
    if not isinstance(selected, dict):
        raise ExecutionError(
            f"Phase G action is unavailable or out of order: {action_id}/{actor_ref}"
        )

    current = description["progress"]["current_encounter"]
    step = description["progress"]["step"]
    projected = _phase_g_project_state(
        resolved, before, encounter_ref=current, step=step
    )
    if current == "roadside-tracks":
        inputs = _phase_g_random_inputs(random_inputs, {"dice_terms", "random_seed"})
        mechanic = execute_investigation(
            resolved,
            projected,
            encounter_ref=current,
            action_id=action_id,
            actor_ref=actor_ref,
            dice_terms=inputs.get("dice_terms"),
            random_seed=inputs.get("random_seed"),
        )
    elif current == "frightened-witness":
        inputs = _phase_g_random_inputs(random_inputs, {"dice_terms", "random_seed"})
        mechanic = execute_social_interaction(
            resolved,
            projected,
            encounter_ref=current,
            action_id=action_id,
            actor_ref=actor_ref,
            dice_terms=inputs.get("dice_terms"),
            random_seed=inputs.get("random_seed"),
        )
    elif current == "washed-out-path":
        inputs = _phase_g_random_inputs(random_inputs, {"dice_terms", "random_seed"})
        mechanic = execute_environment_challenge(
            resolved,
            projected,
            encounter_ref=current,
            action_id=action_id,
            actor_ref=actor_ref,
            dice_terms=inputs.get("dice_terms"),
            random_seed=inputs.get("random_seed"),
        )
    elif current == "bandit-scout" and step == "action":
        inputs = _phase_g_random_inputs(
            random_inputs,
            {"attack_terms", "defense_terms", "damage_terms", "random_seed"},
        )
        combat_binding = _phase_e_binding(resolved, current)
        mechanic = execute_combat_exchange(
            resolved,
            projected,
            encounter_ref=current,
            action_id=action_id,
            actor_ref=actor_ref,
            target_ref=combat_binding["target_ref"],
            defense_kind=combat_binding["defense"]["kind"],
            attack_terms=inputs.get("attack_terms"),
            defense_terms=inputs.get("defense_terms"),
            damage_terms=inputs.get("damage_terms"),
            random_seed=inputs.get("random_seed"),
        )
    elif current == "bandit-scout" and step == "recovery":
        inputs = _phase_g_random_inputs(
            random_inputs,
            {"consciousness_terms", "stun_terms", "random_seed"},
        )
        mechanic = execute_recovery(
            resolved,
            projected,
            encounter_ref=current,
            action_id=action_id,
            actor_ref=actor_ref,
            consciousness_terms=inputs.get("consciousness_terms"),
            stun_terms=inputs.get("stun_terms"),
            random_seed=inputs.get("random_seed"),
        )
    else:
        raise ExecutionError(f"Phase G cannot execute {current}/{step}")

    after = copy.deepcopy(before)
    _phase_g_merge_mechanic_state(after, mechanic["state_after"])
    after_index = validate_scenario_runtime_state(resolved, after)
    progress_delta = []
    terminal_branch = None
    next_encounter = current

    if current != "bandit-scout":
        position = order.index(current)
        if position + 1 >= len(order):
            raise ExecutionError("Phase G noncombat encounter cannot terminate canonical order")
        next_encounter = order[position + 1]
        effect_ref = binding["advance_effect_refs"].get(next_encounter)
        if not effect_ref:
            raise ExecutionError(
                f"Phase G has no normalized advance effect for {next_encounter}"
            )
        progress_delta.append(
            _apply_phase_g_effect(resolved, after, after_index, effect_ref)
        )
    elif step == "action":
        unconscious = _state_value(after_index, "unconscious")
        stunned = _state_value(after_index, "stunned")
        consciousness_required = _state_value(
            after_index, "consciousness-check-required"
        )
        if not unconscious and (stunned or consciousness_required):
            progress_delta.append(
                _apply_phase_g_effect(
                    resolved, after, after_index, binding["recovery_effect_ref"]
                )
            )
        else:
            terminal_branch = _phase_g_terminal_branch(
                completion,
                encounter_ref=current,
                can_act_normally=(
                    not unconscious and not stunned and not consciousness_required
                ),
            )
    else:
        recovery_outcome = _require_mapping(
            mechanic.get("outcome"), "Phase G recovery outcome"
        )
        can_act_normally = recovery_outcome.get("can_act_normally")
        terminal_branch = _phase_g_terminal_branch(
            completion,
            encounter_ref=current,
            can_act_normally=can_act_normally,
        )

    if terminal_branch is not None:
        for effect_ref in binding["terminal_effect_refs"][terminal_branch]:
            progress_delta.append(
                _apply_phase_g_effect(
                    resolved, after, after_index, effect_ref
                )
            )
        next_encounter = "complete"

    after["revision"] = str(int(before["revision"]) + 1)
    final_index = validate_scenario_runtime_state(resolved, after)
    success_match = _phase_g_condition_matches(
        resolved, final_index, binding["completion_condition_ref"]
    )
    failure_match = _phase_g_condition_matches(
        resolved, final_index, binding["failure_condition_ref"]
    )
    if success_match and failure_match:
        raise ExecutionError("Phase G success and failure conditions cannot both match")
    if terminal_branch == "success" and not success_match:
        raise ExecutionError("Phase G success terminal state does not satisfy DODGE condition")
    if terminal_branch == "failure" and not failure_match:
        raise ExecutionError("Phase G failure terminal state does not satisfy DODGE condition")
    if terminal_branch is None and (success_match or failure_match):
        raise ExecutionError("Phase G nonterminal state unexpectedly satisfies an end condition")

    final_refs = binding["progress_refs"]
    final_progress = {
        role: _state_value(final_index, ref)
        for role, ref in final_refs.items()
    }
    conclusion = (
        completion[terminal_branch]["conclusion_text"]
        if terminal_branch is not None
        else None
    )
    condition_ref = None
    end_condition_id = None
    if terminal_branch == "success":
        condition_ref = binding["completion_condition_ref"]
    elif terminal_branch == "failure":
        condition_ref = binding["failure_condition_ref"]
    if condition_ref is not None:
        end_condition_id = _phase_g_end_condition_id(resolved, condition_ref)

    sources = _require_mapping(resolved.get("sources"), "resolved sources")
    return {
        "format": binding["result_format"],
        "scenario_ref": binding["scenario_ref"],
        "encounter_ref": current,
        "step": step,
        "action_id": action_id,
        "actor_ref": actor_ref,
        "random_inputs": copy.deepcopy(inputs),
        "mechanic_result": mechanic,
        "progression": {
            "advanced_to": next_encounter,
            "terminal": terminal_branch is not None,
            "outcome": final_progress["outcome"],
            "information": final_progress["information"],
            "objective_complete": success_match,
            "end_condition_id": end_condition_id,
            "conclusion_text": conclusion,
        },
        "state_before": before,
        "state_after": after,
        "state_delta": copy.deepcopy(mechanic.get("state_delta", [])) + progress_delta,
        "trace": {
            "progression_binding": {
                "ref": "proto_sidecar.phase_g_progression_bindings.scenario-01",
                "source_ref": binding["binding_source_ref"],
                "authority": sources[binding["binding_source_ref"]].get("authority"),
            },
            "canonical_order": {
                "path": binding["encounter_order_source"],
                "encounter_order": copy.deepcopy(order),
                "source_ref": binding["scenario_source_ref"],
                "authority": sources[binding["scenario_source_ref"]].get("authority"),
            },
            "terminal_conditions": {
                "success": binding["completion_condition_ref"],
                "failure": binding["failure_condition_ref"],
            },
            "mechanic_result_format": mechanic.get("format"),
        },
    }


def replay_scenario_progression(resolved, record):
    if not isinstance(record, dict) or record.get("format") != PHASE_G_RESULT_FORMAT:
        raise ExecutionError("unsupported Phase G scenario-progression record format")
    recomputed = execute_scenario_action(
        resolved,
        copy.deepcopy(record.get("state_before")),
        action_id=record.get("action_id"),
        actor_ref=record.get("actor_ref"),
        random_inputs=copy.deepcopy(record.get("random_inputs")),
    )
    if recomputed != record:
        raise ExecutionError("scenario-progression record divergence detected")
    return recomputed
