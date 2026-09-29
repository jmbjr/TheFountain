import {WretchedEngine} from "./engine.js";
import {createSeededRng} from "./random.js";

export const REPLAY_FORMAT="wretched-replay.v1";

function same(a,b){return JSON.stringify(a)===JSON.stringify(b)}

export function runReplay(data,replay,{verifyState=true}={}){
  if(replay?.format!==REPLAY_FORMAT)throw new Error(`Unsupported replay format: ${replay?.format??"<missing>"}`);
  if(replay.seed===undefined||replay.seed===null)throw new Error("Replay seed is required");
  if(!Array.isArray(replay.steps))throw new Error("Replay steps must be an array");
  const game=new WretchedEngine(data,{rng:createSeededRng(replay.seed)});
  game.reset(replay.crew||"security");
  const results=[];
  for(let i=0;i<replay.steps.length;i++){
    const step=replay.steps[i], action=step?.action;
    if(!action||typeof action.type!=="string")throw new Error(`Step ${i}: missing action.type`);
    const before=game.snapshot();
    const accepted=game.dispatch(action);
    if(!accepted)throw new Error(`Step ${i}: nonsensical/rejected action ${JSON.stringify(action)}`);
    const state=game.snapshot();
    if(verifyState&&step.state!==undefined&&!same(state,step.state)){
      const err=new Error(`Step ${i}: state mismatch after ${action.type}`);
      err.step=i;err.expected=step.state;err.actual=state;throw err;
    }
    results.push({index:i,action,before,state});
  }
  return {game,results,state:game.snapshot()};
}

export class ReplayRecorder{
  constructor(game,{seed,crew="security",captureState=true}={}){
    this.game=game;this.captureState=captureState;
    this.replay={format:REPLAY_FORMAT,seed:String(seed),crew,steps:[]};
  }
  dispatch(action){
    const accepted=this.game.dispatch(action);
    if(!accepted)return false;
    const step={action:structuredClone(action)};
    if(this.captureState)step.state=this.game.snapshot();
    this.replay.steps.push(step);return true;
  }
  toJSON(){return structuredClone(this.replay)}
}
