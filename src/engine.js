export class FountainEngine {
  constructor(def){this.def=def;this.reset();}
  reset(){this.state=structuredClone(this.def.player);this.log=[];}
  stage(){return [...this.def.mutation_stages].reverse().find(s=>this.state.mutation>=s.min)||this.def.mutation_stages[0];}
  apply(choice){
    for(const k of ["health","mutation","humanity","knowledge"]) this.state[k]=Math.max(0,(this.state[k]||0)+(choice[k]||0));
    this.state.humanity=Math.min(100,this.state.humanity); this.state.health=Math.min(this.state.max_health,this.state.health);
    if(this.state.health<=0)this.resurrect();
  }
  resurrect(){this.state.deaths++;this.state.health=this.state.max_health;this.state.mutation=Math.min(100,this.state.mutation+12);this.state.humanity=Math.max(0,this.state.humanity-7);this.log.push("You died. The Fountain rebuilt you incorrectly.");}
}