// Target-neutral view model for displaying a materialized room graph.
export function buildTopologyView(state){
  const roomIds=[...state.rooms];
  const known=new Set(roomIds);
  const nodes=roomIds.map(id=>({
    id,
    current:id===state.crew.room,
    corpses:state.corpses[id]||0,
    chrysalis:state.chrysalises.some(c=>c.room===id),
    enemies:state.enemies.filter(e=>e.room===id).length
  }));
  const seen=new Set(),edges=[];
  for(const from of roomIds){
    for(const to of state.connections[from]||[]){
      if(!known.has(to))continue;
      const key=[from,to].sort().join("\u0000");
      if(seen.has(key))continue;
      seen.add(key);edges.push({from,to});
    }
  }
  return {nodes,edges};
}
