#!/usr/bin/env python3
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dirps_runtime import (
    ExecutionError,
    create_scenario_runtime_state,
    describe_scenario,
    execute_scenario_action,
    replay_scenario_progression,
)
from game_registry import scenario_config
from resolve_dirps_dodge import ResolutionError, resolve, resolve_documents


class DirpsPhaseGProgressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())
        cls.resolved = resolve()

    @staticmethod
    def progress(resolved, state):
        return describe_scenario(resolved, state)["progress"]

    def execute(self, state, action_id, actor_ref, random_inputs=None, resolved=None):
        return execute_scenario_action(
            resolved or self.resolved,
            state,
            action_id=action_id,
            actor_ref=actor_ref,
            random_inputs=random_inputs,
        )

    def advance_to_bandit(self, resolved=None):
        resolved = resolved or self.resolved
        state = create_scenario_runtime_state(resolved)
        roadside = self.execute(
            state,
            "investigate-tracks",
            "pc",
            {"dice_terms": [3, 3, 3]},
            resolved,
        )
        witness = self.execute(
            roadside["state_after"],
            "reassure-and-question",
            "pc",
            {"dice_terms": [3, 3, 3]},
            resolved,
        )
        path = self.execute(
            witness["state_after"],
            "cross-washed-out-path",
            "pc",
            {"dice_terms": [3, 3, 3]},
            resolved,
        )
        return roadside, witness, path

    def complete_failure(self):
        _, _, path = self.advance_to_bandit()
        return self.execute(
            path["state_after"],
            "strike-bandit-scout",
            "pc",
            {"attack_terms": [6, 6, 6]},
        )

    def test_initial_state_exposes_only_first_canonical_encounter(self):
        state = create_scenario_runtime_state(self.resolved)
        view = describe_scenario(self.resolved, state)
        self.assertEqual(
            view["encounter_order"],
            ["roadside-tracks", "frightened-witness", "washed-out-path", "bandit-scout"],
        )
        self.assertEqual(
            view["progress"],
            {
                "status": "in-progress",
                "current_encounter": "roadside-tracks",
                "step": "action",
                "outcome": "undetermined",
                "information": "accumulating",
            },
        )
        self.assertEqual(
            [(row["id"], row["actor_ref"]) for row in view["available_actions"]],
            [("investigate-tracks", "pc")],
        )
        self.assertEqual(view["runtime_state_revision"], "0")

    def test_encounters_advance_in_canonical_order_and_retain_information(self):
        state = create_scenario_runtime_state(self.resolved)
        roadside = self.execute(
            state,
            "investigate-tracks",
            "pc",
            {"dice_terms": [6, 6, 6]},
        )
        view = describe_scenario(self.resolved, roadside["state_after"])
        self.assertEqual(view["progress"]["current_encounter"], "frightened-witness")
        self.assertEqual(
            view["retained_state"]["roadside-tracks"]["information"],
            "trail-inconclusive",
        )
        self.assertEqual(
            [(row["id"], row["actor_ref"]) for row in view["available_actions"]],
            [("reassure-and-question", "pc")],
        )

        witness = self.execute(
            roadside["state_after"],
            "reassure-and-question",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )
        view = describe_scenario(self.resolved, witness["state_after"])
        self.assertEqual(view["progress"]["current_encounter"], "washed-out-path")
        self.assertNotEqual(
            view["retained_state"]["frightened-witness"]["information"],
            "unknown",
        )

        path = self.execute(
            witness["state_after"],
            "cross-washed-out-path",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )
        view = describe_scenario(self.resolved, path["state_after"])
        self.assertEqual(view["progress"]["current_encounter"], "bandit-scout")
        self.assertEqual(
            view["retained_state"]["washed-out-path"]["progress"],
            "crossed",
        )

    def test_full_scenario_can_complete_successfully(self):
        roadside, witness, path = self.advance_to_bandit()
        combat = self.execute(
            path["state_after"],
            "strike-bandit-scout",
            "pc",
            {"attack_terms": [1, 1, 1]},
        )
        combat_view = describe_scenario(self.resolved, combat["state_after"])
        self.assertEqual(combat_view["progress"]["current_encounter"], "bandit-scout")
        self.assertEqual(combat_view["progress"]["step"], "recovery")
        self.assertEqual(
            [(row["id"], row["actor_ref"]) for row in combat_view["available_actions"]],
            [("resolve-bandit-next-turn", "bandit-scout")],
        )

        recovery = self.execute(
            combat["state_after"],
            "resolve-bandit-next-turn",
            "bandit-scout",
            {"consciousness_terms": [6, 6, 6]},
        )
        self.assertEqual(recovery["format"], "dirps-scenario-progression-result.v1")
        self.assertEqual(recovery["mechanic_result"]["format"], "dirps-recovery-result.v1")
        self.assertEqual(
            recovery["progression"],
            {
                "advanced_to": "complete",
                "terminal": True,
                "outcome": "success",
                "information": "courier-fate-established",
                "objective_complete": True,
                "end_condition_id": "missing-courier-success",
                "conclusion_text": self.canonical["progression"]["completion"]["success"]["conclusion_text"],
            },
        )
        final_view = describe_scenario(self.resolved, recovery["state_after"])
        self.assertEqual(final_view["progress"]["status"], "complete")
        self.assertEqual(final_view["available_actions"], [])
        self.assertEqual(
            final_view["retained_state"]["roadside-tracks"]["information"],
            roadside["mechanic_result"]["consequence"]["information"],
        )
        self.assertEqual(
            final_view["retained_state"]["frightened-witness"]["information"],
            witness["mechanic_result"]["consequence"]["information"],
        )
        self.assertEqual(
            final_view["retained_state"]["washed-out-path"]["progress"],
            path["mechanic_result"]["consequence"]["progress"],
        )
        self.assertTrue(final_view["retained_state"]["bandit-scout"]["unconscious"])
        print("PASS dirps/scenario-01: Phase G scenario progression and completion")

    def test_full_scenario_has_deterministic_failure_end_state(self):
        record = self.complete_failure()
        self.assertEqual(record["mechanic_result"]["format"], "dirps-combat-exchange-result.v1")
        self.assertEqual(record["mechanic_result"]["outcome_branch"], "attack-missed")
        self.assertEqual(record["progression"]["outcome"], "failure")
        self.assertEqual(record["progression"]["information"], "courier-fate-unresolved")
        self.assertFalse(record["progression"]["objective_complete"])
        self.assertEqual(record["progression"]["end_condition_id"], "missing-courier-failure")
        view = describe_scenario(self.resolved, record["state_after"])
        self.assertEqual(
            view["progress"],
            {
                "status": "complete",
                "current_encounter": "complete",
                "step": "complete",
                "outcome": "failure",
                "information": "courier-fate-unresolved",
            },
        )
        self.assertEqual(view["available_actions"], [])

    def test_out_of_order_and_post_completion_actions_fail_without_mutation(self):
        state = create_scenario_runtime_state(self.resolved)
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(ExecutionError, "unavailable or out of order"):
            self.execute(
                state,
                "reassure-and-question",
                "pc",
                {"dice_terms": [3, 3, 3]},
            )
        self.assertEqual(state, before)

        completed = self.complete_failure()["state_after"]
        before = copy.deepcopy(completed)
        with self.assertRaisesRegex(ExecutionError, "already complete"):
            self.execute(
                completed,
                "investigate-tracks",
                "pc",
                {"dice_terms": [3, 3, 3]},
            )
        self.assertEqual(completed, before)

    def test_unsupported_random_inputs_fail_visibly_without_mutation(self):
        state = create_scenario_runtime_state(self.resolved)
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(ExecutionError, "unsupported keys"):
            self.execute(
                state,
                "investigate-tracks",
                "pc",
                {"damage_terms": [1]},
            )
        self.assertEqual(state, before)

    def test_one_record_replay_and_divergence_evidence(self):
        state = create_scenario_runtime_state(self.resolved)
        record = self.execute(
            state,
            "investigate-tracks",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )
        self.assertEqual(replay_scenario_progression(self.resolved, record), record)

        tampered = copy.deepcopy(record)
        tampered["progression"]["advanced_to"] = "washed-out-path"
        with self.assertRaisesRegex(ExecutionError, "divergence"):
            replay_scenario_progression(self.resolved, tampered)

    def test_canonical_order_perturbation_changes_runtime_progression(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["encounters"][1], canonical["encounters"][2] = (
            canonical["encounters"][2],
            canonical["encounters"][1],
        )
        resolved = resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)
        state = create_scenario_runtime_state(resolved)
        record = self.execute(
            state,
            "investigate-tracks",
            "pc",
            {"dice_terms": [3, 3, 3]},
            resolved,
        )
        self.assertEqual(record["progression"]["advanced_to"], "washed-out-path")
        view = describe_scenario(resolved, record["state_after"])
        self.assertEqual(view["progress"]["current_encounter"], "washed-out-path")
        self.assertEqual(view["available_actions"][0]["id"], "cross-washed-out-path")

    def test_resolved_completion_trigger_drift_fails_before_runtime(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["scenario"]["progression"]["completion"]["success"]["trigger"][
            "bandit_can_act_normally"
        ] = True
        state = copy.deepcopy(
            resolved["runtime_states"]["scenario-01-playable-initial"]
        )
        with self.assertRaisesRegex(
            ExecutionError, "canonical success completion trigger"
        ):
            describe_scenario(resolved, state)

    def test_resolved_terminal_effect_drift_fails_before_runtime(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["rules"]["effects"]["phase-g-information-success"]["value"] = (
            "courier-fate-unresolved"
        )
        state = copy.deepcopy(
            resolved["runtime_states"]["scenario-01-playable-initial"]
        )
        with self.assertRaisesRegex(
            ExecutionError, "success terminal state/effect alignment"
        ):
            describe_scenario(resolved, state)

    def test_resolved_terminal_condition_drift_fails_before_runtime(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["rules"]["conditions"]["scenario-success"]["right"] = "failure"
        state = copy.deepcopy(
            resolved["runtime_states"]["scenario-01-playable-initial"]
        )
        with self.assertRaisesRegex(
            ExecutionError, "success terminal state/condition alignment"
        ):
            describe_scenario(resolved, state)

    def test_dodge_completion_drift_fails_semantic_resolution(self):
        dodge = copy.deepcopy(self.dodge)
        dodge["scenarios"]["scenario-01"]["objectives"][0]["completion"] = "scenario-failure"
        with self.assertRaisesRegex(ResolutionError, "Phase G objective completion"):
            resolve_documents(dodge, self.canonical, self.sidecar, self.cfg)

    def test_progression_bridge_drift_fails_resolution(self):
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["phase_g_progression_bindings"]["scenario-01"]["recovery_effect_ref"] = (
            "missing-effect"
        )
        with self.assertRaisesRegex(ResolutionError, "Phase G progression binding"):
            resolve_documents(self.dodge, self.canonical, sidecar, self.cfg)

    def test_phase_g_does_not_promote_session_history_or_rewrite_old_records(self):
        self.assertEqual(
            self.sidecar["proto_specs"]["replay_session_history"]["status"],
            "suspected",
        )
        self.assertEqual(
            self.sidecar["proto_specs"]["replay_session_history"]["candidate_for_dodge"],
            "not-yet-candidate",
        )
        _, _, path = self.advance_to_bandit()
        combat = self.execute(
            path["state_after"],
            "strike-bandit-scout",
            "pc",
            {"attack_terms": [6, 6, 6]},
        )
        self.assertEqual(combat["mechanic_result"]["format"], "dirps-combat-exchange-result.v1")
        self.assertNotIn("scenario_progression", combat["mechanic_result"])


if __name__ == "__main__":
    unittest.main()
