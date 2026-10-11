# Scenario 01 MVP — assumptions and target

## Target

Produce one complete, data-driven vertical slice of **Wretched Demesne: Plateau of Leng** that can be consumed by three sibling targets without rewriting game rules:

1. GitHub Pages playable implementation
2. Print-and-Play PDF
3. Tabletop Simulator ZIP

The same canonical dataset must drive all three. Renderers/exporters may contain presentation and platform adaptation logic, but **must not contain independent balance values or game rules**.

## Source authority

The supplied GDD remains authoritative. The existing lossless DODGE + sidecar import remains the preservation layer. This MVP dataset is an executable prototype interpretation of that design, not a replacement for it.

## Prototype assumptions

The GDD intentionally leaves exact deck size, health/damage scale, Threat implementation, ammunition representation, dungeon generation and several other details unresolved. To make Scenario 01 playable, this step adopts provisional values:

- 10-card role decks, 5-card hand, 3 actions per turn.
- Baseline crew Health 7–10 and simple attack-minus-defense damage.
- Shared Ammo starts at 8, caps at 12.
- Threat runs 0–12, with escalation at 4, 8 and 12.
- Modular room-card exploration is used for the first prototype.
- Each searchable room can be searched once.
- Spider feeding and pupation use a compact two-corpse lifecycle so the ecosystem appears during a 30–60 minute test.
- Scenario 01 uses an Ancient Power Cell → Ancient Relay → extraction objective chain.
- Precise card effects, enemy numeric stats, encounter effects and most role abilities are provisional tuning content.
- Permanent death, full Stress/Sanity, campaign structure, detailed ship infiltration, full Men of Leng faction play and Black Pyramid endgame remain out of MVP scope.

Every provisional content record is marked with `provenance: "prototype_assumption"` or equivalent wording.

## MVP acceptance target

A playtest should exercise: exploration, a five-card hand, three-action turns, searching/loot, firearm ammo and Noise, global Threat, enemy activation, Spider Corpses, feeding, chrysalis/evolution, voluntary retreat, the objective chain, extraction, win and loss.

This step defines the data. **The next step is implementation of the shared runtime and three exporters.**

## Tuning rule

When playtesting changes a number or rule, change the canonical dataset (or the lossless sidecar when it is still outside official DODGE). Do not patch Web, PnP or TTS independently.
