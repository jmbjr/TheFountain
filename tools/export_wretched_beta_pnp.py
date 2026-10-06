#!/usr/bin/env python3
"""Generate the Wretched Demesne Scenario 01 beta Print-and-Play PDF.

DODGE 0.2.1 is the baseline. The exporter reads the active DODGE document to
select the Scenario 01 source, then renders physical content from that declared
canonical source. It contains layout policy only; it must not invent game
balance, rules, membership, or quantities.
"""
from __future__ import annotations
import argparse, json, pathlib, sys
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable

ROOT=pathlib.Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from resolve_wretched_dodge import resolve
DODGE_PATH=ROOT/"game/wretched-demesne.dodge.v0.2.1.json"
parser=argparse.ArgumentParser()
parser.add_argument("--git-sha",default="local")
args=parser.parse_args()
CONTRACT_PATH=ROOT/"game/export-contracts/wretched-beta-pnp.dodge-export.json"
SHORT_SHA=args.git_sha[:12] if args.git_sha!="local" else "local"
OUT=ROOT/f"wretched-demesne/beta/downloads/wretched-demesne-scenario-01-beta-pnp-{SHORT_SHA}.pdf"
MANIFEST_OUT=ROOT/f"wretched-demesne/beta/downloads/wretched-demesne-scenario-01-beta-pnp-manifest-{SHORT_SHA}.json"

resolved=resolve(DODGE_PATH,CONTRACT_PATH)
data=resolved["canonical"]
contract=resolved["export_contract"]
manifest=resolved["target_manifest"]
manifest_by_id={x["content_id"]:x for x in manifest["contents"]}
MANIFEST_OUT.parent.mkdir(parents=True,exist_ok=True)
MANIFEST_OUT.write_text(json.dumps(manifest,indent=2)+"\n")
inclusion=next((x for x in contract["representation_inclusions"] if x["state_ref"]=="health"),None)
if not inclusion or inclusion["mode"]!="alternatives":
    raise SystemExit("Beta PnP contract must bundle Health alternatives")
health_reps=[(ref,resolved["representations"][ref]) for ref in inclusion["representation_refs"]]
if any(rep["state_ref"]!="health" for _,rep in health_reps):
    raise SystemExit("All bundled Health representations must bind Health")
OUT.parent.mkdir(parents=True,exist_ok=True)

UNIT_TO_IN={"in":1.0,"mm":1/25.4,"cm":1/2.54,"pt":1/72}
def component_inches(archetype_id):
    comp=resolved["archetypes"][archetype_id]["component"]
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

def diagnostic_contents_rows():
    rows=[[Paragraph("<b>Semantic component / source</b>",small),Paragraph("<b>Qty</b>",small),Paragraph("<b>Component</b>",small),Paragraph("<b>Diagnostics</b>",small)]]
    children={}
    for candidate in manifest["contents"]:
        if candidate.get("parent_content_id"):
            children.setdefault(candidate["parent_content_id"],[]).append(candidate)
    # The designer-facing view is intentionally hierarchical: scene collections
    # are one row; their deterministic leaf members remain in the manifest.
    primary=[x for x in manifest["contents"] if not x.get("parent_content_id")]
    for item in primary:
        if item["inclusion"]=="excluded-override":
            continue
        comp=item.get("component_effective") or item.get("component_inherited") or {}
        dims=comp.get("dimensions",{})
        size=""
        if dims:
            size=f'{dims.get("width","?")} × {dims.get("height","?")} {dims.get("unit","")}'
        component=" · ".join(x for x in [comp.get("form"),comp.get("size_class"),size] if x)
        identity=item["content_id"]
        source=item["source"]
        refs=[f'{source["kind"]}: {source["ref"]}']
        if item.get("representation_ref"):
            refs.append(f'representation: {item["representation_ref"]}')
        if item.get("variant_of"):
            refs.append(f'variant of: {item["variant_of"]}')
        flags=[]
        if item["inclusion"]=="included-override":
            flags.append("TARGET OVERRIDE")
        for diag in item.get("diagnostics",[]):
            if diag.get("classification")=="noncanonical-playtest":
                flags.append("NONCANONICAL PLAYTEST")
            elif diag.get("status")=="overridden" and diag.get("field")!="inclusion":
                flags.append(f'override: {diag.get("field")}')
        provenance=" → ".join(f'{p["kind"]}:{p["ref"]}' for p in item.get("provenance",[]))
        member_rows=[x for x in children.get(identity,[]) if x["inclusion"]!="excluded-override"]
        member_note=""
        quantity=str(item["resolved_quantity"])
        if member_rows:
            total=sum(x["resolved_quantity"] for x in member_rows)
            member_note=f'<br/><b>{len(member_rows)} member definitions · {total} physical cards/items</b>'
            quantity=str(total)
        left=f'<b>{esc(identity)}</b><br/>{esc(" · ".join(refs))}{member_note}<br/><font size="5.5">{esc(provenance)}</font>'
        rows.append([Paragraph(left,small),Paragraph(quantity,small),Paragraph(esc(component or "—"),small),Paragraph(esc(" · ".join(dict.fromkeys(flags)) or "canonical/inherited"),small)])
    return rows

