#!/usr/bin/env python3
"""Target-neutral Wretched Scenario 01 resolver for DODGE 0.2.1."""
from __future__ import annotations
import copy,hashlib,json
from wretched_semantic_validation import require_source_semantics, require_resolved_semantics
from pathlib import Path
ROOT=Path(__file__).parents[1]
DEFAULT_DODGE=ROOT/"game/wretched-demesne.dodge.v0.2.1.json"
class ResolutionError(ValueError): pass
def _load(p): return json.loads(Path(p).read_text())
def _sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
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
def _component(dodge,archetype_ref,object_spec=None):
    base=copy.deepcopy(dodge["archetypes"].get(archetype_ref,{}).get("component"))
    override=(object_spec or {}).get("component")
    if base is None: return copy.deepcopy(override)
    if override: base.update(copy.deepcopy(override))
    return base
def _diag(field,status,classification,canonical=None,effective=None,reason=None):
    d={"field":field,"status":status,"classification":classification}
    if canonical is not None: d["canonical"]=copy.deepcopy(canonical)
    if effective is not None: d["effective"]=copy.deepcopy(effective)
    if reason: d["reason"]=reason
    return d
def _manifest(dodge,dodge_path,contract,contract_path,scenario,scene,canonical,rep_rows):
    scene_ref=scenario["scene_ref"]
    entries=[]
    def provenance(kind,ref,path): return {"kind":kind,"ref":ref,"path":path}
    def add_scene(instance,index):
        obj_ref=instance["object_ref"]; obj=dodge["objects"][obj_ref]; archetype=obj.get("archetype_ref")
        cid=f"scene/{scene_ref}/instance/{instance['id']}"; qty=instance.get("quantity",1)
        prov=[provenance("dodge-document",dodge["document_id"],"/"),provenance("scene",scene_ref,f"/scenes/{scene_ref}"),provenance("instance",instance["id"],f"/scenes/{scene_ref}/instances/{index}"),provenance("object",obj_ref,f"/objects/{obj_ref}")]
        if archetype: prov.append(provenance("archetype",archetype,f"/archetypes/{archetype}"))
        comp=_component(dodge,archetype,obj)
        e={"content_id":cid,"source":{"kind":"scene-instance","ref":instance["id"],"path":f"/scenes/{scene_ref}/instances/{index}"},"canonical_quantity":qty,"resolved_quantity":qty,"inclusion":"included-inherited","provenance":prov,"diagnostics":[_diag("inclusion","inherited","canonical",True,True),_diag("quantity","derived","canonical",qty,qty)]}
        if comp is not None: e["component_inherited"]=copy.deepcopy(comp);e["component_effective"]=copy.deepcopy(comp)
        entries.append(e)
        if obj.get("kind")=="collection":
            for mi,member in enumerate(obj.get("members",[])):
                mqty=qty*member.get("quantity",1); mid=f"{cid}/member/{mi}"; ma=member.get("archetype_ref"); mcomp=_component(dodge,ma)
                mp=prov+[provenance("collection-member",str(mi),f"/objects/{obj_ref}/members/{mi}")]
                if ma: mp.append(provenance("archetype",ma,f"/archetypes/{ma}"))
                me={"content_id":mid,"parent_content_id":cid,"source":{"kind":"collection-member","ref":member.get("entity_ref",member.get("object_ref",str(mi))),"path":f"/objects/{obj_ref}/members/{mi}"},"canonical_quantity":mqty,"resolved_quantity":mqty,"inclusion":"included-inherited","provenance":mp,"diagnostics":[_diag("inclusion","inherited","canonical",True,True),_diag("quantity","derived","canonical",mqty,mqty)]}
                entity_ref=member.get("entity_ref")
                if entity_ref and entity_ref.startswith("scenario-mvp:"):
                    _,catalog,item_id=entity_ref.split(":",2)
                    matches=[x for x in canonical.get(catalog,[]) if x.get("id")==item_id]
                    if len(matches)!=1: raise ResolutionError(f"Expected one canonical entity for {entity_ref}")
                    me["provenance"].append(provenance("collection-member",entity_ref,f"/{catalog}/{item_id}"))
                if mcomp is not None: me["component_inherited"]=copy.deepcopy(mcomp);me["component_effective"]=copy.deepcopy(mcomp)
                entries.append(me)
    for i,instance in enumerate(scene.get("instances",[])): add_scene(instance,i)
    for inc in contract.get("representation_inclusions",[]):
        for rep_ref in inc["representation_refs"]:
            rep=dodge["representations"][rep_ref]
            for ci,comp_req in enumerate(rep.get("components",[])):
                rows=[x for x in rep_rows if x["representation_ref"]==rep_ref and x["object_ref"]==comp_req["object_ref"] and x["role"]==comp_req.get("role")]
                qty=sum(x["quantity"] for x in rows)
                obj_ref=comp_req["object_ref"];obj=dodge["objects"][obj_ref];archetype=obj.get("archetype_ref");component=_component(dodge,archetype,obj)
                cid=f"representation/{rep_ref}/component/{ci}"
                prov=[provenance("dodge-document",dodge["document_id"],"/"),provenance("representation",rep_ref,f"/representations/{rep_ref}"),provenance("object",obj_ref,f"/objects/{obj_ref}")]
                if archetype: prov.append(provenance("archetype",archetype,f"/archetypes/{archetype}"))
                prov.append(provenance("export-contract",contract["contract_id"],"/representation_inclusions"))
                e={"content_id":cid,"source":{"kind":"representation-component","ref":obj_ref,"path":f"/representations/{rep_ref}/components/{ci}"},"representation_ref":rep_ref,"representation_mode":inc["mode"],"canonical_quantity":qty,"resolved_quantity":qty,"inclusion":"included-inherited","provenance":prov,"diagnostics":[_diag("inclusion","derived","canonical",True,True),_diag("quantity","derived","canonical",qty,qty)]}
                if component is not None:e["component_inherited"]=copy.deepcopy(component);e["component_effective"]=copy.deepcopy(component)
                entries.append(e)
    by_id={e["content_id"]:e for e in entries}
    seen=set()
    for oi,ov in enumerate(contract.get("content_configuration",{}).get("entries",[])):
        ref=ov["content_ref"]
        if ref in seen: raise ResolutionError(f"Duplicate content configuration ref {ref}")
        seen.add(ref)
        if ref not in by_id: raise ResolutionError(f"content_configuration ref does not resolve: {ref}")
        e=by_id[ref]; e["provenance"].append(provenance("content-configuration",ref,f"/content_configuration/entries/{oi}"))
        inclusion=ov.get("inclusion","inherit")
        if inclusion=="exclude":
            e["inclusion"]="excluded-override";e["resolved_quantity"]=0;e["diagnostics"].append(_diag("inclusion","overridden","presentation",True,False,"Explicit target exclusion."))
        elif inclusion=="include":
            e["inclusion"]="included-override";e["diagnostics"].append(_diag("inclusion","overridden","presentation",True,True,"Explicit target inclusion."))
        if "group" in ov:
            e["group"]=ov["group"];e["diagnostics"].append(_diag("group","overridden","presentation",None,ov["group"],"Target-owned grouping."))
        if "notes" in ov:
            e["notes"]=copy.deepcopy(ov["notes"]);e["diagnostics"].append(_diag("notes","overridden","presentation",None,ov["notes"],"Target-owned notes."))
        if "component_overrides" in ov:
            inherited=copy.deepcopy(e.get("component_effective",{})); effective=copy.deepcopy(inherited); effective.update(copy.deepcopy(ov["component_overrides"]));e["component_effective"]=effective
            for field,value in ov["component_overrides"].items(): e["diagnostics"].append(_diag(f"component.{field}","overridden","presentation",inherited.get(field),value,"Explicit target component override."))
        if "quantity_override" in ov:
            q=ov["quantity_override"];old=e["resolved_quantity"];e["resolved_quantity"]=q["value"];e["inclusion"]="included-override";e["diagnostics"].append(_diag("quantity","overridden",q["classification"],old,q["value"],q["reason"]))
        variants=ov.get("presentation_variants",[])
        if variants:
            policy=ov["variant_policy"]
            if policy=="replace-base":
                e["inclusion"]="excluded-override";e["resolved_quantity"]=0;e["diagnostics"].append(_diag("presentation_variant","overridden","presentation","base","replaced","Presentation variants replace base."))
            base_qty=e["canonical_quantity"] if policy=="replace-base" else e["resolved_quantity"]
            for v in variants:
                ve=copy.deepcopy(e);ve["content_id"]=f"{ref}/variant/{v['id']}";ve["parent_content_id"]=ref;ve["variant_of"]=ref;ve["source"]={"kind":"presentation-variant","ref":v["id"],"path":f"/content_configuration/entries/{oi}/presentation_variants/{v['id']}"};ve["inclusion"]="included-override";ve["resolved_quantity"]=base_qty;ve["provenance"].append(provenance("presentation-variant",v["id"],ve["source"]["path"]));ve["diagnostics"].append(_diag("presentation_variant","overridden","presentation","base",v["id"],"Target presentation variant."))
                if "component_overrides" in v:
                    old=copy.deepcopy(ve.get("component_effective",{}));new=copy.deepcopy(old);new.update(copy.deepcopy(v["component_overrides"]));ve["component_effective"]=new
                    for field,value in v["component_overrides"].items():ve["diagnostics"].append(_diag(f"component.{field}","overridden","presentation",old.get(field),value,"Presentation variant component override."))
                if "quantity_override" in v:
                    q=v["quantity_override"];oldq=ve["resolved_quantity"];ve["resolved_quantity"]=q["value"];ve["diagnostics"].append(_diag("quantity","overridden",q["classification"],oldq,q["value"],q["reason"]))
                if "notes" in v:ve["notes"]=copy.deepcopy(v["notes"])
                entries.append(ve)
    return {"manifest_version":"0.2.1","manifest_id":f"{contract['contract_id']}:{scenario['scene_ref']}".replace("-","."),"target":contract["target"],"dodge_identity":{"dodge_version":dodge["dodge_version"],"document_id":dodge["document_id"],"sha256":_sha256(dodge_path)},"contract_identity":{"contract_version":contract["contract_version"],"contract_id":contract["contract_id"],"sha256":_sha256(contract_path)},"resolution_scope":{"scene_ref":scene_ref,"scenario_ref":"scenario-01"},"contents":entries}
