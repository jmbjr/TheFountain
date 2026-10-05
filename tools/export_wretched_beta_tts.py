#!/usr/bin/env python3
"""Build a functional Wretched Demesne Scenario 01 TTS save from DODGE + canonical scenario data."""
from __future__ import annotations
import argparse,json,pathlib,hashlib,textwrap,sys
from PIL import Image,ImageDraw,ImageFont

ROOT=pathlib.Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from resolve_wretched_dodge import resolve
DODGE=ROOT/"game/wretched-demesne.dodge.v0.2.1.json"
SCENARIO=ROOT/"game/wretched-demesne.scenario-01.mvp.v0.1.json"
CONTRACT=ROOT/"game/export-contracts/wretched-beta-tts.dodge-export.json"
p=argparse.ArgumentParser();p.add_argument("--git-sha",default="local");a=p.parse_args()
sha=a.git_sha[:12] if a.git_sha!="local" else "local"
resolved=resolve(DODGE,CONTRACT); dodge=json.loads(DODGE.read_text()); data=resolved["canonical"]; contract=resolved["export_contract"]; manifest=resolved["target_manifest"]; manifest_by_id={x["content_id"]:x for x in manifest["contents"]}
if dodge["dodge_version"]!="0.2.1": raise SystemExit("TTS beta requires DODGE 0.2.1")
inc=next(x for x in contract["representation_inclusions"] if x["state_ref"]=="health")
if inc["mode"]!="alternatives": raise SystemExit("TTS beta must bundle Health alternatives")
outdir=ROOT/"wretched-demesne/beta/downloads"; assetdir=ROOT/"wretched-demesne/beta/tts/assets"/sha
outdir.mkdir(parents=True,exist_ok=True);assetdir.mkdir(parents=True,exist_ok=True)
outfile=outdir/f"wretched-demesne-scenario-01-beta-tts-{sha}.json"
BASE=f"https://jmbjr.github.io/TheFountain/wretched-demesne/beta/tts/assets/{sha}"

font=ImageFont.load_default()
def face(key,title,body,kind="CARD"):
    path=assetdir/f"{key}.png"
    im=Image.new("RGB",(630,880),"white"); dr=ImageDraw.Draw(im)
    dr.rectangle((8,8,621,871),outline="black",width=5);dr.text((35,30),kind,font=font,fill="black")
    dr.text((35,65),title,font=font,fill="black")
    y=110
    for line in textwrap.wrap(body or "",72):
        dr.text((35,y),line,font=font,fill="black");y+=18
    dr.text((35,835),f"WD BETA {sha}",font=font,fill="black")
    im.save(path)
    return f"{BASE}/{key}.png"

back_url=face("card-back","WRETCHED DEMESNE","Scenario 01 · The Cave","BACK")

def guid(seed): return hashlib.sha1((sha+seed).encode()).hexdigest()[:6]
def tr(x,z,y=1.2,ry=180): return {"posX":x,"posY":y,"posZ":z,"rotX":0,"rotY":ry,"rotZ":180,"scaleX":1,"scaleY":1,"scaleZ":1}
deck_counter=10
def make_deck(key,name,cards,x,z):
    global deck_counter
    custom={}; contained=[]; ids=[]
    for i,c in enumerate(cards):
        did=deck_counter+i
        url=face(f"{key}-{i:02d}-{c['id']}",c["name"],c.get("text") or c.get("effect") or c.get("objective") or "",c.get("type","CARD").upper())
        custom[str(did)]={"FaceURL":url,"BackURL":back_url,"NumWidth":1,"NumHeight":1,"BackIsHidden":True,"UniqueBack":False,"Type":0}
        cid=did*100
        ids.append(cid)
        contained.append({"GUID":guid(f"{key}-{i}"),"Name":"CardCustom","Transform":tr(0,0),"Nickname":c["name"],"Description":c.get("text") or c.get("effect") or "","CardID":cid,"CustomDeck":{str(did):custom[str(did)]}})
    deck_counter+=len(cards)+1
    return {"GUID":guid(key),"Name":"DeckCustom","Transform":tr(x,z),"Nickname":name,"Description":f"Generated from DODGE 0.2.1 · {sha}","DeckIDs":ids,"CustomDeck":custom,"ContainedObjects":contained}
def chip(name,desc,seed):
    return {"GUID":guid(seed),"Name":"Chip","Transform":tr(0,0,1,0),"Nickname":name,"Description":desc,"ColorDiffuse":{"r":0.8,"g":0.8,"b":0.8}}
def bag(key,name,items,x,z,desc=""):
    return {"GUID":guid(key),"Name":"Bag","Transform":tr(x,z,1,0),"Nickname":name,"Description":desc,"ContainedObjects":items}

objects=[]
# Starter decks come from resolved semantic collection membership, never qty_by_deck.
for n,crew in enumerate(data["crew"]):
    instance_id=f"{crew['id']}-starter-deck-1"
    prefix=f"scene/scenario-01-the-cave/instance/{instance_id}/member/"
    cards=[]
    for item in [x for x in manifest["contents"] if x["content_id"].startswith(prefix) and x["inclusion"]!="excluded-override"]:
        _,catalog,item_id=item["source"]["ref"].split(":",2)
        entity=next(x for x in data[catalog] if x["id"]==item_id)
        cards.extend([entity]*item["resolved_quantity"])
    objects.append(make_deck(f"starter-{crew['id']}",f"{crew['name']} Starter Deck",cards,-8+n*4,-7))
