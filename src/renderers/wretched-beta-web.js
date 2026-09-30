import {WretchedEngine} from "../wretched/engine.js";
import {loadWretchedResolved} from "../wretched/model.js";
import {createSeededRng} from "../wretched/random.js";
import {ReplayRecorder,runReplay} from "../wretched/replay.js";
import {buildTopologyView} from "../wretched/topology-view.js";
const $=s=>document.querySelector(s); let data,game,recorder,currentSeed;
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
try{data=await loadWretchedResolved("../../game/wretched-resolved-game.v1.json");boot()}catch(e){$("#setup").hidden=true;$("#fatal").hidden=false;$("#fatal").innerHTML=`<h2>Unable to open the expedition</h2><p>${esc(e.message)}</p>`}
function boot(){for(const crew of data.crew){const b=document.createElement("button");b.innerHTML=`<strong>${esc(crew.name)}</strong><small>HP ${crew.health} · DEF ${crew.defense} · ACC +${crew.accuracy}</small><span>${esc(crew.ability)}</span>`;b.className="wd-crew";b.onclick=()=>start(crew.id);$("#crewChoices").append(b)}}
function start(id,seed=$("#testSeed").value||"quick-test-001"){currentSeed=String(seed);game=new WretchedEngine(data,{rng:createSeededRng(currentSeed)});game.reset(id);recorder=new ReplayRecorder(game,{seed:currentSeed,crew:id,captureState:true});$("#setup").hidden=true;$("#play").hidden=false;render()}
function act(action){const before=game.state.actions;if(!recorder.dispatch(action)&&game.state.status==="playing")game.log("That action is not available right now.");else if(before===game.state.actions&&action.type!=="end-turn"&&game.state.status==="playing"){}render()}
function render(){
 const s=game.state,r=game.room();$("#hud").innerHTML=stat("Round",s.round)+stat("Actions",s.actions)+stat("Health",`${s.crew.currentHealth}/${s.crew.health}`)+stat("Ammo",`${s.ammo}/${data.rules.ammo.max}`)+stat("Threat",`${s.threat}/${data.rules.threat.max}`)+stat("Scrap",s.scrap)+stat("Seed",currentSeed);
 $("#roomName").textContent=r.name;$("#roomMeta").textContent=r.terrain?String(r.terrain).toUpperCase():"";
 $("#roomDetail").textContent=r.hazard||r.objective||r.lock||r.setup|| (r.searchable?"The room may contain something useful.":"Nothing obvious remains here.");
 $("#objective").textContent=data.scenario.objective;$("#inventory").innerHTML=`<h3>Inventory</h3>${s.inventory.length?s.inventory.map(id=>`<span class="wd-chip">${esc(data.salvage.find(x=>x.id===id)?.name||id)}</span>`).join(""):"<em>Empty</em>"}`;
 const ra=$("#roomActions");ra.innerHTML="";
 const moves=game.legalMoves();if(moves.length){const label=document.createElement("p");label.className="quiet";label.textContent="MOVE — follow an existing connection";ra.append(label)}
 moves.forEach(id=>button(ra,`Move → ${game.room(id).name}`,()=>act({type:"move",target:id}),s.actions<1));
 const exploreLabel=document.createElement("p");exploreLabel.className="quiet";exploreLabel.textContent=`EXPLORE — reveal a new room connected from ${r.name}`;ra.append(exploreLabel);
 button(ra,`Explore from ${r.name}`,()=>act({type:"explore"}),s.actions<1||!game.canExplore());
 button(ra,"Search room",()=>act({type:"search"}),s.actions<1||!r.searchable||s.searched.includes(r.id));
 button(ra,"Interact",()=>act({type:"interact"}),s.actions<1||!(r.id==="relay"&&s.inventory.includes("power-cell")));
 if(r.id==="entrance")button(ra,s.relayActive?"Extract — complete mission":"Retreat to ship",()=>act({type:"extract"}),s.actions<1);
 $("#hand").innerHTML="";s.hand.forEach((id,i)=>{const card=game.card(id),b=document.createElement("button");b.className="wd-card";b.innerHTML=`<small>${esc(card.type)}</small><strong>${esc(card.name)}</strong><span>${esc(card.text)}</span>${card.attack?`<i>ATK ${card.attack} · RNG ${card.range} · AMMO ${card.ammo} · NOISE ${card.noise}</i>`:""}`;b.disabled=s.actions<1||s.status!=="playing";if(id==="move"){const moves=game.legalMoves();b.disabled=b.disabled||moves.length!==1;b.title=moves.length===1?`Move to ${game.room(moves[0]).name}`:"Use the explicit Move destination buttons above."}b.onclick=()=>{const action={type:"play-card",handIndex:i,enemyIndex:0};if(id==="move"){const moves=game.legalMoves();if(moves.length!==1)return;action.target=moves[0]}act(action)};$("#hand").append(b)});
 const es=$("#enemies");es.innerHTML=s.enemies.length?s.enemies.map((e,i)=>`<div class="wd-enemy"><div><strong>${esc(e.name)}</strong><span>${esc(game.room(e.room)?.name||e.room)} · HP ${e.health} · ATK ${e.attack} · DEF ${e.defense}${e.fed?" · FED":""}</span></div><button data-enemy="${i}" ${s.actions<1||s.ammo<1?"disabled":""}>Fire Sidearm</button></div>`).join(""):"<p class='quiet'>No hostiles visible.</p>";
 es.querySelectorAll("[data-enemy]").forEach(b=>b.onclick=()=>act({type:"attack",enemyIndex:+b.dataset.enemy,cardId:"sidearm"}));
 const topology=buildTopologyView(s),nodeById=new Map(topology.nodes.map(n=>[n.id,n]));
 $("#rooms").innerHTML=topology.edges.map(({from,to})=>{
   const roomLabel=id=>{const n=nodeById.get(id);return `<span class="wd-room ${n.current?"here":""}">${esc(game.room(id).name)}${n.enemies?` 👾×${n.enemies}`:""}${n.corpses?` <b>☠×${n.corpses}</b>`:""}${n.chrysalis?" ◉":""}</span>`};
   return `<div class="wd-edge">${roomLabel(from)}<span class="arrow">↔</span>${roomLabel(to)}</div>`;
 }).join("")||topology.nodes.map(n=>`<span class="wd-room ${n.current?"here":""}">${esc(game.room(n.id).name)}</span>`).join("");
 $("#log").innerHTML=s.log.slice(0,10).map(x=>`<p>${esc(x)}</p>`).join("");
 $("#statusBanner").className="wd-banner "+s.status;$("#statusBanner").textContent=s.status==="playing"?`${s.crew.name} · ${s.relayActive?"RELAY ACTIVE — RETURN TO CAVE MOUTH":"EXPEDITION ACTIVE"}`:s.status==="won"?"SCENARIO COMPLETE":s.status==="retreated"?"EXPEDITION RETREATED":"EXPEDITION LOST";
 $("#endTurn").disabled=s.status!=="playing";document.querySelectorAll("#play button:not(#restart):not(#exportReplay)").forEach(b=>{if(s.status!=="playing")b.disabled=true});
}
function stat(n,v){return `<div><small>${n}</small><strong>${esc(v)}</strong></div>`}
function button(parent,label,fn,disabled=false){const b=document.createElement("button");b.textContent=label;b.disabled=disabled;b.onclick=fn;parent.append(b)}
$("#endTurn").onclick=()=>act({type:"end-turn"});
$("#exportReplay").onclick=()=>{if(!recorder)return;const blob=new Blob([JSON.stringify(recorder.toJSON(),null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`wretched-replay-${currentSeed}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),0)};
$("#loadReplay").onclick=async()=>{const file=$("#replayFile").files[0],out=$("#replayResult");if(!file){out.textContent="Choose a replay JSON file first.";return}try{const replay=JSON.parse(await file.text()),result=runReplay(data,replay);game=result.game;currentSeed=String(replay.seed);recorder=new ReplayRecorder(game,{seed:currentSeed,crew:replay.crew||"security",captureState:true});recorder.replay=structuredClone(replay);$("#setup").hidden=true;$("#play").hidden=false;render();out.textContent=""}catch(e){out.textContent=`Replay failed: ${e.message}`;if(e.step!==undefined)out.textContent+=` (step ${e.step})`}};
$("#restart").onclick=()=>{game=null;recorder=null;$("#play").hidden=true;$("#setup").hidden=false};
