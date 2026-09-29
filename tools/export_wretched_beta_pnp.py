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
parser.add_argument("--health-representation",choices=["tokens","track","crew-card"],default="crew-card")
args=parser.parse_args()
CONTRACT_PATH=ROOT/f"game/export-contracts/wretched-beta-pnp-health-{args.health_representation}.dodge-export.json"
OUT=ROOT/f"wretched-demesne/beta/downloads/wretched-demesne-scenario-01-beta-pnp-health-{args.health_representation}.pdf"

dodge=json.loads(DODGE_PATH.read_text())
if dodge.get("dodge_version")!="0.2.1":
    raise SystemExit("Beta PnP requires DODGE 0.2.1")
src=dodge["sources"]["scenario-mvp"]["uri"].split("#",1)[0]
data=json.loads((ROOT/src).read_text())
contract=json.loads(CONTRACT_PATH.read_text())
selection=next((x for x in contract["representation_selections"] if x["state_ref"]=="health"),None)
if not selection: raise SystemExit("PnP contract must select a Health representation")
health_rep=dodge["representations"][selection["representation_ref"]]
if health_rep["state_ref"]!="health": raise SystemExit("Selected Health representation does not bind Health")
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
        Flowable.__init__(self)
        self.width=CARD_W_IN*inch
        self.height=CARD_H_IN*inch
        self.name,self.kind,self.text,self.footer=name,kind,text,footer
    def wrap(self,availWidth,availHeight):
        return self.width,self.height
    def draw(self):
        p=self.canv
        w,h=self.width,self.height
        p.setStrokeColor(colors.black); p.setLineWidth(.6); p.rect(0,0,w,h,fill=0,stroke=1)
        # Digitropolis-style subtle rounded-corner cutting guides.
        r=.125*inch; d=2*r
        p.setStrokeColor(colors.HexColor("#AAAAAA")); p.setLineWidth(.25)
        p.arc(0,0,d,d,180,90); p.arc(w-d,0,w,d,270,90)
        p.arc(w-d,h-d,w,h,0,90); p.arc(0,h-d,d,h,90,90)
        y=h-10
        for txt,sty in [(esc(self.kind).upper(),card_type),(esc(self.name),card_title),(esc(self.text).replace("\\n","<br/>"),body)]:
            para=Paragraph(txt,sty); pw,ph=para.wrap(w-18,y)
            y-=ph; para.drawOn(p,9,y); y-=4
        if self.footer:
            para=Paragraph(esc(self.footer),small); pw,ph=para.wrap(w-18,max(0,y))
            para.drawOn(p,9,10)

def card(name,kind,text,footer=""):
    return CardFace(name,kind,text,footer)