def resolve(dodge_path=DEFAULT_DODGE,export_contract_path=None):
    dodge=_load(dodge_path)
    if dodge.get("dodge_version")!="0.2.1": raise ResolutionError("Requires DODGE 0.2.1")
    canonical,scenario_src=_source(dodge,"scenario-mvp"); sidecar,gdd_src=_source(dodge,"gdd")
    require_source_semantics(dodge,canonical)
    scenario=dodge["scenarios"]["scenario-01"]; scene=dodge["scenes"][scenario["scene_ref"]];topology=dodge["topologies"][scenario["topology_ref"]]
    semantic_collections={}
    for instance in scene.get("instances",[]):
        obj=dodge["objects"][instance["object_ref"]]
        if obj.get("kind")!="collection": continue
        semantic_collections[instance["id"]]={"object_ref":instance["object_ref"],"source_ref":obj.get("source_ref"),"members":copy.deepcopy(obj.get("members",[]))}
    out={"format":"wretched-resolved-game.v1","dodge_version":dodge["dodge_version"],"document_id":dodge["document_id"],"game_id":dodge["game_id"],"scenario_id":"scenario-01","authority":{"scenario-mvp":scenario_src["authority"],"gdd":gdd_src["authority"],"rule":"DODGE structure/policy is normalized semantics; declared sources supply referenced content. Provisional facts remain provisional and sidecar content is not silently promoted."},"sources":copy.deepcopy(dodge["sources"]),"archetypes":copy.deepcopy(dodge["archetypes"]),"objects":copy.deepcopy(dodge["objects"]),"representations":copy.deepcopy(dodge["representations"]),"scenario":copy.deepcopy(scenario),"scene":copy.deepcopy(scene),"topology":copy.deepcopy(topology),"rules":copy.deepcopy(dodge["rules"]),"entity_invocations":copy.deepcopy(dodge.get("entity_invocations",{})),"canonical":canonical,"sidecars":{"gdd":sidecar},"semantic_collections":semantic_collections,"inventory":{"scene_instances":copy.deepcopy(scene.get("instances",[])),"representations":[],"unresolved":[]}}
    for obj in ("spider-corpse","chrysalis"): out["inventory"]["unresolved"].append({"object_ref":obj,"reason":"Canonical physical supply quantity is unresolved."})
    if export_contract_path:
        contract=_load(export_contract_path)
        for inc in contract.get("representation_inclusions",[]):
            for rep_ref in inc["representation_refs"]:
                rep=dodge["representations"][rep_ref]
                for comp in rep.get("components",[]):
                    q=comp.get("quantity",{"basis":"fixed","value":1});bindings=canonical["crew"] if q.get("per_binding") else [None]
                    for binding in bindings:out["inventory"]["representations"].append({"state_ref":inc["state_ref"],"mode":inc["mode"],"representation_ref":rep_ref,"object_ref":comp["object_ref"],"role":comp.get("role"),"binding_ref":binding.get("id") if binding else None,"quantity":_qty(q,binding)})
        out["export_contract"]=contract
        out["target_manifest"]=_manifest(dodge,dodge_path,contract,export_contract_path,scenario,scene,canonical,out["inventory"]["representations"])
    require_resolved_semantics(out)
    return out
def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--dodge",type=Path,default=DEFAULT_DODGE);p.add_argument("--export-contract",type=Path);p.add_argument("--out",type=Path);p.add_argument("--manifest-out",type=Path)
    a=p.parse_args();resolved=resolve(a.dodge,a.export_contract)
    if a.manifest_out:
        if "target_manifest" not in resolved:raise SystemExit("--manifest-out requires --export-contract")
        a.manifest_out.parent.mkdir(parents=True,exist_ok=True);a.manifest_out.write_text(json.dumps(resolved["target_manifest"],indent=2)+"\n")
    text=json.dumps(resolved,indent=2)
    if a.out:a.out.write_text(text+"\n")
    elif not a.manifest_out:print(text)
if __name__=="__main__": main()
