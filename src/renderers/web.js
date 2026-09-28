import {FountainEngine} from "../engine.js";
const data=await fetch("./game/game.json").then(r=>r.json()); const g=new FountainEngine(data);
const $=s=>document.querySelector(s);
function stats(){const s=g.state;$("#stats").innerHTML=[["Health",s.health],["Humanity",s.humanity],["Mutation",s.mutation],["Knowledge",s.knowledge]].map(([n,v])=>`<div><b>${n}</b><span>${v}</span><i style="width:${Math.min(v,100)}%"></i></div>`).join("")+`<div><b>Deaths</b><span>${s.deaths}</span></div>`;$("#stage").textContent=g.stage().name;}
function encounter(i=0){const e=data.encounters[i%data.encounters.length];$("#encounter").innerHTML=`<p class="eyebrow">ENCOUNTER ${i+1}</p><h2>${e.title}</h2><p>${e.text}</p><div class="choices"></div>`;e.choices.forEach(c=>{let b=document.createElement("button");b.textContent=c.label;b.onclick=()=>{g.apply(c);stats();encounter(i+1);};$(".choices").append(b);});}
$("#reset").onclick=()=>{g.reset();stats();encounter(0)};stats();encounter();
