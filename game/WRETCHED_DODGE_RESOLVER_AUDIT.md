# Wretched DODGE 0.2.1 source/resolver audit

This audit records the authority boundary used by the shared resolver. It is intentionally conservative: unresolved Design Lead facts remain unresolved rather than being invented by a target.

| Layer | Current role | Authority / rule |
|---|---|---|
| `game/wretched-demesne.dodge.v0.2.1.json` | Normalized DODGE structure: scene/scenario selection, rules/resources, phases/procedures, topology declaration, representations, source declarations | Active DODGE 0.2.1 working contract |
| `game/wretched-demesne.gdd.sidecar.v0.1.json` | Lossless Design Lead/GDD semantics and authoritative catalogs referenced by DODGE | Authoritative where DODGE declares the source authoritative; never silently normalized/promoted |
| `game/wretched-demesne.scenario-01.mvp.v0.1.json` | Executable Scenario 01 prototype facts used by the current Beta | Provisional where declared by DODGE; does not override authoritative GDD facts |
| export contract | Target selection of representations/features | May select/arrange representations; may not invent game semantics or canonical quantities |
| shared resolver | Follows DODGE references, preserves authority, emits one target-neutral resolved model/inventory | No target presentation policy |
| PnP renderer | Physical page/card/token presentation | Layout only |

## Findings

1. The DODGE document already declares the relevant source graph and authority labels. The resolver should start there rather than treating the Scenario JSON as the root.
2. The lossless GDD sidecar remains necessary. It is not a conformance defect and must not be discarded to simplify the resolver.
3. Scenario 01 still contains provisional executable assumptions. The resolver exposes them; it does not upgrade their authority.
4. Health representation alternatives are resolvable from DODGE + the PnP export contract. Per-binding maximum quantities currently bind to canonical crew Health.
5. Corpse/chrysalis physical supply quantities remain unresolved. The old PnP exporter explicitly invented playtest token counts. Those counts must remain visibly non-canonical until a source defines them; the resolver reports them as unresolved rather than adopting them.
6. The Medic starter-deck quantity inconsistency remains an upstream canonical-data issue and is deliberately not corrected by resolution.
7. Topology generation is declared in DODGE but still contains prose procedure steps. The resolver can carry the declaration now; executable topology convergence remains a later gate step.
8. TTS is intentionally out of scope for this phase. Do not use TTS defects to distort the resolver or PnP work until PnP conformance is accepted.

## Resolver contract v1

`tools/resolve_wretched_dodge.py` emits `wretched-resolved-game.v1` with:

- DODGE/document/scenario identity;
- declared source graph and authority summary;
- selected Scenario, Scene and topology declaration;
- normalized DODGE rules;
- resolved Scenario 01 canonical content;
- lossless GDD sidecar content;
- deterministic scene-instance and selected-representation inventory; and
- an explicit unresolved-inventory list.

This first contract is deliberately additive. It creates one neutral boundary without rewriting the working Web runtime. PnP is the first consumer. Once PnP output is accepted, additional target/runtime interpretation can migrate behind the same boundary.
