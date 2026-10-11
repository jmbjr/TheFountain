# DIRPS Scenario 01 — DODGE 0.2.1 G2 core-validation evidence

This is the auditable G2 evidence record required by TheFountain issue #170.

- Candidate: `game/dirps/dodge/dirps-scenario-01.dodge.v0.2.1.json`
- DODGE version: `0.2.1`
- DODGE revision pinned by CI: `978700d8c2887f65a60930f9e0f2ac8f8963d2f9`
- Normative checklist: `DODGE_SPEC.md` §15.3
- Lifecycle rule: `IMPLEMENTATION_GUIDE.md` §9
- Executable audit: `tests/test_dirps_g2_core.py`
- G3+ status: intentionally not claimed

The audit distinguishes **PASS** from **N/A**. N/A means the normalized feature is absent from the G2 candidate and the test suite asserts that absence so later additions cannot silently inherit the old evidence.

## Base §15.3 checks

| Check | Applicability | Evidence | Notes |
|---|---|---|---|
| 15.3.1 required local/external references resolve | PASS | `test_every_applicable_15_3_rule_passes`; negative missing-archetype fixture | Local source URIs and named DODGE refs used by DIRPS resolve. DIRPS G2 has no external entity/catalog references; the external GURPS URL is a source locator, not an external DODGE entity binding. |
| 15.3.2 object/archetype kinds and face slots agree | PASS | positive audit + negative face-slot fixture | Both actor objects are tokens bound to the token archetype and use its declared `front` slot. |
| 15.3.3 collection nesting and procedure refs acyclic unless explicit repetition | PASS | positive audit + negative self-cycle fixture | DIRPS declares no collections. Procedure-to-procedure graph is acyclic. |
| 15.3.4 coherent quantities / positive valid dimensions / supported units | N/A | audit asserts no explicit quantities or dimensions | G2 logical RPG actors have target-owned physical representation and no explicit dimensions. No collection/member/topology quantity is declared. |
| 15.3.5 source hashes match | N/A | audit asserts no `sources.*.sha256` | No source hash is declared in this candidate. |
| 15.3.6 scene instance and topology node IDs unique | PASS | positive audit + negative duplicate-instance fixture | Scene instance IDs are unique. No topology nodes are declared. |
| 15.3.7 topology edges reference existing nodes | N/A | audit asserts no topology edges | DIRPS G2 declares no topology. |
| 15.3.8 rule refs target correct definition kinds | PASS | positive audit + negative wrong-kind fixture | Action condition/procedure refs, procedure step refs, scenario action refs, and turn procedure ref are kind-checked. |
| 15.3.9 defaults satisfy types and bounds | PASS | positive audit + negative boolean-default fixture | Explicit defaults are the boolean `stunned=false` and `unconscious=false`. |
| 15.3.10 phase transitions and scenario end-condition evaluation deterministic | N/A | audit asserts no phases and no executable `end_conditions`; negative prose-end fixture | The former prose-only end condition was removed because prose cannot count as deterministic executable evaluation. Completion intent remains preserved in the prose objective and scenario source for a later executable gate. |
| 15.3.11 AI priorities executable or prose-only | N/A | audit asserts no AI profiles | No normalized AI profile is present at G2. |
| 15.3.12 target contract supports all required normalized features | N/A | audit inspects DIRPS registry and asserts no target/export contract | Targets begin at G6; no target contract is registered for DIRPS G2. |

## Conditional §15.3 groups

| Conditional group | Applicability | Evidence | Notes |
|---|---|---|---|
| representations | N/A | audit asserts no `representations` | No state-representation candidate or inclusion is declared. |
| target content configuration | N/A | no target/export contract registered | No target manifest/configuration exists in G2 scope. |
| invocations | N/A | audit asserts no object/member/entity invocation declarations | The G2 document does not claim playable-object invocation bindings. |
| requirements / modifiers / choices / equipment | PASS — choices only | positive choice audit + negative duplicate-option-ID fixture | No normalized requirements, modifiers, or equipment profiles are present. `tutorial-turn` now uses three named `choice_options` with unique IDs and kind-correct action steps. The older unnamed `options` form was removed. |

## G2 corrections discovered by the audit

Two actual core-validation gaps were found in the G1 document:

1. `tutorial-turn` used unnamed legacy `choice.options`. It now uses named `choice_options` with stable IDs, labels, and action steps.
2. Scenario 01 declared a prose-only `end_condition`. Because §15.3 requires deterministic end-condition evaluation, the executable end-condition declaration was removed at G2 rather than inventing completion state. The prose objective and scenario source preserve the intended completion semantics for later formalization.

These are neutral DODGE-core corrections. They do not add DIRPS domain semantic validation, a resolver, runtime dice, replay, or a target.

## Negative fixtures

`tests/test_dirps_g2_core.py` proves the audit rejects at least:

- a missing archetype reference;
- an invalid face slot;
- a procedure cycle;
- duplicate scene instance IDs;
- a rule ref resolving to the wrong definition kind;
- a default with the wrong type;
- reintroduction of a prose-only executable end condition;
- duplicate choice-option IDs.

## Gate boundary

G2 evidence proves only DODGE 0.2.1 generic core validity for the bounded candidate.

It does **not** prove the DIRPS/GURPS-specific implications described by the scenario. Those belong to **G3 — Semantic-valid** and remain intentionally unimplemented.
