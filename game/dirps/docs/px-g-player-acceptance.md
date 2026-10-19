# DIRPS PX-G — player acceptance

PX-G is the final player-experience acceptance tranche for **Scenario 01: The Missing Courier** under issue #190.

It does not add gameplay, presentation semantics, or another maturity gate. Its purpose is to verify that the accepted G7 runtime plus PX-A through PX-F can now be used as a short RPG tutorial by a player who does not need to understand DODGE or the implementation evidence.

## Baseline

- PX-F accepted/merged PR: #196.
- PX-F accepted head: `43942b323ecca619a090acf7851e06ca63509bd4`.
- PX-F merge SHA: `bfaa7ed3e31a546c275a42f1e92e469eca387100`.
- PX-G branch baseline: post-merge `main` at `29c7dcd59be92080dc24ae13d50a9d5f81367e6a`.
- Public player target: `/dirps/`.
- G7 authority/runtime/replay contracts remain unchanged.

## Acceptance rule

PX-G requires **both**:

1. exact-head automated evidence; and
2. at least one fresh human playthrough of the default player experience.

The human playthrough is not replaceable by headless browser automation.

Issue #190 must remain open until both evidence classes pass and the PX-G candidate is independently reviewed.

## Automated player acceptance

CI runs:

```text
npm run test:dirps-web-smoke
npm run test:dirps-player-acceptance
python -m unittest discover -s tests -p 'test_*.py'
```

The dedicated PX-G browser pass uses a 390×844 viewport and plays the real browser/Pyodide target from the opening state to an accepted terminal state.

During that run it deliberately does **not** open:

- Advanced evidence and debug tools;
- Technical resolution evidence;
- deterministic seed controls;
- Runtime Debug View.

The test continuously verifies that those surfaces stay closed while normal play remains possible.

### #190 question matrix

| Player question | Default player evidence | Automated check |
|---|---|---|
| Who am I? | Rook identity + role | non-empty identity/role before every action |
| What am I trying to accomplish? | scenario objective | visible objective remains player-readable |
| What is happening right now? | current encounter title + opening fiction | both are non-empty before every action |
| What can I do? | runtime-described player action | exactly one honest bounded action is visible |
| What did the roll/result mean? | human-readable last resolution | resolution title and player-facing result are present after each nonterminal action |
| What changed because of it? | consequence + transition outcome | consequence and transition outcome are present |
| Why am I at the next encounter? | transition bridge + next encounter fiction | bridge and next scene are present before continuing |
| Did I win or lose, and why? | dedicated PX-E ending | Success/Failure and courier conclusion are explicit |

The existing source tests continue to reject target-side gameplay literals/calculation, and the normal Phase I smoke continues to verify the shared Python runtime, deterministic replay evidence, advanced evidence recovery, and mobile/focus behavior.

## Fresh human playthrough protocol

Use a fresh load of the current PX-G candidate player target.

Do **not** open **Advanced evidence and debug tools** or **Technical resolution evidence** until the scenario is over.

Play normally from the first Roadside Tracks action to the terminal ending.

At each stage, confirm you can answer from the normal player UI:

- [ ] Who am I?
- [ ] What am I trying to accomplish?
- [ ] What is happening right now?
- [ ] What can I do?
- [ ] What did the roll/result mean?
- [ ] What changed because of it?
- [ ] Why am I at the next encounter?
- [ ] Did I win or lose, and why?

Also record:

- device / viewport:
- browser:
- terminal result:
- anything confusing or implementation-centric in the default flow:
- any point where debug/evidence had to be opened to understand play:

### Human acceptance status

**PENDING.**

A human PASS should be recorded on the PX-G PR or issue #190 with the device/browser and any material observations.

If the human pass finds a player-experience defect, fix that defect before closing #190. Do not mark the checklist PASS merely because automated CI is green.

## Closure

PX-G is complete only when:

- exact-head conformance is green;
- the dedicated no-debug player acceptance browser run is green;
- existing Web-target authority/anti-recomputation tests remain green;
- independent review accepts the candidate;
- a fresh human playthrough passes the checklist above.

Only then should issue #190 be closed.
