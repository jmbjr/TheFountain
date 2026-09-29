import {WretchedEngine} from "../wretched/engine.js?v=20260928-3";
import {loadWretchedMvp} from "../wretched/model.js?v=20260928-3";
const $=s=>document.querySelector(s); let data,game;
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
try{data=await loadWretchedMvp("../../game/wretched-demesne.scenario-01.mvp.v0.1.json?build=20260928-beta-1");boot()}catch(e){$("#setup").hidden=true;$("#fatal").hidden=false;$("#fatal").innerHTML=`<h2>Unable to open the expedition</h2><p>${esc(e.message)}</p>`}
function boot(){for(const c of data.crew){const b=document.createElement("button");b.innerHTML=`<strong>${esc(c.name)}</strong><small>HP ${c.health} · DEF ${c.defense} · ACC +${c.accuracy}</small><span>${esc(c.ability)}</span>`;b.className="wd-crew";b.onclick=()=>start(c.id);$("#crewChoices").append(b)}}
function start(id){game=new WretchedEngine(data);game.reset(id);$("#setup").hidden=true;$("#play").hidden=false;render()}
function act(fn){const before=game.state.actions;fn();if(before===game.state.actions&&game.state.status==="playing")game.log("That action is not available right now.");render()}
function render(){
 const s=game.state,r=game.room();$("#hud").innerHTML=stat("Round",s.round)+stat("Actions",s.actions)+stat("Health",`${s.crew.currentHealth}/${s.crew.health}`)+stat("Ammo",`${s.ammo}/${data.rules.ammo.max}`)+stat("Threat",`${s.threat}/${data.rules.threat.max}`)+stat("Scrap",s.scrap);
 $("#roomName").textContent=r.name;$("#roomMeta").textContent=r.terrain?String(r.terrain).toUpperCase():"";
 $("#roomDetail").textContent=r.hazard||r.objective||r.lock||r.setup|| (r.searchable?"The room may contain something useful.":"Nothing obvious remains here.");
 $("#objective").textContent=data.scenario.objective;$("#inventory").innerHTML=`<h3>Inventory</h3>${s.inventory.length?s.inventory.map(id=>`<span class="wd-chip">${esc(data.salvage.find(x=>x.id===id)?.name||id)}</span>`).join(""):"<em>Empty</em>"}`;
 const ra=$("#roomActions");ra.innerHTML="";
 game.legalMoves().forEach(id=>button(ra,`Move to ${game.room(id).name}`,()=>act(()=>game.move(id)),s.actions<1));
 button(ra,"Explore new room",()=>act(()=>game.explore()),s.actions<1||!s.roomDeck.length);
 button(ra,"Search room",()=>act(()=>game.search()),s.actions<1||!r.searchable||s.searched.includes(r.id));
 button(ra,"Interact",()=>act(()=>game.interact()),s.actions<1||!(r.id==="relay"&&s.inventory.includes("power-cell")));
 if(r.id==="entrance")button(ra,s.relayActive?"Extract — complete mission":"Retreat to ship",()=>act(()=>game.extract()),s.actions<1);
 $("#hand").innerHTML="";s.hand.forEach((id,i)=>{const c=game.card(id),b=document.createElement("button");b.className="wd-card";b.innerHTML=`<small>${esc(c.type)}</small><strong>${esc(c.name)}</strong><span>${esc(c.text)}</span>${c.attack?`<i>ATK ${c.attack} · RNG ${c.range} · AMMO ${c.ammo} · NOISE ${c.noise}</i>`:""}`;b.disabled=s.actions<1||s.status!=="playing";b.onclick=()=>act(()=>game.playCard(i,0));$("#hand").append(b)});
 const es=$("#enemies");es.innerHTML=s.enemies.length?s.enemies.map((e,i)=>`<div class="wd-enemy"><div><strong>${esc(e.name)}</strong><span>${esc(game.room(e.room)?.name||e.room)} · HP ${e.health} · ATK ${e.attack} · DEF ${e.defense}${e.fed?" · FED":""}</span></div><button data-enemy="${i}" ${s.actions<1||s.ammo<1?"disabled":""}>Fire Sidearm</button></div>`).join(""):"<p class='quiet'>No hostiles visible.</p>";
 es.querySelectorAll("[data-enemy]").forEach(b=>b.onclick=()=>act(()=>game.attack(+b.dataset.enemy)));
 $("#rooms").innerHTML=s.rooms.map(id=>`<span class="wd-room ${id===s.crew.room?"here":""}">${esc(game.room(id).name)}${s.corpses[id]?` <b>☠×${s.corpses[id]}</b>`:""}${s.chrysalises.some(c=>c.room===id)?" ◉":""}</span>`).join("<span class='arrow'>↔</span>");
 $("#log").innerHTML=s.log.slice(0,10).map(x=>`<p>${esc(x)}</p>`).join("");
 $("#statusBanner").className="wd-banner "+s.status;$("#statusBanner").textContent=s.status==="playing"?`${s.crew.name} · ${s.relayActive?"RELAY ACTIVE — RETURN TO CAVE MOUTH":"EXPEDITION ACTIVE"}`:s.status==="won"?"SCENARIO COMPLETE":s.status==="retreated"?"EXPEDITION RETREATED":"EXPEDITION LOST";
 $("#endTurn").disabled=s.status!=="playing";document.querySelectorAll("#play button:not(#restart)").forEach(b=>{if(s.status!=="playing")b.disabled=true});
}
function stat(n,v){return `<div><small>${n}</small><strong>${v}</strong></div>`}
function button(parent,label,fn,disabled=false){const b=document.createElement("button");b.textContent=label;b.disabled=disabled;b.onclick=fn;parent.append(b)}
$("#endTurn").onclick=()=>act(()=>game.endTurn());$("#restart").onclick=()=>{game=null;$("#play").hidden=true;$("#setup").hidden=false};
