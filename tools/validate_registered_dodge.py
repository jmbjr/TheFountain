#!/usr/bin/env python3
"""Discover and validate every registered DODGE-backed scenario in TheFountain.

The runner deliberately keeps repository-specific execution hooks small:
- DODGE owns schema + validation-profile declarations.
- game.json identifies the scenario's target-neutral resolver module.
- semantic validator modules are discovered from DODGE sources.
- runtime/target tests remain ordinary repository tests and are discovered separately.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from game_registry import ROOT, discover_games, scenario_config

VALID_MATURITY={f"G{i}" for i in range(8)}
SCAFFOLD_STATUSES={"planned","scaffold"}


class ConformanceError(RuntimeError):
    pass


def load_json(path: Path):
    return json.loads(path.read_text())


def load_module(path: Path, label: str):
    path=path.resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ConformanceError(f"{label}: module path escapes repository root: {path}") from exc
    if not path.is_file():
        raise ConformanceError(f"{label}: module not found: {path}")
    name="tf_conformance_"+str(abs(hash((str(path),label))))
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise ConformanceError(f"{label}: cannot import {path}")
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def version_root(dodge_root: Path, version: str):
    candidates=[
        dodge_root/"official"/f"v{version}",
        dodge_root/"draft"/f"v{version}",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    raise ConformanceError(
        f"DODGE {version}: no official/v{version} or draft/v{version} under {dodge_root}"
    )


def validate_schema(instance_path: Path, schema_path: Path, label: str):
    schema=load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    instance=load_json(instance_path)
    errors=sorted(Draft202012Validator(schema).iter_errors(instance),key=lambda e:list(e.path))
    if errors:
        detail="\n".join(
            f"  {'.'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in errors
        )
        raise ConformanceError(f"{label}: schema validation failed\n{detail}")
    return instance


def repo_uri_path(uri: str, label: str):
    file_uri=uri.partition("#")[0]
    if "://" in file_uri:
        raise ConformanceError(
            f"{label}: executable validator must be a repository-local source URI, got {uri}"
        )
    path=(ROOT/file_uri).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ConformanceError(f"{label}: validator URI escapes repository root: {uri}") from exc
    return path


def profile_modules(dodge: dict):
    declaration=dodge.get("validation") or {}
    profiles=declaration.get("required_profiles",[])
    modules=[]
    for profile in profiles:
        source_ref=profile["validator_source_ref"]
        try:
            source=dodge["sources"][source_ref]
        except KeyError as exc:
            raise ConformanceError(
                f"{profile['profile_id']}: missing semantic validator source {source_ref}"
            ) from exc
        if source.get("kind")!="semantic_validator":
            raise ConformanceError(
                f"{profile['profile_id']}: {source_ref} must have kind semantic_validator"
            )
        required_version=profile["version"]
        source_version=source.get("version")
        if source_version!=required_version:
            raise ConformanceError(
                f"{profile['profile_id']}@{required_version}: semantic validator source "
                f"{source_ref} declares version {source_version!r}; required profile/source "
                "versions must match"
            )
        path=repo_uri_path(source["uri"],profile["profile_id"])
        modules.append((profile,load_module(path,profile["profile_id"])))
    return modules


def context_for(cfg: dict, dodge: dict):
    source=cfg.get("source")
    return {
        "root":ROOT,
        "game_id":cfg["game_id"],
        "scenario_id":cfg["scenario_id"],
        "config":cfg,
        "dodge":dodge,
        "dodge_path":cfg["dodge"],
        "scenario_source":load_json(source) if source and source.is_file() else None,
        "scenario_source_path":source,
    }


def require_no_errors(errors, label):
    rows=list(errors or [])
    if rows:
        raise ConformanceError(label+":\n  " + "\n  ".join(str(x) for x in rows))


def run_scenario(cfg: dict, dodge_root: Path):
    conformance=cfg.get("conformance")
    status=cfg.get("status")
    label=f"{cfg['game_id']}/{cfg['scenario_id']}"

    if not conformance:
        if status in SCAFFOLD_STATUSES:
            print(f"SKIP {label}: {status} scenario has no active conformance pipeline")
            return {"label":label,"status":"skipped"}
        raise ConformanceError(
            f"{label}: DODGE-backed scenario has no conformance declaration in game.json"
        )

    maturity=conformance.get("maturity")
    if maturity not in VALID_MATURITY:
        raise ConformanceError(f"{label}: conformance.maturity must be one of {sorted(VALID_MATURITY)}")
    if maturity=="G0":
        print(f"SKIP {label}: explicit G0 scaffold")
        return {"label":label,"status":"scaffold"}

    dodge_path=cfg["dodge"]
    if not dodge_path or not dodge_path.is_file():
        raise ConformanceError(f"{label}: DODGE document not found: {dodge_path}")
    dodge_preview=load_json(dodge_path)
    version=dodge_preview.get("dodge_version")
    if not version:
        raise ConformanceError(f"{label}: DODGE document has no dodge_version")
    spec_root=version_root(dodge_root,version)

    dodge=validate_schema(
        dodge_path,
        spec_root/"schemas"/f"dodge.schema.v{version}.json",
        f"{label} DODGE",
    )
    print(f"PASS {label}: DODGE {version} schema")

    for target,contract_path in sorted(cfg.get("export_contracts",{}).items()):
        validate_schema(
            contract_path,
            spec_root/"schemas"/f"dodge-export-contract.schema.v{version}.json",
            f"{label} {target} export contract",
        )
        print(f"PASS {label}: {target} export contract schema")

    declaration=dodge.get("validation")
    modules=profile_modules(dodge) if declaration else []
    if maturity in {"G3","G4","G5","G6","G7"} and not declaration:
        raise ConformanceError(
            f"{label}: maturity {maturity} requires a DODGE validation declaration"
        )

    context=context_for(cfg,dodge)
    for profile,module in modules:
        if "source" not in profile.get("stages",[]):
            continue
        hook=getattr(module,"validate_source_context",None)
        if hook is None:
            raise ConformanceError(
                f"{label}: validator {profile['profile_id']} lacks validate_source_context(context)"
            )
        require_no_errors(
            hook(context),
            f"{label} semantic profile {profile['profile_id']}@{profile['version']} source failed",
        )
        print(f"PASS {label}: semantic source {profile['profile_id']}@{profile['version']}")

    resolver_path=conformance.get("resolver")
    if maturity in {"G4","G5","G6","G7"} and not resolver_path:
        raise ConformanceError(f"{label}: maturity {maturity} requires conformance.resolver")
    resolved=None
    resolver=None
    if resolver_path:
        resolver=load_module(resolver_path,f"{label} resolver")
        hook=getattr(resolver,"resolve_context",None)
        if hook is None:
            raise ConformanceError(
                f"{label}: resolver lacks resolve_context(context, export_contract_path=None)"
            )
        resolved=hook(context)
        context["resolved"]=resolved
        print(f"PASS {label}: neutral resolver")

        for profile,module in modules:
            if "resolved-game" not in profile.get("stages",[]):
                continue
            validate_hook=getattr(module,"validate_resolved_context",None)
            if validate_hook is None:
                raise ConformanceError(
                    f"{label}: validator {profile['profile_id']} lacks validate_resolved_context(context)"
                )
            require_no_errors(
                validate_hook(context),
                f"{label} semantic profile {profile['profile_id']}@{profile['version']} resolved-game failed",
            )
            print(f"PASS {label}: semantic resolved-game {profile['profile_id']}@{profile['version']}")

    if maturity in {"G6","G7"}:
        manifest_schema=spec_root/"schemas"/f"dodge-target-manifest.schema.v{version}.json"
        for target,contract_path in sorted(cfg.get("export_contracts",{}).items()):
            if resolver is None:
                raise ConformanceError(f"{label}: target manifest validation requires resolver")
            target_resolved=resolver.resolve_context(context,contract_path)
            manifest=target_resolved.get("target_manifest")
            if manifest is None:
                raise ConformanceError(
                    f"{label}: resolver did not emit target_manifest for {target}"
                )
            schema=load_json(manifest_schema)
            Draft202012Validator.check_schema(schema)
            errors=sorted(Draft202012Validator(schema).iter_errors(manifest),key=lambda e:list(e.path))
            if errors:
                detail="\n".join(
                    f"  {'.'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in errors
                )
                raise ConformanceError(f"{label} {target} target manifest invalid\n{detail}")
            print(f"PASS {label}: {target} resolved target manifest")

    return {"label":label,"status":"pass","maturity":maturity,"dodge_version":version}


def discovered_dodge_scenarios():
    rows=[]
    for game_id,entry in discover_games().items():
        for scenario_id,spec in entry["descriptor"].get("scenarios",{}).items():
            if spec.get("dodge"):
                rows.append(scenario_config(game_id,scenario_id))
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument(
        "--dodge-root",
        type=Path,
        required=True,
        help="Checkout root of jmbjr/DODGE; version roots are discovered under official/ or draft/.",
    )
    args=parser.parse_args()
    rows=discovered_dodge_scenarios()
    if not rows:
        raise SystemExit("No registered DODGE-backed scenarios found.")
    print("Discovered DODGE scenarios:")
    for cfg in rows:
        maturity=(cfg.get("conformance") or {}).get("maturity","undeclared")
        print(f"  - {cfg['game_id']}/{cfg['scenario_id']} ({maturity})")
    try:
        results=[run_scenario(cfg,args.dodge_root.resolve()) for cfg in rows]
    except ConformanceError as exc:
        raise SystemExit(str(exc)) from exc
    passed=sum(1 for r in results if r["status"]=="pass")
    skipped=sum(1 for r in results if r["status"]!="pass")
    print(f"Conformance discovery complete: {passed} passed, {skipped} skipped.")


if __name__=="__main__":
    main()
