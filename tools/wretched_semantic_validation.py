#!/usr/bin/env python3
"""Wretched-owned semantic validation profile for Scenario 01.

DODGE validates neutral structure. This module validates cross-field contracts that
only Wretched can define, both before and after target-neutral resolution.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).parents[1]
SCENARIO=ROOT/"game/wretched-demesne.scenario-01.mvp.v0.1.json"
ALLOWED_TRIGGERS={"play","enter","search","interact","resolve","turn-start"}

class SemanticValidationError(ValueError):
    pass

def load_json(path):
    return json.loads(Path(path).read_text())

def _invocation_refs(steps, effects, conditions, errors, where):
    for step in steps or []:
        kind=step.get("kind")
        if kind=="effect" and step.get("ref") not in effects:
            errors.append(f"{where}: unknown effect ref {step.get('ref')}")
        elif kind=="condition" and step.get("condition_ref") not in conditions:
            errors.append(f"{where}: unknown condition ref {step.get('condition_ref')}")
        elif kind=="branch":
            for branch in step.get("branches",[]):
                cond=branch.get("condition")
                if cond and cond not in conditions:
                    errors.append(f"{where}: unknown branch condition {cond}")
                _invocation_refs(branch.get("steps",[]),effects,conditions,errors,where)
            _invocation_refs(step.get("else_steps",[]),effects,conditions,errors,where)

def _entity_ids(canonical):
    return {catalog:{x["id"] for x in canonical.get(catalog,[])} for catalog in ("rooms","encounters","cards","crew","enemies","salvage")}

def validate_source_semantics(dodge, canonical):
    """Return a bounded list of Wretched semantic-profile violations."""
    errors=[]
    ids=_entity_ids(canonical)
    invocations=dodge.get("entity_invocations",{})
    effects=dodge.get("rules",{}).get("effects",{})
    conditions=dodge.get("rules",{}).get("conditions",{})

    # Capability -> executable behavior contracts.
    for room in canonical.get("rooms",[]):
        key=f"scenario-mvp:rooms:{room['id']}"
        triggers={x.get("trigger") for x in invocations.get(key,[])}
        if room.get("searchable") and "search" not in triggers:
            errors.append(f"room {room['id']}: searchable=true requires executable search invocation")
        if room.get("objective_item_ref") and "search" not in triggers:
            errors.append(f"room {room['id']}: objective_item_ref requires executable search invocation")
        if room.get("hazard") and "enter" not in triggers:
            errors.append(f"room {room['id']}: hazard requires executable enter invocation")
        if room.get("lock") and "enter" not in triggers:
            errors.append(f"room {room['id']}: lock requires executable enter invocation")
        interaction=room.get("interaction")
        if interaction:
            if not interaction.get("effects"):
                errors.append(f"room {room['id']}: interaction requires effects")
            required=interaction.get("requires_inventory_ref")
            if required and required not in ids["salvage"]:
                errors.append(f"room {room['id']}: interaction inventory ref {required} is not salvage")

    # Invocation keys, triggers, and rule references must be satisfiable.
    for key, rows in invocations.items():
        parts=key.split(":")
        if len(parts)!=3 or parts[0]!="scenario-mvp":
            errors.append(f"invocation key {key}: expected scenario-mvp:<catalog>:<id>")
            continue
        catalog,item_id=parts[1],parts[2]
        if catalog not in ids or item_id not in ids[catalog]:
            errors.append(f"invocation key {key}: entity does not exist")
        seen=set()
        for inv in rows:
            trigger=inv.get("trigger")
            if trigger not in ALLOWED_TRIGGERS:
                errors.append(f"{key}/{inv.get('id','<missing>')}: unsupported trigger {trigger}")
            ident=inv.get("id")
            if ident in seen:
                errors.append(f"{key}: duplicate invocation id {ident}")
            seen.add(ident)
            _invocation_refs(inv.get("steps",[]),effects,conditions,errors,f"{key}/{ident}")

    # Scenario/runtime references must point at canonical rooms/resources.
    scenario=dodge.get("scenarios",{}).get("scenario-01",{})
    runtime=scenario.get("runtime",{})
    room_ids=ids["rooms"]
    start=runtime.get("start_room_ref")
    if start not in room_ids:
        errors.append(f"scenario runtime: start_room_ref {start} is not a room")
    extraction=runtime.get("extraction",{})
    if extraction.get("room_ref") not in room_ids:
        errors.append(f"scenario runtime: extraction room_ref {extraction.get('room_ref')} is not a room")

    # Semantic collection membership must resolve to exactly one canonical entity.
    for obj_id,obj in dodge.get("objects",{}).items():
        for member in obj.get("members",[]):
            ref=member.get("entity_ref","")
            if not ref.startswith("scenario-mvp:"):
                continue
            parts=ref.split(":")
            if len(parts)!=3 or parts[1] not in ids or parts[2] not in ids[parts[1]]:
                errors.append(f"object {obj_id}: collection member {ref} does not resolve")

    return errors

def validate_resolved_semantics(resolved):
    """Validate the executable resolved model independently of source validation."""
    errors=[]
    if resolved.get("format")!="wretched-resolved-game.v1":
        errors.append("resolved game: unexpected format")
        return errors
    canonical=resolved.get("canonical") or {}
    # Re-run cross-field contracts against the actual resolved semantics.
    projection={"entity_invocations":resolved.get("entity_invocations",{}),
                "rules":resolved.get("rules",{}),
                "scenarios":{"scenario-01":resolved.get("scenario",{})},
                "objects":resolved.get("objects",{})}
    errors.extend(f"resolved: {e}" for e in validate_source_semantics(projection,canonical))

    ids=_entity_ids(canonical)
    required_collections={
        "scenario-room-cards-1":"rooms",
        "scenario-encounter-cards-1":"encounters",
        "scenario-salvage-cards-1":"salvage",
    }
    for crew in ids["crew"]:
        required_collections[f"{crew}-starter-deck-1"]="cards"
    collections=resolved.get("semantic_collections",{})
    for instance,catalog in required_collections.items():
        collection=collections.get(instance)
        if not collection:
            errors.append(f"resolved: missing semantic collection {instance}")
            continue
        prefix=f"scenario-mvp:{catalog}:"
        for member in collection.get("members",[]):
            ref=member.get("entity_ref","")
            if not ref.startswith(prefix) or ref[len(prefix):] not in ids[catalog]:
                errors.append(f"resolved: {instance} has unsatisfied member {ref}")
    return errors

def require_source_semantics(dodge,canonical):
    errors=validate_source_semantics(dodge,canonical)
    if errors: raise SemanticValidationError("\n".join(errors))

def require_resolved_semantics(resolved):
    errors=validate_resolved_semantics(resolved)
    if errors: raise SemanticValidationError("\n".join(errors))
