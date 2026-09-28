"""DODGE adapter: neutral game/game.json -> TTS-friendly JSON manifest."""
import json,pathlib
ROOT=pathlib.Path(__file__).parents[1]; d=json.loads((ROOT/"game/game.json").read_text())
out=ROOT/"dist/tts";out.mkdir(parents=True,exist_ok=True)
manifest={"ObjectStates":[],"DODGE":{"source":"game/game.json","mutations":d["mutations"],"encounters":d["encounters"]}}
(out/"TheFountain.json").write_text(json.dumps(manifest,indent=2));print(out/"TheFountain.json")
