#!/usr/bin/env python3
"""Target-neutral Wretched Scenario 01 resolver for DODGE 0.2.1."""
from __future__ import annotations
import copy,json
from pathlib import Path
ROOT=Path(__file__).parents[1]
DEFAULT_DODGE=ROOT/"game/wretched-demesne.dodge.v0.2.1.json"
class ResolutionError(ValueError): pass
def _load(p): return json.loads(Path(p).read_text())
def _source(dodge,ref):
    try: spec=dodge["sources"][ref]
    except KeyError as e: raise ResolutionError(f"Unknown source_ref {ref}") from e
    file_uri,_,fragment=spec["uri"].partition("#"); value=_load(ROOT/file_uri)
    for part in fragment.lstrip("/").split("/") if fragment else []: value=value[part.replace("~1","/").replace("~0","~")]
    return copy.deepcopy(value),spec
def _qty(q,binding):
    basis=q.get("basis","fixed")
    if basis=="fixed": return q.get("value",1)
    if basis=="maximum":
        if not binding or "health" not in binding: raise ResolutionError("maximum quantity requires a binding with health")
        return binding["health"]
    if basis=="current": raise ResolutionError("current quantities require runtime state")
    raise ResolutionError(f"Unsupported quantity basis {basis}")
def resolve(dodge_path=DEFAULT_DODGE,export_contract_path=None):
    dodge=_load(dodge_path)
    if dodge.get("dodge_version")!="0.2.1": raise ResolutionError("Requires DODGE 0.2.1")
    canonical,scenario_src=_source(dodge,"scenario-mvp"); sidecar,gdd_src=_source(dodge,"gdd")
    scenario=dodge["scenarios"]["scenario-01"]; scene=dodge["scenes"][scenario["scene_ref"]]
    topology=dodge["rules"]["topologies"][scenario["topology_ref"]]
    out={"format":"wretched-resolved-game.v1","dodge_version":dodge["dodge_version"],"document_id":dodge["document_id"],"game_id":dodge["game_id"],"scenario_id":"scenario-01",
      "authority":{"scenario-mvp":scenario_src["authority"],"gdd":gdd_src["authority"],"rule":"DODGE structure/policy is normalized semantics; declared sources supply referenced content. Provisional facts remain provisional and sidecar content is not silently promoted."},
      "sources":copy.deepcopy(dodge["sources"]),"scenario":copy.deepcopy(scenario),"scene":copy.deepcopy(scene),"topology":copy.deepcopy(topology),"rules":copy.deepcopy(dodge["rules"]),
      "canonical":canonical,"sidecars":{"gdd":sidecar},"inventory":{"scene_instances":copy.deepcopy(scene.get("instances",[])),"representations":[],"unresolved":[]}}
    for obj in ("spider-corpse","chrysalis"): out["inventory"]["unresolved"].append({"object_ref":obj,"reason":"Canonical physical supply quantity is unresolved."})
    if export_contract_path:
        contract=_load(export_contract_path)
        for inc in contract.get("representation_inclusions",[]):
            for rep_ref in inc["representation_refs"]:
                rep=dodge["representations"][rep_ref]
                for comp in rep.get("components",[]):
                    q=comp.get("quantity",{"basis":"fixed","value":1}); bindings=canonical["crew"] if q.get("per_binding") else [None]
                    for binding in bindings: out["inventory"]["representations"].append({"state_ref":inc["state_ref"],"mode":inc["mode"],"representation_ref":rep_ref,"object_ref":comp["object_ref"],"role":comp.get("role"),"binding_ref":binding.get("id") if binding else None,"quantity":_qty(q,binding)})
        out["export_contract"]=contract
    return out
def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--dodge",type=Path,default=DEFAULT_DODGE);p.add_argument("--export-contract",type=Path);p.add_argument("--out",type=Path)
    a=p.parse_args(); text=json.dumps(resolve(a.dodge,a.export_contract),indent=2)
    if a.out: a.out.write_text(text+"\n")
    else: print(text)
if __name__=="__main__": main()
