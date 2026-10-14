#!/usr/bin/env python3
"""DIRPS-owned semantic validation profile for Scenario 01.

DODGE core validates neutral structure. This module validates bounded DIRPS
cross-source/domain contracts that generic DODGE cannot infer across the
source/resolved lifecycle. G5 also makes a small subset of proto semantics
executable, so those exercised contracts are validated here rather than hidden
inside the runtime.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]

PROFILE_ID = "dirps"
PROFILE_VERSION = "0.1.0"

RULES_SOURCE = "gurps-lite"
SCENARIO_SOURCE = "scenario-01-source"
PROTO_SOURCE = "dirps-proto"
CHARACTER_EXTENSION = "org.dirps.character"
PROTO_EXTENSION = "org.dirps.proto"

RULES_AUTHORITY_LABEL = "GURPS Lite, June 2003 (Third Edition-era introductory rules)"
PC_PROVENANCE = "prototype_assumption"
PRIMARY_ATTRIBUTES = frozenset({"st", "dx", "iq", "ht"})

ACTION_PROCEDURES = {
    "attempt-skill": "success-roll",
    "attempt-attribute": "success-roll",
    "attack": "attack-resolution",
    "recover": "recovery-check",
}

G5_EXERCISED_PROTO = frozenset(
    {
        "dice_resolution",
        "procedure_context",
        "actor_character_model",
        "skill_model",
        "resolution_trace",
    }
)
PHASE_A_EXERCISED_PROTO = G5_EXERCISED_PROTO
PHASE_C_EXERCISED_PROTO = PHASE_A_EXERCISED_PROTO | frozenset({"lookup_tables"})


def _repo_relative(path):
    if path is None:
        return None
    return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()


def _scene_for_scenario(dodge):
    scenario = dodge.get("scenarios", {}).get("scenario-01")
    if not scenario:
        return None, None
    scene_ref = scenario.get("scene_ref")
    return scenario, dodge.get("scenes", {}).get(scene_ref)


def _instance_map(scene):
    return {
        row.get("id"): row
        for row in (scene or {}).get("instances", [])
        if row.get("id") is not None
    }


def _object_for_instance(dodge, instance):
    if not instance:
        return None
    return dodge.get("objects", {}).get(instance.get("object_ref"))


def _source_contract(errors, owner, row, source_ref, authority):
    if not row:
        errors.append(f"{owner}: missing semantic definition")
        return
    if row.get("source_ref") != source_ref:
        errors.append(
            f"{owner}: source_ref must be {source_ref}, got {row.get('source_ref')}"
        )
    if row.get("authority") != authority:
        errors.append(
            f"{owner}: authority must be {authority}, got {row.get('authority')}"
        )


def _validate_authority_paths(dodge, canonical, config, errors):
    authority = canonical.get("authority", {})
    if authority.get("rules") != RULES_AUTHORITY_LABEL:
        errors.append(
            "canonical authority.rules must identify the bounded GURPS Lite June 2003 rules authority"
        )

    if not config:
        return

    expected_dodge = _repo_relative(config.get("dodge"))
    expected_source = _repo_relative(config.get("source"))
    sidecars = config.get("sidecars") or []
    expected_sidecar = _repo_relative(sidecars[0]) if len(sidecars) == 1 else None

    if authority.get("dodge") != expected_dodge:
        errors.append(
            "canonical authority.dodge must identify the registered DIRPS DODGE document"
        )
    if expected_sidecar and authority.get("proto_sidecar") != expected_sidecar:
        errors.append(
            "canonical authority.proto_sidecar must identify the registered DIRPS proto sidecar"
        )

    sources = dodge.get("sources", {})
    scenario_source = sources.get(SCENARIO_SOURCE, {})
    if scenario_source.get("uri") != expected_source:
        errors.append(
            "DODGE scenario-01-source URI must identify the registered canonical scenario source"
        )
    if expected_sidecar and sources.get(PROTO_SOURCE, {}).get("uri") != expected_sidecar:
        errors.append(
            "DODGE dirps-proto URI must identify the registered DIRPS proto sidecar"
        )


def _registered_sidecar(config):
    if not config:
        return None
    sidecars = config.get("sidecars") or []
    if len(sidecars) != 1 or not sidecars[0].is_file():
        return None
    return json.loads(sidecars[0].read_text())


def _validate_g5_proto_semantics(sidecar, errors, dodge=None, canonical=None):
    if not isinstance(sidecar, dict):
        errors.append("G5 requires the registered DIRPS proto sidecar")
        return

    specs = sidecar.get("proto_specs")
    if not isinstance(specs, dict):
        errors.append("G5 DIRPS proto sidecar must contain proto_specs")
        return

    for proto_id in sorted(PHASE_C_EXERCISED_PROTO):
        spec = specs.get(proto_id)
        if not isinstance(spec, dict):
            errors.append(f"G5 exercised proto {proto_id}: missing")
            continue
        if spec.get("status") != "exercised":
            errors.append(
                f"exercised proto {proto_id}: status must be exercised, got {spec.get('status')}"
            )
        if spec.get("candidate_for_dodge") != "not-yet-candidate":
            errors.append(
                f"exercised proto {proto_id}: must remain not-yet-candidate"
            )

    dice = specs.get("dice_resolution") or {}
    shape = dice.get("proposed_shape") or {}
    randomizer = shape.get("randomizer") or {}
    comparator = shape.get("comparator") or {}
    if shape.get("id") != "success-roll-3d6":
        errors.append("G5 dice_resolution id must be success-roll-3d6")
    if randomizer != {
        "kind": "dice-pool",
        "count": 3,
        "sides": 6,
        "combine": "sum",
    }:
        errors.append(
            "G5 dice_resolution randomizer must remain the declared 3d6 sum contract"
        )
    if comparator != {"op": "lte", "target_ref": "effective-target"}:
        errors.append(
            "G5 dice_resolution comparator must remain lte effective-target"
        )
    required_outputs = {"rolled_terms", "total", "success", "margin"}
    if not required_outputs.issubset(set(shape.get("outputs") or [])):
        errors.append(
            "G5 dice_resolution outputs must include rolled_terms/total/success/margin"
        )

    legacy_bindings = sidecar.get("g5_execution_bindings")
    expected_legacy_binding = {
        "action_ref": "attempt-skill",
        "procedure_ref": "success-roll",
        "actor_input": "actor_ref",
        "target_input": "skill_ref",
        "target_source": {
            "kind": "resolved-character-skill",
            "path": "scene.instances[].character.skills",
        },
        "effective_target": {
            "from": "selected-skill-level",
            "modifier_policy": "unsupported",
            "supported_domain": {"minimum": 4, "maximum": 16},
            "outside_domain": "error",
        },
        "dice_resolution_ref": "dice_resolution",
        "result_format": "dirps-execution-result.v1",
        "state_mutation": "none",
        "binding_source_ref": "dirps-proto",
        "target_provenance": {
            "source_ref": "scenario-01-source",
            "character_provenance": "prototype_assumption",
            "canonical_path": "player_character.skills",
        },
        "result_scope": "binary-success-and-margin-only",
    }
    if not isinstance(legacy_bindings, dict):
        errors.append("G5 DIRPS sidecar must preserve g5_execution_bindings")
        legacy_binding = None
    else:
        legacy_binding = legacy_bindings.get("attempt-skill")
        if legacy_binding != expected_legacy_binding:
            errors.append(
                "Phase A must preserve the accepted G5 dirps-execution-result.v1 binding exactly"
            )

    phase_bindings = sidecar.get("phase_a_execution_bindings")
    if not isinstance(phase_bindings, dict):
        errors.append("Phase A DIRPS sidecar must declare phase_a_execution_bindings")
        binding = None
    else:
        binding = phase_bindings.get("attempt-skill")
        expected_binding = {
            "action_ref": "attempt-skill",
            "procedure_ref": "success-roll",
            "actor_input": "actor_ref",
            "target_input": "skill_ref",
            "target_source": {
                "kind": "resolved-character-skill",
                "path": "scene.instances[].character.skills",
            },
            "effective_target": {
                "from": "selected-skill-level-plus-context-modifiers",
                "modifier_policy": "sum-resolved-context-modifiers",
                "minimum": 3,
                "below_minimum": "error",
                "rule_source_ref": "gurps-lite",
                "rule_locator": "p. 2, Modifiers and Effective Skill",
            },
            "dice_resolution_ref": "dice_resolution",
            "result_format": "dirps-execution-result.v2",
            "state_mutation": "none",
            "binding_source_ref": "dirps-proto",
            "target_provenance": {
                "source_ref": "scenario-01-source",
                "character_provenance": "prototype_assumption",
                "canonical_path": "player_character.skills",
                "context_source_ref": "scenario-01-source",
                "context_path": "contextual_checks",
            },
            "result_scope": "success-failure-margin-and-critical-classification",
            "context_input": "context_ref",
            "context_source": {
                "kind": "resolved-scenario-contextual-check",
                "path": "scenario.contextual_checks",
            },
            "critical_resolution": {
                "rule_source_ref": "gurps-lite",
                "rule_locator": "p. 2, Critical Success and Failure",
                "critical_success": [
                    {"roll_max": 4},
                    {"roll": 5, "minimum_effective_target": 15},
                    {"roll": 6, "minimum_effective_target": 16},
                ],
                "critical_failure": [
                    {"roll": 18},
                    {"roll": 17, "maximum_effective_target": 15},
                    {"roll_minus_effective_target_minimum": 10},
                ],
                "ordinary_failure": [
                    {"roll": 17, "minimum_effective_target": 16},
                ],
                "classifications": [
                    "critical-success",
                    "success",
                    "failure",
                    "critical-failure",
                ],
            },
            "random_evidence": {
                "supplied_terms": {"supported": True},
                "generated": {
                    "supported": True,
                    "seed_required": True,
                    "algorithm": "sha256-rejection-v1",
                },
            },
        }
        if binding != expected_binding:
            errors.append(
                "Phase A attempt-skill execution binding must match the declared v2 contract"
            )

    for label, candidate in (
        ("G5", legacy_binding),
        ("Phase A", binding),
    ):
        if dodge and isinstance(candidate, dict):
            action = (dodge.get("rules", {}).get("actions", {}) or {}).get(
                candidate.get("action_ref")
            )
            procedure = (dodge.get("rules", {}).get("procedures", {}) or {}).get(
                candidate.get("procedure_ref")
            )
            if not action:
                errors.append(f"{label} execution binding action_ref does not resolve")
            elif action.get("procedure_ref") != candidate.get("procedure_ref"):
                errors.append(
                    f"{label} execution binding disagrees with the DODGE action procedure_ref"
                )
            if not procedure:
                errors.append(f"{label} execution binding procedure_ref does not resolve")

    phase_b_bindings = sidecar.get("phase_b_encounter_bindings")
    expected_phase_b_binding = {
        "encounter_ref": "roadside-tracks",
        "action_id": "investigate-tracks",
        "actor_ref": "pc",
        "action_ref": "attempt-skill",
        "context_ref": "roadside-tracks-tracking",
        "runtime_state_ref": "scenario-01-initial",
        "required_state": [
            {"ref": "roadside-tracks-status", "value": "ready"},
        ],
        "consequences": {
            "success": {
                "effect_refs": [
                    "roadside-tracks-set-status-resolved",
                    "roadside-tracks-set-outcome-success",
                    "roadside-tracks-set-information-clear-trail",
                ],
            },
            "failure": {
                "effect_refs": [
                    "roadside-tracks-set-status-resolved",
                    "roadside-tracks-set-outcome-failure",
                    "roadside-tracks-set-information-trail-inconclusive",
                ],
            },
        },
        "skill_result_format": "dirps-execution-result.v2",
        "result_format": "dirps-encounter-result.v1",
        "binding_source_ref": "dirps-proto",
        "consequence_source_ref": "scenario-01-source",
    }
    if not isinstance(phase_b_bindings, dict):
        errors.append("Phase B DIRPS sidecar must declare phase_b_encounter_bindings")
    else:
        phase_b = phase_b_bindings.get("roadside-tracks")
        if phase_b != expected_phase_b_binding:
            errors.append(
                "Phase B roadside-tracks encounter binding must match the declared state/consequence bridge"
            )
        elif dodge:
            effects = dodge.get("rules", {}).get("effects", {}) or {}
            for branch in ("success", "failure"):
                for effect_ref in phase_b["consequences"][branch]["effect_refs"]:
                    if effect_ref not in effects:
                        errors.append(
                            f"Phase B consequence effect_ref does not resolve: {effect_ref}"
                        )
            if phase_b.get("runtime_state_ref") not in (dodge.get("runtime_states") or {}):
                errors.append(
                    "Phase B runtime_state_ref must resolve in DODGE runtime_states"
                )

    lookup_spec = specs.get("lookup_tables") or {}
    if lookup_spec.get("status") != "exercised":
        errors.append("Phase C must mark lookup_tables exercised")
    if lookup_spec.get("candidate_for_dodge") != "not-yet-candidate":
        errors.append("Phase C lookup_tables must remain not-yet-candidate")

    reaction_timing = specs.get("reaction_timing") or {}
    if reaction_timing.get("status") != "exercised":
        errors.append("Phase E must mark reaction_timing exercised")
    if reaction_timing.get("candidate_for_dodge") != "not-yet-candidate":
        errors.append("Phase E reaction_timing must remain not-yet-candidate")

    expected_lookup = {
        "key_ref": "modified-reaction-total",
        "rows": [
            {"when": {"min": None, "max": 0}, "value": "disastrous"},
            {"when": {"min": 1, "max": 3}, "value": "very-bad"},
            {"when": {"min": 4, "max": 6}, "value": "bad"},
            {"when": {"min": 7, "max": 9}, "value": "poor"},
            {"when": {"min": 10, "max": 12}, "value": "neutral"},
            {"when": {"min": 13, "max": 15}, "value": "good"},
            {"when": {"min": 16, "max": 18}, "value": "very-good"},
            {"when": {"min": 19, "max": None}, "value": "excellent"},
        ],
        "fallback": "error",
        "source_ref": RULES_SOURCE,
        "authority": "authoritative",
        "rule_locator": "p. 3, Reaction Table",
    }
    lookups = sidecar.get("phase_c_lookup_tables")
    if not isinstance(lookups, dict) or lookups.get("gurps-lite-reaction-table") != expected_lookup:
        errors.append(
            "Phase C must preserve the authoritative GURPS Lite Reaction Table lookup exactly"
        )

    reaction_order = [
        "disastrous",
        "very-bad",
        "bad",
        "poor",
        "neutral",
        "good",
        "very-good",
        "excellent",
    ]
    canonical_consequences = {}
    if isinstance(canonical, dict):
        witness = next(
            (
                row
                for row in canonical.get("encounters", [])
                if isinstance(row, dict) and row.get("id") == "frightened-witness"
            ),
            None,
        )
        if isinstance(witness, dict):
            actions = witness.get("actions") or []
            if len(actions) == 1 and isinstance(actions[0], dict):
                canonical_consequences = actions[0].get("consequences") or {}

    expected_consequences = {}
    for reaction in reaction_order:
        information = (canonical_consequences.get(reaction) or {}).get("information")
        if not isinstance(information, str) or not information:
            errors.append(
                f"Phase C canonical consequence information is required for {reaction}"
            )
            information = "missing"
        expected_consequences[reaction] = {
            "effect_refs": [
                "frightened-witness-set-status-resolved",
                f"frightened-witness-set-reaction-{reaction}",
                f"frightened-witness-set-information-{information}",
            ]
        }
    expected_social_binding = {
        "encounter_ref": "frightened-witness",
        "action_id": "reassure-and-question",
        "actor_ref": "pc",
        "procedure_ref": "reaction-roll",
        "runtime_state_ref": "scenario-01-frightened-witness-initial",
        "required_state": [
            {"ref": "frightened-witness-status", "value": "ready"},
        ],
        "modifier_source": {
            "kind": "encounter-action-reaction-modifiers",
            "path": "scenario.encounters[].actions[].reaction_modifiers",
        },
        "random_evidence": {
            "randomizer": {
                "kind": "dice-pool",
                "count": 3,
                "sides": 6,
                "combine": "sum",
            },
            "supplied_terms": {"supported": True},
            "generated": {
                "supported": True,
                "seed_required": True,
                "algorithm": "sha256-rejection-v1",
            },
        },
        "lookup_table_ref": "gurps-lite-reaction-table",
        "consequences": expected_consequences,
        "reaction_result_format": "dirps-reaction-result.v1",
        "result_format": "dirps-social-encounter-result.v1",
        "binding_source_ref": PROTO_SOURCE,
        "consequence_source_ref": SCENARIO_SOURCE,
    }
    social_bindings = sidecar.get("phase_c_social_bindings")
    if not isinstance(social_bindings, dict):
        errors.append("Phase C DIRPS sidecar must declare phase_c_social_bindings")
    else:
        social = social_bindings.get("frightened-witness")
        if social != expected_social_binding:
            errors.append(
                "Phase C frightened-witness social binding must match the declared reaction contract"
            )
        elif dodge:
            procedure = (dodge.get("rules", {}).get("procedures", {}) or {}).get(
                social["procedure_ref"]
            )
            if not isinstance(procedure, dict):
                errors.append("Phase C procedure_ref must resolve in DODGE procedures")
            effects = dodge.get("rules", {}).get("effects", {}) or {}
            for consequence in social["consequences"].values():
                for effect_ref in consequence["effect_refs"]:
                    if effect_ref not in effects:
                        errors.append(
                            f"Phase C consequence effect_ref does not resolve: {effect_ref}"
                        )
            if social["runtime_state_ref"] not in (dodge.get("runtime_states") or {}):
                errors.append(
                    "Phase C runtime_state_ref must resolve in DODGE runtime_states"
                )

    phase_d_bindings = sidecar.get("phase_d_environment_bindings")
    canonical_d = {}
    if isinstance(canonical, dict):
        env = next((row for row in canonical.get("encounters", []) if isinstance(row, dict) and row.get("id") == "washed-out-path"), None)
        if isinstance(env, dict) and len(env.get("actions") or []) == 1:
            canonical_d = env["actions"][0].get("consequences") or {}
    expected_phase_d = {
        "encounter_ref":"washed-out-path",
        "action_id":"cross-washed-out-path",
        "actor_ref":"pc",
        "action_ref":"attempt-attribute",
        "procedure_ref":"success-roll",
        "context_ref":"washed-out-path-dx",
        "target_source":{"kind":"resolved-character-primary-attribute","path":"scene.instances[].character.primary_attributes"},
        "runtime_state_ref":"scenario-01-washed-out-path-initial",
        "required_state":[{"ref":"washed-out-path-status","value":"ready"}],
        "consequences":{
            "success":{"effect_refs":["washed-out-path-set-status-resolved","washed-out-path-set-outcome-success",f"washed-out-path-set-progress-{(canonical_d.get('success') or {}).get('progress')}"]},
            "failure":{"effect_refs":["washed-out-path-set-status-resolved","washed-out-path-set-outcome-failure",f"washed-out-path-set-progress-{(canonical_d.get('failure') or {}).get('progress')}"]},
        },
        "effective_target":{
            "from":"selected-attribute-level-plus-context-modifiers",
            "modifier_policy":"sum-resolved-context-modifiers",
            "minimum":3,
            "below_minimum":"error",
            "rule_source_ref":RULES_SOURCE,
            "rule_locator":"p. 2, Success Rolls; Modifiers and Effective Skill",
        },
        "dice_resolution_ref":"dice_resolution",
        "critical_resolution_ref":"phase_a_execution_bindings.attempt-skill.critical_resolution",
        "random_evidence_ref":"phase_a_execution_bindings.attempt-skill.random_evidence",
        "attribute_result_format":"dirps-attribute-result.v1",
        "result_format":"dirps-environment-encounter-result.v1",
        "binding_source_ref":PROTO_SOURCE,
        "target_source_ref":SCENARIO_SOURCE,
        "consequence_source_ref":SCENARIO_SOURCE,
    }
    if not isinstance(phase_d_bindings, dict) or phase_d_bindings.get("washed-out-path") != expected_phase_d:
        errors.append("Phase D washed-out-path environment binding must match the declared attribute/consequence contract")
    elif dodge:
        phase_d = phase_d_bindings["washed-out-path"]
        if phase_d["runtime_state_ref"] not in (dodge.get("runtime_states") or {}):
            errors.append("Phase D runtime_state_ref must resolve in DODGE runtime_states")
        effects = dodge.get("rules", {}).get("effects", {}) or {}
        for consequence in phase_d["consequences"].values():
            for effect_ref in consequence["effect_refs"]:
                if effect_ref not in effects:
                    errors.append(f"Phase D consequence effect_ref does not resolve: {effect_ref}")

    phase_e_expressions = sidecar.get("phase_e_expressions")
    expected_phase_e_expressions = {
        "bandit-dodge-target": {
            "op": "add",
            "args": [
                {
                    "op": "subtract",
                    "args": [
                        {
                            "op": "floor",
                            "arg": {
                                "op": "divide",
                                "args": [
                                    {
                                        "op": "add",
                                        "args": [
                                            {"ref": "defender.dx"},
                                            {"ref": "defender.ht"},
                                        ],
                                    },
                                    {"literal": 4},
                                ],
                            },
                        },
                        {"ref": "defender.encumbrance_penalty"},
                    ],
                },
                {"ref": "defender.passive_defense"},
            ],
            "source_ref": RULES_SOURCE,
            "authority": "authoritative",
            "rule_locator": "pp. 20, 26, Basic Speed/Move/Dodge; Defense/Passive Defense",
        },
        "cutting-injury": {
            "op": "add",
            "args": [
                {"ref": "penetrating_damage"},
                {
                    "op": "floor",
                    "arg": {
                        "op": "divide",
                        "args": [
                            {"ref": "penetrating_damage"},
                            {"literal": 2},
                        ],
                    },
                },
            ],
            "source_ref": RULES_SOURCE,
            "authority": "authoritative",
            "rule_locator": "p. 18, Damage Types; p. 27, Injury",
        },
    }
    if phase_e_expressions != expected_phase_e_expressions:
        errors.append("Phase E expressions must match the bounded authoritative combat math exactly")

    expected_phase_e_derived = {
        "bandit-dodge": {
            "value_type": "integer",
            "expression_ref": "bandit-dodge-target",
            "dependencies": [
                "defender.dx",
                "defender.ht",
                "defender.encumbrance_penalty",
                "defender.passive_defense",
            ],
            "recompute": "on-dependency-change",
        },
        "cutting-injury": {
            "value_type": "integer",
            "expression_ref": "cutting-injury",
            "dependencies": ["penetrating_damage"],
            "recompute": "on-dependency-change",
        },
    }
    if sidecar.get("phase_e_derived_values") != expected_phase_e_derived:
        errors.append("Phase E derived values must match the bounded Dodge/injury contract exactly")

    expected_phase_e_lookup = {
        "key_ref": "attacker.st",
        "rows": [
            {
                "when": {"min": 10, "max": 10},
                "value": {"count": 1, "sides": 6, "adds": 0},
            }
        ],
        "fallback": "error",
        "source_ref": RULES_SOURCE,
        "authority": "authoritative",
        "rule_locator": "p. 18, Basic Weapon Damage",
    }
    lookups_e = sidecar.get("phase_e_lookup_tables")
    if not isinstance(lookups_e, dict) or lookups_e.get("gurps-lite-st10-swing") != expected_phase_e_lookup:
        errors.append("Phase E must preserve the authoritative bounded ST10 swing-damage lookup exactly")

    expected_phase_e_binding = {
        "encounter_ref": "bandit-scout",
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
        "reaction_window": {
            "trigger": "successful-noncritical-attack",
            "responder_ref": "bandit-scout",
            "eligible_defenses": ["dodge"],
            "resolution_order": "attack-then-defense-before-damage",
        },
        "defense": {
            "kind": "dodge",
            "target_expression_ref": "bandit-dodge-target",
            "random_evidence_ref": "phase_a_execution_bindings.attempt-skill.random_evidence",
            "rule_source_ref": RULES_SOURCE,
            "rule_locator": "p. 26, Defense / Dodging",
            "result_format": "dirps-active-defense-result.v1",
        },
        "damage": {
            "strength_lookup_ref": "gurps-lite-st10-swing",
            "weapon_add": 1,
            "damage_type": "cutting",
            "minimum_basic_damage": 1,
            "armor_dr_source": "encounter.opponent.defense_assumptions.armor_dr",
            "injury_expression_ref": "cutting-injury",
            "rule_source_ref": RULES_SOURCE,
            "rule_locator": "pp. 18-19, Weapon Damage; pp. 26-28, Damage and Injury",
            "result_format": "dirps-damage-result.v1",
            "critical_attack_total_three": {
                "attack_total": 3,
                "resolution": "automatic-maximum-profile-damage",
                "damage_random_evidence": "none",
                "rule_source_ref": RULES_SOURCE,
                "rule_locator": "Rolling to Attack / Critical Hits",
            },
        },
        "injury_state": {
            "hit_points_ref": "hit-points",
            "stunned_ref": "stunned",
            "unconscious_ref": "unconscious",
            "consciousness_check_required_ref": "consciousness-check-required",
            "major_wound_rule": "injury > defender.ht / 2",
            "consciousness_check_rule": "remaining_hp <= 0",
            "consciousness_check_timing": "next-turn-start",
            "recovery_phase": "Phase F",
        },
        "attack_result_format": "dirps-attack-result.v1",
        "result_format": "dirps-combat-exchange-result.v1",
        "binding_source_ref": PROTO_SOURCE,
        "scenario_source_ref": SCENARIO_SOURCE,
    }
    combat_bindings = sidecar.get("phase_e_combat_bindings")
    if not isinstance(combat_bindings, dict) or combat_bindings.get("bandit-scout") != expected_phase_e_binding:
        errors.append("Phase E bandit-scout combat binding must match the declared bounded contract")
    elif dodge:
        combat = combat_bindings["bandit-scout"]
        if combat["runtime_state_ref"] not in (dodge.get("runtime_states") or {}):
            errors.append("Phase E runtime_state_ref must resolve in DODGE runtime_states")
        action = (dodge.get("rules", {}).get("actions", {}) or {}).get(combat["action_ref"])
        if not isinstance(action, dict) or action.get("procedure_ref") != combat["procedure_ref"]:
            errors.append("Phase E attack action/procedure binding must resolve in DODGE rules")

    expected_phase_f_binding = {
        "encounter_ref": "bandit-scout",
        "action_id": "resolve-bandit-next-turn",
        "actor_ref": "bandit-scout",
        "action_ref": "recover",
        "procedure_ref": "recovery-check",
        "timing": "next-turn-start",
        "resolution_order": ["consciousness", "stun-recovery"],
        "minimum_state_revision": 1,
        "ht_source": "encounter.opponent.attributes.ht",
        "dice_resolution_ref": "dice_resolution",
        "critical_resolution_ref": "phase_a_execution_bindings.attempt-skill.critical_resolution",
        "random_evidence_ref": "phase_a_execution_bindings.attempt-skill.random_evidence",
        "consciousness": {
            "hit_points_ref": "hit-points",
            "check_required_ref": "consciousness-check-required",
            "unconscious_ref": "unconscious",
            "will_modifier_source": "encounter.post_combat_recovery.consciousness.will_modifier",
            "success_effect_refs": [],
            "failure_effect_refs": [
                "phase-f-bandit-set-unconscious",
                "phase-f-bandit-clear-consciousness-check-required",
            ],
            "rule_source_ref": RULES_SOURCE,
            "rule_locator": "p. 27, General Damage / Unconsciousness",
        },
        "stun_recovery": {
            "stunned_ref": "stunned",
            "unconscious_ref": "unconscious",
            "success_effect_refs": ["phase-f-bandit-clear-stunned"],
            "failure_effect_refs": [],
            "rule_source_ref": RULES_SOURCE,
            "rule_locator": "p. 27, Stunning; p. 26, Knockdown and Stunning",
        },
        "long_term_unconscious_recovery": "unsupported",
        "check_result_format": "dirps-ht-check-result.v1",
        "result_format": "dirps-recovery-result.v1",
        "binding_source_ref": PROTO_SOURCE,
        "scenario_source_ref": SCENARIO_SOURCE,
    }
    phase_f_bindings = sidecar.get("phase_f_recovery_bindings")
    if not isinstance(phase_f_bindings, dict) or phase_f_bindings.get("bandit-scout") != expected_phase_f_binding:
        errors.append(
            "Phase F bandit-scout recovery binding must match the declared next-turn HT contract"
        )
    elif dodge:
        recovery = phase_f_bindings["bandit-scout"]
        action = (dodge.get("rules", {}).get("actions", {}) or {}).get(
            recovery["action_ref"]
        )
        if not isinstance(action, dict) or action.get("procedure_ref") != recovery["procedure_ref"]:
            errors.append(
                "Phase F recover action/procedure binding must resolve in DODGE rules"
            )
        phase_a = (sidecar.get("phase_a_execution_bindings") or {}).get("attempt-skill")
        if not isinstance(phase_a, dict):
            errors.append("Phase F reuse contract requires Phase A attempt-skill binding")
        else:
            if recovery.get("dice_resolution_ref") != phase_a.get("dice_resolution_ref"):
                errors.append(
                    "Phase F dice_resolution_ref must reuse the accepted Phase A dice_resolution_ref"
                )
            if recovery.get("critical_resolution_ref") != "phase_a_execution_bindings.attempt-skill.critical_resolution":
                errors.append(
                    "Phase F critical_resolution_ref must point to the accepted Phase A critical_resolution"
                )
            if not isinstance(phase_a.get("critical_resolution"), dict):
                errors.append(
                    "Phase F critical_resolution_ref target must exist on the accepted Phase A binding"
                )
            if recovery.get("random_evidence_ref") != "phase_a_execution_bindings.attempt-skill.random_evidence":
                errors.append(
                    "Phase F random_evidence_ref must point to the accepted Phase A random_evidence"
                )
            if not isinstance(phase_a.get("random_evidence"), dict):
                errors.append(
                    "Phase F random_evidence_ref target must exist on the accepted Phase A binding"
                )

        effects = dodge.get("rules", {}).get("effects", {}) or {}
        for check_name in ("consciousness", "stun_recovery"):
            check = recovery[check_name]
            for branch in ("success_effect_refs", "failure_effect_refs"):
                for effect_ref in check[branch]:
                    if effect_ref not in effects:
                        errors.append(
                            f"Phase F recovery effect_ref does not resolve: {effect_ref}"
                        )

    expected_phase_g_binding = {
        "scenario_ref": "scenario-01",
        "runtime_state_ref": "scenario-01-playable-initial",
        "encounter_order_source": "scenario.progression.encounter_order",
        "progress_refs": {
            "status": "scenario-progress-status",
            "current_encounter": "scenario-current-encounter",
            "step": "scenario-progress-step",
            "outcome": "scenario-outcome",
            "information": "scenario-completion-information",
        },
        "phase_runtime_state_refs": {
            "roadside-tracks": "scenario-01-initial",
            "frightened-witness": "scenario-01-frightened-witness-initial",
            "washed-out-path": "scenario-01-washed-out-path-initial",
            "bandit-scout": "scenario-01-bandit-scout-initial",
        },
        "advance_effect_refs": {
            "frightened-witness": "phase-g-current-frightened-witness",
            "washed-out-path": "phase-g-current-washed-out-path",
            "bandit-scout": "phase-g-current-bandit-scout",
        },
        "recovery_effect_ref": "phase-g-step-recovery",
        "terminal_effect_refs": {
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
        },
        "completion_condition_ref": "scenario-success",
        "failure_condition_ref": "scenario-failure",
        "result_format": "dirps-scenario-progression-result.v1",
        "binding_source_ref": PROTO_SOURCE,
        "scenario_source_ref": SCENARIO_SOURCE,
    }
    phase_g_bindings = sidecar.get("phase_g_progression_bindings")
    if (
        not isinstance(phase_g_bindings, dict)
        or phase_g_bindings.get("scenario-01") != expected_phase_g_binding
    ):
        errors.append("Phase G progression binding must match the bounded orchestration contract")
    elif dodge:
        binding = phase_g_bindings["scenario-01"]
        runtime_states = dodge.get("runtime_states") or {}
        if binding["runtime_state_ref"] not in runtime_states:
            errors.append("Phase G playable runtime_state_ref must resolve in DODGE runtime_states")
        for state_ref in binding["phase_runtime_state_refs"].values():
            if state_ref not in runtime_states:
                errors.append(f"Phase G phase runtime state does not resolve: {state_ref}")
        effects = (dodge.get("rules") or {}).get("effects") or {}
        effect_refs = list(binding["advance_effect_refs"].values())
        effect_refs.append(binding["recovery_effect_ref"])
        for branch in binding["terminal_effect_refs"].values():
            effect_refs.extend(branch)
        for effect_ref in effect_refs:
            if effect_ref not in effects:
                errors.append(f"Phase G progression effect_ref does not resolve: {effect_ref}")
        conditions = (dodge.get("rules") or {}).get("conditions") or {}
        for condition_ref in (
            binding["completion_condition_ref"],
            binding["failure_condition_ref"],
        ):
            if condition_ref not in conditions:
                errors.append(f"Phase G terminal condition_ref does not resolve: {condition_ref}")

    for proto_id in ("derived_values", "expressions", "damage_injury"):
        spec = specs.get(proto_id) or {}
        if spec.get("status") != "exercised":
            errors.append(f"Phase E must mark {proto_id} exercised")
        if spec.get("candidate_for_dodge") != "not-yet-candidate":
            errors.append(f"Phase E {proto_id} must remain not-yet-candidate")

    if (specs.get("replay_session_history") or {}).get("status") != "suspected":
        errors.append(
            "Phase F single-turn recovery replay must not promote replay_session_history"
        )


def _validate_source_roles(dodge, errors):
    sources = dodge.get("sources", {})
    expected = {
        RULES_SOURCE: ("rules", "authoritative"),
        SCENARIO_SOURCE: ("scenario", "provisional"),
        PROTO_SOURCE: ("sidecar", "provisional"),
    }
    for source_id, (kind, authority) in expected.items():
        source = sources.get(source_id)
        if not source:
            errors.append(f"source {source_id}: missing")
            continue
        if source.get("kind") != kind:
            errors.append(
                f"source {source_id}: kind must be {kind}, got {source.get('kind')}"
            )
        if source.get("authority") != authority:
            errors.append(
                f"source {source_id}: authority must be {authority}, got {source.get('authority')}"
            )

    sidecar_refs = {
        row.get("source_ref") for row in dodge.get("sidecars", [])
    }
    if PROTO_SOURCE not in sidecar_refs:
        errors.append("DIRPS proto source must be declared in DODGE sidecars")

    proto_extension = dodge.get("extensions", {}).get(PROTO_EXTENSION, {})
    if proto_extension.get("sidecar_ref") != PROTO_SOURCE:
        errors.append(
            f"{PROTO_EXTENSION}: sidecar_ref must be {PROTO_SOURCE}"
        )


def _validate_actor_model(dodge, canonical, errors):
    pc = canonical.get("player_character")
    if not isinstance(pc, dict):
        errors.append("canonical player_character is required")
        return

    scenario, scene = _scene_for_scenario(dodge)
    if not scenario or not scene:
        errors.append("DIRPS scenario-01 must resolve one source scene")
        return

    instances = _instance_map(scene)
    pc_id = pc.get("id")
    pc_instance = instances.get(pc_id)
    if not pc_instance:
        errors.append(f"canonical player character {pc_id}: missing DODGE scene instance")
        return

    pc_object = _object_for_instance(dodge, pc_instance)
    if not pc_object:
        errors.append(f"canonical player character {pc_id}: missing DODGE object")
        return

    if pc.get("provenance") != PC_PROVENANCE:
        errors.append(
            f"canonical player character {pc_id}: provenance must be {PC_PROVENANCE}"
        )

    if "player-character" not in pc_object.get("tags", []):
        errors.append(f"canonical player character {pc_id}: DODGE object lacks player-character tag")
    if pc_object.get("name") != pc.get("name"):
        errors.append(
            f"canonical player character {pc_id}: name disagrees between scenario source and DODGE"
        )

    values = dodge.get("rules", {}).get("values", {})
    actor_values = {
        value_id
        for value_id, definition in values.items()
        if definition.get("owner_scope") == "actor"
    }
    for value_id in sorted(actor_values):
        if value_id == "consciousness-check-required":
            _source_contract(
                errors,
                f"value {value_id}",
                values[value_id],
                PROTO_SOURCE,
                "provisional",
            )
        else:
            _source_contract(
                errors,
                f"value {value_id}",
                values[value_id],
                RULES_SOURCE,
                "authoritative",
            )

    # DIRPS Scenario 01 requires explicit initial bindings for every declared
    # actor-scoped value so tutorial actors do not depend on hidden runtime defaults.
    for instance_id, instance in instances.items():
        obj = _object_for_instance(dodge, instance)
        if not obj or "actor" not in obj.get("tags", []):
            continue
        state = instance.get("state", {})
        missing = sorted(actor_values - set(state))
        if missing:
            errors.append(
                f"actor {instance_id}: missing explicit actor-state bindings {missing}"
            )

    state = pc_instance.get("state", {})
    attributes = pc.get("attributes", {})
    if not isinstance(attributes, dict):
        errors.append("canonical player_character.attributes must be an object")
        attributes = {}

    attribute_ids = set(attributes)
    missing_primary = sorted(PRIMARY_ATTRIBUTES - attribute_ids)
    unexpected_primary = sorted(attribute_ids - PRIMARY_ATTRIBUTES)
    if missing_primary:
        errors.append(
            f"canonical player character {pc_id}: missing primary attributes {missing_primary}"
        )
    if unexpected_primary:
        errors.append(
            f"canonical player character {pc_id}: unexpected primary attributes {unexpected_primary}; "
            "the bounded primary build is exactly ST/DX/IQ/HT"
        )

    for attribute_id in sorted(PRIMARY_ATTRIBUTES):
        if attribute_id not in attributes:
            continue
        canonical_value = attributes[attribute_id]
        definition = values.get(attribute_id)
        if not definition:
            errors.append(
                f"canonical player attribute {attribute_id}: missing DODGE value definition"
            )
            continue
        if definition.get("owner_scope") != "actor":
            errors.append(
                f"canonical player attribute {attribute_id}: DODGE value must be actor-owned"
            )
        if state.get(attribute_id) != canonical_value:
            errors.append(
                f"canonical player attribute {attribute_id}: scenario value {canonical_value} "
                f"!= DODGE scene value {state.get(attribute_id)}"
            )

    extension = pc_instance.get("extensions", {}).get(CHARACTER_EXTENSION)
    if not isinstance(extension, dict):
        errors.append(
            f"canonical player character {pc_id}: missing {CHARACTER_EXTENSION} extension"
        )
        return
    if extension.get("skills") != pc.get("skills"):
        errors.append(
            f"canonical player character {pc_id}: skills disagree between scenario source and DODGE extension"
        )
    if extension.get("equipment") != pc.get("equipment"):
        errors.append(
            f"canonical player character {pc_id}: equipment disagrees between scenario source and DODGE extension"
        )


def _tutorial_choice_actions(procedure):
    refs = []
    for step in (procedure or {}).get("steps", []):
        if step.get("kind") != "choice":
            continue
        for option in step.get("choice_options", []) or []:
            for nested in option.get("steps", []) or []:
                if nested.get("kind") == "action" and nested.get("ref"):
                    refs.append(nested["ref"])
    return refs


def _validate_rule_meaning(dodge, errors):
    rules = dodge.get("rules", {})
    actions = rules.get("actions", {})
    procedures = rules.get("procedures", {})
    conditions = rules.get("conditions", {})
    scenario = dodge.get("scenarios", {}).get("scenario-01", {})

    conscious = conditions.get("actor-conscious")
    _source_contract(
        errors, "condition actor-conscious", conscious, RULES_SOURCE, "authoritative"
    )
    if conscious:
        if conscious.get("op") != "eq":
            errors.append("condition actor-conscious: expected equality predicate")
        left = conscious.get("left", {})
        if left.get("ref") != "unconscious":
            errors.append("condition actor-conscious: must read the unconscious value")
        if left.get("subject", {}).get("relative") != "current-actor":
            errors.append("condition actor-conscious: must evaluate the current actor")
        if conscious.get("right") is not False:
            errors.append("condition actor-conscious: must require unconscious == false")

    for action_id, procedure_id in ACTION_PROCEDURES.items():
        action = actions.get(action_id)
        _source_contract(
            errors, f"action {action_id}", action, RULES_SOURCE, "authoritative"
        )
        if not action:
            continue
        if action.get("procedure_ref") != procedure_id:
            errors.append(
                f"action {action_id}: must bind DIRPS procedure {procedure_id}"
            )
        if "actor-conscious" not in action.get("condition_refs", []):
            errors.append(
                f"action {action_id}: must require actor-conscious"
            )

    for procedure_id in ("success-roll", "attack-resolution", "recovery-check"):
        _source_contract(
            errors,
            f"procedure {procedure_id}",
            procedures.get(procedure_id),
            RULES_SOURCE,
            "authoritative",
        )

    attack_steps = (procedures.get("attack-resolution") or {}).get("steps", [])
    if not any(
        step.get("kind") == "procedure" and step.get("ref") == "success-roll"
        for step in attack_steps
    ):
        errors.append(
            "procedure attack-resolution: must compose the DIRPS success-roll procedure"
        )

    tutorial = procedures.get("tutorial-turn")
    _source_contract(
        errors,
        "procedure tutorial-turn",
        tutorial,
        SCENARIO_SOURCE,
        "provisional",
    )
    if scenario.get("turn_procedure_ref") != "tutorial-turn":
        errors.append("scenario-01: turn_procedure_ref must be tutorial-turn")

    scenario_actions = scenario.get("action_refs", [])
    choice_actions = _tutorial_choice_actions(tutorial)
    if set(choice_actions) != set(scenario_actions) or len(choice_actions) != len(scenario_actions):
        errors.append(
            "tutorial-turn choices must expose each scenario-01 action exactly once"
        )


def _validate_scenario_duplication(dodge, canonical, errors):
    scenario, scene = _scene_for_scenario(dodge)
    if not scenario or not scene:
        return

    if scenario.get("target_duration_minutes") != canonical.get("tutorial", {}).get("target_minutes"):
        errors.append(
            "Scenario 01 target duration disagrees between canonical scenario source and DODGE"
        )

    instances = _instance_map(scene)
    for encounter in canonical.get("encounters", []):
        if encounter.get("type") != "combat":
            continue
        encounter_id = encounter.get("id")
        instance = instances.get(encounter_id)
        if not instance:
            errors.append(
                f"combat encounter {encounter_id}: missing concrete DODGE opponent instance"
            )
            continue
        obj = _object_for_instance(dodge, instance)
        tags = set((obj or {}).get("tags", []))
        if not {"actor", "non-player-character"}.issubset(tags):
            errors.append(
                f"combat encounter {encounter_id}: concrete DODGE object must be an actor/non-player-character"
            )

    _source_contract(
        errors,
        "scenario scenario-01",
        scenario,
        SCENARIO_SOURCE,
        "provisional",
    )


def _validate_phase_a_contextual_checks(dodge, canonical, errors):
    checks = canonical.get("contextual_checks")
    if not isinstance(checks, dict):
        errors.append("Phase A requires canonical contextual_checks")
        return

    check = checks.get("roadside-tracks-tracking")
    if not isinstance(check, dict):
        errors.append("Phase A requires contextual check roadside-tracks-tracking")
        return

    encounters = {
        row.get("id"): row
        for row in canonical.get("encounters", [])
        if isinstance(row, dict) and row.get("id")
    }
    encounter_ref = check.get("encounter_ref")
    if encounter_ref not in encounters:
        errors.append(
            "Phase A contextual check encounter_ref must resolve in canonical encounters"
        )

    if check.get("action_ref") != "attempt-skill":
        errors.append("Phase A contextual check must use attempt-skill")
    if "attempt-skill" not in (dodge.get("rules", {}).get("actions", {}) or {}):
        errors.append("Phase A contextual check action_ref must resolve in DODGE actions")

    pc = canonical.get("player_character") or {}
    skills = pc.get("skills") or {}
    skill_ref = check.get("skill_ref")
    if skill_ref not in skills:
        errors.append("Phase A contextual check skill_ref must resolve on the canonical PC")

    if check.get("provenance") != PC_PROVENANCE:
        errors.append(
            f"Phase A contextual check provenance must be {PC_PROVENANCE}"
        )

    modifiers = check.get("modifiers")
    if not isinstance(modifiers, list) or not modifiers:
        errors.append("Phase A contextual check must declare at least one modifier")
        return

    seen = set()
    total = 0
    for index, modifier in enumerate(modifiers):
        if not isinstance(modifier, dict):
            errors.append(f"Phase A modifier {index}: must be an object")
            continue
        modifier_id = modifier.get("id")
        if not isinstance(modifier_id, str) or not modifier_id:
            errors.append(f"Phase A modifier {index}: id is required")
        elif modifier_id in seen:
            errors.append(f"Phase A modifier {modifier_id}: duplicate id")
        else:
            seen.add(modifier_id)

        amount = modifier.get("amount")
        if not isinstance(amount, int) or isinstance(amount, bool):
            errors.append(f"Phase A modifier {modifier_id or index}: amount must be integer")
        else:
            total += amount

        if modifier.get("source_ref") != SCENARIO_SOURCE:
            errors.append(
                f"Phase A modifier {modifier_id or index}: source_ref must be {SCENARIO_SOURCE}"
            )
        if modifier.get("authority") != "provisional":
            errors.append(
                f"Phase A modifier {modifier_id or index}: authority must be provisional"
            )
        if modifier.get("provenance") != PC_PROVENANCE:
            errors.append(
                f"Phase A modifier {modifier_id or index}: provenance must be {PC_PROVENANCE}"
            )
        if not isinstance(modifier.get("reason"), str) or not modifier.get("reason"):
            errors.append(f"Phase A modifier {modifier_id or index}: reason is required")

    base = skills.get(skill_ref)
    if isinstance(base, int) and not isinstance(base, bool):
        if base + total < 3:
            errors.append(
                "Phase A contextual check effective target must be at least 3"
            )


def _validate_phase_b_investigation_contract(dodge, canonical, errors):
    encounters = {
        row.get("id"): row
        for row in canonical.get("encounters", [])
        if isinstance(row, dict) and row.get("id")
    }
    encounter = encounters.get("roadside-tracks")
    if not isinstance(encounter, dict):
        errors.append("Phase B requires canonical roadside-tracks encounter")
        return

    state_contract = encounter.get("state_contract")
    if not isinstance(state_contract, dict):
        errors.append("Phase B roadside-tracks requires state_contract")
        return
    refs = state_contract.get("refs")
    initial = state_contract.get("initial")
    if not isinstance(refs, dict) or set(refs) != {"status", "outcome", "information"}:
        errors.append(
            "Phase B roadside-tracks state_contract.refs must define status/outcome/information"
        )
        return
    if not isinstance(initial, dict) or set(initial) != set(refs):
        errors.append(
            "Phase B roadside-tracks state_contract.initial must define status/outcome/information"
        )
        return

    actions = encounter.get("actions")
    if not isinstance(actions, list) or len(actions) != 1:
        errors.append("Phase B roadside-tracks must expose exactly one investigation action")
        return
    action = actions[0]
    if not isinstance(action, dict):
        errors.append("Phase B roadside-tracks action must be an object")
        return
    if action.get("id") != "investigate-tracks":
        errors.append("Phase B roadside-tracks action id must be investigate-tracks")
    if action.get("actor_ref") != "pc":
        errors.append("Phase B roadside-tracks investigation actor_ref must be pc")
    if action.get("action_ref") != "attempt-skill":
        errors.append("Phase B roadside-tracks investigation must bind attempt-skill")
    if action.get("context_ref") != "roadside-tracks-tracking":
        errors.append(
            "Phase B roadside-tracks investigation must bind roadside-tracks-tracking"
        )
    if action.get("source_ref") != SCENARIO_SOURCE:
        errors.append(
            f"Phase B roadside-tracks action source_ref must be {SCENARIO_SOURCE}"
        )
    if action.get("authority") != "provisional":
        errors.append("Phase B roadside-tracks action authority must be provisional")
    if action.get("provenance") != PC_PROVENANCE:
        errors.append(
            f"Phase B roadside-tracks action provenance must be {PC_PROVENANCE}"
        )

    contextual = (canonical.get("contextual_checks") or {}).get(
        action.get("context_ref")
    )
    if not isinstance(contextual, dict):
        errors.append(
            "Phase B roadside-tracks action context_ref must resolve in canonical contextual_checks"
        )
    else:
        if contextual.get("encounter_ref") != encounter.get("id"):
            errors.append(
                "Phase B roadside-tracks contextual check must point back to the encounter"
            )
        if contextual.get("action_ref") != action.get("action_ref"):
            errors.append(
                "Phase B roadside-tracks action/context action_ref must agree"
            )

    consequences = action.get("consequences")
    if not isinstance(consequences, dict) or set(consequences) != {"success", "failure"}:
        errors.append(
            "Phase B roadside-tracks action must define success and failure consequences"
        )
        return
    for branch in ("success", "failure"):
        row = consequences.get(branch)
        if not isinstance(row, dict):
            errors.append(f"Phase B roadside-tracks {branch} consequence must be an object")
            continue
        if set(row) != {"status", "outcome", "information", "information_text"}:
            errors.append(
                f"Phase B roadside-tracks {branch} consequence must define status/outcome/information/information_text"
            )
        if not isinstance(row.get("information_text"), str) or not row.get(
            "information_text"
        ):
            errors.append(
                f"Phase B roadside-tracks {branch} information_text is required"
            )

    success = consequences.get("success") or {}
    failure = consequences.get("failure") or {}
    if success.get("status") != failure.get("status"):
        errors.append(
            "Phase B uses one shared encounter-resolution status; success/failure status must agree"
        )

    values = dodge.get("rules", {}).get("values", {}) or {}
    ordered_by_role = {
        "status": [initial.get("status"), success.get("status"), failure.get("status")],
        "outcome": [initial.get("outcome"), success.get("outcome"), failure.get("outcome")],
        "information": [
            initial.get("information"),
            success.get("information"),
            failure.get("information"),
        ],
    }
    for role, value_ref in refs.items():
        if not isinstance(value_ref, str) or not value_ref:
            errors.append(f"Phase B state ref {role} must be a non-empty id")
            continue
        definition = values.get(value_ref)
        if not isinstance(definition, dict):
            errors.append(f"Phase B state ref {value_ref} must resolve in DODGE rules.values")
            continue
        expected_values = []
        for item in ordered_by_role[role]:
            if item not in expected_values:
                expected_values.append(item)
        expected_definition = {
            "name": definition.get("name"),
            "type": "enum",
            "owner_scope": "scenario",
            "persistence_scope": "scenario",
            "default": initial.get(role),
            "enum_values": expected_values,
            "source_ref": SCENARIO_SOURCE,
            "authority": "provisional",
        }
        if definition != expected_definition:
            errors.append(
                f"Phase B DODGE value {value_ref} must normalize canonical {role} state exactly"
            )

    scenario = (dodge.get("scenarios") or {}).get("scenario-01") or {}
    initial_bindings = [
        {
            "ref": refs[role],
            "subject": {"relative": "scenario"},
            "value": initial[role],
            "authority": "provisional",
        }
        for role in ("status", "outcome", "information")
    ]
    if scenario.get("initial_state") != initial_bindings:
        errors.append(
            "Phase B DODGE scenario initial_state must normalize canonical Roadside state exactly"
        )

    runtime_state = (dodge.get("runtime_states") or {}).get("scenario-01-initial")
    expected_runtime_state = {
        "scenario_ref": "scenario-01",
        "bindings": initial_bindings,
        "events": [],
        "revision": "0",
    }
    if runtime_state != expected_runtime_state:
        errors.append(
            "Phase B DODGE runtime_states.scenario-01-initial must match scenario initial_state"
        )

    effects = dodge.get("rules", {}).get("effects", {}) or {}
    effect_expectations = {
        "roadside-tracks-set-status-resolved": (
            refs["status"],
            success.get("status"),
        ),
        "roadside-tracks-set-outcome-success": (
            refs["outcome"],
            success.get("outcome"),
        ),
        "roadside-tracks-set-information-clear-trail": (
            refs["information"],
            success.get("information"),
        ),
        "roadside-tracks-set-outcome-failure": (
            refs["outcome"],
            failure.get("outcome"),
        ),
        "roadside-tracks-set-information-trail-inconclusive": (
            refs["information"],
            failure.get("information"),
        ),
    }
    for effect_id, (target_ref, value) in effect_expectations.items():
        expected_effect = {
            "op": "set",
            "target_ref": target_ref,
            "subject": {"relative": "scenario"},
            "value": value,
            "source_ref": SCENARIO_SOURCE,
            "authority": "provisional",
        }
        if effects.get(effect_id) != expected_effect:
            errors.append(
                f"Phase B DODGE effect {effect_id} must normalize canonical consequence exactly"
            )


def _validate_phase_c_social_contract(dodge, canonical, errors):
    encounters = {
        row.get("id"): row
        for row in canonical.get("encounters", [])
        if isinstance(row, dict) and row.get("id")
    }
    encounter = encounters.get("frightened-witness")
    if not isinstance(encounter, dict):
        errors.append("Phase C requires canonical frightened-witness encounter")
        return

    state_contract = encounter.get("state_contract")
    if not isinstance(state_contract, dict):
        errors.append("Phase C frightened-witness requires state_contract")
        return
    refs = state_contract.get("refs")
    initial = state_contract.get("initial")
    if not isinstance(refs, dict) or set(refs) != {"status", "reaction", "information"}:
        errors.append(
            "Phase C frightened-witness state_contract.refs must define status/reaction/information"
        )
        return
    if not isinstance(initial, dict) or set(initial) != set(refs):
        errors.append(
            "Phase C frightened-witness state_contract.initial must define status/reaction/information"
        )
        return

    actions = encounter.get("actions")
    if not isinstance(actions, list) or len(actions) != 1:
        errors.append("Phase C frightened-witness must expose exactly one social action")
        return
    action = actions[0]
    if not isinstance(action, dict):
        errors.append("Phase C frightened-witness action must be an object")
        return
    if action.get("id") != "reassure-and-question":
        errors.append("Phase C frightened-witness action id must be reassure-and-question")
    if action.get("actor_ref") != "pc":
        errors.append("Phase C frightened-witness actor_ref must be pc")
    if action.get("procedure_ref") != "reaction-roll":
        errors.append("Phase C frightened-witness must bind reaction-roll")
    if action.get("source_ref") != SCENARIO_SOURCE:
        errors.append(
            f"Phase C frightened-witness action source_ref must be {SCENARIO_SOURCE}"
        )
    if action.get("authority") != "provisional":
        errors.append("Phase C frightened-witness action authority must be provisional")
    if action.get("provenance") != PC_PROVENANCE:
        errors.append(
            f"Phase C frightened-witness action provenance must be {PC_PROVENANCE}"
        )

    modifiers = action.get("reaction_modifiers")
    if not isinstance(modifiers, list) or len(modifiers) != 1:
        errors.append(
            "Phase C frightened-witness must declare exactly one bounded reaction modifier"
        )
    else:
        modifier = modifiers[0]
        if not isinstance(modifier, dict):
            errors.append("Phase C reaction modifier must be an object")
        else:
            expected_keys = {
                "id",
                "amount",
                "source_ref",
                "authority",
                "provenance",
                "rule_source_ref",
                "rule_locator",
                "reason",
            }
            if set(modifier) != expected_keys:
                errors.append(
                    "Phase C reassuring approach modifier must preserve the bounded declared shape"
                )
            if modifier.get("id") != "reassuring-approach":
                errors.append("Phase C reaction modifier id must be reassuring-approach")
            amount = modifier.get("amount")
            if not isinstance(amount, int) or isinstance(amount, bool):
                errors.append("Phase C reaction modifier amount must be integer")
            if modifier.get("source_ref") != SCENARIO_SOURCE:
                errors.append(
                    f"Phase C reaction modifier source_ref must be {SCENARIO_SOURCE}"
                )
            if modifier.get("authority") != "provisional":
                errors.append("Phase C reaction modifier authority must remain provisional")
            if modifier.get("provenance") != PC_PROVENANCE:
                errors.append(
                    f"Phase C reaction modifier provenance must be {PC_PROVENANCE}"
                )
            if modifier.get("rule_source_ref") != RULES_SOURCE:
                errors.append(
                    f"Phase C reaction modifier rule_source_ref must be {RULES_SOURCE}"
                )
            if modifier.get("rule_locator") != "p. 3, Reaction Modifiers":
                errors.append("Phase C reaction modifier rule locator is unsupported")
            if not isinstance(modifier.get("reason"), str) or not modifier.get("reason"):
                errors.append("Phase C reassuring approach modifier reason is required")

    procedure = (dodge.get("rules", {}).get("procedures", {}) or {}).get("reaction-roll")
    if not isinstance(procedure, dict):
        errors.append("Phase C requires DODGE reaction-roll procedure")
    else:
        if procedure.get("source_ref") != RULES_SOURCE:
            errors.append("Phase C reaction-roll procedure must use gurps-lite source")
        if procedure.get("authority") != "authoritative":
            errors.append("Phase C reaction-roll procedure must remain authoritative")
        if not isinstance(procedure.get("steps"), list) or not procedure.get("steps"):
            errors.append("Phase C reaction-roll procedure must preserve executable intent")

    reaction_order = [
        "disastrous",
        "very-bad",
        "bad",
        "poor",
        "neutral",
        "good",
        "very-good",
        "excellent",
    ]
    consequences = action.get("consequences")
    if not isinstance(consequences, dict) or list(consequences) != reaction_order:
        errors.append(
            "Phase C frightened-witness consequences must preserve Reaction Table order"
        )
        return
    for reaction in reaction_order:
        row = consequences.get(reaction)
        if not isinstance(row, dict):
            errors.append(f"Phase C {reaction} consequence must be an object")
            continue
        if set(row) != {"status", "reaction", "information", "information_text"}:
            errors.append(
                f"Phase C {reaction} consequence must define status/reaction/information/information_text"
            )
        if row.get("reaction") != reaction:
            errors.append(f"Phase C {reaction} consequence must preserve its reaction id")
        if row.get("status") != "resolved":
            errors.append(f"Phase C {reaction} consequence status must be resolved")
        if not isinstance(row.get("information_text"), str) or not row.get(
            "information_text"
        ):
            errors.append(f"Phase C {reaction} information_text is required")

    values = dodge.get("rules", {}).get("values", {}) or {}
    ordered_by_role = {
        "status": [initial.get("status")]
        + [consequences[r].get("status") for r in reaction_order],
        "reaction": [initial.get("reaction")]
        + [consequences[r].get("reaction") for r in reaction_order],
        "information": [initial.get("information")]
        + [consequences[r].get("information") for r in reaction_order],
    }
    for role, value_ref in refs.items():
        definition = values.get(value_ref)
        if not isinstance(definition, dict):
            errors.append(f"Phase C state ref {value_ref} must resolve in DODGE rules.values")
            continue
        enum_values = []
        for item in ordered_by_role[role]:
            if item not in enum_values:
                enum_values.append(item)
        expected_definition = {
            "name": definition.get("name"),
            "type": "enum",
            "owner_scope": "scenario",
            "persistence_scope": "scenario",
            "default": initial.get(role),
            "enum_values": enum_values,
            "source_ref": SCENARIO_SOURCE,
            "authority": "provisional",
        }
        if definition != expected_definition:
            errors.append(
                f"Phase C DODGE value {value_ref} must normalize canonical {role} state exactly"
            )

    initial_bindings = [
        {
            "ref": refs[role],
            "subject": {"relative": "scenario"},
            "value": initial[role],
            "authority": "provisional",
        }
        for role in ("status", "reaction", "information")
    ]
    runtime_state = (dodge.get("runtime_states") or {}).get(
        "scenario-01-frightened-witness-initial"
    )
    expected_runtime_state = {
        "scenario_ref": "scenario-01",
        "bindings": initial_bindings,
        "events": [],
        "revision": "0",
    }
    if runtime_state != expected_runtime_state:
        errors.append(
            "Phase C witness runtime state must normalize canonical initial state exactly"
        )

    effects = dodge.get("rules", {}).get("effects", {}) or {}
    expected_effects = {
        "frightened-witness-set-status-resolved": (
            refs["status"],
            "resolved",
        )
    }
    for reaction in reaction_order:
        expected_effects[f"frightened-witness-set-reaction-{reaction}"] = (
            refs["reaction"],
            reaction,
        )
    for information in ("no-useful-account", "partial-account", "useful-lead"):
        expected_effects[f"frightened-witness-set-information-{information}"] = (
            refs["information"],
            information,
        )
    for effect_id, (target_ref, value) in expected_effects.items():
        expected_effect = {
            "op": "set",
            "target_ref": target_ref,
            "subject": {"relative": "scenario"},
            "value": value,
            "source_ref": SCENARIO_SOURCE,
            "authority": "provisional",
        }
        if effects.get(effect_id) != expected_effect:
            errors.append(
                f"Phase C DODGE effect {effect_id} must normalize canonical witness consequence exactly"
            )


def _validate_phase_d_environment_contract(dodge, canonical, errors):
    encounters = {row.get("id"): row for row in canonical.get("encounters", []) if isinstance(row, dict)}
    encounter = encounters.get("washed-out-path")
    if not isinstance(encounter, dict):
        errors.append("Phase D requires canonical washed-out-path encounter")
        return
    state = encounter.get("state_contract") or {}
    refs = state.get("refs") or {}
    initial = state.get("initial") or {}
    if set(refs) != {"status", "outcome", "progress"} or set(initial) != set(refs):
        errors.append("Phase D washed-out-path state contract must define status/outcome/progress")
        return
    actions = encounter.get("actions") or []
    if len(actions) != 1 or not isinstance(actions[0], dict):
        errors.append("Phase D washed-out-path must expose exactly one environmental action")
        return
    action = actions[0]
    expected_identity = {
        "id": "cross-washed-out-path", "actor_ref": "pc", "action_ref": "attempt-attribute",
        "context_ref": "washed-out-path-dx", "source_ref": SCENARIO_SOURCE,
        "authority": "provisional", "provenance": PC_PROVENANCE,
    }
    for field, expected in expected_identity.items():
        if action.get(field) != expected:
            errors.append(f"Phase D washed-out-path action {field} must be {expected!r}")
    check = (canonical.get("contextual_checks") or {}).get(action.get("context_ref"))
    if not isinstance(check, dict):
        errors.append("Phase D environmental context_ref must resolve")
        return
    if check.get("encounter_ref") != "washed-out-path" or check.get("action_ref") != "attempt-attribute":
        errors.append("Phase D environmental contextual check identity is malformed")
    dodge_action = (dodge.get("rules", {}).get("actions", {}) or {}).get("attempt-attribute")
    expected_dodge_action = {
        "name": "Attempt attribute",
        "condition_refs": ["actor-conscious"],
        "procedure_ref": "success-roll",
        "source_ref": RULES_SOURCE,
        "authority": "authoritative",
    }
    if dodge_action != expected_dodge_action:
        errors.append(
            "Phase D DODGE attempt-attribute action must preserve the authoritative success-roll binding"
        )
    attribute_ref = check.get("attribute_ref")
    attributes = (canonical.get("player_character") or {}).get("attributes") or {}
    if attribute_ref not in attributes:
        errors.append("Phase D attribute_ref must resolve on canonical PC attributes")
    if check.get("provenance") != PC_PROVENANCE:
        errors.append("Phase D contextual check provenance must remain prototype_assumption")
    modifiers = check.get("modifiers")
    if not isinstance(modifiers, list) or not modifiers:
        errors.append("Phase D environmental check requires at least one modifier")
    else:
        for row in modifiers:
            if row.get("source_ref") != SCENARIO_SOURCE or row.get("authority") != "provisional" or row.get("provenance") != PC_PROVENANCE:
                errors.append("Phase D environmental modifier authority/provenance is malformed")
            if not isinstance(row.get("amount"), int) or isinstance(row.get("amount"), bool):
                errors.append("Phase D environmental modifier amount must be integer")
            if not isinstance(row.get("reason"), str) or not row.get("reason"):
                errors.append("Phase D environmental modifier reason is required")
    consequences = action.get("consequences") or {}
    if set(consequences) != {"success", "failure"}:
        errors.append("Phase D must define success and failure consequences")
        return
    values = dodge.get("rules", {}).get("values", {}) or {}
    ordered = {
        "status": [initial.get("status"), consequences["success"].get("status"), consequences["failure"].get("status")],
        "outcome": [initial.get("outcome"), consequences["success"].get("outcome"), consequences["failure"].get("outcome")],
        "progress": [initial.get("progress"), consequences["success"].get("progress"), consequences["failure"].get("progress")],
    }
    for role, ref in refs.items():
        unique = []
        for value in ordered[role]:
            if value not in unique: unique.append(value)
        definition = values.get(ref) or {}
        if (
            definition.get("type") != "enum"
            or definition.get("owner_scope") != "scenario"
            or definition.get("persistence_scope") != "scenario"
            or definition.get("default") != initial.get(role)
            or definition.get("enum_values") != unique
            or definition.get("source_ref") != SCENARIO_SOURCE
            or definition.get("authority") != "provisional"
        ):
            errors.append(f"Phase D DODGE value {ref} must normalize canonical {role} state exactly")
    runtime = (dodge.get("runtime_states") or {}).get("scenario-01-washed-out-path-initial") or {}
    expected_bindings = [
        {"ref": refs[role], "subject": {"relative": "scenario"}, "value": initial[role], "authority": "provisional"}
        for role in ("status","outcome","progress")
    ]
    if runtime != {"scenario_ref":"scenario-01","bindings":expected_bindings,"events":[],"revision":"0"}:
        errors.append("Phase D initial runtime state must normalize canonical environmental state exactly")
    expected_effects = {
        "washed-out-path-set-status-resolved": (refs["status"], consequences["success"].get("status")),
        "washed-out-path-set-outcome-success": (refs["outcome"], consequences["success"].get("outcome")),
        f"washed-out-path-set-progress-{consequences['success'].get('progress')}": (
            refs["progress"],
            consequences["success"].get("progress"),
        ),
        "washed-out-path-set-outcome-failure": (refs["outcome"], consequences["failure"].get("outcome")),
        f"washed-out-path-set-progress-{consequences['failure'].get('progress')}": (
            refs["progress"],
            consequences["failure"].get("progress"),
        ),
    }
    effects = dodge.get("rules", {}).get("effects", {}) or {}
    for effect_id, (target_ref, value) in expected_effects.items():
        expected = {"op":"set","target_ref":target_ref,"subject":{"relative":"scenario"},"value":value,"source_ref":SCENARIO_SOURCE,"authority":"provisional"}
        if effects.get(effect_id) != expected:
            errors.append(f"Phase D DODGE effect {effect_id} must normalize canonical consequence exactly")


def _validate_phase_e_combat_contract(dodge, canonical, errors):
    encounter = next(
        (
            row
            for row in canonical.get("encounters", [])
            if isinstance(row, dict) and row.get("id") == "bandit-scout"
        ),
        None,
    )
    if not isinstance(encounter, dict):
        errors.append("Phase E requires canonical bandit-scout encounter")
        return

    opponent = encounter.get("opponent")
    if not isinstance(opponent, dict):
        errors.append("Phase E bandit-scout requires canonical opponent data")
        return
    if opponent.get("actor_ref") != "bandit-scout":
        errors.append("Phase E opponent actor_ref must be bandit-scout")
    if opponent.get("provenance") != PC_PROVENANCE:
        errors.append("Phase E opponent provenance must be prototype_assumption")
    attributes = opponent.get("attributes")
    if not isinstance(attributes, dict) or set(attributes) != {"st", "dx", "ht"}:
        errors.append("Phase E bounded opponent attributes must define exactly ST/DX/HT")
        attributes = {}
    for ref in ("st", "dx", "ht"):
        value = attributes.get(ref)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            errors.append(f"Phase E opponent attribute {ref} must be a positive integer")

    opponent_state = opponent.get("state")
    if not isinstance(opponent_state, dict) or set(opponent_state) != {
        "hit_points", "stunned", "unconscious"
    }:
        errors.append("Phase E bounded opponent state must define HP/stunned/unconscious")
        opponent_state = {}
    if not isinstance(opponent_state.get("hit_points"), int) or isinstance(
        opponent_state.get("hit_points"), bool
    ):
        errors.append("Phase E opponent hit_points must be an integer")
    for ref in ("stunned", "unconscious"):
        if not isinstance(opponent_state.get(ref), bool):
            errors.append(f"Phase E opponent {ref} must be boolean")
        elif opponent_state.get(ref) is not False:
            errors.append(f"Phase E bounded combat requires initial {ref} == false")

    assumptions = opponent.get("defense_assumptions")
    if not isinstance(assumptions, dict) or set(assumptions) != {
        "aware_of_attack", "encumbrance_penalty", "armor_dr", "passive_defense"
    }:
        errors.append("Phase E defense assumptions must define awareness/encumbrance/DR/passive defense")
        assumptions = {}
    if assumptions.get("aware_of_attack") is not True:
        errors.append("Phase E bounded Dodge slice requires an aware defender")
    for ref in ("encumbrance_penalty", "armor_dr", "passive_defense"):
        value = assumptions.get(ref)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"Phase E defense assumption {ref} must be a nonnegative integer")
    if encounter.get("bounded_combat") != {"maximum_exchanges": 1}:
        errors.append("Phase E combat scope must remain exactly one exchange")

    actions = encounter.get("actions")
    if not isinstance(actions, list) or len(actions) != 1:
        errors.append("Phase E bandit-scout must expose exactly one supported combat action")
        return
    action = actions[0]
    expected_action = {
        "id": "strike-bandit-scout",
        "label": "Attack the bandit scout with Rook's broadsword",
        "actor_ref": "pc",
        "target_ref": "bandit-scout",
        "action_ref": "attack",
        "skill_ref": "broadsword",
        "weapon_ref": "broadsword",
        "attack_mode": "swing-cut",
        "source_ref": SCENARIO_SOURCE,
        "authority": "provisional",
        "provenance": PC_PROVENANCE,
        "supported_defense": "dodge",
    }
    if action != expected_action:
        errors.append("Phase E combat action must match the bounded broadsword/Dodge contract")

    pc = canonical.get("player_character") or {}
    if (pc.get("skills") or {}).get("broadsword") is None:
        errors.append("Phase E requires canonical PC broadsword skill")
    if "broadsword" not in (pc.get("equipment") or []):
        errors.append("Phase E requires canonical PC broadsword equipment")

    scenario, scene = _scene_for_scenario(dodge)
    instances = _instance_map(scene)
    bandit = instances.get("bandit-scout") or {}
    bandit_state = bandit.get("state") or {}
    expected_actor_state = {
        "st": attributes.get("st"),
        "dx": attributes.get("dx"),
        "ht": attributes.get("ht"),
        "hit-points": opponent_state.get("hit_points"),
        "stunned": opponent_state.get("stunned"),
        "unconscious": opponent_state.get("unconscious"),
    }
    for ref, expected in expected_actor_state.items():
        if bandit_state.get(ref) != expected:
            errors.append(
                f"Phase E bandit DODGE scene state {ref} must equal canonical value {expected!r}"
            )

    value = (dodge.get("rules", {}).get("values", {}) or {}).get(
        "consciousness-check-required"
    )
    expected_value = {
        "name": "Consciousness check required",
        "type": "boolean",
        "default": False,
        "source_ref": PROTO_SOURCE,
        "authority": "provisional",
        "owner_scope": "actor",
        "persistence_scope": "scenario",
        "assumptions": [
            "Materializes the GURPS Lite beginning-of-turn consciousness-check obligation after HP reaches 0 or less; Phase F consumes the obligation while the actor remains conscious."
        ],
    }
    if value != expected_value:
        errors.append(
            "Phase E consciousness-check-required DODGE value must match the declared deferred Phase F contract"
        )

    runtime = (dodge.get("runtime_states") or {}).get(
        "scenario-01-bandit-scout-initial"
    )
    expected_runtime = {
        "scenario_ref": "scenario-01",
        "bindings": [
            {
                "ref": "hit-points",
                "subject": {"instance_ref": "bandit-scout"},
                "value": opponent_state.get("hit_points"),
                "authority": "provisional",
            },
            {
                "ref": "stunned",
                "subject": {"instance_ref": "bandit-scout"},
                "value": opponent_state.get("stunned"),
                "authority": "provisional",
            },
            {
                "ref": "unconscious",
                "subject": {"instance_ref": "bandit-scout"},
                "value": opponent_state.get("unconscious"),
                "authority": "provisional",
            },
            {
                "ref": "consciousness-check-required",
                "subject": {"instance_ref": "bandit-scout"},
                "value": False,
                "authority": "provisional",
            },
        ],
        "events": [],
        "revision": "0",
    }
    if runtime != expected_runtime:
        errors.append(
            "Phase E bandit combat runtime state must normalize canonical opponent state exactly"
        )


def _validate_phase_f_recovery_contract(dodge, canonical, errors):
    encounter = next(
        (
            row
            for row in canonical.get("encounters", [])
            if isinstance(row, dict) and row.get("id") == "bandit-scout"
        ),
        None,
    )
    if not isinstance(encounter, dict):
        errors.append("Phase F requires canonical bandit-scout encounter")
        return

    recovery = encounter.get("post_combat_recovery")
    if not isinstance(recovery, dict):
        errors.append("Phase F bandit-scout requires post_combat_recovery")
        return

    action = recovery.get("action")
    expected_action = {
        "id": "resolve-bandit-next-turn",
        "label": "Resolve the bandit scout's next-turn injury checks",
        "actor_ref": "bandit-scout",
        "action_ref": "recover",
        "source_ref": SCENARIO_SOURCE,
        "authority": "provisional",
        "provenance": PC_PROVENANCE,
    }
    if action != expected_action:
        errors.append("Phase F recovery action must match the bounded next-turn contract")

    if recovery.get("timing") != "next-turn-start":
        errors.append("Phase F recovery timing must be next-turn-start")
    if recovery.get("resolution_order") != ["consciousness", "stun-recovery"]:
        errors.append(
            "Phase F recovery order must be consciousness then stun-recovery"
        )
    if recovery.get("long_term_unconscious_recovery") != "unsupported":
        errors.append(
            "Phase F must keep long-term unconscious recovery explicitly unsupported"
        )

    consciousness = recovery.get("consciousness")
    if not isinstance(consciousness, dict):
        errors.append("Phase F recovery requires consciousness assumptions")
    else:
        modifier = consciousness.get("will_modifier")
        if not isinstance(modifier, int) or isinstance(modifier, bool):
            errors.append("Phase F consciousness will_modifier must be an integer")
        if consciousness.get("modifier_source_ref") != SCENARIO_SOURCE:
            errors.append(
                "Phase F consciousness modifier_source_ref must be scenario-01-source"
            )
        if consciousness.get("authority") != "provisional":
            errors.append("Phase F consciousness modifier must remain provisional")
        if consciousness.get("provenance") != PC_PROVENANCE:
            errors.append(
                "Phase F consciousness modifier provenance must be prototype_assumption"
            )

    actions = dodge.get("rules", {}).get("actions", {}) or {}
    procedures = dodge.get("rules", {}).get("procedures", {}) or {}
    recover_action = actions.get("recover")
    if not isinstance(recover_action, dict) or recover_action.get("procedure_ref") != "recovery-check":
        errors.append("Phase F DODGE recover action must resolve recovery-check")
    if "recovery-check" not in procedures:
        errors.append("Phase F DODGE recovery-check procedure is required")

    effects = dodge.get("rules", {}).get("effects", {}) or {}
    expected_effects = {
        "phase-f-bandit-set-unconscious": {
            "op": "set",
            "target_ref": "unconscious",
            "subject": {"instance_ref": "bandit-scout"},
            "value": True,
            "source_ref": RULES_SOURCE,
            "authority": "authoritative",
        },
        "phase-f-bandit-clear-consciousness-check-required": {
            "op": "set",
            "target_ref": "consciousness-check-required",
            "subject": {"instance_ref": "bandit-scout"},
            "value": False,
            "source_ref": PROTO_SOURCE,
            "authority": "provisional",
        },
        "phase-f-bandit-clear-stunned": {
            "op": "set",
            "target_ref": "stunned",
            "subject": {"instance_ref": "bandit-scout"},
            "value": False,
            "source_ref": RULES_SOURCE,
            "authority": "authoritative",
        },
    }
    for effect_id, expected in expected_effects.items():
        if effects.get(effect_id) != expected:
            errors.append(
                f"Phase F DODGE effect {effect_id} must match the declared recovery consequence"
            )



def _validate_phase_g_progression_contract(dodge, canonical, errors):
    progression = canonical.get("progression")
    if not isinstance(progression, dict):
        errors.append("Phase G requires canonical progression")
        return
    if progression.get("source_ref") != SCENARIO_SOURCE:
        errors.append("Phase G progression source_ref must be scenario-01-source")
    if progression.get("authority") != "provisional":
        errors.append("Phase G progression authority must remain provisional")
    if progression.get("provenance") != PC_PROVENANCE:
        errors.append("Phase G progression provenance must be prototype_assumption")
    if progression.get("runtime_state_ref") != "scenario-01-playable-initial":
        errors.append("Phase G progression must use scenario-01-playable-initial")

    encounter_ids = [
        row.get("id")
        for row in canonical.get("encounters", [])
        if isinstance(row, dict) and row.get("id")
    ]
    order = progression.get("encounter_order")
    if order != encounter_ids:
        errors.append("Phase G encounter_order must exactly follow canonical encounter order")
        return
    if len(order) != len(set(order)) or set(order) != {
        "roadside-tracks",
        "frightened-witness",
        "washed-out-path",
        "bandit-scout",
    }:
        errors.append("Phase G bounded encounter_order must contain each accepted encounter exactly once")
        return

    contract = progression.get("state_contract")
    if not isinstance(contract, dict):
        errors.append("Phase G progression requires state_contract")
        return
    refs = contract.get("refs")
    initial = contract.get("initial")
    expected_refs = {
        "status": "scenario-progress-status",
        "current_encounter": "scenario-current-encounter",
        "step": "scenario-progress-step",
        "outcome": "scenario-outcome",
        "information": "scenario-completion-information",
    }
    if refs != expected_refs:
        errors.append("Phase G progress refs must match the declared neutral DODGE state")
        return
    expected_initial = {
        "status": "in-progress",
        "current_encounter": order[0],
        "step": "action",
        "outcome": "undetermined",
        "information": "accumulating",
    }
    if initial != expected_initial:
        errors.append("Phase G initial progress state must start at the first canonical encounter")

    completion = progression.get("completion")
    if not isinstance(completion, dict) or completion.get("objective_id") != "resolve-courier-mystery":
        errors.append("Phase G completion must bind resolve-courier-mystery")
        return
    branches = {
        "success": {
            "trigger": {"encounter_ref": "bandit-scout", "bandit_can_act_normally": False},
            "state": {
                "status": "complete",
                "current_encounter": "complete",
                "step": "complete",
                "outcome": "success",
                "information": "courier-fate-established",
            },
        },
        "failure": {
            "trigger": {"encounter_ref": "bandit-scout", "bandit_can_act_normally": True},
            "state": {
                "status": "complete",
                "current_encounter": "complete",
                "step": "complete",
                "outcome": "failure",
                "information": "courier-fate-unresolved",
            },
        },
    }
    for branch, expected in branches.items():
        row = completion.get(branch)
        if not isinstance(row, dict):
            errors.append(f"Phase G completion branch {branch} is required")
            continue
        if row.get("trigger") != expected["trigger"] or row.get("state") != expected["state"]:
            errors.append(f"Phase G completion branch {branch} is malformed")
        if not isinstance(row.get("conclusion_text"), str) or not row.get("conclusion_text"):
            errors.append(f"Phase G completion branch {branch} requires conclusion_text")

    unsupported = progression.get("unsupported")
    if not isinstance(unsupported, list) or not unsupported:
        errors.append("Phase G must declare unsupported progression branches explicitly")

    values = (dodge.get("rules") or {}).get("values") or {}
    value_expectations = {
        refs["status"]: ("in-progress", ["in-progress", "complete"]),
        refs["current_encounter"]: (
            order[0],
            ["roadside-tracks", "frightened-witness", "washed-out-path", "bandit-scout", "complete"],
        ),
        refs["step"]: ("action", ["action", "recovery", "complete"]),
        refs["outcome"]: ("undetermined", ["undetermined", "success", "failure"]),
        refs["information"]: (
            "accumulating",
            ["accumulating", "courier-fate-established", "courier-fate-unresolved"],
        ),
    }
    for ref, (default, enum_values) in value_expectations.items():
        definition = values.get(ref)
        if not isinstance(definition, dict):
            errors.append(f"Phase G DODGE value is missing: {ref}")
            continue
        if (
            definition.get("type") != "enum"
            or definition.get("owner_scope") != "scenario"
            or definition.get("persistence_scope") != "scenario"
            or definition.get("default") != default
            or set(definition.get("enum_values") or []) != set(enum_values)
            or definition.get("source_ref") != SCENARIO_SOURCE
            or definition.get("authority") != "provisional"
        ):
            errors.append(f"Phase G DODGE value {ref} must normalize canonical progress state")

    conditions = (dodge.get("rules") or {}).get("conditions") or {}
    expected_conditions = {
        "scenario-success": {
            "op": "eq",
            "left": {"ref": refs["outcome"], "subject": {"relative": "scenario"}},
            "right": "success",
            "source_ref": SCENARIO_SOURCE,
            "authority": "provisional",
        },
        "scenario-failure": {
            "op": "eq",
            "left": {"ref": refs["outcome"], "subject": {"relative": "scenario"}},
            "right": "failure",
            "source_ref": SCENARIO_SOURCE,
            "authority": "provisional",
        },
    }
    for condition_id, expected in expected_conditions.items():
        if conditions.get(condition_id) != expected:
            errors.append(f"Phase G DODGE condition {condition_id} must match the terminal state")

    scenario = (dodge.get("scenarios") or {}).get("scenario-01") or {}
    expected_objective = {
        "id": "resolve-courier-mystery",
        "name": "Determine what happened to the missing courier",
        "completion": "scenario-success",
    }
    if scenario.get("objectives") != [expected_objective]:
        errors.append("Phase G objective completion must reference scenario-success")
    expected_end_conditions = [
        {"id": "missing-courier-success", "outcome": "win", "condition": "scenario-success", "priority": 1},
        {"id": "missing-courier-failure", "outcome": "loss", "condition": "scenario-failure", "priority": 2},
    ]
    if scenario.get("end_conditions") != expected_end_conditions:
        errors.append("Phase G DODGE end_conditions must define deterministic win/loss semantics")

    runtime_states = dodge.get("runtime_states") or {}
    expected_bindings = []
    for state_ref in (
        "scenario-01-initial",
        "scenario-01-frightened-witness-initial",
        "scenario-01-washed-out-path-initial",
        "scenario-01-bandit-scout-initial",
    ):
        state = runtime_states.get(state_ref)
        if not isinstance(state, dict):
            errors.append(f"Phase G requires accepted runtime state {state_ref}")
            continue
        expected_bindings.extend(copy.deepcopy(state.get("bindings", [])))
    for role in ("status", "current_encounter", "step", "outcome", "information"):
        expected_bindings.append(
            {
                "ref": refs[role],
                "subject": {"relative": "scenario"},
                "value": initial[role],
                "authority": "provisional",
            }
        )
    expected_runtime = {
        "scenario_ref": "scenario-01",
        "bindings": expected_bindings,
        "events": [],
        "revision": "0",
    }
    if runtime_states.get(progression.get("runtime_state_ref")) != expected_runtime:
        errors.append("Phase G playable runtime state must compose accepted encounter state plus progress state")

    effects = (dodge.get("rules") or {}).get("effects") or {}
    effect_expectations = {
        "phase-g-current-frightened-witness": (refs["current_encounter"], "frightened-witness"),
        "phase-g-current-washed-out-path": (refs["current_encounter"], "washed-out-path"),
        "phase-g-current-bandit-scout": (refs["current_encounter"], "bandit-scout"),
        "phase-g-current-complete": (refs["current_encounter"], "complete"),
        "phase-g-step-recovery": (refs["step"], "recovery"),
        "phase-g-step-complete": (refs["step"], "complete"),
        "phase-g-status-complete": (refs["status"], "complete"),
        "phase-g-outcome-success": (refs["outcome"], completion["success"]["state"]["outcome"]),
        "phase-g-outcome-failure": (refs["outcome"], completion["failure"]["state"]["outcome"]),
        "phase-g-information-success": (refs["information"], completion["success"]["state"]["information"]),
        "phase-g-information-failure": (refs["information"], completion["failure"]["state"]["information"]),
    }
    for effect_id, (target_ref, value) in effect_expectations.items():
        expected = {
            "op": "set",
            "target_ref": target_ref,
            "subject": {"relative": "scenario"},
            "value": value,
            "source_ref": SCENARIO_SOURCE,
            "authority": "provisional",
        }
        if effects.get(effect_id) != expected:
            errors.append(f"Phase G DODGE effect {effect_id} must normalize canonical progression")


def validate_source_semantics(dodge, canonical, config=None):
    """Return bounded DIRPS G3 source-stage semantic-profile violations."""
    errors = []
    if not isinstance(canonical, dict):
        return ["DIRPS canonical scenario source is required"]

    _validate_authority_paths(dodge, canonical, config, errors)
    _validate_source_roles(dodge, errors)
    _validate_actor_model(dodge, canonical, errors)
    _validate_rule_meaning(dodge, errors)
    _validate_scenario_duplication(dodge, canonical, errors)
    _validate_phase_a_contextual_checks(dodge, canonical, errors)
    _validate_phase_b_investigation_contract(dodge, canonical, errors)
    _validate_phase_c_social_contract(dodge, canonical, errors)
    _validate_phase_d_environment_contract(dodge, canonical, errors)
    _validate_phase_e_combat_contract(dodge, canonical, errors)
    _validate_phase_f_recovery_contract(dodge, canonical, errors)
    _validate_phase_g_progression_contract(dodge, canonical, errors)
    return errors


def validate_source_context(context):
    """Generic TheFountain source-stage conformance hook."""
    errors = validate_source_semantics(
        context["dodge"],
        context["scenario_source"],
        context.get("config"),
    )
    maturity = ((context.get("config") or {}).get("conformance") or {}).get("maturity")
    if maturity in {"G5", "G6", "G7"}:
        _validate_g5_proto_semantics(
            _registered_sidecar(context.get("config")),
            errors,
            context["dodge"],
            context["scenario_source"],
        )
    return errors

def _resolved_unresolved_index(sidecar):
    return [
        {
            "proto_ref": proto_id,
            "status": spec.get("status"),
            "candidate_for_dodge": spec.get("candidate_for_dodge"),
        }
        for proto_id, spec in sorted((sidecar.get("proto_specs") or {}).items())
    ]


def _expected_resolved_instance(dodge, canonical, instance):
    object_ref = instance.get("object_ref")
    obj = dodge.get("objects", {}).get(object_ref, {})
    archetype = dodge.get("archetypes", {}).get(obj.get("archetype_ref"), {})
    row = {
        "id": instance.get("id"),
        "object_ref": object_ref,
        "kind": obj.get("kind"),
        "name": obj.get("name"),
        "tags": obj.get("tags", []),
        "faces": obj.get("faces", []),
        "component": archetype.get("component"),
        "state": instance.get("state", {}),
        "extensions": instance.get("extensions", {}),
    }
    pc = canonical.get("player_character") or {}
    if instance.get("id") == pc.get("id"):
        row["character"] = {
            "provenance": pc.get("provenance"),
            "primary_attributes": pc.get("attributes", {}),
            "skills": pc.get("skills", {}),
            "equipment": pc.get("equipment", []),
        }
    return row


def validate_resolved_semantics(resolved, dodge, canonical, sidecar):
    """Validate the exact DIRPS G4 target-neutral model against authoritative inputs."""
    errors = []
    if not isinstance(resolved, dict):
        return ["resolved game must be an object"]
    if resolved.get("format") != "dirps-resolved-game.v1":
        return ["resolved game: unexpected format"]

    expected_identity = {
        "dodge_version": dodge.get("dodge_version"),
        "document_id": dodge.get("document_id"),
        "game_id": dodge.get("game_id"),
        "scenario_id": "scenario-01",
    }
    for field, expected in expected_identity.items():
        if resolved.get(field) != expected:
            errors.append(
                f"resolved game: {field} must be {expected!r}, got {resolved.get(field)!r}"
            )

    if resolved.get("sources") != dodge.get("sources"):
        errors.append("resolved game: sources must preserve the DODGE source declarations exactly")
    for field, default in (
        ("game_profile", {}),
        ("archetypes", {}),
        ("objects", {}),
        ("sidecars", []),
        ("extensions", {}),
        ("runtime_states", {}),
    ):
        if resolved.get(field) != dodge.get(field, default):
            errors.append(
                f"resolved game: DODGE {field} changed or disappeared during resolution"
            )

    canonical_source = resolved.get("canonical_source") or {}
    expected_canonical_source = {
        "source_ref": SCENARIO_SOURCE,
        "schema_version": canonical.get("schema_version"),
        "dataset_id": canonical.get("dataset_id"),
        "status": canonical.get("status"),
        "authority": canonical.get("authority"),
        "implementation_boundary": canonical.get("implementation_boundary"),
    }
    if canonical_source != expected_canonical_source:
        errors.append("resolved game: canonical_source does not match Scenario 01 authority/provenance")

    dodge_scenario = dodge.get("scenarios", {}).get("scenario-01") or {}
    tutorial = canonical.get("tutorial") or {}
    expected_scenario = {
        "name": dodge_scenario.get("name"),
        "description": dodge_scenario.get("description"),
        "players": dodge_scenario.get("players"),
        "source_ref": dodge_scenario.get("source_ref"),
        "authority": dodge_scenario.get("authority"),
        "assumptions": dodge_scenario.get("assumptions", []),
        "scene_ref": dodge_scenario.get("scene_ref"),
        "premise": tutorial.get("premise"),
        "design_goal": tutorial.get("design_goal"),
        "target_duration_minutes": tutorial.get("target_minutes"),
        "action_refs": dodge_scenario.get("action_refs", []),
        "turn_procedure_ref": dodge_scenario.get("turn_procedure_ref"),
        "objectives": dodge_scenario.get("objectives", []),
        "end_conditions": dodge_scenario.get("end_conditions", []),
        "initial_state": dodge_scenario.get("initial_state", []),
        "encounters": canonical.get("encounters", []),
        "progression": canonical.get("progression", {}),
        "contextual_checks": canonical.get("contextual_checks", {}),
    }
    if resolved.get("scenario") != expected_scenario:
        errors.append(
            "resolved game: scenario must preserve DODGE bindings and canonical fiction/order/duration"
        )

    if resolved.get("rules") != dodge.get("rules"):
        errors.append("resolved game: normalized DODGE rules were dropped, changed, or invented")

    scene_ref = dodge_scenario.get("scene_ref")
    source_scene = dodge.get("scenes", {}).get(scene_ref) or {}
    resolved_scene = resolved.get("scene") or {}
    if resolved_scene.get("id") != scene_ref:
        errors.append(f"resolved game: scene id must be {scene_ref}")
    if resolved_scene.get("name") != source_scene.get("name"):
        errors.append("resolved game: scene name changed during resolution")
    if resolved_scene.get("source_ref") != source_scene.get("source_ref"):
        errors.append("resolved game: scene source_ref changed during resolution")

    expected_instances = [
        _expected_resolved_instance(dodge, canonical, instance)
        for instance in source_scene.get("instances", [])
    ]
    if resolved_scene.get("instances") != expected_instances:
        errors.append(
            "resolved game: selected scene instances are incomplete, reordered, or inconsistent"
        )

    pc_id = (canonical.get("player_character") or {}).get("id")
    resolved_pc = next(
        (row for row in resolved_scene.get("instances", []) if row.get("id") == pc_id),
        None,
    )
    if not resolved_pc:
        errors.append("resolved game: canonical player character is missing from the scene")
    else:
        character = resolved_pc.get("character") or {}
        if character.get("primary_attributes") != (canonical.get("player_character") or {}).get("attributes"):
            errors.append("resolved game: canonical primary PC build did not survive resolution")
        state = resolved_pc.get("state") or {}
        for attribute_id, value in character.get("primary_attributes", {}).items():
            if state.get(attribute_id) != value:
                errors.append(
                    f"resolved game: PC primary attribute {attribute_id} disagrees with resolved actor state"
                )

    if resolved.get("proto_sidecar") != sidecar:
        errors.append("resolved game: DIRPS proto sidecar semantics were dropped or changed")

    # G5 and later gameplay tranches make these proto contracts executable;
    # resolved validation must continue to guard their exact authority/status boundary.
    if (canonical.get("status") or "").startswith(("g5-", "g6-")):
        _validate_g5_proto_semantics(sidecar, errors, dodge, canonical)

    expected_unresolved = _resolved_unresolved_index(sidecar)
    if resolved.get("unresolved") != expected_unresolved:
        errors.append("resolved game: unresolved proto index must be derived exactly from the sidecar")

    forbidden = {"runtime", "replay", "target_manifest", "execution_results"}
    present = sorted(forbidden.intersection(resolved))
    if present:
        errors.append(f"resolved game: G5/G6 material is out of scope at G4: {present}")

    return errors


def validate_resolved_context(context):
    """Generic TheFountain resolved-game conformance hook."""
    sidecars = (context.get("config") or {}).get("sidecars") or []
    if len(sidecars) != 1 or not sidecars[0].is_file():
        return ["DIRPS resolved validation requires exactly one registered proto sidecar"]
    sidecar = json.loads(sidecars[0].read_text())
    return validate_resolved_semantics(
        context["resolved"],
        context["dodge"],
        context["scenario_source"],
        sidecar,
    )


def require_source_semantics(dodge, canonical, config=None):
    errors = validate_source_semantics(dodge, canonical, config)
    if errors:
        raise ValueError("DIRPS source semantic validation failed:\n" + "\n".join(errors))


def require_resolved_semantics(resolved, dodge, canonical, sidecar):
    errors = validate_resolved_semantics(resolved, dodge, canonical, sidecar)
    if errors:
        raise ValueError("DIRPS resolved semantic validation failed:\n" + "\n".join(errors))

