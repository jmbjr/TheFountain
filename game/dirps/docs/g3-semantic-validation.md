# DIRPS Scenario 01 — G3 semantic-validation evidence

This is the durable source-stage semantic-contract audit for DIRPS Scenario 01.

- Candidate: `game/dirps/dodge/dirps-scenario-01.dodge.v0.2.1.json`
- DODGE version: `0.2.1`
- DODGE revision pinned by TheFountain CI: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- DODGE lifecycle authority: `IMPLEMENTATION_GUIDE.md` Step 7
- Normative validation ownership: `DODGE_SPEC.md` §15.1–§15.2
- DIRPS profile: `dirps@0.1.0`
- Stage: `source` only
- Validator: `tools/dirps_semantic_validation.py`
- Negative evidence: `tests/test_dirps_validation.py`
- G4+ status: intentionally not claimed

G2 already proved the generic DODGE §15.3 core contract. G3 does not re-implement those checks. It validates only DIRPS-specific implications, unavoidable duplicated facts, and source-authority relationships that generic DODGE cannot infer.

## Semantic-contract audit

| DIRPS claim / relationship | Classification | Authoritative source | Why this is not DODGE-core responsibility | G3 enforcement / evidence |
|---|---|---|---|---|
| The registered canonical scenario source, DODGE document, proto sidecar, and external rules authority are the sources DIRPS says they are. | DIRPS-specific authority/provenance contract | `game/dirps/game.json` registration + `scenario.json.authority` + DODGE `sources` | Core can resolve individual refs/URIs, but cannot know that DIRPS's independently authored authority pointers and bounded rules-authority claim must agree with the registered source model. | Validator checks registered paths against canonical authority pointers and DODGE source URIs, and requires the canonical rules authority to remain the bounded GURPS Lite June 2003 authority. Negative fixtures corrupt `authority.proto_sidecar` and `authority.rules`. |
| GURPS rules are external authoritative mechanics; Scenario 01 source is provisional scenario authority; the proto sidecar is provisional; the PC build is a prototype assumption rather than external rules authority. | DIRPS-specific authority/provenance contract | DODGE `sources` + `scenario.json.player_character.provenance` | Core validates legal source kinds/refs, not whether DIRPS assigned the correct domain ownership/provenance role to independently authored facts. | Validator enforces source kind/authority roles and `player_character.provenance == prototype_assumption`. Negative fixtures move Attack to `scenario-01-source` and alter PC provenance. |
| The proto sidecar remains the declared bridge for unsupported DIRPS semantics. | DIRPS-specific extension/provenance contract | DODGE `sidecars`, `org.dirps.proto`, registry sidecar | Core intentionally treats extensions as opaque and cannot infer the DIRPS bridge. | Validator requires `dirps-proto` in sidecars and `org.dirps.proto.sidecar_ref`. Negative fixture points the extension at another source. |
| `scenario.json.player_character` owns the prototype PC build. Its bounded canonical primary-attribute set is exactly ST/DX/IQ/HT; HP/Fatigue and status fields are additional normalized actor state, not primary build facts. DODGE duplicates the identity/primary attributes needed by the normalized scene and duplicates skills/equipment only in the DIRPS extension. | DIRPS-specific duplicated-fact contract | `scenario.json.player_character` | DODGE core cannot know that these independently authored scenario and DODGE facts are intended to describe the same DIRPS character or which actor fields are canonical primary-build facts versus additional state. | Validator requires the canonical attribute keys to be exactly `st`, `dx`, `iq`, `ht`; rejects removals/additions; matches their values to DODGE actor state/value definitions; and requires exact skills/equipment extension content. Negative fixtures change DX, delete DX, add `hit-points` to the primary set, and drift Tracking/equipment. |
| Every DIRPS actor in this bounded tutorial has explicit initial bindings for every declared actor-scoped DODGE value. | DIRPS-specific actor initialization contract | DODGE actor-scoped value declarations + Scenario 01 bounded initialization policy | Generic DODGE may permit game-specific binding/default policies; DIRPS requires explicit tutorial state so later execution cannot silently invent actor values. | Validator derives the required set from `rules.values[*].owner_scope == actor` and checks each actor instance. Negative fixture removes `unconscious` from the opponent. |
| `actor-conscious` means the current actor is not unconscious, and the three DIRPS tutorial actions require it. | DIRPS rule-meaning contract | DIRPS normalized DODGE rules, attributed to GURPS source | Core can prove reference kind/resolution, but not that this named DIRPS condition has the intended game meaning or is required by these actions. | Validator checks predicate meaning and action condition usage. Negative fixture changes the predicate to read `stunned`. |
| DIRPS action IDs have the current bounded procedure meanings: Attempt skill → Success roll; Attack → Attack resolution; Recover → Recovery check. | DIRPS rule-meaning contract | DIRPS normalized DODGE action/procedure definitions | Core verifies that a procedure ref resolves to a procedure, not that it is the correct DIRPS procedure. | Validator enforces the action→procedure mapping and GURPS authority. Negative fixture binds Attack to the valid-but-wrong `success-roll` procedure. |
| Attack resolution composes the common success-roll procedure. | DIRPS rule-composition contract | DIRPS normalized DODGE procedures | Core checks procedure-reference kind/cycles; it cannot infer this DIRPS domain implication. | Validator requires a `success-roll` procedure step inside `attack-resolution`. |
| Scenario action availability and the tutorial-turn player choice remain synchronized. | DIRPS scenario-completeness contract | DODGE Scenario 01 `action_refs` + provisional `tutorial-turn` procedure | Core checks individual refs and choice shape, not that DIRPS intends the scenario action set and tutorial menu to be the same semantic set. | Validator requires every scenario action exactly once in tutorial choices. Negative fixture removes one choice while leaving the scenario claim intact. |
| The canonical combat encounter `bandit-scout` has a concrete actor/NPC occurrence in the DODGE scene. | DIRPS encounter-completeness contract | `scenario.json.encounters` owns encounter composition | Core cannot know that a DIRPS encounter ID is intended to correspond to an actor instance. | Validator requires each canonical combat encounter ID to resolve to an actor + non-player-character scene instance. Negative fixture removes the opponent instance. |
| Scenario target duration is one fact, not two drifting authored values. | DIRPS duplicated-fact contract | `scenario.json.tutorial.target_minutes` | DODGE core validates the duration shape but cannot know it duplicates the canonical Scenario 01 planning fact. | Validator requires equality with DODGE `target_duration_minutes`. Negative fixture changes the canonical maximum. |

