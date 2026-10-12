#!/usr/bin/env python3
"""Target-neutral DIRPS Scenario 01 resolver for DODGE 0.2.1 G4."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from dirps_semantic_validation import (
    validate_resolved_semantics,
    validate_source_semantics,
)
from game_registry import ROOT, scenario_config

DIRPS_SCENARIO = scenario_config("dirps", "scenario-01")
DEFAULT_DODGE = DIRPS_SCENARIO["dodge"]

SCENARIO_SOURCE = "scenario-01-source"
PROTO_SOURCE = "dirps-proto"


class ResolutionError(ValueError):
    pass


def _load(path):
    return json.loads(Path(path).read_text())


def _local_source_path(dodge, source_ref):
    try:
        source = dodge["sources"][source_ref]
    except KeyError as exc:
        raise ResolutionError(f"missing declared source {source_ref}") from exc
    uri = source.get("uri", "")
    file_uri = uri.partition("#")[0]
    if not file_uri or "://" in file_uri:
        raise ResolutionError(
            f"{source_ref}: resolver requires a repository-local source URI, got {uri!r}"
        )
    path = (ROOT / file_uri).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ResolutionError(f"{source_ref}: source URI escapes repository root") from exc
    if not path.is_file():
        raise ResolutionError(f"{source_ref}: source file not found: {file_uri}")
    return path


def _resolved_instance(dodge, canonical, instance):
    object_ref = instance["object_ref"]
    try:
        obj = dodge["objects"][object_ref]
    except KeyError as exc:
        raise ResolutionError(
            f"scene instance {instance.get('id')}: unknown object_ref {object_ref}"
        ) from exc
    archetype_ref = obj.get("archetype_ref")
    try:
        archetype = dodge["archetypes"][archetype_ref]
    except KeyError as exc:
        raise ResolutionError(
            f"object {object_ref}: unknown archetype_ref {archetype_ref}"
        ) from exc

    row = {
        "id": instance["id"],
        "object_ref": object_ref,
        "kind": obj.get("kind"),
        "name": obj.get("name"),
        "tags": copy.deepcopy(obj.get("tags", [])),
        "faces": copy.deepcopy(obj.get("faces", [])),
        "component": copy.deepcopy(archetype.get("component")),
        "state": copy.deepcopy(instance.get("state", {})),
        "extensions": copy.deepcopy(instance.get("extensions", {})),
    }

    pc = canonical.get("player_character") or {}
    if instance["id"] == pc.get("id"):
        row["character"] = {
            "provenance": pc.get("provenance"),
            "primary_attributes": copy.deepcopy(pc.get("attributes", {})),
            "skills": copy.deepcopy(pc.get("skills", {})),
            "equipment": copy.deepcopy(pc.get("equipment", [])),
        }
    return row


def _unresolved_index(sidecar):
    return [
        {
            "proto_ref": proto_id,
            "status": spec.get("status"),
            "candidate_for_dodge": spec.get("candidate_for_dodge"),
        }
        for proto_id, spec in sorted((sidecar.get("proto_specs") or {}).items())
    ]


def resolve_documents(dodge, canonical, sidecar, config=None):
    """Resolve already-loaded G3-valid DIRPS documents into one neutral G4 model."""
    if dodge.get("dodge_version") != "0.2.1":
        raise ResolutionError("DIRPS G4 requires DODGE 0.2.1")
    if dodge.get("game_id") != "dirps":
        raise ResolutionError("DIRPS G4 resolver received a non-DIRPS document")

    source_errors = validate_source_semantics(dodge, canonical, config)
    if source_errors:
        raise ResolutionError(
            "DIRPS source semantic validation failed before resolution:\n  "
            + "\n  ".join(source_errors)
        )

    proto_source = dodge.get("sources", {}).get(PROTO_SOURCE) or {}
    if sidecar.get("sidecar_version") != proto_source.get("version"):
        raise ResolutionError(
            "DIRPS proto sidecar version must match the declared dirps-proto source version"
        )
    if sidecar.get("game_id") != "dirps":
        raise ResolutionError("DIRPS proto sidecar game_id must be dirps")
    if sidecar.get("dodge_target_version") != dodge.get("dodge_version"):
        raise ResolutionError(
            "DIRPS proto sidecar dodge_target_version must match the DODGE document"
        )
    if not isinstance(sidecar.get("proto_specs"), dict) or not sidecar["proto_specs"]:
        raise ResolutionError("DIRPS proto sidecar must preserve its proto_specs")

    scenario = (dodge.get("scenarios") or {}).get("scenario-01")
    if not scenario:
        raise ResolutionError("DIRPS DODGE document is missing scenario-01")
    scene_ref = scenario.get("scene_ref")
    scene = (dodge.get("scenes") or {}).get(scene_ref)
    if not scene:
        raise ResolutionError(f"DIRPS scenario-01 scene_ref does not resolve: {scene_ref}")

    tutorial = canonical.get("tutorial") or {}
    resolved = {
        "format": "dirps-resolved-game.v1",
        "dodge_version": dodge["dodge_version"],
        "document_id": dodge["document_id"],
        "game_id": dodge["game_id"],
        "scenario_id": "scenario-01",
        "canonical_source": {
            "source_ref": SCENARIO_SOURCE,
            "schema_version": canonical.get("schema_version"),
            "dataset_id": canonical.get("dataset_id"),
            "status": canonical.get("status"),
            "authority": copy.deepcopy(canonical.get("authority")),
            "implementation_boundary": copy.deepcopy(
                canonical.get("implementation_boundary")
            ),
        },
        "sources": copy.deepcopy(dodge.get("sources", {})),
        "game_profile": copy.deepcopy(dodge.get("game_profile", {})),
        "archetypes": copy.deepcopy(dodge.get("archetypes", {})),
        "objects": copy.deepcopy(dodge.get("objects", {})),
        "sidecars": copy.deepcopy(dodge.get("sidecars", [])),
        "extensions": copy.deepcopy(dodge.get("extensions", {})),
        "scenario": {
            "name": scenario.get("name"),
            "description": scenario.get("description"),
            "players": copy.deepcopy(scenario.get("players")),
            "source_ref": scenario.get("source_ref"),
            "authority": scenario.get("authority"),
            "assumptions": copy.deepcopy(scenario.get("assumptions", [])),
            "scene_ref": scene_ref,
            "premise": tutorial.get("premise"),
            "design_goal": tutorial.get("design_goal"),
            "target_duration_minutes": copy.deepcopy(tutorial.get("target_minutes")),
            "action_refs": copy.deepcopy(scenario.get("action_refs", [])),
            "turn_procedure_ref": scenario.get("turn_procedure_ref"),
            "objectives": copy.deepcopy(scenario.get("objectives", [])),
            # List order is canonical Scenario 01 encounter order.
            "encounters": copy.deepcopy(canonical.get("encounters", [])),
        },
        "scene": {
            "id": scene_ref,
            "name": scene.get("name"),
            "source_ref": scene.get("source_ref"),
            "instances": [
                _resolved_instance(dodge, canonical, instance)
                for instance in scene.get("instances", [])
            ],
        },
        "rules": copy.deepcopy(dodge.get("rules", {})),
        # Preserve unsupported semantics losslessly as unresolved source material.
        "proto_sidecar": copy.deepcopy(sidecar),
        # Convenience index is derived only; it does not promote or execute proto specs.
        "unresolved": _unresolved_index(sidecar),
    }

    resolved_errors = validate_resolved_semantics(
        resolved, dodge, canonical, sidecar
    )
    if resolved_errors:
        raise ResolutionError(
            "DIRPS resolved-game validation failed during resolution:\n  "
            + "\n  ".join(resolved_errors)
        )
    return resolved


def resolve(dodge_path=DEFAULT_DODGE):
    dodge = _load(dodge_path)
    canonical = _load(_local_source_path(dodge, SCENARIO_SOURCE))
    sidecar = _load(_local_source_path(dodge, PROTO_SOURCE))
    return resolve_documents(dodge, canonical, sidecar, DIRPS_SCENARIO)


def resolve_context(context, export_contract_path=None):
    """Generic TheFountain neutral-resolver hook."""
    if export_contract_path is not None:
        raise ResolutionError(
            "DIRPS G4 has no target contract; target-specific resolution starts at G6"
        )
    dodge = context["dodge"]
    canonical = context["scenario_source"]
    sidecar = _load(_local_source_path(dodge, PROTO_SOURCE))
    return resolve_documents(dodge, canonical, sidecar, context.get("config"))


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dodge", type=Path, default=DEFAULT_DODGE)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    text = json.dumps(resolve(args.dodge), indent=2) + "\n"
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
