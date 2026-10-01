// Shared, renderer-agnostic runtime for Wretched Demesne Scenario 01.
// Gameplay values live in the canonical dataset, not here.
export class WretchedEngine {
  constructor(data, {rng=Math.random}={}) { this.data=data; this.rng=rng; this.reset(); }
  reset(crewId="security") {
    const crew=this.data.crew.find(c=>c.id===crewId) || this.data.crew[0];
    this.state={round:1,phase:"crew",crew:{...crew,currentHealth:crew.health,room:"entrance",extracted:false,incapacitated:false},
      actions:this.data.rules.actions_per_turn.value,ammo:this.data.rules.ammo.starting,scrap:0,knowledge:0,threat:this.data.rules.threat.start,
      relayActive:false,inventory:[],searched:[],rooms:["entrance"],roomDeck:this.shuffle((this.data.semantic_decks?.rooms||this.data.rooms.map(r=>r.id)).filter(id=>id!=="entrance"&&id!=="relay")),
      encounters:this.shuffle(this.data.semantic_decks?.encounters||this.data.encounters.map(e=>e.id)),salvage:this.shuffle(this.data.semantic_decks?.salvage||this.data.salvage.map(s=>s.id)),
      connections:{entrance:[]},enemies:[],corpses:{},chrysalises:[],log:[],actionNumber:0,status:"playing"};
    this.log("Expedition begins at the Cave Mouth.");
    const relay=this.state.roomDeck.length<3?this.state.roomDeck.length:Math.max(0,this.state.roomDeck.length-3+Math.floor(this.rng()*3));
    this.state.roomDeck.splice(relay,0,"relay"); this.buildDeck(crewId); return this.state;
  }
  shuffle(a){a=[...a];for(let i=a.length-1;i>0;i--){const j=Math.floor(this.rng()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
  buildDeck(id){const resolved=this.data.starter_decks?.[id];let d=resolved?[...resolved]:[];if(!resolved){for(const c of this.data.cards){for(let i=0;i<(c.qty_by_deck?.[id]||0);i++)d.push(c.id)}}this.state.deck=this.shuffle(d);this.state.discard=[];this.state.hand=[];this.draw(this.data.rules.hand_size.value);}
  draw(n=1){while(n--){if(!this.state.deck.length){this.state.deck=this.shuffle(this.state.discard);this.state.discard=[]}if(this.state.deck.length)this.state.hand.push(this.state.deck.pop())}}
  spend(){if(this.state.status!=="playing"||this.state.actions<1)return false;this.state.actions--;return true}
  log(message,level="INFO"){this.state.log.unshift({level,round:this.state.round,action:this.state.actionNumber||0,message})}
  room(id=this.state.crew.room){return this.data.rooms.find(r=>r.id===id)}
  card(id){return this.data.cards.find(c=>c.id===id)}
  connect(a,b){this.state.connections[a]??=[];this.state.connections[b]??=[];if(!this.state.connections[a].includes(b))this.state.connections[a].push(b);if(!this.state.connections[b].includes(a))this.state.connections[b].push(a)}
  legalMoves(room=this.state.crew.room){return (this.state.connections[room]||[]).filter(id=>this.state.rooms.includes(id))}
  explorationCapacityPolicy(){return this.data.rules.topology?.exploration_capacity?.value||"declared"}
  canExplore(room=this.state.crew.room){if(!this.state.roomDeck.length)return false;if(this.explorationCapacityPolicy()==="unbounded")return true;return !(this.state.exploredFrom||[]).includes(room)}
  shortestPath(from,to){if(from===to)return [from];const queue=[[from]],seen=new Set([from]);while(queue.length){const path=queue.shift(),at=path[path.length-1];for(const next of this.legalMoves(at)){if(seen.has(next))continue;const candidate=[...path,next];if(next===to)return candidate;seen.add(next);queue.push(candidate)}}return null}
  moveEnemyToward(e,target=this.state.crew.room){const path=this.shortestPath(e.room,target);if(!path||path.length<2)return false;const steps=Math.min(e.move||1,path.length-1);e.room=path[steps];this.log(`${e.name} moves to ${this.room(e.room)?.name||e.room}.`);return true}
  revealRoom(from=this.state.crew.room){if(!this.canExplore(from))return null;const id=this.state.roomDeck.shift();this.state.rooms.push(id);this.connect(from,id);const r=this.room(id);this.log(`Revealed ${r.name}.`);this.resolveRoomSetup(r);this.resolveEncounter();return r}
  move(target=null){if(!target||!this.legalMoves().includes(target)||!this.spend())return false;this.state.crew.room=target;this.log(`Moved to ${this.room().name}.`);return true}
  explore(){const from=this.state.crew.room;if(!this.canExplore(from)||!this.spend())return false;const r=this.revealRoom(from);if(r){this.state.exploredFrom??=[];if(!this.state.exploredFrom.includes(from))this.state.exploredFrom.push(from);this.state.crew.room=r.id;this.log(`Entered ${r.name}.`)}return !!r}
  search(){const r=this.room();if(!r.searchable||this.state.searched.includes(r.id)||!this.spend())return false;this.state.searched.push(r.id);let item;
    if(r.objective_item==="Ancient Power Cell") item=this.data.salvage.find(s=>s.id==="power-cell"); else item=this.data.salvage.find(s=>s.id===this.state.salvage.shift());
    if(item){this.state.inventory.push(item.id);this.applySalvage(item);this.log(`Found ${item.name}.`)}return true}
  applySalvage(i){if(i.id==="ammo-cache")this.state.ammo=Math.min(this.data.rules.ammo.max,this.state.ammo+3);if(i.id==="scrap")this.state.scrap+=2;if(i.id==="med-gel")this.state.crew.currentHealth=Math.min(this.state.crew.health,this.state.crew.currentHealth+3);if(i.id==="translation-fragment")this.state.knowledge++}
  interact(){if(!this.spend())return false;const r=this.room();if(r.id==="relay"&&this.state.inventory.includes("power-cell")){this.state.relayActive=true;this.addThreat(2);this.log("The Ancient Relay awakens. Extraction is active.");return true}this.log(`Interacted with ${r.name}.`);return true}
  reload(){const amount=this.data.rules.reload?.ammo??this.card("reload")?.restore_ammo;if(!Number.isFinite(amount)||!this.spend())return false;this.state.ammo=Math.min(this.data.rules.ammo.max,this.state.ammo+amount);this.log("Reloaded shared ammunition.");return true}
  attack(enemyIndex=0,cardId="sidearm"){const c=this.card(cardId);const e=this.state.enemies[enemyIndex];if(!c||!e||!this.spend()||this.state.ammo<(c.ammo||0))return false;this.state.ammo-=c.ammo||0;this.addThreat(c.noise||0);const dmg=Math.max(0,(c.attack||0)+this.state.crew.accuracy-e.defense);e.health-=dmg;this.log(`${c.name} hits ${e.name} for ${dmg}.`);if(e.health<=0)this.killEnemy(enemyIndex);return true}
  killEnemy(i){const e=this.state.enemies[i];if(e.corpse)this.state.corpses[e.room]=(this.state.corpses[e.room]||0)+1;this.log(`${e.name} is killed${e.corpse?"; a corpse remains.":"."}`);this.state.enemies.splice(i,1)}
  spawn(id,room=this.state.crew.room){const p=this.data.enemies.find(e=>e.id===id);if(p){this.state.enemies.push({...p,health:p.health,room,fed:0,suppressed:false});this.log(`${p.name} appears in ${this.room(room)?.name||room}.`)}}
  thresholdAt(t){return t.at??(t.condition?.op==="gte"&&typeof t.condition?.right==="number"?t.condition.right:null)}
  resolveEffect(effect){if(!effect)return false;if(effect.op==="emit"&&effect.event==="spawn-enemy"){const ref=effect.payload?.entity_ref||"";const id=ref.includes(":")?ref.slice(ref.lastIndexOf(":")+1):ref;if(id)this.spawn(id);return !!id}if(effect.op==="add"&&effect.target_ref==="threat"){this.addThreat(Number(effect.value)||0);return true}if(effect.op==="add"&&effect.target_ref==="spider-corpse"){const room=this.state.crew.room;this.state.corpses[room]=(this.state.corpses[room]||0)+(Number(effect.value)||0);return true}if(effect.op==="subtract"&&effect.target_ref==="health"){this.damageCrew(Number(effect.value)||0);return true}if(effect.prose){this.log(effect.prose,"DEBUG");return true}return false}
  addThreat(n){const before=this.state.threat;this.state.threat=Math.min(this.data.rules.threat.max,this.state.threat+n);for(const t of this.data.rules.threat.thresholds||[]){const at=this.thresholdAt(t);if(Number.isFinite(at)&&before<at&&this.state.threat>=at){for(const effect of t.effects||[])this.resolveEffect(effect);if(t.spawn_enemy)this.spawn(t.spawn_enemy);this.log(`Threat ${at}: ${t.effect||t.effects?.find(e=>e.prose)?.prose||"threshold crossed"}`)}}}
  resolveEncounter(){if(!this.state.encounters.length)this.state.encounters=this.shuffle(this.data.semantic_decks?.encounters||this.data.encounters.map(e=>e.id));const e=this.data.encounters.find(x=>x.id===this.state.encounters.shift());if(!e)return;this.log(`Encounter — ${e.name}: ${e.effect}`);for(const effect of e.effects||[])this.resolveEffect(effect)}
  resolveRoomSetup(r){if(r.id==="bone-pit")this.state.corpses[r.id]=(this.state.corpses[r.id]||0)+1;if(r.id==="nest"){this.spawn("small-spider",r.id);this.spawn("small-spider",r.id)}}
  damageCrew(n){this.state.crew.currentHealth=Math.max(0,this.state.crew.currentHealth-n);if(!this.state.crew.currentHealth){this.state.crew.incapacitated=true;this.state.status="lost";this.log("The crew is incapacitated. Expedition lost.")}}
  enemyPhase(){for(let i=0;i<this.state.enemies.length;i++){const e=this.state.enemies[i];if(e.suppressed){e.suppressed=false;continue}if((this.state.corpses[e.room]||0)>0&&e.id.includes("spider")){this.feed(e);continue}if(e.room!==this.state.crew.room)this.moveEnemyToward(e);if(e.room===this.state.crew.room){this.damageCrew(Math.max(0,e.attack-(this.state.crew.defense||0)));if(this.state.status!=="playing")break}}}
  feed(e){this.state.corpses[e.room]--;e.fed++;this.log(`${e.name} feeds on a corpse.`);if(e.fed===1&&e.id==="small-spider"){e.health++;e.maxHealth=(e.maxHealth||e.health)+1}else if(e.fed===1&&e.id==="large-spider")e.regeneration=true;else if(e.fed>=2&&(e.id==="small-spider"||e.id==="large-spider")){this.state.chrysalises.push({room:e.room,hatch:e.id==="small-spider"?"large-spider":"alpha-spider",age:0});this.state.enemies.splice(this.state.enemies.indexOf(e),1)}}
  endTurn(){if(this.state.status!=="playing")return;this.enemyPhase();for(const e of this.state.enemies)if(e.regeneration)e.health=Math.min(e.maxHealth||e.health+1,e.health+1);for(const c of this.state.chrysalises)c.age++;for(const c of [...this.state.chrysalises])if(c.age>=1){this.spawn(c.hatch,c.room);this.state.chrysalises.splice(this.state.chrysalises.indexOf(c),1)}if(this.state.threat>=this.data.rules.threat.max&&!this.state.crew.extracted){this.state.status="lost";this.log("Threat overwhelms the expedition.")}this.state.round++;this.state.actions=this.data.rules.actions_per_turn.value;while(this.state.hand.length<this.data.rules.hand_size.value)this.draw();this.log(`Round ${this.state.round} begins.`)}
  extract(){if(this.state.crew.room!=="entrance"||!this.spend())return false;this.state.crew.extracted=true;this.state.status=this.state.relayActive?"won":"retreated";this.log(this.state.relayActive?"Extraction complete. Scenario won.":"The crew retreats with what they found.");return true}
  playCard(handIndex,enemyIndex=0,target=null){const id=this.state.hand[handIndex],c=this.card(id);if(!c)return false;let ok=false;if(id==="move")ok=this.move(target);else if(id==="sidearm")ok=this.attack(enemyIndex,id);else if(id==="reload")ok=this.reload();else if(id==="search")ok=this.search();else if(id==="interact")ok=this.interact();else if(id==="triage"){if(this.spend()){this.state.crew.currentHealth=Math.min(this.state.crew.health,this.state.crew.currentHealth+2);ok=true}}else if(id==="jury-rig"){if(this.spend()){this.state.scrap++;ok=true}}else if(id==="scout-ahead"){if(this.spend()){this.revealRoom();ok=true}}else if(id==="take-cover"){if(this.spend()){this.state.crew.defense+=2;ok=true}}else if(id==="security-training"){if(this.spend()){this.state.crew.accuracy+=2;ok=true}}else if(id==="suppressive-fire"){if(this.spend()&&this.state.ammo){this.state.ammo--;this.addThreat(2);if(this.state.enemies[enemyIndex])this.state.enemies[enemyIndex].suppressed=true;ok=true}}else if(this.spend())ok=true;if(ok){this.state.hand.splice(handIndex,1);this.state.discard.push(id)}return ok}
  dispatch(action){
    if(!action||typeof action.type!=="string")return false;
    const beforeLog=this.state.log.length,beforeRound=this.state.round,beforeAction=this.state.actionNumber||0;
    this.state.actionNumber=beforeAction+1;
    let ok=false;
    switch(action.type){
      case "move": ok=this.move(action.target); break;
      case "explore": ok=this.explore(); break;
      case "search": ok=this.search(); break;
      case "interact": ok=this.interact(); break;
      case "reload": ok=this.reload(); break;
      case "attack": ok=this.attack(action.enemyIndex??0,action.cardId??"sidearm"); break;
      case "play-card": ok=this.playCard(action.handIndex,action.enemyIndex??0,action.target??null); break;
      case "extract": ok=this.extract(); break;
      case "end-turn": if(this.state.status==="playing"){this.endTurn();ok=true} break;
      default: break;
    }
    if(!ok){this.state.actionNumber=beforeAction;return false}
    if(this.state.log.length===beforeLog)this.log(`Action: ${action.type}.`,"DEBUG");
    if(this.state.round!==beforeRound)this.state.actionNumber=0;
    return true;
  }
  snapshot(){return JSON.parse(JSON.stringify(this.state))}
}