objects.append(make_deck("encounters","Encounter Deck",data["encounters"],-7,-2))
objects.append(make_deck("salvage","Salvage Deck",data["salvage"],-3,-2))
entrance=next(r for r in data["rooms"] if r["id"]=="entrance")
rooms=[r for r in data["rooms"] if r["id"]!="entrance"]
objects.append(make_deck("rooms","Unexplored Room Deck",rooms,1,-2))
objects.append(make_deck("entrance","Cave Mouth",[entrance],5,-2))
crewrefs=[{"id":c["id"],"name":c["name"],"type":"crew reference","text":f"Health {c['health']} · Accuracy {c['accuracy']:+d} · Defense {c['defense']}\n{c['ability']}"} for c in data["crew"]]
objects.append(make_deck("crew-reference","Crew Reference Cards",crewrefs,9,-2))

# Separate physical supplies, never one massive token bag.
enemy_prefix="scene/scenario-01-the-cave/instance/enemy-token-supply-1/member/"
enemy_items=[x for x in manifest["contents"] if x["content_id"].startswith(enemy_prefix) and x["inclusion"]!="excluded-override"]
for n,e in enumerate(data["enemies"]):
    item=next(x for x in enemy_items if x["source"]["ref"].endswith(":"+e["id"]))
    count=item["resolved_quantity"]
    items=[chip(e["name"],f"HP {e['health']} · ATK {e['attack']} · DEF {e['defense']} · MOVE {e['move']}",f"{e['id']}-{i}") for i in range(count)]
    objects.append(bag(f"bag-{e['id']}",f"{e['name']} Tokens",items,-8+n*4,4,"Prototype physical supply count; not game canon."))
scenario_supply_prefix="scene/scenario-01-the-cave/instance/scenario-token-supply-1/member/"
scenario_supplies=[x for x in manifest["contents"] if x["content_id"].startswith(scenario_supply_prefix) and x["inclusion"]!="excluded-override"]
corpse_count=next(x["resolved_quantity"] for x in scenario_supplies if x["source"]["ref"]=="spider-corpse")
chrysalis_count=next(x["resolved_quantity"] for x in scenario_supplies if x["source"]["ref"]=="chrysalis")
objects.append(bag("corpse-bag","Spider Corpse Tokens",[chip("Spider Corpse","Spider food",f"corpse-{i}") for i in range(corpse_count)],-8,8,"Target-manifest playtest supply count."))
objects.append(bag("chrysalis-bag","Chrysalis Tokens",[chip("Chrysalis","Hatches next End phase",f"chrysalis-{i}") for i in range(chrysalis_count)],-4,8,"Target-manifest playtest supply count."))

# Health representation laboratory: quantities come from resolved representation manifest rows.
health_manifest=[x for x in manifest["contents"] if x["content_id"].startswith("representation/") and x["inclusion"]!="excluded-override"]
unit_count=next(x["resolved_quantity"] for x in health_manifest if x["content_id"]=="representation/health-unit-tokens/component/0")
objects.append(bag("health-unit-bag","HEALTH ALT A · Unit Tokens",[chip("Health","+1 Health",f"health-unit-{i}") for i in range(unit_count)],0,8,"Alternative representation: unit tokens."))
track_count=next(x["resolved_quantity"] for x in health_manifest if x["content_id"]=="representation/health-numbered-track/component/0")
track_marker_count=next(x["resolved_quantity"] for x in health_manifest if x["content_id"]=="representation/health-numbered-track/component/1")
tracks=[chip(f"Health Track {i+1}","Numbered Health track",f"health-track-{i}") for i in range(track_count)]
markers=[chip("HP Marker","Place on numbered Health track",f"health-track-marker-{i}") for i in range(track_marker_count)]
objects.append(bag("health-track-bag","HEALTH ALT B · Numbered Tracks",tracks+markers,4,8,"Alternative representation: numbered tracks + markers."))
health_card_count=next(x["resolved_quantity"] for x in health_manifest if x["content_id"]=="representation/health-crew-card-marker/component/0")
health_card_marker_count=next(x["resolved_quantity"] for x in health_manifest if x["content_id"]=="representation/health-crew-card-marker/component/1")
healthcards=[{"id":f"health-{i}","name":f"Health Card {i+1}","type":"health","text":"Health reference card. Use one marker to show current Health."} for i in range(health_card_count)]
objects.append(make_deck("health-cards","HEALTH ALT C · Crew Health Cards",healthcards,8,8))
objects.append(bag("health-card-markers","Health Card Markers",[chip("HP Marker","Place on crew Health card",f"health-card-marker-{i}") for i in range(health_card_marker_count)],11,8))

save={"SaveName":f"Wretched Demesne Scenario 01 Beta {sha}","GameMode":"","Date":"","VersionNumber":"","GameType":"","GameComplexity":"","Tags":["DODGE","Wretched Demesne","Beta"],"Gravity":0.5,"PlayArea":0.5,"Table":"","Sky":"","Note":f"DODGE 0.2.1 · source {a.git_sha}\nHealth alternatives are evaluation variants; choose one representation during play.","Rules":"","XmlUI":"","LuaScript":"","LuaScriptState":"","ObjectStates":objects,"DODGE":{"version":"0.2.1","document_id":dodge["document_id"],"git_sha":a.git_sha,"contract":contract["contract_id"],"health_representation_mode":"alternatives"}}
outfile.write_text(json.dumps(save,indent=2))
print(outfile)
