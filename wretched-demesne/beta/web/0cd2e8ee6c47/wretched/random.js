// Small deterministic PRNG for reproducible Wretched runs.
// Seed strings are hashed to uint32; mulberry32 then supplies the random stream.
export function seedToUint32(seed){
  let h=2166136261>>>0;
  for(const ch of String(seed)){h^=ch.charCodeAt(0);h=Math.imul(h,16777619)}
  return h>>>0;
}
export function createSeededRng(seed){
  let a=seedToUint32(seed);
  return ()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296};
}