## Claims deliberately not promoted into G3 contracts

These claims remain preserved but are not treated as executable or fully normalized merely because a semantic validator now exists:

| Claim | G3 classification | Reason for deferral |
|---|---|---|
| Encounter ordering is canonical scenario composition. | Canonical-source-only at G3; not yet normalized | The order of `scenario.json.encounters` is authoritative scenario composition, but the G3 DODGE document has no neutral encounter-sequence binding. G3 must not invent one. G4 must preserve or explicitly expose that order in the resolved model rather than reorder/infer it. |
| Investigation encounter executes an ordinary success roll. | Prose/provisional; future-gate concern | Scenario source expresses intent, but there is no explicit normalized encounter→action binding yet. Do not infer one from prose or IDs. |
| Social/reaction-oriented encounter executes social resolution. | Prose/provisional; future-gate concern | The current candidate does not normalize a social/reaction semantic binding. |
| Environmental challenge has a concrete consequence. | Prose/provisional; future-gate concern | No normalized encounter/consequence binding exists yet. |
| Combat fully executes attack → defense → damage/injury. | Prose/provisional; future-gate concern | `attack-resolution` preserves this as prose after the common success-roll step. Reaction timing and injury remain suspected proto gaps. |
| Recovery executes HT/consciousness mechanics. | Prose/provisional; future-gate concern | `recovery-check` is currently prose-only. |
| Scenario completion/win evaluation is executable. | Prose/provisional; future-gate concern | G2 intentionally removed the prose-only executable end condition; the objective remains descriptive. |
| Skills have governing attributes/default semantics. | Preserved proto concern | Skills are preserved in canonical data + DIRPS extension; no first-class normalized skill model exists. |
| Equipment has executable RPG item/equip semantics. | Preserved proto concern | The canonical list is preserved and consistency-checked, but no DIRPS equipment execution model is claimed. |
| HP/Fatigue are derived from attributes according to external rules. | Unresolved; not silently decided | Derived-value/formula semantics remain suspected proto gaps. G3 validates presence/state ownership, not an invented formula. |
| Dice terms, margin, resolution trace, replay, reaction windows, damage/injury execution. | Future G4/G5 concern; proto remains suspected | These require resolver/runtime evidence before they can move from `suspected` to `exercised`. |

## Negative fixtures

`tests/test_dirps_validation.py` proves the DIRPS profile rejects meaningful contradictions rather than merely snapshotting today's source:

- canonical rules-authority drift;
- canonical PC provenance drift;
- canonical PC attribute value drift;
- a missing canonical primary attribute;
- an unexpected field added to the canonical ST/DX/IQ/HT primary set;
- canonical PC skill drift;
- canonical PC equipment drift;
- a missing explicit actor-state binding;
- semantic drift in the `actor-conscious` predicate;
- an action bound to a valid but semantically wrong DIRPS procedure;
- tutorial choice/action-set drift;
- a canonical combat encounter with no concrete opponent;
- target-duration drift between canonical source and DODGE;
- GURPS rule authority drift to the scenario source;
- proto-sidecar bridge drift;
- registered authority-path drift.

## Gate boundary

A G3 PASS means the current bounded DIRPS source is internally complete and consistent for the semantic contracts above.

It does **not** mean:

- a neutral resolved model exists;
- resolved-game validation exists;
- prose procedures are executable;
- dice or reaction mechanics execute;
- replay exists;
- any target exists;
- any proto concept has moved beyond `suspected`.

Those are later gates. G4 must start from this validated source and introduce one neutral resolver without changing the meaning established here.
