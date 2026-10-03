import {WretchedEngine} from "./engine.js";
import {createSeededRng} from "./random.js";

export const REPLAY_FORMAT="wretched-replay.v1";
export const REPLAY_STATE_SCHEMA="wretched-state.v2";
const LEGACY_STATE_SCHEMA="wretched-state.v1";
const STATE_MIGRATIONS=[
  {from:LEGACY_STATE_SCHEMA,to:REPLAY_STATE_SCHEMA,id:"runtime-state-v2",description:"relayActive → relay-active; add replay bookkeeping defaults",apply(state){if(!state)return false;let changed=false;if(Object.prototype.hasOwnProperty.call(state,"relayActive")){if(!Object.prototype.hasOwnProperty.call(state,"relay-active"))state["relay-active"]=state.relayActive;delete state.relayActive;changed=true}if(!Object.prototype.hasOwnProperty.call(state,"encounteredRooms")){state.encounteredRooms=[...(state.rooms||[])];changed=true}if(!Object.prototype.hasOwnProperty.call(state,"modifiers")){state.modifiers=[];changed=true}return changed}}
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
function diffSummary(expected,actual){
  const keys=new Set([...Object.keys(expected||{}),...Object.keys(actual||{})]),changed=[];
  for(const k of keys)if(!same(expected?.[k],actual?.[k]))changed.push(k);
  return {changedTopLevel:changed,diagnostics:replayDiagnostics(expected||{},actual||{})};
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
    const before=game.snapshot(),accepted=game.dispatch(action);if(!accepted){const err=new Error(`Step ${i}: nonsensical/rejected action ${JSON.stringify(action)}`);err.step=i;err.results=results;err.game=game;throw err}
    const state=game.snapshot(),diagnostics=replayDiagnostics(before,state);
    if(verifyState&&step.state!==undefined){const comparable=comparableState(step.state,state);if(!same(comparable.actual,comparable.expected)){const summary=diffSummary(comparable.expected,comparable.actual);const err=new Error(`Step ${i}: state mismatch after ${action.type}; changed: ${summary.changedTopLevel.join(", ")||"<unknown>"}`);err.step=i;err.expected=step.state;err.actual=state;err.diff=summary;err.results=results;err.game=game;throw err}}
    results.push({index:i,action,before,state,diagnostics});
  }
  return {game,results,state:game.snapshot(),normalization};
}
export class ReplayRecorder{
  constructor(game,{seed,crew="security",captureState=true,build=null}={}){this.game=game;this.captureState=captureState;this.replay={format:REPLAY_FORMAT,state_schema:REPLAY_STATE_SCHEMA,seed:String(seed),crew,steps:[]};if(build)this.replay.source={git_sha:String(build),short_sha:String(build).slice(0,12)}}
  dispatch(action){const before=this.game.snapshot(),accepted=this.game.dispatch(action);if(!accepted)return false;const state=this.game.snapshot(),step={action:structuredClone(action),diagnostics:replayDiagnostics(before,state)};if(this.captureState)step.state=state;this.replay.steps.push(step);return true}
  toJSON(){return structuredClone(this.replay)}
}
