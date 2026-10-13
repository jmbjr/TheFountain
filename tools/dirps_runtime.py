#!/usr/bin/env python3
"""Bounded DIRPS execution runtime.

This module consumes only an accepted `dirps-resolved-game.v1` model.
It executes the accepted success-roll path, Phase A contextual checks, and
Phase B's first stateful investigation encounter using neutral DODGE runtime
state/effects.

It does not own canonical scenario facts or target presentation.
"""
from __future__ import annotations

import copy
import hashlib


BINDING_ID = "attempt-skill"
RNG_ALGORITHM = "sha256-rejection-v1"
PHASE_B_RESULT_FORMAT = "dirps-encounter-result.v1"


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
