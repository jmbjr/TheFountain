#!/usr/bin/env python3
"""Generate the Wretched Demesne Scenario 01 beta Print-and-Play PDF.

DODGE 0.2.1 is the baseline. The exporter reads the active DODGE document to
select the Scenario 01 source, then renders physical content from that declared
canonical source. It contains layout policy only; it must not invent game
balance, rules, membership, or quantities.
"""
from __future__ import annotations
import argparse, json, pathlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable

ROOT=pathlib.Path(__file__).parents[1]
DODGE_PATH=ROOT/"game/wretched-demesne.dodge.v0.2.1.json"
parser=argparse.ArgumentParser()
parser.add_argument("--git-sha",default="local")
args=parser.parse_args()
CONTRACT_PATH=ROOT/"game/export-contracts/wretched-beta-pnp.dodge-export.json"
SHORT_SHA=args.git_sha[:12] if args.git_sha != "local" else "local"\nOUT=ROOT/f"wretched-demesne/beta/downloads/wretched-demesne-scenario-01-beta-pnp-{SHORT_SHA}.pdf"

dodge=json.loads(DODGE_PATH.read_text())
if dodge.get("dodge_version")!="0.2.1":
    raise SystemExit("Beta PnP requires DODGE 0.2.1")
src=dodge["sources"]["scenario-mvp"]["uri"].split("#",1)[0]
data=json.loads((ROOT/src).read_text())
contract=json.loads(CONTRACT_PATH.read_text())
inclusion=next((x for x in contract["representation_inclusions"] if x["state_ref"]=="health"),None)
if not inclusion or inclusion["mode"]!="alternatives":
    raise SystemExit("Beta PnP contract must bundle Health alternatives")
health_reps=[dodge["representations"][ref] for ref in inclusion["representation_refs"]]
if any(rep["state_ref"]!="health" for rep in health_reps):
    raise SystemExit("All bundled Health representations must bind Health")
OUT.parent.mkdir(parents=True,exist_ok=True)

UNIT_TO_IN={"in":1.0,"mm":1/25.4,"cm":1/2.54,"pt":1/72}
def component_inches(archetype_id):
    comp=dodge["archetypes"][archetype_id]["component"]
    dims=comp.get("dimensions")
    if not dims or "width" not in dims or "height" not in dims:
        raise SystemExit(f"{archetype_id} requires explicit rectangular dimensions for dimensionally accurate PnP")
    scale=UNIT_TO_IN[dims["unit"]]
    return dims["width"]*scale,dims["height"]*scale

CARD_W_IN,CARD_H_IN=component_inches("standard-card")

styles=getSampleStyleSheet()
title=ParagraphStyle("title",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=22,leading=25,spaceAfter=10)
h=ParagraphStyle("h",parent=styles["Heading2"],fontName="Helvetica-Bold",fontSize=12,leading=14,spaceAfter=5)
body=ParagraphStyle("body",parent=styles["BodyText"],fontName="Helvetica",fontSize=8.3,leading=10.2)
small=ParagraphStyle("small",parent=body,fontSize=6.8,leading=8)
card_title=ParagraphStyle("ct",parent=body,fontName="Helvetica-Bold",fontSize=11,leading=12,alignment=TA_CENTER,spaceAfter=5)
card_type=ParagraphStyle("ctype",parent=small,fontName="Helvetica-Bold",alignment=TA_CENTER,textColor=colors.HexColor("#555555"),spaceAfter=4)

def esc(x):
    return str(x).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

class CardFace(Flowable):
    def __init__(self,name,kind,text,footer=""):
        Flowable.__init__(self); self.width=CARD_W_IN*inch; self.height=CARD_H_IN*inch
        self.name,self.kind,self.text,self.footer=name,kind,text,footer
    def wrap(self,availWidth,availHeight): return self.width,self.height
    def draw(self):
        p=self.canv; w,h=self.width,self.height
        p.setStrokeColor(colors.black); p.setLineWidth(.6); p.rect(0,0,w,h,fill=0,stroke=1)
        r=.125*inch; d=2*r
        p.setStrokeColor(colors.HexColor("#AAAAAA")); p.setLineWidth(.25)
        p.arc(0,0,d,d,180,90); p.arc(w-d,0,w,d,270,90); p.arc(w-d,h-d,w,h,0,90); p.arc(0,h-d,d,h,90,90)
        y=h-10
        for txt,sty in [(esc(self.kind).upper(),card_type),(esc(self.name),card_title),(esc(self.text).replace("\\n","<br/>"),body)]:
            para=Paragraph(txt,sty); _,ph=para.wrap(w-18,max(1,y)); y-=ph; para.drawOn(p,9,y); y-=4
        if self.footer:
            para=Paragraph(esc(self.footer),small); para.wrap(w-18,max(1,y)); para.drawOn(p,9,10)

