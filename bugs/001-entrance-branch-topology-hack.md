# Bug 001: The Entrance Branch Topology Hack

## Summary

During a deterministic Wretched Demesne Beta playtest, the player explored deeply into the cave, deliberately backtracked all the way to the Cave Mouth, and then chose **Explore** again.

The runtime correctly interpreted Explore as "reveal a new room connected to the room the crew currently occupies." Because the crew was back at the Cave Mouth, the newly revealed **Whispering Dead End** became a second branch directly off the entrance.

The result felt like a shortcut exploit: after progressing deeply through one branch, the player could retreat to the entrance and begin a fresh branch there rather than continuing from the frontier.

This is not actually a corrupt topology edge. It is an emergent consequence of the current topology/exploration rules — and a fun hack.

## How it was found

This appeared during manual Beta play using deterministic seed:

`quick-test-001`

The player noticed that after reaching Whispering Dead End, moving back seemed to jump directly to Cave Mouth, apparently skipping a large number of rooms. The on-screen **Discovered Path** reinforced that impression because it displayed rooms in discovery order rather than rendering the actual connection graph.

Fortunately, the run had been recorded with the new deterministic replay system.

Replaying the exported `wretched-replay.v1` JSON reproduced the behavior exactly. Inspection of the recorded states showed the causal sequence:

1. The original expedition path grew outward from Cave Mouth through Bone Pit and several subsequent rooms.
2. The player backtracked through the existing graph to Cave Mouth.
3. While standing at Cave Mouth, the player selected **Explore**.
4. Explore revealed Whispering Dead End.
5. The engine connected the newly revealed room to its exploration origin: Cave Mouth.
6. Later, moving from Whispering Dead End directly to Cave Mouth was therefore a legal one-edge move.

Conceptually, the actual topology had become:

```text
                  +-- Whispering Dead End -- Ancient Relay -- ...
                  |
Cave Mouth -------+
                  |
                  +-- Bone Pit -- Ruined Workshop -- Collapsed Gallery -- ...
```

The UI instead presented rooms roughly in discovery order, making the new branch look like it had been appended to the far end of the first branch.

## Why this is neat

This is a useful example of a bug report uncovering **emergent gameplay rather than a broken simulation**.

The player's intuition was that the game had accidentally created a shortcut. Deterministic replay showed that the engine had actually followed its rules consistently: the player had intentionally returned to the entrance, and Explore created a new edge from the player's current location.

That makes the behavior potentially exploitable as a topology strategy:

- explore deeply down one branch;
- decide the current frontier is inconvenient or dangerous;
- backtrack to a strategically useful earlier room;
- Explore there;
- grow a new branch from that point.

In particular, returning to Cave Mouth before exploring can keep newly discovered branches only one edge from extraction. Depending on the intended design, that could become a legitimate tactical technique, an unintended exploit, or the seed of a more explicit branching-cave mechanic.

It is also a nice demonstration of why deterministic replay is valuable. Without the replay, this looked like a transient navigation bug. With the replay, we could reconstruct exactly where the edge was created and distinguish three separate things:

1. **Runtime topology:** behaved consistently.
2. **Exploration rules:** permit strategic branch creation and may need design review.
3. **Topology visualization:** misleadingly displayed discovery order as though it were connectivity.

## Related issues

- #39 — Beta map: render actual topology instead of discovery order
- #40 — Replay diagnostics: make topology mutations and movement provenance inspectable
- #41 — Beta navigation: distinguish Move from Explore and show exploration origin

## Status

Preserved as an interesting Beta behavior for design review rather than classified solely as an engine defect.

The topology hack should remain reproducible with seed `quick-test-001` and its captured replay while the navigation/topology design evolves.
