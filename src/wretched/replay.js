import {WretchedEngine} from "./engine.js";
import {createSeededRng} from "./random.js";

export const REPLAY_FORMAT="wretched-replay.v1";
export const REPLAY_STATE_SCHEMA="wretched-state.v2";
const LEGACY_STATE_SCHEMA="wretched-state.v1";
const STATE_MIGRATIONS=[
  {from:LEGACY_STATE_SCHEMA,to:REPLAY_STATE_SCHEMA,id:"runtime-state-v2",description:"relayActive → relay-active; add replay bookkeeping defaults",apply(state){if(!state)return false;let changed=false;if(Object.prototype.hasOwnProperty.call(state,"relayActive")){if(!Object.prototype.hasOwnProperty.call(state,"relay-active"))state["relay-active"]=state.relayActive;delete state.relayActive;changed=true}if(!Object.prototype.hasOwnProperty.call(state,"encounteredRooms")){state.encounteredRooms=[...(state.rooms||[])];changed=true}if(!Object.prototype.hasOwnProperty.call(state,"modifiers")){state.modifiers=[];changed=true}if(!Object.prototype.hasOwnProperty.call(state,"exploredFrom")){const origins=[];for(const [room,neighbors] of Object.entries(state.connections||{}))if((neighbors||[]).length&&room!==(state.crew?.room))origins.push(room);if(origins.length){state.exploredFrom=origins;changed=true}}return changed}}
];
export function normalizeReplay(replay){
  const normalized=structuredClone(replay),migrations=[];
  let schema=normalized?.state_schema||LEGACY_STATE_SCHEMA;
  const seen=new Set();
  while(schema!==REPLAY_STATE_SCHEMA){
    if(seen.has(schema))throw new Error(`Replay state-schema migration cycle at ${schema}`);
    seen.add(schema);
    const migration=STATE_MIGRATIONS.find(x=>x.from===schema);
    if(!migration)throw new Error(`Unsupported replay state schema: ${schema}`);
    let changedStates=0;
    for(const step of normalized.steps||[])if(step?.state&&migration.apply(step.state))changedStates++;
    migrations.push({id:migration.id,from:migration.from,to:migration.to,description:migration.description,changed_states:changedStates});
    schema=migration.to;
  }
  normalized.state_schema=REPLAY_STATE_SCHEMA;
  return {replay:normalized,changed:migrations.length>0,migrations,original_state_schema:replay?.state_schema||LEGACY_STATE_SCHEMA,state_schema:REPLAY_STATE_SCHEMA};
}
const COMPATIBILITY_MIGRATIONS=[
  {id:"explore-encounter-location-v1",description:"Historical Explore encounter location → entered room",applies(replay){return replay?.state_schema===REPLAY_STATE_SCHEMA&&Array.isArray(replay.steps)},apply(replay){let changed=0;for(const step of replay.steps){if(step?.action?.type!=="explore"||!step.state)continue;const s=step.state,entered=s.crew?.room;if(!entered)continue;const oldRooms=new Set((s.connections?.[entered]||[]).filter(Boolean));for(const enemy of s.enemies||[]){if(!oldRooms.has(enemy.room)||enemy.room===entered)continue;const oldRoom=enemy.room;enemy.room=entered;for(const entry of s.log||[]){if(typeof entry==="string"){const oldName=oldRoom==="entrance"?"Cave Mouth":oldRoom,newName=entered==="bone-pit"?"Bone Pit":entered;if(entry.includes(`appears in ${oldName}.`))s.log[s.log.indexOf(entry)]=entry.replace(`appears in ${oldName}.`,`appears in ${newName}.`)}else if(entry?.message){const oldName=oldRoom==="entrance"?"Cave Mouth":oldRoom,newName=entered==="bone-pit"?"Bone Pit":entered;if(entry.message.includes(`appears in ${oldName}.`))entry.message=entry.message.replace(`appears in ${oldName}.`,`appears in ${newName}.`)}}changed++}}return changed}}
];
export function applyReplayCompatibility(replay,{force=false}={}){
  const compatible=structuredClone(replay),compatibility=[];
  if(!force)return {replay:compatible,changed:false,compatibility};
  for(const migration of COMPATIBILITY_MIGRATIONS){if(!migration.applies(compatible))continue;const changedSteps=migration.apply(compatible);if(changedSteps)compatibility.push({id:migration.id,description:migration.description,changed_steps:changedSteps,kind:"semantic-compatibility-override"})}
  return {replay:compatible,changed:compatibility.length>0,compatibility};
}
function same(a,b){if(Object.is(a,b))return true;if(Array.isArray(a)||Array.isArray(b))return Array.isArray(a)&&Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>same(v,b[i]));if(a&&b&&typeof a==="object"&&typeof b==="object"){const ak=Object.keys(a),bk=Object.keys(b);return ak.length===bk.length&&ak.every(k=>Object.prototype.hasOwnProperty.call(b,k)&&same(a[k],b[k]))}return false}
function comparableState(expected,actual){const e=structuredClone(expected),a=structuredClone(actual);if(Array.isArray(e?.log)&&e.log.every(x=>typeof x==="string")&&Array.isArray(a?.log))a.log=a.log.filter(x=>typeof x==="string"||x.level!=="DEBUG").map(x=>typeof x==="string"?x:x.message);if(e?.actionNumber===undefined)delete a.actionNumber;return {expected:e,actual:a}}
function edges(state){
  const out=new Set();
  for(const [a,bs] of Object.entries(state.connections||{}))for(const b of bs||[])out.add([a,b].sort().join("\u0000"));
  return out;
}
function edgeObj(key){const [a,b]=key.split("\u0000");return {from:a,to:b}}
export function replayDiagnostics(before,after){
  const b=edges(before),a=edges(after);
  const added=[...a].filter(x=>!b.has(x)).map(edgeObj),removed=[...b].filter(x=>!a.has(x)).map(edgeObj);
  const revealed=(after.rooms||[]).filter(id=>!(before.rooms||[]).includes(id));
  const movement=before.crew?.room!==after.crew?.room?{from:before.crew?.room,to:after.crew?.room}:null;
  const revealOrigins=revealed.map(room=>({room,connectedTo:(after.connections?.[room]||[]).filter(id=>(before.rooms||[]).includes(id))}));
  return {movement,revealed:revealOrigins,topology:{added,removed}};
}
function mismatchPaths(expected,actual,path="$",out=[]){if(same(expected,actual))return out;if(Array.isArray(expected)||Array.isArray(actual)){if(!Array.isArray(expected)||!Array.isArray(actual)){out.push({path,expected,actual});return out}const n=Math.max(expected.length,actual.length);for(let i=0;i<n;i++)mismatchPaths(expected[i],actual[i],`${path}[${i}]`,out);return out}if(expected&&actual&&typeof expected==="object"&&typeof actual==="object"){const keys=new Set([...Object.keys(expected),...Object.keys(actual)]);for(const k of keys)mismatchPaths(expected[k],actual[k],`${path}.${k}`,out);return out}out.push({path,expected,actual});return out}
function diffSummary(expected,actual){
  const keys=new Set([...Object.keys(expected||{}),...Object.keys(actual||{})]),changed=[];
  for(const k of keys)if(!same(expected?.[k],actual?.[k]))changed.push(k);
  return {changedTopLevel:changed,mismatches:mismatchPaths(expected,actual).slice(0,50),diagnostics:replayDiagnostics(expected||{},actual||{})};
}
export function runReplay(data,replay,{verifyState=true}={}){
  const normalization=normalizeReplay(replay);replay=normalization.replay;
  if(replay?.format!==REPLAY_FORMAT)throw new Error(`Unsupported replay format: ${replay?.format??"<missing>"}`);
  if(replay.seed===undefined||replay.seed===null)throw new Error("Replay seed is required");
  if(!Array.isArray(replay.steps))throw new Error("Replay steps must be an array");
  const game=new WretchedEngine(data,{rng:createSeededRng(replay.seed)});game.reset(replay.crew||"security");
  const results=[];
  for(let i=0;i<replay.steps.length;i++){
    const step=replay.steps[i],action=step?.action;if(!action||typeof action.type!=="string"){const err=new Error(`Step ${i}: missing action.type`);err.step=i;err.results=results;err.game=game;throw err}
    const before=game.snapshot(),accepted=game.dispatch(action);if(!accepted){const err=new Error(`Step ${i}: nonsensical/rejected action ${JSON.stringify(action)}`);err.step=i;err.results=results;err.game=game;err.normalization=normalization;err.compatibility=compatibility;err.replay=replay;throw err}
    const state=game.snapshot(),diagnostics=replayDiagnostics(before,state);
    if(verifyState&&step.state!==undefined){const comparable=comparableState(step.state,state);if(!same(comparable.actual,comparable.expected)){const summary=diffSummary(comparable.expected,comparable.actual);const paths=summary.mismatches.map(x=>x.path).join(", ");const err=new Error(`Step ${i}: state mismatch after ${action.type}; changed: ${summary.changedTopLevel.join(", ")||"<unknown>"}; paths: ${paths||"<unknown>"}`);err.step=i;err.expected=step.state;err.actual=state;err.diff=summary;err.results=results;err.game=game;err.normalization=normalization;err.compatibility=compatibility;err.replay=replay;throw err}}
    results.push({index:i,action,before,state,diagnostics});
  }
  return {game,results,state:game.snapshot(),normalization,compatibility};
}
export class ReplayRecorder{
  constructor(game,{seed,crew="security",captureState=true,build=null}={}){this.game=game;this.captureState=captureState;this.replay={format:REPLAY_FORMAT,state_schema:REPLAY_STATE_SCHEMA,seed:String(seed),crew,steps:[]};if(build)this.replay.source={git_sha:String(build),short_sha:String(build).slice(0,12)}}
  dispatch(action){const before=this.game.snapshot(),accepted=this.game.dispatch(action);if(!accepted)return false;const state=this.game.snapshot(),step={action:structuredClone(action),diagnostics:replayDiagnostics(before,state)};if(this.captureState)step.state=state;this.replay.steps.push(step);return true}
  toJSON(){return structuredClone(this.replay)}
}