def diagnostic_contents_table():
    rows=diagnostic_contents_rows()
    table=Table(rows,colWidths=[3.15*inch,.42*inch,1.45*inch,1.55*inch],repeatRows=1,hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.25,colors.HexColor("#999999")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#EEEEEE")),
        ("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    return table

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

story += [Paragraph("CONTENTS — DODGE DIAGNOSTIC",h),Paragraph(
    "Generated from the exact resolved DODGE target manifest consumed by this PDF. "
    "Quantities and component metadata shown here are effective target values; target overrides and noncanonical playtest quantities are explicitly flagged.",body),Spacer(1,8),
    diagnostic_contents_table(),PageBreak()]

story += [Paragraph("HEALTH REPRESENTATION LAB",h),Paragraph(
    "The Beta PnP export profile bundles all configured Health alternatives into this one packet. "
    "They bind the same DODGE Health state and are alternatives for evaluation, not simultaneous gameplay requirements.",body),Spacer(1,8)]

all_cards=[]
manifest_card_groups=[
    ("crew-reference-cards-1","Crew reference",None),
    ("captain-starter-deck-1","Action","Captain"),
    ("security-starter-deck-1","Action","Security"),
    ("engineer-starter-deck-1","Action","Engineer"),
    ("medic-starter-deck-1","Action","Medic"),
    ("scout-starter-deck-1","Action","Scout"),
    ("scenario-room-cards-1","Room",None),
    ("scenario-encounter-cards-1","Encounter",None),
    ("scenario-salvage-cards-1","Salvage",None),
    ("enemy-reference-cards-1","Enemy reference",None),
]
for instance_id,kind,deck_name in manifest_card_groups:
    prefix=f"scene/scenario-01-the-cave/instance/{instance_id}/member/"
    for item in [x for x in manifest["contents"] if x["content_id"].startswith(prefix) and x["inclusion"]!="excluded-override"]:
        source_ref=item["source"]["ref"]
        _,catalog,item_id=source_ref.split(":",2)
        matches=[x for x in data.get(catalog,[]) if x.get("id")==item_id]
        if len(matches)!=1:
            raise SystemExit(f"Expected one canonical entity for {source_ref}")
        entity=matches[0]
        if kind=="Crew reference":
            text=f'Health {entity["health"]} · Accuracy +{entity["accuracy"]} · Defense {entity["defense"]}\\n\\n{entity["ability"]}'
            footer=""
        elif kind=="Action":
            text=entity["text"]; stats=[]
            for key,label in (("attack","ATK"),("range","RNG"),("ammo","AMMO"),("noise","NOISE")):
                if key in entity: stats.append(f'{label} {entity[key]}')
            footer=" · ".join(([f"{deck_name} starter"] if deck_name else [])+stats)
        elif kind=="Room":
            details=[f'Connections: {entity["connections"]}',"Searchable" if entity["searchable"] else "Not searchable"]
            for key in ("terrain","setup","hazard","lock","objective_item","objective","tag"):
                if entity.get(key): details.append(f'{key.replace("_"," ").title()}: {entity[key]}')
            text="\\n".join(details); footer=""
        elif kind=="Encounter":
            text=entity["effect"]; footer=""
        elif kind=="Salvage":
            text=entity["effect"]; footer=entity["type"]
        else:
            text=f'Health {entity["health"]} · Attack {entity["attack"]} · Defense {entity["defense"]} · Move {entity["move"]}\\n\\nAI: {entity["ai"]}\\n\\n{"Leaves Spider Corpse" if entity["corpse"] else "No Spider Corpse"}'; footer=""
        for _ in range(item["resolved_quantity"]):
            all_cards.append(card(entity["name"],kind,text,footer))

# Render the representation inventory already resolved by DODGE. PnP owns only
# presentation; binding and quantities must not be recomputed from crew Health here.
rep_inventory=resolved["inventory"]["representations"]
crew_by_id={crew["id"]:crew for crew in data["crew"]}
marker_items=[]
for rep_ref,rep in health_reps:
    story += [Paragraph(esc(rep["name"]).upper(),h)]
    items=[x for x in rep_inventory if x["representation_ref"]==rep_ref]
    if rep["kind"]=="unit_tokens":
        cells=[]
        for item in [x for x in items if x["role"]=="unit"]:
            crew=crew_by_id[item["binding_ref"]]
            for _ in range(item["quantity"]):
                cells.append(Paragraph(f'{esc(crew["name"])}<br/>HP',ParagraphStyle("hptok",parent=small,alignment=TA_CENTER,fontName="Helvetica-Bold")))
        rows=[cells[i:i+8] for i in range(0,len(cells),8)]
        while len(rows[-1])<8: rows[-1].append("")
        t=Table(rows,colWidths=[18/25.4*inch]*8,rowHeights=[18/25.4*inch]*len(rows),hAlign="CENTER")
        t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.5,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        story += [t,Spacer(1,10)]
    elif rep["kind"]=="numbered_track":
        tracks=[]
        for item in [x for x in items if x["role"]=="track"]:
            crew=crew_by_id[item["binding_ref"]]
            nums="  ".join(str(x) for x in range(crew["health"]+1))
            for _ in range(item["quantity"]):
                tracks.append(Table([[Paragraph(f'<b>{esc(crew["name"])} HEALTH</b><br/>{nums}',body)]],colWidths=[50/25.4*inch],rowHeights=[100/25.4*inch],style=[("BOX",(0,0),(-1,-1),.6,colors.black),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),8)]))
        for i in range(0,len(tracks),3):
            row=tracks[i:i+3]
            while len(row)<3: row.append("")
            story += [Table([row],colWidths=[50/25.4*inch]*3,hAlign="CENTER",style=[("VALIGN",(0,0),(-1,-1),"TOP")]),Spacer(1,8)]
        marker_items.extend(x for x in items if x["role"]=="marker")
    elif rep["kind"]=="marker_track":
        for item in [x for x in items if x["role"]=="reference-track"]:
            crew=crew_by_id[item["binding_ref"]]
            for _ in range(item["quantity"]):
                all_cards.append(card(crew["name"],"Health alternative · crew card","Health\\n"+" · ".join(str(x) for x in range(crew["health"]+1)),"Use one marker/cube to show current Health."))
        marker_items.extend(x for x in items if x["role"]=="marker")

