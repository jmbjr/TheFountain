# DIRPS Scenario 01 — G4 resolved-model evidence

This is the durable G4 resolver/resolved-game contract for DIRPS Scenario 01.

- Baseline: accepted/merged G3 PR #172
- G3 final head: `1a18528cd9ad30c17dee19cad76f58f1558dd30d`
- G3 merge SHA: `74ff374abea23bf0aea5639736137c967ae8f40e`
- G4 branch base: `7b4d241a904ba689473cdef0d597b8491fc04ca3`
- DODGE version: `0.2.1`
- DODGE revision pinned by TheFountain CI: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- Resolver: `tools/resolve_dirps_dodge.py`
- Resolved identity: `dirps-resolved-game.v1`
- Semantic profile: `dirps@0.1.0`
- Profile stages: `source`, `resolved-game`
- G5+ status: intentionally not claimed

DODGE 0.2.1 does not define one universal resolved-game JSON schema. Its G4 contract is architectural: validate the source, resolve once into a target-neutral model, and run every declared `resolved-game` semantic profile against the exact model supplied downstream. TheFountain's generic runner discovers the repository-local resolver from `game.json`.

## Resolved-model shape

`dirps-resolved-game.v1` contains only target-neutral source/resolution data:

| Field | Ownership / derivation |
|---|---|
| `format`, DODGE/document/game/scenario IDs | Resolver identity derived from the selected DODGE candidate |
| `canonical_source` | Scenario source identity, authority, and implementation boundary copied from `scenario.json` |
| `sources` | Exact DODGE source declarations |
| `game_profile`, `archetypes`, `objects`, `sidecars`, `extensions` | Exact neutral DODGE tables/registrations retained so resolved references and bindings stay unambiguous |
| `scenario` | DODGE scenario bindings plus its `source_ref`, `authority`, `assumptions`, explicit `scene_ref`, and canonical premise/design goal/target duration/ordered encounters |
| `scene.instances` | Selected DODGE scene instances resolved with object/archetype metadata, state, and extensions |
| PC `character` | Canonical prototype provenance, exact ST/DX/IQ/HT primary build, skills, and equipment |
| `rules` | Exact normalized DODGE rules used by later execution |
| `proto_sidecar` | Exact current DIRPS proto sidecar preserved as unresolved source material |
| `unresolved` | Derived index of proto ID/status/candidate state; it is convenience data, not a second authority |

The resolver does not emit runtime state transitions, random results, replay data, target manifests, target presentation, or execution results.

## G4 preservation contracts

Resolved-stage validation proves that resolution did not drop, weaken, duplicate authoritatively, or invent the bounded meaning established at G3.

| Contract | Authoritative input | Resolved evidence |
|---|---|---|
| Scenario identity / traceability | DODGE `scenario-01` + canonical dataset | Resolved IDs, `canonical_source.dataset_id`, and exact DODGE scenario `source_ref`, `authority`, `assumptions`, and `scene_ref` |
| Source/provenance | DODGE `sources` + canonical `authority` / implementation boundary | Exact equality in resolved `sources` and `canonical_source` |
| Canonical PC identity/build | `scenario.json.player_character` | PC resolved instance carries canonical provenance, exact ST/DX/IQ/HT primary attributes, skills, equipment; actor state must agree with the primary values |
| Additional actor state | DODGE scene instance state | Preserved separately in each resolved scene instance; HP/Fatigue/status are not reclassified as canonical primary attributes |
| Concrete actors/NPCs | DODGE scene/object/archetype data | Every selected scene instance is resolved with object kind/name/tags/faces/component/state/extensions in source order |
| Available actions / action→procedure relationships | DODGE scenario + `rules.actions` / procedures | Scenario action refs and exact normalized `rules` survive unchanged |
| Target duration | Canonical `tutorial.target_minutes` (G3-validated against DODGE) | Resolved `scenario.target_duration_minutes` derives from canonical source |
| Encounter ordering | Ordered `scenario.json.encounters` | Resolved `scenario.encounters` copies the exact canonical list order |
| Proto/unresolved semantics | Registered DIRPS sidecar | Exact sidecar survives; derived unresolved index must match it exactly |

## Perturbation and negative evidence

`tests/test_dirps_resolution.py` is intentionally derivation-oriented rather than a single snapshot.

It proves:

1. the current source resolves and passes the resolved-stage profile;
2. changing canonical DX, with the corresponding G3-valid DODGE actor state change, changes both the resolved canonical PC build and actor state;
3. removing a required canonical primary attribute fails before a stale value can survive into resolution;
4. changing canonical encounter order changes resolved encounter order exactly;
5. changing a schema-valid DODGE scenario assumption changes the resolved scenario assumption exactly; dropping it from the resolved model fails validation;
6. source declarations, canonical authority, implementation boundary, scenario provenance/binding, and PC provenance survive resolution;
7. deleting a proto semantic from the resolved model fails resolved-stage validation;
8. the unresolved index is derived exactly from the sidecar and cannot silently promote a status;
9. deleting a required DIRPS action causes visible pre-resolution failure;
10. dropping a DODGE object definition referenced by the resolved scene fails resolved-stage validation;
11. dropping a normalized rule from an otherwise produced resolved model fails resolved-stage validation.

These tests complement the retained G3 source semantic tests. They do not claim runtime execution.

## Proto status

No proto concept is promoted at G4.

Every current sidecar entry remains `suspected`. The resolver preserving a suspected concept as unresolved source material is not enough to make it `exercised`: no runtime behavior consumes the proto shape yet.

The progression remains:

```text
suspected → exercised → candidate
```

G5 execution evidence is required before considering promotion.

## G5 boundary

G4 does **not** implement:

- 3d6/RNG execution;
- success/failure or margin calculation;
- active-defense timing;
- damage/injury execution;
- recovery execution;
- scenario-completion execution;
- replay/resolution traces;
- divergence detection;
- Web/CLI/PnP/TTS target behavior.

The next gate may consume `dirps-resolved-game.v1`, but it must not reconstruct or override the source/resolution semantics established here.
