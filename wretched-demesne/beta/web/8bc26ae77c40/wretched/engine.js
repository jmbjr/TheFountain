// Shared, renderer-agnostic runtime for Wretched Demesne Scenario 01.
// Gameplay values live in the canonical dataset, not here.
export class WretchedEngine {
  constructor(data, {rng=Math.random}={}) { this.data=data; this.rng=rng; this.reset(); }
  reset(crewId="security") {
    const crew=this.data.crew.find(c=>c.id===crewId) || this.data.crew[0],startRoom=this.data.scenario?.runtime?.start_room_ref||"entrance";
    this.state={round:1,phase:"crew",crew:{...crew,currentHealth:crew.health,room:startRoom,extracted:false,incapacitated:false},
      actions:this.data.rules.actions_per_turn.value,ammo:this.data.rules.ammo.starting,scrap:0,knowledge:0,threat:this.data.rules.threat.start,
      relayActive:false,inventory:[],searched:[],rooms:[startRoom],roomDeck:[],
      encounters:this.shuffle(this.data.semantic_decks?.encounters||this.data.encounters.map(e=>e.id)),salvage:this.shuffle(this.data.semantic_decks?.salvage||this.data.salvage.map(s=>s.id)),
      connections:{[startRoom]:[]},enemies:[],corpses:{},chrysalises:[],log:[],actionNumber:0,status:"playing"};
    this.log("Expedition begins at the Cave Mouth.");
    this.state.roomDeck=this.buildScenarioDeck("rooms",id=>id!==startRoom); this.buildDeck(crewId); return this.state;
  }
  shuffle(a){a=[...a];for(let i=a.length-1;i>0;i--){const j=Math.floor(this.rng()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
  buildScenarioDeck(collectionRef,include=()=>true){const source=this.data.semantic_decks?.[collectionRef]||[];const placements=(this.data.scenario?.setup_constraints?.deck_placements||[]).filter(p=>p.collection_ref===collectionRef);const placed=new Set(placements.map(p=>p.entity_ref));const deck=this.shuffle(source.filter(id=>include(id)&&!placed.has(id)));for(const p of placements){if(!include(p.entity_ref)||!source.includes(p.entity_ref))continue;const within=Math.max(1,Number(p.within_last)||1),start=Math.max(0,deck.length-within+1),index=start+Math.floor(this.rng()*(deck.length-start+1));deck.splice(index,0,p.entity_ref)}return deck;}
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
    if(r.objective_item_ref) item=this.data.salvage.find(s=>s.id===r.objective_item_ref); else item=this.data.salvage.find(s=>s.id===this.state.salvage.shift());
    if(item){this.state.inventory.push(item.id);this.applySalvage(item);this.log(`Found ${item.name}.`)}return true}
  applySalvage(i){for(const effect of i.effects||[])this.resolveEffect(effect)}
  interact(){if(!this.spend())return false;const r=this.room(),interaction=r.interaction;if(interaction&&(!interaction.requires_inventory_ref||this.state.inventory.includes(interaction.requires_inventory_ref))){for(const effect of interaction.effects||[])this.resolveEffect(effect,r.id);this.log(`${r.name} interaction resolved.`);return true}this.log(`Interacted with ${r.name}.`);return true}
  reload(){const amount=this.data.rules.reload?.ammo??this.card("reload")?.restore_ammo;if(!Number.isFinite(amount)||!this.spend())return false;this.state.ammo=Math.min(this.data.rules.ammo.max,this.state.ammo+amount);this.log("Reloaded shared ammunition.");return true}
  attack(enemyIndex=0,cardId="sidearm"){const c=this.card(cardId);const e=this.state.enemies[enemyIndex];if(!c||!e||!this.spend()||this.state.ammo<(c.ammo||0))return false;this.state.ammo-=c.ammo||0;this.addThreat(c.noise||0);const dmg=Math.max(0,(c.attack||0)+this.state.crew.accuracy-e.defense);e.health-=dmg;this.log(`${c.name} hits ${e.name} for ${dmg}.`);if(e.health<=0)this.killEnemy(enemyIndex);return true}
  killEnemy(i){const e=this.state.enemies[i];if(e.corpse)this.state.corpses[e.room]=(this.state.corpses[e.room]||0)+1;this.log(`${e.name} is killed${e.corpse?"; a corpse remains.":"."}`);this.state.enemies.splice(i,1)}
  spawn(id,room=this.state.crew.room){const p=this.data.enemies.find(e=>e.id===id);if(p){this.state.enemies.push({...p,health:p.health,room,fed:0,suppressed:false});this.log(`${p.name} appears in ${this.room(room)?.name||room}.`)}}
  thresholdAt(t){return t.at??(t.condition?.op==="gte"&&typeof t.condition?.right==="number"?t.condition.right:null)}
  resolveEffect(effect,location=this.state.crew.room){if(!effect)return false;if(effect.op==="emit"&&effect.event==="spawn-enemy"){const ref=effect.payload?.entity_ref||"";const id=ref.includes(":")?ref.slice(ref.lastIndexOf(":")+1):ref;if(id)this.spawn(id,location);return !!id}if(effect.op==="set"&&effect.target_ref==="relay-active"){this.state.relayActive=!!effect.value;return true}if(effect.op==="add"&&effect.target_ref==="threat"){this.addThreat(Number(effect.value)||0);return true}if(effect.op==="add"&&effect.target_ref==="ammunition"){this.state.ammo=Math.min(this.data.rules.ammo.max,this.state.ammo+(Number(effect.value)||0));return true}if(effect.op==="add"&&effect.target_ref==="scrap"){this.state.scrap+=Number(effect.value)||0;return true}if(effect.op==="add"&&effect.target_ref==="knowledge"){this.state.knowledge+=Number(effect.value)||0;return true}if(effect.op==="add"&&effect.target_ref==="health"){this.state.crew.currentHealth=Math.min(this.state.crew.health,this.state.crew.currentHealth+(Number(effect.value)||0));return true}if(effect.op==="add"&&effect.target_ref==="spider-corpse"){const room=location;this.state.corpses[room]=(this.state.corpses[room]||0)+(Number(effect.value)||0);return true}if(effect.op==="subtract"&&effect.target_ref==="health"){this.damageCrew(Number(effect.value)||0);return true}if(effect.op==="subtract"&&effect.target_ref==="ammunition"){const n=Number(effect.value)||0;if(this.state.ammo<n)return false;this.state.ammo-=n;return true}if(effect.op==="add"&&effect.target_ref==="defense"){this.state.crew.defense+=Number(effect.value)||0;return true}if(effect.op==="add"&&effect.target_ref==="accuracy"){this.state.crew.accuracy+=Number(effect.value)||0;return true}if(effect.prose){this.log(effect.prose,"DEBUG");return true}return false}
  addThreat(n){const before=this.state.threat;this.state.threat=Math.min(this.data.rules.threat.max,this.state.threat+n);for(const t of this.data.rules.threat.thresholds||[]){const at=this.thresholdAt(t);if(Number.isFinite(at)&&before<at&&this.state.threat>=at){for(const effect of t.effects||[])this.resolveEffect(effect);this.log(`Threat ${at}: ${t.effect||t.effects?.find(e=>e.prose)?.prose||"threshold crossed"}`)}}}
  resolveEncounter(){if(!this.state.encounters.length)this.state.encounters=this.shuffle(this.data.semantic_decks?.encounters||this.data.encounters.map(e=>e.id));const e=this.data.encounters.find(x=>x.id===this.state.encounters.shift());if(!e)return;this.log(`Encounter — ${e.name}: ${e.effect}`);for(const effect of e.effects||[])this.resolveEffect(effect)}
  resolveRoomSetup(r){for(const effect of r.setup_effects||[])this.resolveEffect(effect,r.id)}
  damageCrew(n){this.state.crew.currentHealth=Math.max(0,this.state.crew.currentHealth-n);if(!this.state.crew.currentHealth){this.state.crew.incapacitated=true;this.state.status="lost";this.log("The crew is incapacitated. Expedition lost.")}}
  feedingRule(){return this.data.rules.spider_feeding?.mechanic||null}
  feedingLineage(e){return this.feedingRule()?.lineages?.[e.id]||null}
  resolveEnemyEffect(e,effect){if(!effect)return false;if(effect.op==="add"&&effect.target_ref==="enemy-health"){e.health+=(Number(effect.value)||0);return true}if(effect.op==="add"&&effect.target_ref==="enemy-max-health"){e.maxHealth=(e.maxHealth??e.health)+(Number(effect.value)||0);return true}if(effect.op==="set"&&effect.target_ref==="enemy-regeneration"){e.regeneration=!!effect.value;return true}return false}
  enemyPhase(){for(let i=0;i<this.state.enemies.length;i++){const e=this.state.enemies[i];if(e.suppressed){e.suppressed=false;continue}if((this.state.corpses[e.room]||0)>0&&this.feedingLineage(e)){this.feed(e);continue}if(e.room!==this.state.crew.room)this.moveEnemyToward(e);if(e.room===this.state.crew.room){this.damageCrew(Math.max(0,e.attack-(this.state.crew.defense||0)));if(this.state.status!=="playing")break}}}
  feed(e){const rule=this.feedingRule(),lineage=this.feedingLineage(e);if(!rule||!lineage)return false;this.state.corpses[e.room]--;e.fed++;this.log(`${e.name} feeds on a corpse.`);if(e.fed===1)for(const effect of lineage.first_feed_effects||[])this.resolveEnemyEffect(e,effect);if(e.fed>=rule.chrysalis_after_feeds&&lineage.hatch_enemy_ref){this.state.chrysalises.push({room:e.room,hatch:lineage.hatch_enemy_ref,age:0});this.state.enemies.splice(this.state.enemies.indexOf(e),1)}return true}
  endTurn(){if(this.state.status!=="playing")return;this.enemyPhase();for(const e of this.state.enemies)if(e.regeneration)e.health=Math.min(e.maxHealth||e.health+1,e.health+1);for(const c of this.state.chrysalises)c.age++;for(const c of [...this.state.chrysalises])if(c.age>=(this.feedingRule()?.hatch_after_end_phases??1)){this.spawn(c.hatch,c.room);this.state.chrysalises.splice(this.state.chrysalises.indexOf(c),1)}if(this.state.threat>=this.data.rules.threat.max&&!this.state.crew.extracted){this.state.status="lost";this.log("Threat overwhelms the expedition.")}this.state.round++;this.state.actions=this.data.rules.actions_per_turn.value;while(this.state.hand.length<this.data.rules.hand_size.value)this.draw();this.log(`Round ${this.state.round} begins.`)}
  scenarioState(ref){if(ref==="relay-active")return this.state.relayActive;return this.state[ref]}
  extract(){const rule=this.data.scenario?.runtime?.extraction,room=rule?.room_ref;if(!room||this.state.crew.room!==room||!this.spend())return false;this.state.crew.extracted=true;const success=(rule.success_requires||[]).every(r=>this.scenarioState(r.state_ref)===r.equals);this.state.status=success?(rule.success_status||"won"):(rule.fallback_status||"retreated");this.log(success?"Extraction complete. Scenario won.":"The crew retreats with what they found.");return true}
  playCard(handIndex,enemyIndex=0,target=null){const id=this.state.hand[handIndex],c=this.card(id);if(!c)return false;let ok=false;if(id==="move")ok=this.move(target);else if(id==="sidearm")ok=this.attack(enemyIndex,id);else if(id==="reload")ok=this.reload();else if(id==="search")ok=this.search();else if(id==="interact")ok=this.interact();else if(id==="scout-ahead"){if(this.spend()){this.revealRoom();ok=true}}else if(c.effects?.length){const ammoCost=c.effects.filter(e=>e.op==="subtract"&&e.target_ref==="ammunition").reduce((n,e)=>n+(Number(e.value)||0),0);if(this.state.ammo>=ammoCost&&this.spend()){ok=true;for(const effect of c.effects){if(effect.subject?.relative==="target-enemy"){const enemy=this.state.enemies[enemyIndex];if(effect.op==="set"&&effect.target_ref==="suppressed"&&enemy)enemy.suppressed=!!effect.value;else if(!enemy)ok=false}else this.resolveEffect(effect)}}}else if(this.spend())ok=true;if(ok){this.state.hand.splice(handIndex,1);this.state.discard.push(id)}return ok}
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
