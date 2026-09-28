"""DODGE adapter: neutral game/game.json -> printable prototype.
Keep game semantics out of this renderer. A production version emits PDF cards/sheets.
"""
import json, pathlib
ROOT=pathlib.Path(__file__).parents[1]
data=json.loads((ROOT/"game/game.json").read_text())
out=ROOT/"dist/pnp"; out.mkdir(parents=True,exist_ok=True)
text=[data["title"],data["tagline"],"","MUTATIONS"]
text += [f'{m["name"]}: {m["benefit"]} / {m["cost"]}' for m in data["mutations"]]
text += ["","ENCOUNTERS"]+[e["title"]+": "+e["text"] for e in data["encounters"]]
(out/"prototype.txt").write_text("\n".join(text))
print(out/"prototype.txt")
