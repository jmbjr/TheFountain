// Neutral loader/validator boundary for the Wretched Demesne resolved Scenario 01 model.
const REQUIRED=["rules","crew","cards","enemies","rooms","salvage","encounters","scenario"];
export function validateWretchedMvp(data){const errors=[];for(const k of REQUIRED)if(!data?.[k])errors.push(`Missing ${k}`);if(data?.game_id!=="wretched-demesne-plateau-of-leng")errors.push("Unexpected game_id");if(data?.rules?.actions_per_turn?.value!==3)errors.push("MVP expects canonical actions_per_turn");if(data?.rules?.hand_size?.value!==5)errors.push("MVP expects canonical hand_size");const runtime=data?.scenario?.runtime,extraction=runtime?.extraction;if(!runtime?.start_room_ref)errors.push("Missing scenario.runtime.start_room_ref");if(!extraction?.room_ref)errors.push("Missing scenario.runtime.extraction.room_ref");if(!extraction?.success_status)errors.push("Missing scenario.runtime.extraction.success_status");if(!extraction?.fallback_status)errors.push("Missing scenario.runtime.extraction.fallback_status");return {ok:!errors.length,errors}}
function expandEntityCollection(resolved,instanceId,catalog){
  const collection=resolved.semantic_collections?.[instanceId];
  if(!collection)throw new Error(`Resolved DODGE collection missing: ${instanceId}`);
  const prefix=`scenario-mvp:${catalog}:`,out=[];
  for(const member of collection.members||[]){
    if(!member.entity_ref?.startsWith(prefix))throw new Error(`Unexpected ${catalog} collection member: ${member.entity_ref||member.object_ref||"<missing>"}`);
    const id=member.entity_ref.slice(prefix.length);
    for(let i=0;i<(member.quantity||1);i++)out.push(id);
  }
  return out;
}
export function runtimeFromResolved(resolved){
  if(resolved?.format!=="wretched-resolved-game.v1")throw new Error("Unexpected resolved Wretched format");
  const data=structuredClone(resolved.canonical);
  data.rules=structuredClone(data.rules||{});
  const resources=resolved.rules?.resources||{};
  if(resources.actions)data.rules.actions_per_turn={value:resources.actions.default,provenance:"dodge-resolved"};
  if(resources["hand-size"])data.rules.hand_size={value:resources["hand-size"].default,provenance:"dodge-resolved"};
  if(resources.ammunition)data.rules.ammo={value:data.rules.ammo?.value,starting:resources.ammunition.default,max:resources.ammunition.maximum,provenance:"dodge-resolved"};
  if(resources.threat){data.rules.threat={...data.rules.threat,start:resources.threat.default,max:resources.threat.maximum,provenance:"dodge-resolved"};if(resources.threat.thresholds)data.rules.threat.thresholds=structuredClone(resources.threat.thresholds);}
  const reloadEffect=resolved.rules?.actions?.reload?.effects?.find(effect=>effect.op==="add"&&effect.target_ref==="ammunition");
  if(reloadEffect)data.rules.reload={ammo:reloadEffect.value,provenance:"dodge-resolved"};
  if(resolved.rules?.topology)data.rules.topology=structuredClone(resolved.rules.topology);
  data.resolved_dodge={document_id:resolved.document_id,dodge_version:resolved.dodge_version,scenario_id:resolved.scenario_id};
  data.action_definitions=structuredClone(resolved.rules?.actions||{});\n  for(const card of data.cards||[])card.invocations=structuredClone(resolved.entity_invocations?.[`scenario-mvp:cards:${card.id}`]||[]);\n  data.starter_decks={};
  for(const crew of data.crew||[]){
    const instanceId=`${crew.id}-starter-deck-1`;
    data.starter_decks[crew.id]=expandEntityCollection(resolved,instanceId,"cards");
  }
  data.semantic_decks={
    rooms:expandEntityCollection(resolved,"scenario-room-cards-1","rooms"),
    encounters:expandEntityCollection(resolved,"scenario-encounter-cards-1","encounters"),
    salvage:expandEntityCollection(resolved,"scenario-salvage-cards-1","salvage")
  };
  const v=validateWretchedMvp(data);if(!v.ok)throw new Error(v.errors.join("; "));
  return data;
}
export function validateResolvedWretched(resolved){
  const errors=[];
  if(resolved?.format!=="wretched-resolved-game.v1")errors.push("Unexpected resolved Wretched format");
  if(resolved?.dodge_version!=="0.2.1")errors.push("Web requires DODGE 0.2.1");
  if(!resolved?.canonical)errors.push("Missing resolved canonical source");
  if(!resolved?.semantic_collections)errors.push("Missing resolved semantic collections");
  return {ok:!errors.length,errors};
}
export async function loadWretchedResolved(path="../game/wretched-resolved-game.v1.json"){
  const url=new URL(path,import.meta.url);const r=await fetch(url,{cache:"no-store"});
  if(!r.ok)throw new Error(`Unable to load resolved DODGE game: ${r.status}`);
  const resolved=await r.json(),v=validateResolvedWretched(resolved);if(!v.ok)throw new Error(v.errors.join("; "));
  return runtimeFromResolved(resolved);
}
