#!/usr/bin/env python3
"""DIRPS-owned semantic validation profile for Scenario 01.

DODGE core validates neutral structure. This module validates bounded DIRPS
cross-source/domain contracts that generic DODGE cannot infer. It intentionally
implements source-stage G3 only; resolved-game validation belongs to G4.
"""
from __future__ import annotations

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
    "attack": "attack-resolution",
    "recover": "recovery-check",
}


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
    if not config:
        return

    authority = canonical.get("authority", {})
    expected_dodge = _repo_relative(config.get("dodge"))
    expected_source = _repo_relative(config.get("source"))
    sidecars = config.get("sidecars") or []
    expected_sidecar = _repo_relative(sidecars[0]) if len(sidecars) == 1 else None

    if authority.get("rules") != RULES_AUTHORITY_LABEL:
        errors.append(
            "canonical authority.rules must identify the bounded GURPS Lite June 2003 rules authority"
        )
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
    return errors


def validate_source_context(context):
    """Generic TheFountain source-stage conformance hook."""
    return validate_source_semantics(
        context["dodge"],
        context["scenario_source"],
        context.get("config"),
    )
