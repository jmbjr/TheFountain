#!/usr/bin/env python3
"""Verify generated Wretched Beta TTS save/package against resolved target manifest."""
from __future__ import annotations

import argparse, json, zipfile
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).parents[1]
SCENARIO=ROOT/"game/wretched-demesne.scenario-01.mvp.v0.1.json"

def fail(msg): raise SystemExit(f"TTS verification failed: {msg}")

def included(x): return x.get("inclusion")!="excluded-override" and x.get("resolved_quantity",0)>0

def walk(objects):
    for obj in objects or []:
        yield obj
        yield from walk(obj.get("ContainedObjects",[]))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--save",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--asset-dir",required=True)
    p.add_argument("--git-sha",required=True)
    p.add_argument("--zip")
    a=p.parse_args()

    save=json.loads(Path(a.save).read_text())
    manifest=json.loads(Path(a.manifest).read_text())
    data=json.loads(SCENARIO.read_text())
    by_id={x["content_id"]:x for x in manifest["contents"]}
    short=a.git_sha[:12]

    meta=save.get("DODGE",{})
    expected_meta={"version":"0.2.1","git_sha":a.git_sha,"contract":"wd-beta-tts","manifest_id":manifest["manifest_id"]}
    for k,v in expected_meta.items():
        if meta.get(k)!=v: fail(f"DODGE metadata {k} mismatch: {meta.get(k)!r} != {v!r}")

    objs=save.get("ObjectStates") or []
    names=[o.get("Nickname") for o in objs]
    if len(names)!=len(set(names)): fail("duplicate top-level object nicknames")

    all_objs=list(walk(objs))
    guids=[o.get("GUID") for o in all_objs if o.get("GUID")]
    if len(guids)!=len(set(guids)): fail("duplicate object GUIDs")

    for deck in [o for o in objs if o.get("Name")=="DeckCustom"]:
        ids=deck.get("DeckIDs") or []
        children=deck.get("ContainedObjects") or []
        if len(ids)!=len(children): fail(f"{deck.get('Nickname')}: DeckIDs/ContainedObjects count mismatch")
        if len(ids)!=len(set(ids)): fail(f"{deck.get('Nickname')}: duplicate CardIDs")
        custom=deck.get("CustomDeck") or {}
        for child in children:
            cid=child.get("CardID")
            if cid not in ids: fail(f"{deck.get('Nickname')}: child CardID missing from DeckIDs")
            key=str(cid//100)
            if key not in custom: fail(f"{deck.get('Nickname')}: CustomDeck missing key {key}")
            if key not in (child.get("CustomDeck") or {}): fail(f"{deck.get('Nickname')}: child CustomDeck missing key {key}")

    def entity(ref):
        if not ref.startswith("scenario-mvp:"): fail(f"unexpected semantic ref {ref}")
        _,catalog,eid=ref.split(":",2)
        matches=[x for x in data.get(catalog,[]) if x.get("id")==eid]
        if len(matches)!=1: fail(f"cannot resolve {ref}")
        return matches[0]

    def expected_names(instance_id):
        prefix=f"scene/scenario-01-the-cave/instance/{instance_id}/member/"
        out=[]
        for row in manifest["contents"]:
            if row["content_id"].startswith(prefix) and included(row):
                out += [entity(row["source"]["ref"])["name"]]*row["resolved_quantity"]
        if not out: fail(f"manifest has no included members for {instance_id}")
        return out

    top={o["Nickname"]:o for o in objs}
    mapping={
        "Captain Starter Deck":"captain-starter-deck-1",
        "Security Starter Deck":"security-starter-deck-1",
        "Engineer Starter Deck":"engineer-starter-deck-1",
        "Medic Starter Deck":"medic-starter-deck-1",
        "Scout Starter Deck":"scout-starter-deck-1",
        "Encounter Deck":"scenario-encounter-cards-1",
        "Salvage Deck":"scenario-salvage-cards-1",
        "Crew Reference Cards":"crew-reference-cards-1",
    }
    for deck_name,instance_id in mapping.items():
        if deck_name not in top: fail(f"missing {deck_name}")
        observed=[x.get("Nickname") for x in top[deck_name].get("ContainedObjects",[])]
        if Counter(observed)!=Counter(expected_names(instance_id)):
            fail(f"{deck_name} contents differ from manifest")

    room_names=expected_names("scenario-room-cards-1")
    start_ref=data["scenario"]["runtime"]["start_room_ref"]
    start_name=next(r["name"] for r in data["rooms"] if r["id"]==start_ref)
    if start_name not in top: fail(f"missing start room object {start_name}")
    start_obs=[x.get("Nickname") for x in top[start_name].get("ContainedObjects",[])]
    if start_obs!=[start_name]: fail("start room object does not contain exactly the start room card")
    unexplored=[x.get("Nickname") for x in top["Unexplored Room Deck"].get("ContainedObjects",[])]
    expected_unexplored=list(room_names); expected_unexplored.remove(start_name)
    if Counter(unexplored)!=Counter(expected_unexplored): fail("Unexplored Room Deck differs from manifest")

    enemy_prefix="scene/scenario-01-the-cave/instance/enemy-token-supply-1/member/"
    enemy_by_id={e["id"]:e for e in data["enemies"]}
    for row in manifest["contents"]:
        if row["content_id"].startswith(enemy_prefix) and included(row):
            token_ref=row["source"]["ref"]; eid=token_ref.removesuffix("-token")
            label=enemy_by_id[eid]["name"]; bag=f"{label} Tokens"
            if bag not in top or len(top[bag].get("ContainedObjects",[]))!=row["resolved_quantity"]:
                fail(f"{bag} quantity differs from manifest")

    scenario_labels={"spider-corpse":"Spider Corpse Tokens","chrysalis":"Chrysalis Tokens"}
    scenario_prefix="scene/scenario-01-the-cave/instance/scenario-token-supply-1/member/"
    for row in manifest["contents"]:
        if row["content_id"].startswith(scenario_prefix) and included(row):
            bag=scenario_labels[row["source"]["ref"]]
            if bag not in top or len(top[bag].get("ContainedObjects",[]))!=row["resolved_quantity"]:
                fail(f"{bag} quantity differs from manifest")

    health={
      "HEALTH ALT A · Unit Tokens":["representation/health-unit-tokens/component/0"],
      "HEALTH ALT B · Numbered Tracks":["representation/health-numbered-track/component/0","representation/health-numbered-track/component/1"],
      "HEALTH ALT C · Crew Health Cards":["representation/health-crew-card-marker/component/0"],
      "Health Card Markers":["representation/health-crew-card-marker/component/1"],
    }
    for name,ids in health.items():
        expected=sum(by_id[i]["resolved_quantity"] for i in ids)
        if name not in top or len(top[name].get("ContainedObjects",[]))!=expected:
            fail(f"{name} quantity differs from manifest")

    asset_dir=Path(a.asset_dir)
    expected_prefix=f"https://jmbjr.github.io/TheFountain/wretched-demesne/beta/tts/assets/{short}/"
    urls=set()
    for obj in all_objs:
        for cd in (obj.get("CustomDeck") or {}).values():
            for k in ("FaceURL","BackURL"):
                url=cd.get(k)
                if url:
                    if not url.startswith(expected_prefix): fail(f"asset URL outside build namespace: {url}")
                    urls.add(url)
    referenced={u.rsplit("/",1)[-1] for u in urls}
    actual={p.name for p in asset_dir.glob("*.png")}
    if referenced!=actual:
        fail(f"asset file set mismatch: missing={sorted(referenced-actual)} extra={sorted(actual-referenced)}")

    if a.zip:
        zp=Path(a.zip)
        with zipfile.ZipFile(zp) as z:
            files=set(z.namelist())
        required={Path(a.save).name,Path(a.manifest).name}|{f"assets/{x}" for x in actual}
        if not required.issubset(files): fail(f"zip missing files: {sorted(required-files)}")

    print(f"TTS verification passed: {Path(a.save).name} matches {manifest['manifest_id']} with {len(objs)} top-level objects.")

if __name__=="__main__": main()
