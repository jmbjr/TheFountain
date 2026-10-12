#!/usr/bin/env python3
"""Bounded DIRPS execution runtime.

This module consumes only an accepted `dirps-resolved-game.v1` model.
It executes the accepted success-roll path, including Phase A contextual
modifiers, critical classification, and deterministic generated random evidence.

It does not own canonical scenario facts or target presentation.
"""
from __future__ import annotations

import copy
import hashlib


BINDING_ID = "attempt-skill"
RNG_ALGORITHM = "sha256-rejection-v1"


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
        sidecar.get("g5_execution_bindings"), "resolved g5_execution_bindings"
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
    if binding.get("result_format") != "dirps-execution-result.v1":
        raise ExecutionError("attempt-skill result format is unsupported")
    if binding.get("state_mutation") != "none":
        raise ExecutionError("bounded attempt-skill must not declare state mutation")
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


def _critical_classification(total, effective_target, binding):
    contract = _require_mapping(
        binding.get("critical_resolution"), "critical-resolution binding"
    )

    critical_success = (
        total <= 4
        or (total == 5 and effective_target >= 15)
        or (total == 6 and effective_target >= 16)
    )
    if critical_success:
        return "critical-success", True

    critical_failure = (
        total == 18
        or (total == 17 and effective_target <= 15)
        or (total - effective_target >= 10)
    )
    if critical_failure:
        return "critical-failure", False

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
    """Describe the accepted executable capability without executing it."""
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
                "ref": f"proto_sidecar.g5_execution_bindings.{BINDING_ID}",
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
    """Execute the accepted unmodified success roll with supplied evidence."""
    return _execute_attempt_skill(
        resolved,
        actor_ref=actor_ref,
        skill_ref=skill_ref,
        context_ref=None,
        modifiers=[],
        dice_terms=dice_terms,
        random_seed=None,
    )


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
    """Re-evaluate one unmodified execution record and fail on divergence."""
    binding = _execution_binding(resolved)
    if not isinstance(record, dict) or record.get("format") != binding["result_format"]:
        raise ExecutionError("record is not a DIRPS execution result")
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
    """Re-evaluate one contextual execution record from its recorded evidence."""
    binding = _execution_binding(resolved)
    if not isinstance(record, dict) or record.get("format") != binding["result_format"]:
        raise ExecutionError("record is not a DIRPS execution result")
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
