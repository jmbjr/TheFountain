#!/usr/bin/env python3
"""Discover authored games and scenario paths from game/<game-id>/game.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).parents[1]
GAME_ROOT=ROOT/"game"

class GameRegistryError(ValueError):
    pass

def _load(path: Path):
    return json.loads(path.read_text())

def discover_games():
    games={}
    for descriptor_path in sorted(GAME_ROOT.glob("*/game.json")):
        spec=_load(descriptor_path)
        game_id=spec.get("id")
        if not game_id:
            raise GameRegistryError(f"{descriptor_path}: missing id")
        if descriptor_path.parent.name != game_id:
            raise GameRegistryError(
                f"{descriptor_path}: id {game_id!r} must match directory {descriptor_path.parent.name!r}"
            )
        if game_id in games:
            raise GameRegistryError(f"duplicate game id: {game_id}")
        games[game_id]={"descriptor_path":descriptor_path,"root":descriptor_path.parent,"descriptor":spec}
    return games

def game_config(game_id: str):
    try:
        return discover_games()[game_id]
    except KeyError as exc:
        raise GameRegistryError(f"unknown game id: {game_id}") from exc

def _resolve(root: Path, rel: str | None):
    if rel is None:
        return None
    path=(root/rel).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise GameRegistryError(f"path escapes repository root: {rel}") from exc
    return path

def _resolve_repo(rel: str | None):
    if rel is None:
        return None
    path=(ROOT/rel).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise GameRegistryError(f"path escapes repository root: {rel}") from exc
    return path

def scenario_config(game_id: str, scenario_id: str):
    game=game_config(game_id)
    scenarios=game["descriptor"].get("scenarios",{})
    if scenario_id not in scenarios:
        raise GameRegistryError(f"{game_id}: unknown scenario id: {scenario_id}")
    spec=scenarios[scenario_id]
    root=game["root"]
    out={
        "game_id":game_id,
        "scenario_id":scenario_id,
        "game_root":root,
        "game_descriptor":game["descriptor"],
        "scenario":spec,
        "status":spec.get("status"),
        "dodge":_resolve(root,spec.get("dodge")),
        "source":_resolve(root,spec.get("source")),
        "path":_resolve(root,spec.get("path")),
        "sidecars":[_resolve(root,p) for p in spec.get("sidecars",[])],
        "export_contracts":{k:_resolve(root,p) for k,p in spec.get("export_contracts",{}).items()},
        "generated_targets":dict(spec.get("generated_targets",{})),
        "conformance":{
            **{k:v for k,v in spec.get("conformance",{}).items() if k!="resolver"},
            "resolver":_resolve_repo(spec.get("conformance",{}).get("resolver")),
        } if spec.get("conformance") else None,
    }
    return out

if __name__=="__main__":
    print(json.dumps({
        game_id:{
            "title":entry["descriptor"].get("title"),
            "status":entry["descriptor"].get("status"),
            "scenarios":entry["descriptor"].get("scenarios",{}),
        }
        for game_id,entry in discover_games().items()
    },indent=2,default=str))
