#!/usr/bin/env python3
"""Build a functional Wretched Demesne Scenario 01 TTS save from DODGE + canonical scenario data."""
from __future__ import annotations
import argparse,json,pathlib,hashlib,textwrap
from PIL import Image,ImageDraw,ImageFont

ROOT=pathlib.Path(__file__).parents[1]
DODGE=ROOT/"game/wretched-demesne.dodge.v0.2.1.json"
SCENARIO=ROOT/"game/wretched-demesne.scenario-01.mvp.v0.1.json"
CONTRACT=ROOT/"game/export-contracts/wretched-beta-tts.dodge-export.json"
p=argparse.ArgumentParser();p.add_argument("--git-sha",default="local");a=p.parse_args()
sha=a.git_sha[:12] if a.git_sha!="local" else "local"
dodge=json.loads(DODGE.read_text()); data=json.loads(SCENARIO.read_text()); contract=json.loads(CONTRACT.read_text())
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
# Rational card groups: one starter deck per crew, plus independent encounter, salvage and room decks.
for n,crew in enumerate(data["crew"]):
    cards=[]
    for c in data["cards"]:
        for _ in range(c.get("qty_by_deck",{}).get(crew["id"],0)): cards.append(c)
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
enemy_counts={"small-spider":6,"large-spider":4,"alpha-spider":2,"brood-mother":1,"leng-servant":2}
for n,e in enumerate(data["enemies"]):
    count=enemy_counts[e["id"]]
    items=[chip(e["name"],f"HP {e['health']} · ATK {e['attack']} · DEF {e['defense']} · MOVE {e['move']}",f"{e['id']}-{i}") for i in range(count)]
    objects.append(bag(f"bag-{e['id']}",f"{e['name']} Tokens",items,-8+n*4,4,"Prototype physical supply count; not game canon."))
objects.append(bag("corpse-bag","Spider Corpse Tokens",[chip("Spider Corpse","Spider food",f"corpse-{i}") for i in range(8)],-8,8,"Prototype physical supply count."))
objects.append(bag("chrysalis-bag","Chrysalis Tokens",[chip("Chrysalis","Hatches next End phase",f"chrysalis-{i}") for i in range(4)],-4,8,"Prototype physical supply count."))

# Health representation laboratory: all three configured alternatives, kept separate.
max_hp=max(c["health"] for c in data["crew"])
objects.append(bag("health-unit-bag","HEALTH ALT A · Unit Tokens",[chip("Health","+1 Health",f"health-unit-{i}") for i in range(max_hp*len(data["crew"]))],0,8,"Alternative representation: unit tokens."))
tracks=[chip(f"{c['name']} Health Track",f"0–{c['health']} numbered track",f"health-track-{c['id']}") for c in data["crew"]]
markers=[chip("HP Marker","Place on numbered Health track",f"health-track-marker-{i}") for i in range(len(data["crew"]))]
objects.append(bag("health-track-bag","HEALTH ALT B · Numbered Tracks",tracks+markers,4,8,"Alternative representation: numbered tracks + markers."))
healthcards=[{"id":c["id"],"name":f"{c['name']} Health","type":"health","text":f"Health 0–{c['health']}. Use one marker on this card."} for c in data["crew"]]
objects.append(make_deck("health-cards","HEALTH ALT C · Crew Health Cards",healthcards,8,8))
objects.append(bag("health-card-markers","Health Card Markers",[chip("HP Marker","Place on crew Health card",f"health-card-marker-{i}") for i in range(len(data["crew"]))],11,8))

save={"SaveName":f"Wretched Demesne Scenario 01 Beta {sha}","GameMode":"","Date":"","VersionNumber":"","GameType":"","GameComplexity":"","Tags":["DODGE","Wretched Demesne","Beta"],"Gravity":0.5,"PlayArea":0.5,"Table":"","Sky":"","Note":f"DODGE 0.2.1 · source {a.git_sha}\nHealth alternatives are evaluation variants; choose one representation during play.","Rules":"","XmlUI":"","LuaScript":"","LuaScriptState":"","ObjectStates":objects,"DODGE":{"version":"0.2.1","document_id":dodge["document_id"],"git_sha":a.git_sha,"contract":contract["contract_id"],"health_representation_mode":"alternatives"}}
outfile.write_text(json.dumps(save,indent=2))
print(outfile)