def card(name,kind,text,footer=""):
    return CardFace(name,kind,text,footer)

class CardSheet(Flowable):
    """Deterministic portrait Letter 3x3 imposition, matching Digitropolis."""
    def __init__(self,cards):
        Flowable.__init__(self); self.cards=cards
        self.card_w=CARD_W_IN*inch; self.card_h=CARD_H_IN*inch
        self.width=self.card_w*3; self.height=self.card_h*3
    def wrap(self,availWidth,availHeight): return self.width,self.height
    def draw(self):
        p=self.canv
        for slot,item in enumerate(self.cards[:9]):
            col=slot%3; row=2-slot//3
            item.drawOn(p,col*self.card_w,row*self.card_h)
        p.setStrokeColor(colors.HexColor("#666666")); p.setLineWidth(.25); mark=6
        for col in range(4):
            x=col*self.card_w; p.line(x,-mark,x,0); p.line(x,self.height,x,self.height+mark)
        for row in range(4):
            y=row*self.card_h; p.line(-mark,y,0,y); p.line(self.width,y,self.width+mark,y)

def card_sheets(cards):
    return [CardSheet(cards[i:i+9]) for i in range(0,len(cards),9)]

story=[Paragraph("WRETCHED DEMESNE",title),Paragraph("Scenario 01: The Cave — Beta Print-and-Play · DODGE 0.2.1",h),
 Paragraph(f"This is the Implementor review build · Git {esc(args.git_sha[:12])}. Game content comes from the Scenario 01 source declared by the active DODGE 0.2.1 document. Cut on card borders. No artwork is required for this functional prototype.",body),Spacer(1,8),
 Paragraph("SETUP",h)]
for x in data["scenario"]["setup"]: story.append(Paragraph("• "+esc(x),body))
story += [Spacer(1,6),Paragraph("OBJECTIVE",h),Paragraph(esc(data["scenario"]["objective"]),body),Spacer(1,6),Paragraph("WIN",h),Paragraph(esc(data["scenario"]["win"]),body),Spacer(1,6),Paragraph("LOSS",h)]
for x in data["scenario"]["loss"]: story.append(Paragraph("• "+esc(x),body))
story += [Spacer(1,8),Paragraph("CORE RULES",h)]
for k,v in data["rules"].items():
    if isinstance(v,dict):
        val=v.get("value")
        if val is None and k=="threat": val="Threat starts at %s and maxes at %s. %s"%(v["start"],v["max"]," ".join("At %s: %s"%(q["at"],q["effect"]) for q in v["thresholds"]))
        if val is None and k=="ammo": val=v["value"]+" Start %s / max %s."%(v["starting"],v["max"])
        if val is not None: story.append(Paragraph("<b>%s:</b> %s"%(esc(k.replace("_"," ").title()),esc(val)),body))
story.append(PageBreak())

story += [Paragraph("HEALTH REPRESENTATION LAB",h),Paragraph(
    "The Beta PnP export profile bundles all configured Health alternatives into this one packet. "
    "They bind the same DODGE Health state and are alternatives for evaluation, not simultaneous gameplay requirements.",body),Spacer(1,8)]

all_cards=[]
for crew in data["crew"]:
    all_cards.append(card(crew["name"],"Crew reference",f'Health {crew["health"]} · Accuracy +{crew["accuracy"]} · Defense {crew["defense"]}\\n\\n{crew["ability"]}'))

# Starter decks are rendered exactly from qty_by_deck. This intentionally exposes
# the known Medic 11-card inconsistency instead of silently correcting it.
for crew in data["crew"]:
    for action in data["cards"]:
        qty=action.get("qty_by_deck",{}).get(crew["id"],0)
        stats=[]
        for key,label in (("attack","ATK"),("range","RNG"),("ammo","AMMO"),("noise","NOISE")):
            if key in action: stats.append(f'{label} {action[key]}')
        footer=f'{crew["name"]} starter · '+" · ".join(stats)
        for _ in range(qty): all_cards.append(card(action["name"],action["type"],action["text"],footer))

for room in data["rooms"]:
    details=[f'Connections: {room["connections"]}',"Searchable" if room["searchable"] else "Not searchable"]
    for key in ("terrain","setup","hazard","lock","objective_item","objective","tag"):
        if room.get(key): details.append(f'{key.replace("_"," ").title()}: {room[key]}')
    all_cards.append(card(room["name"],"Room","\\n".join(details)))
