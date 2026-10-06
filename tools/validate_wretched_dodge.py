#!/usr/bin/env python3
"""Validate Wretched Demesne against the exact pinned DODGE 0.2.1 draft schemas."""
import argparse, json
from pathlib import Path
from jsonschema import Draft202012Validator
from resolve_wretched_dodge import resolve
from wretched_semantic_validation import validate_source_semantics, validate_resolved_semantics

DODGE_DOCUMENT = Path("game/wretched-demesne.dodge.v0.2.1.json")
EXPORT_CONTRACTS = [
    Path("game/export-contracts/wretched-beta-pnp.dodge-export.json"),
    Path("game/export-contracts/wretched-beta-tts.dodge-export.json"),
]

def validate(instance_path, schema_path):
    instance=json.loads(instance_path.read_text())
    schema=json.loads(schema_path.read_text())
    errors=sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e:list(e.absolute_path))
    if errors:
        print(f"FAIL {instance_path}")
        for e in errors:
            where="/".join(map(str,e.absolute_path)) or "<root>"
            print(f"  {where}: {e.message}")
        return False
    print(f"PASS {instance_path}")
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--schema-root", type=Path, required=True)
    a=p.parse_args()
    doc_schema=a.schema_root/"schemas/dodge.schema.v0.2.1.json"
    contract_schema=a.schema_root/"schemas/dodge-export-contract.schema.v0.2.1.json"
    ok=validate(DODGE_DOCUMENT,doc_schema)
    dodge=json.loads(DODGE_DOCUMENT.read_text())
    canonical=json.loads(Path("game/wretched-demesne.scenario-01.mvp.v0.1.json").read_text())
    semantic_errors=validate_source_semantics(dodge,canonical)
    if semantic_errors:
        ok=False
        print("FAIL Wretched semantic profile")
        for error in semantic_errors: print(f"  {error}")
    else: print("PASS Wretched semantic profile")
    for path in EXPORT_CONTRACTS:
        ok=validate(path,contract_schema) and ok
    if ok:
        resolved=resolve(DODGE_DOCUMENT)
        resolved_errors=validate_resolved_semantics(resolved)
        if resolved_errors:
            ok=False
            print("FAIL resolved Wretched game")
            for error in resolved_errors: print(f"  {error}")
        else: print("PASS resolved Wretched game")
    raise SystemExit(0 if ok else 1)

if __name__=="__main__": main()
