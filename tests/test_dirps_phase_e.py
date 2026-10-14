#!/usr/bin/env python3
import copy
import inspect
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dirps_debug_target
from dirps_debug_target import (
    execute_combat_target,
    execute_encounter_target,
    inspect_encounter_target,
)
from dirps_runtime import (
    ExecutionError,
    create_combat_runtime_state,
    describe_combat_exchange,
    execute_combat_exchange,
    replay_combat_exchange,
)
from game_registry import scenario_config
from resolve_dirps_dodge import resolve, resolve_documents

ENCOUNTER_REF = "bandit-scout"
ACTION_ID = "strike-bandit-scout"


class DirpsPhaseEBoundedCombatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())
        cls.resolved = resolve()

    @staticmethod
    def state_values(state):
        return {row["ref"]: row["value"] for row in state["bindings"]}

    def execute(
        self,
        *,
        resolved=None,
        state=None,
        attack=(4, 4, 4),
        defense=(3, 3, 3),
        damage=(1,),
        seed=None,
        defense_kind="dodge",
    ):
        resolved = resolved or self.resolved
        state = state or create_combat_runtime_state(
            resolved, encounter_ref=ENCOUNTER_REF
        )
        return execute_combat_exchange(
            resolved,
            state,
            encounter_ref=ENCOUNTER_REF,
            action_id=ACTION_ID,
            actor_ref="pc",
            target_ref="bandit-scout",
            defense_kind=defense_kind,
            attack_terms=None if seed is not None else list(attack),
            defense_terms=None if seed is not None else (
                None if defense is None else list(defense)
            ),
            damage_terms=None if seed is not None else (
                None if damage is None else list(damage)
            ),
            random_seed=seed,
        )

    def resolved_with_skill(self, level):
        dodge = copy.deepcopy(self.dodge)
        canonical = copy.deepcopy(self.canonical)
        canonical["player_character"]["skills"]["broadsword"] = level
        scene_ref = dodge["scenarios"]["scenario-01"]["scene_ref"]
        pc = next(
            row
            for row in dodge["scenes"][scene_ref]["instances"]
            if row["id"] == "pc"
        )
        pc["extensions"]["org.dirps.character"]["skills"]["broadsword"] = level
        return resolve_documents(dodge, canonical, self.sidecar, self.cfg)

    def resolved_with_defender_dx(self, level):
        dodge = copy.deepcopy(self.dodge)
        canonical = copy.deepcopy(self.canonical)
        encounter = next(
            row for row in canonical["encounters"] if row["id"] == ENCOUNTER_REF
        )
        encounter["opponent"]["attributes"]["dx"] = level
        scene_ref = dodge["scenarios"]["scenario-01"]["scene_ref"]
        npc = next(
            row
            for row in dodge["scenes"][scene_ref]["instances"]
            if row["id"] == "bandit-scout"
        )
        npc["state"]["dx"] = level
        return resolve_documents(dodge, canonical, self.sidecar, self.cfg)

    def resolved_with_armor_dr(self, dr):
        canonical = copy.deepcopy(self.canonical)
        encounter = next(
            row for row in canonical["encounters"] if row["id"] == ENCOUNTER_REF
        )
        encounter["opponent"]["defense_assumptions"]["armor_dr"] = dr
        return resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)

    def test_initial_combat_state_and_capability(self):
        state = create_combat_runtime_state(self.resolved, encounter_ref=ENCOUNTER_REF)
        self.assertEqual(state["revision"], "0")
        self.assertEqual(
            self.state_values(state),
            {
                "hit-points": 10,
                "stunned": False,
                "unconscious": False,
                "consciousness-check-required": False,
            },
        )
        view = describe_combat_exchange(
            self.resolved, state, encounter_ref=ENCOUNTER_REF
        )
        self.assertEqual([row["id"] for row in view["available_actions"]], [ACTION_ID])
        self.assertEqual(view["combat_capability"]["attack_target"], 12)
        self.assertEqual(view["combat_capability"]["defense"]["kind"], "dodge")
        self.assertEqual(view["combat_capability"]["defense"]["target"], 5)
        self.assertEqual(
            view["combat_capability"]["damage"]["profile"],
            {"count": 1, "sides": 6, "adds": 0},
        )
        self.assertEqual(view["combat_capability"]["damage"]["weapon_add"], 1)

    def test_attack_miss_stops_before_reaction_or_damage(self):
        record = self.execute(attack=(5, 5, 5), defense=None, damage=None)
        self.assertEqual(record["format"], "dirps-combat-exchange-result.v1")
        self.assertEqual(record["outcome_branch"], "attack-missed")
        self.assertFalse(record["reaction_window"]["opened"])
        self.assertIsNone(record["defense_resolution"])
        self.assertIsNone(record["damage_resolution"])
        self.assertEqual(record["state_delta"], [])
        self.assertEqual(record["state_after"]["revision"], "1")

    def test_successful_attack_can_be_defended(self):
        record = self.execute(attack=(4, 4, 4), defense=(1, 1, 2), damage=None)
        self.assertEqual(record["outcome_branch"], "defended")
        self.assertTrue(record["reaction_window"]["opened"])
        self.assertEqual(record["defense_resolution"]["target"], 5)
        self.assertTrue(record["defense_resolution"]["outcome"]["success"])
        self.assertEqual(
            record["defense_resolution"]["outcome"]["classification"],
            "critical-success",
        )
        self.assertIsNone(record["damage_resolution"])
        self.assertEqual(record["state_delta"], [])

    def test_undefended_hit_applies_cutting_injury_and_hp_loss(self):
        record = self.execute(attack=(4, 4, 4), defense=(3, 3, 3), damage=(1,))
        self.assertEqual(record["outcome_branch"], "hit")
        self.assertFalse(record["defense_resolution"]["outcome"]["success"])
        damage = record["damage_resolution"]
        self.assertEqual(damage["basic_damage"], 2)
        self.assertEqual(damage["armor_dr"], 0)
        self.assertEqual(damage["penetrating_damage"], 2)
        self.assertEqual(damage["injury"], 3)
        self.assertEqual(record["injury_effects"]["remaining_hp"], 7)
        self.assertFalse(record["injury_effects"]["major_wound"])
        self.assertFalse(record["injury_effects"]["stunned"])
        self.assertEqual(self.state_values(record["state_after"])["hit-points"], 7)
        self.assertEqual(
            [row["ref"] for row in record["state_delta"]],
            ["hit-points"],
        )

    def test_major_wound_sets_stunned(self):
        record = self.execute(damage=(4,))
        self.assertEqual(record["damage_resolution"]["injury"], 7)
        self.assertTrue(record["injury_effects"]["major_wound"])
        self.assertTrue(record["injury_effects"]["stunned"])
        self.assertEqual(record["injury_effects"]["remaining_hp"], 3)
        values = self.state_values(record["state_after"])
        self.assertTrue(values["stunned"])
        self.assertFalse(values["consciousness-check-required"])

    def test_zero_hp_defers_consciousness_check_to_phase_f(self):
        record = self.execute(damage=(6,))
        self.assertEqual(record["damage_resolution"]["basic_damage"], 7)
        self.assertEqual(record["damage_resolution"]["injury"], 10)
        self.assertEqual(record["injury_effects"]["remaining_hp"], 0)
        self.assertTrue(record["injury_effects"]["stunned"])
        self.assertTrue(record["injury_effects"]["consciousness_check_required"])
        self.assertFalse(record["injury_effects"]["unconscious"])
        self.assertEqual(record["injury_effects"]["deferred_recovery_phase"], "Phase F")
        values = self.state_values(record["state_after"])
        self.assertEqual(values["hit-points"], 0)
        self.assertTrue(values["stunned"])
        self.assertTrue(values["consciousness-check-required"])
        self.assertFalse(values["unconscious"])
        print("PASS dirps/scenario-01: Phase E bounded combat exchange")

    def test_attack_roll_three_bypasses_defense_and_uses_maximum_damage(self):
        # The supplied damage term is deliberately low. Roll 3 must not consume it.
        record = self.execute(attack=(1, 1, 1), defense=None, damage=(1,))
        self.assertEqual(
            record["attack_resolution"]["outcome"]["classification"],
            "critical-success",
        )
        self.assertEqual(record["attack_resolution"]["random_evidence"]["total"], 3)
        self.assertFalse(record["reaction_window"]["opened"])
        self.assertEqual(
            record["reaction_window"]["reason"],
            "critical-hit-bypasses-defense",
        )
        self.assertIsNone(record["defense_resolution"])

        damage = record["damage_resolution"]
        self.assertEqual(damage["resolution_mode"], "automatic-maximum")
        self.assertIsNone(damage["random_evidence"])
        self.assertEqual(damage["basic_damage"], 7)
        self.assertEqual(damage["penetrating_damage"], 7)
        self.assertEqual(damage["injury"], 10)
        self.assertEqual(
            damage["trace"]["critical_maximum_damage"]["maximum_rolled_total"],
            6,
        )
        self.assertEqual(
            damage["trace"]["critical_maximum_damage"]["rule_source_ref"],
            "gurps-lite",
        )

        self.assertEqual(record["injury_effects"]["remaining_hp"], 0)
        self.assertTrue(record["injury_effects"]["major_wound"])
        self.assertTrue(record["injury_effects"]["stunned"])
        self.assertTrue(record["injury_effects"]["consciousness_check_required"])
        self.assertFalse(record["injury_effects"]["unconscious"])

        values = self.state_values(record["state_after"])
        self.assertEqual(values["hit-points"], 0)
        self.assertTrue(values["stunned"])
        self.assertTrue(values["consciousness-check-required"])
        self.assertFalse(values["unconscious"])
        self.assertEqual(replay_combat_exchange(self.resolved, record), record)

    def test_other_critical_hit_bypasses_defense_and_rolls_damage_normally(self):
        record = self.execute(attack=(1, 1, 2), defense=None, damage=(1,))
        self.assertEqual(
            record["attack_resolution"]["outcome"]["classification"],
            "critical-success",
        )
        self.assertEqual(record["attack_resolution"]["random_evidence"]["total"], 4)
        self.assertFalse(record["reaction_window"]["opened"])
        self.assertEqual(
            record["reaction_window"]["reason"],
            "critical-hit-bypasses-defense",
        )
        self.assertIsNone(record["defense_resolution"])
        damage = record["damage_resolution"]
        self.assertEqual(damage["resolution_mode"], "rolled")
        self.assertEqual(damage["random_evidence"]["terms"], [1])
        self.assertEqual(damage["random_evidence"]["rolled_total"], 1)
        self.assertEqual(damage["basic_damage"], 2)
        self.assertEqual(damage["injury"], 3)
        self.assertEqual(replay_combat_exchange(self.resolved, record), record)

    def test_unsupported_active_defense_fails_visibly(self):
        with self.assertRaisesRegex(ExecutionError, "unsupported Phase E active defense"):
            self.execute(defense_kind="parry")

    def test_bounded_exchange_cannot_repeat(self):
        first = self.execute(attack=(5, 5, 5), defense=None, damage=None)
        state = copy.deepcopy(first["state_after"])
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(ExecutionError, "exactly one exchange"):
            self.execute(state=state, attack=(5, 5, 5), defense=None, damage=None)
        self.assertEqual(state, before)
        view = describe_combat_exchange(
            self.resolved, state, encounter_ref=ENCOUNTER_REF
        )
        self.assertEqual(view["available_actions"], [])

    def test_seeded_combat_is_deterministic_and_replays(self):
        first = self.execute(seed="phase-e-seed")
        second = self.execute(seed="phase-e-seed")
        self.assertEqual(first, second)
        self.assertEqual(replay_combat_exchange(self.resolved, first), first)

    def test_replay_detects_injury_state_tampering(self):
        record = self.execute(damage=(4,))
        tampered = copy.deepcopy(record)
        tampered["injury_effects"]["remaining_hp"] = 99
        with self.assertRaisesRegex(ExecutionError, "combat exchange record divergence"):
            replay_combat_exchange(self.resolved, tampered)

    def test_broadsword_skill_perturbation_changes_attack_outcome(self):
        changed = self.resolved_with_skill(13)
        baseline = self.execute(attack=(4, 4, 5), defense=None, damage=None)
        changed_record = self.execute(
            resolved=changed,
            attack=(4, 4, 5),
            defense=(1, 1, 2),
            damage=None,
        )
        self.assertEqual(baseline["attack_resolution"]["target"], 12)
        self.assertFalse(baseline["attack_resolution"]["outcome"]["success"])
        self.assertEqual(changed_record["attack_resolution"]["target"], 13)
        self.assertTrue(changed_record["attack_resolution"]["outcome"]["success"])

    def test_defender_dx_perturbation_changes_dodge_outcome(self):
        changed = self.resolved_with_defender_dx(14)
        baseline = self.execute(
            attack=(4, 4, 4), defense=(1, 2, 3), damage=(1,)
        )
        changed_record = self.execute(
            resolved=changed,
            attack=(4, 4, 4),
            defense=(1, 2, 3),
            damage=None,
        )
        self.assertEqual(baseline["defense_resolution"]["target"], 5)
        self.assertFalse(baseline["defense_resolution"]["outcome"]["success"])
        self.assertEqual(changed_record["defense_resolution"]["target"], 6)
        self.assertTrue(changed_record["defense_resolution"]["outcome"]["success"])
        self.assertEqual(changed_record["outcome_branch"], "defended")

    def test_armor_dr_perturbation_changes_injury(self):
        changed = self.resolved_with_armor_dr(2)
        baseline = self.execute(damage=(6,))
        changed_record = self.execute(resolved=changed, damage=(6,))
        self.assertEqual(baseline["damage_resolution"]["injury"], 10)
        self.assertEqual(changed_record["damage_resolution"]["armor_dr"], 2)
        self.assertEqual(changed_record["damage_resolution"]["penetrating_damage"], 5)
        self.assertEqual(changed_record["damage_resolution"]["injury"], 7)

    def test_unsupported_attacker_strength_fails_in_damage_lookup(self):
        dodge = copy.deepcopy(self.dodge)
        canonical = copy.deepcopy(self.canonical)
        canonical["player_character"]["attributes"]["st"] = 11
        scene_ref = dodge["scenarios"]["scenario-01"]["scene_ref"]
        pc = next(
            row for row in dodge["scenes"][scene_ref]["instances"] if row["id"] == "pc"
        )
        pc["state"]["st"] = 11
        resolved = resolve_documents(dodge, canonical, self.sidecar, self.cfg)
        with self.assertRaisesRegex(ExecutionError, "no unique row for ST 11"):
            self.execute(resolved=resolved, damage=(6,))

    def test_reaction_window_binding_drift_fails_before_roll(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["proto_sidecar"]["phase_e_combat_bindings"][ENCOUNTER_REF][
            "reaction_window"
        ]["eligible_defenses"] = ["parry"]
        with self.assertRaisesRegex(ExecutionError, "reaction window"):
            self.execute(resolved=resolved)

    def test_expression_binding_drift_fails_before_defense(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["proto_sidecar"]["phase_e_expressions"]["bandit-dodge-target"][
            "op"
        ] = "multiply"
        with self.assertRaisesRegex(ExecutionError, "unsupported Phase E expression operator"):
            self.execute(resolved=resolved, defense=(3, 3, 3), damage=(1,))

    def test_proto_maturity_advances_only_exercised_combat_gaps(self):
        specs = self.resolved["proto_sidecar"]["proto_specs"]
        for proto_id in (
            "reaction_timing",
            "derived_values",
            "expressions",
            "damage_injury",
        ):
            self.assertEqual(specs[proto_id]["status"], "exercised")
            self.assertEqual(
                specs[proto_id]["candidate_for_dodge"],
                "not-yet-candidate",
            )
        self.assertEqual(specs["lookup_tables"]["status"], "exercised")
        self.assertEqual(specs["replay_session_history"]["status"], "exercised")
        self.assertEqual(
            specs["replay_session_history"]["candidate_for_dodge"],
            "not-yet-candidate",
        )
        self.assertEqual(specs["visibility_and_secret_state"]["status"], "suspected")

    def test_generic_target_dispatches_combat(self):
        view = inspect_encounter_target(self.resolved, encounter_ref=ENCOUNTER_REF)
        self.assertEqual(view["target"]["format"], "dirps-debug-combat-target.v1")
        self.assertEqual(
            [row["id"] for row in view["capability"]["available_actions"]],
            [ACTION_ID],
        )
        executed = execute_encounter_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
            action_id=ACTION_ID,
            actor_ref="pc",
            target_ref="bandit-scout",
            defense_kind="dodge",
            attack_terms=[4, 4, 4],
            defense_terms=[3, 3, 3],
            damage_terms=[1],
        )
        self.assertEqual(executed["status"], "ok")
        self.assertEqual(executed["execution"]["outcome_branch"], "hit")
        self.assertEqual(executed["capability"]["available_actions"], [])
        print("PASS dirps/scenario-01: Phase E debug target consumes combat runtime")

    def test_target_passes_fake_combat_result_through(self):
        fake_state = {"scenario_ref": "fake", "bindings": [], "events": [], "revision": "0"}
        fake_capability = {"encounter": {"id": "fake"}, "available_actions": []}
        fake_record = {
            "format": "fake-combat",
            "state_after": {"revision": "9"},
            "outcome_branch": "runtime-owned",
        }
        view = execute_combat_target(
            self.resolved,
            encounter_ref="input",
            action_id="action",
            actor_ref="actor",
            target_ref="target",
            defense_kind="defense",
            attack_terms=[99],
            runtime_create=lambda resolved, encounter_ref: fake_state,
            runtime_describe=lambda resolved, state, encounter_ref: fake_capability,
            runtime_execute=lambda *args, **kwargs: fake_record,
        )
        self.assertEqual(view["status"], "ok")
        self.assertIs(view["execution"], fake_record)
        self.assertEqual(view["runtime_state"], fake_record["state_after"])

    def test_target_source_contains_no_phase_e_gameplay_literals(self):
        source = inspect.getsource(dirps_debug_target)
        for literal in [
            '"bandit-scout"',
            '"strike-bandit-scout"',
            '"broadsword"',
            '"dodge"',
            '"hit-points"',
            '"stunned"',
            '"consciousness-check-required"',
        ]:
            self.assertNotIn(literal, source)

    def test_cli_executes_bounded_combat(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "dirps_debug_target.py"),
                "--encounter",
                ENCOUNTER_REF,
                "--action",
                ACTION_ID,
                "--actor",
                "pc",
                "--target",
                "bandit-scout",
                "--defense",
                "dodge",
                "--attack-dice",
                "4",
                "4",
                "4",
                "--defense-dice",
                "3",
                "3",
                "3",
                "--damage-dice",
                "6",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        view = json.loads(proc.stdout)
        self.assertEqual(view["status"], "ok")
        self.assertEqual(
            view["execution"]["format"],
            "dirps-combat-exchange-result.v1",
        )
        self.assertTrue(
            self.state_values(view["runtime_state"])[
                "consciousness-check-required"
            ]
        )


if __name__ == "__main__":
    unittest.main()
