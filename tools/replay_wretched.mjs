#!/usr/bin/env node
import fs from "node:fs";
import {runReplay} from "../src/wretched/replay.js";

const [dataPath,replayPath]=process.argv.slice(2);
if(!dataPath||!replayPath){console.error("usage: node tools/replay_wretched.mjs <scenario.json> <replay.json>");process.exit(2)}
const data=JSON.parse(fs.readFileSync(dataPath,"utf8"));
const replay=JSON.parse(fs.readFileSync(replayPath,"utf8"));
try{
  const out=runReplay(data,replay);
  console.log(`PASS ${out.results.length} steps; final status=${out.state.status}; round=${out.state.round}`);
}catch(e){
  console.error("FAIL "+e.message);
  if(e.step!==undefined){
    console.error(JSON.stringify({step:e.step,expected:e.expected,actual:e.actual},null,2));
  }
  process.exit(1);
}