if marker_items:
    markers=[Paragraph("HP",ParagraphStyle("hpmark",parent=small,alignment=TA_CENTER,fontName="Helvetica-Bold")) for item in marker_items for _ in range(item["quantity"])]
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
playtest_supply_counts={
    "Small Spider":manifest_by_id["scene/scenario-01-the-cave/instance/enemy-token-supply-1/member/0"]["resolved_quantity"],
    "Large Spider":manifest_by_id["scene/scenario-01-the-cave/instance/enemy-token-supply-1/member/1"]["resolved_quantity"],
    "Alpha Spider":manifest_by_id["scene/scenario-01-the-cave/instance/enemy-token-supply-1/member/2"]["resolved_quantity"],
    "Brood Mother":manifest_by_id["scene/scenario-01-the-cave/instance/enemy-token-supply-1/member/3"]["resolved_quantity"],
    "Men of Leng Servant":manifest_by_id["scene/scenario-01-the-cave/instance/enemy-token-supply-1/member/4"]["resolved_quantity"],
    "Spider Corpse":manifest_by_id["scene/scenario-01-the-cave/instance/scenario-token-supply-1/member/0"]["resolved_quantity"],
    "Chrysalis":manifest_by_id["scene/scenario-01-the-cave/instance/scenario-token-supply-1/member/1"]["resolved_quantity"],
}
for label,count in playtest_supply_counts.items():
    # All token-sheet quantities come from the validated target manifest.
    for _ in range(count): tokens.append(Paragraph(esc(label),ParagraphStyle("tok",parent=small,alignment=TA_CENTER,fontName="Helvetica-Bold")))
rows=[tokens[i:i+5] for i in range(0,len(tokens),5)]
while len(rows[-1])<5: rows[-1].append("")
tt=Table(rows,colWidths=[1.35*inch]*5,rowHeights=[.72*inch]*len(rows),hAlign="CENTER")
tt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.6,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
story += [Paragraph("BETA PLAYTEST TOKEN SHEET",h),Paragraph("Token counts on this sheet are explicitly non-canonical physical playtest inventory because DODGE/Scenario 01 does not yet specify supply quantities. Do not treat these counts as game rules.",body),Spacer(1,8),tt]

doc=BaseDocTemplate(str(OUT),pagesize=letter,title="Wretched Demesne Scenario 01 Beta PnP")
margin_x=.25*inch
margin_y=.20*inch
frame=Frame(margin_x,margin_y,letter[0]-2*margin_x,letter[1]-2*margin_y,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id="pnp")
doc.addPageTemplates([PageTemplate(id="pnp",frames=[frame])])
doc.build(story)
print(OUT)
print(MANIFEST_OUT)