for x in data["encounters"]: all_cards.append(card(x["name"],"Encounter",x["effect"]))
for x in data["salvage"]: all_cards.append(card(x["name"],"Salvage · "+x["type"],x["effect"]))
for x in data["enemies"]:
    all_cards.append(card(x["name"],"Enemy reference",f'Health {x["health"]} · Attack {x["attack"]} · Defense {x["defense"]} · Move {x["move"]}\\n\\nAI: {x["ai"]}\\n\\n{"Leaves Spider Corpse" if x["corpse"] else "No Spider Corpse"}'))

# Resolve every representation candidate included by the DODGE alternatives bundle.
marker_count=0
for rep in health_reps:
    story += [Paragraph(esc(rep["name"]).upper(),h)]
    if rep["kind"]=="unit_tokens":
        cells=[]
        for crew in data["crew"]:
            for _ in range(crew["health"]):
                cells.append(Paragraph(f'{esc(crew["name"])}<br/>HP',ParagraphStyle("hptok",parent=small,alignment=TA_CENTER,fontName="Helvetica-Bold")))
        rows=[cells[i:i+8] for i in range(0,len(cells),8)]
        while len(rows[-1])<8: rows[-1].append("")
        t=Table(rows,colWidths=[18/25.4*inch]*8,rowHeights=[18/25.4*inch]*len(rows),hAlign="CENTER")
        t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.5,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        story += [t,Spacer(1,10)]
    elif rep["kind"]=="numbered_track":
        tracks=[]
        for crew in data["crew"]:
            nums="  ".join(str(x) for x in range(crew["health"]+1))
            tracks.append(Table([[Paragraph(f'<b>{esc(crew["name"])} HEALTH</b><br/>{nums}',body)]],colWidths=[50/25.4*inch],rowHeights=[100/25.4*inch],style=[("BOX",(0,0),(-1,-1),.6,colors.black),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),8)]))
        for i in range(0,len(tracks),3):
            row=tracks[i:i+3]
            while len(row)<3: row.append("")
            story += [Table([row],colWidths=[50/25.4*inch]*3,hAlign="CENTER",style=[("VALIGN",(0,0),(-1,-1),"TOP")]),Spacer(1,8)]
        marker_count += len(data["crew"])
    elif rep["kind"]=="marker_track":
        for crew in data["crew"]:
            all_cards.append(card(crew["name"],"Health alternative · crew card","Health\\n"+" · ".join(str(x) for x in range(crew["health"]+1)),"Use one marker/cube to show current Health."))
        marker_count += len(data["crew"])

if marker_count:
    markers=[Paragraph("HP",ParagraphStyle("hpmark",parent=small,alignment=TA_CENTER,fontName="Helvetica-Bold")) for _ in range(marker_count)]
    rows=[markers[i:i+10] for i in range(0,len(markers),10)]
    while len(rows[-1])<10: rows[-1].append("")
    mt=Table(rows,colWidths=[8/25.4*inch]*10,rowHeights=[8/25.4*inch]*len(rows),hAlign="CENTER")
    mt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    story += [Paragraph("HEALTH MARKERS FOR TRACK ALTERNATIVES",h),mt,Spacer(1,8)]

# All poker/MTG-size components are packed continuously. At 63 x 88 mm, three
# columns by three rows fit portrait US Letter when adjacent with no gutters.
story.append(PageBreak())
pages=card_sheets(all_cards)
for index,page in enumerate(pages):
    story.append(page)
    if index != len(pages)-1: story.append(PageBreak())
story.append(PageBreak())

tokens=[]
for label,count in [("Small Spider",6),("Large Spider",4),("Alpha Spider",2),("Brood Mother",1),("Men of Leng Servant",2),("Spider Corpse",8),("Chrysalis",4)]:
    # Token counts are explicitly layout/test inventory, not canonical quantities.
    for _ in range(count): tokens.append(Paragraph(esc(label),ParagraphStyle("tok",parent=small,alignment=TA_CENTER,fontName="Helvetica-Bold")))
rows=[tokens[i:i+5] for i in range(0,len(tokens),5)]
while len(rows[-1])<5: rows[-1].append("")
tt=Table(rows,colWidths=[1.35*inch]*5,rowHeights=[.72*inch]*len(rows),hAlign="CENTER")
tt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.6,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
story += [Paragraph("BETA PLAYTEST TOKEN SHEET",h),Paragraph("Token counts on this sheet are explicitly non-canonical physical playtest inventory because DODGE/Scenario 01 does not yet specify supply quantities. Do not treat these counts as game rules.",body),Spacer(1,8),tt]

doc=SimpleDocTemplate(str(OUT),pagesize=letter,rightMargin=.25*inch,leftMargin=.25*inch,topMargin=.20*inch,bottomMargin=.20*inch,title="Wretched Demesne Scenario 01 Beta PnP")
doc.build(story)
print(OUT)
