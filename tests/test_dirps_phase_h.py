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
    append_scenario_session_step,
    create_scenario_session_history,
    replay_scenario_session_history,
)
from game_registry import scenario_config
from resolve_dirps_dodge import ResolutionError, resolve, resolve_documents


class DirpsPhaseHSessionHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())
        cls.resolved = resolve()

    def append(self, history, action_id, actor_ref, random_inputs):
        return append_scenario_session_step(
            self.resolved,
            history,
            action_id=action_id,
            actor_ref=actor_ref,
            random_inputs=random_inputs,
        )

    def complete_success(self):
        history = create_scenario_session_history(self.resolved)
        history = self.append(
            history,
            "investigate-tracks",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )
        history = self.append(
            history,
            "reassure-and-question",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )
        history = self.append(
            history,
            "cross-washed-out-path",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )
        history = self.append(
            history,
            "strike-bandit-scout",
            "pc",
            {"attack_terms": [1, 1, 1]},
        )
        history = self.append(
            history,
            "resolve-bandit-next-turn",
            "bandit-scout",
            {"consciousness_terms": [6, 6, 6]},
        )
        return history

    def complete_failure(self):
        history = create_scenario_session_history(self.resolved)
        for action_id, actor_ref, random_inputs in (
            ("investigate-tracks", "pc", {"dice_terms": [3, 3, 3]}),
            ("reassure-and-question", "pc", {"dice_terms": [3, 3, 3]}),
            ("cross-washed-out-path", "pc", {"dice_terms": [3, 3, 3]}),
            ("strike-bandit-scout", "pc", {"attack_terms": [6, 6, 6]}),
        ):
            history = self.append(history, action_id, actor_ref, random_inputs)
        return history

    def test_history_is_copy_on_append_and_preserves_step_evidence(self):
        empty = create_scenario_session_history(self.resolved)
        empty_snapshot = copy.deepcopy(empty)
        first = self.append(
            empty,
            "investigate-tracks",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )
        first_snapshot = copy.deepcopy(first)
        second = self.append(
            first,
            "reassure-and-question",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )

        self.assertEqual(empty, empty_snapshot)
        self.assertEqual(empty["steps"], [])
        self.assertEqual(first, first_snapshot)
        self.assertEqual(len(first["steps"]), 1)
        self.assertEqual(len(second["steps"]), 2)
        self.assertEqual(first["steps"], second["steps"][:1])

        step = first["steps"][0]
        self.assertEqual(
            set(step),
            {
                "sequence",
                "declared_action",
                "random_evidence",
                "state_before_hash",
                "state_after_hash",
                "resolution_trace",
                "transition_record",
            },
        )
        self.assertEqual(step["sequence"], 1)
        self.assertEqual(
            step["declared_action"],
            {"action_id": "investigate-tracks", "actor_ref": "pc"},
        )
        self.assertEqual(step["random_evidence"], {"dice_terms": [3, 3, 3]})
        self.assertEqual(
            step["resolution_trace"],
            step["transition_record"]["trace"],
        )
        self.assertEqual(len(step["state_before_hash"]), 64)
        self.assertEqual(len(step["state_after_hash"]), 64)
        self.assertEqual(
            step["transition_record"]["format"],
            "dirps-scenario-progression-result.v1",
        )
        self.assertEqual(
            empty["source_identity"]["algorithm"],
            "sha256-canonical-json-v1",
        )
        self.assertEqual(len(empty["source_identity"]["digest"]), 64)

    def test_complete_success_session_replays_and_audits(self):
        history = self.complete_success()
        replay = replay_scenario_session_history(
            self.resolved, history, require_complete=True
        )
        self.assertEqual(history["format"], "dirps-session-history.v1")
        self.assertEqual([step["sequence"] for step in history["steps"]], [1, 2, 3, 4, 5])
        self.assertEqual(replay["steps_replayed"], 5)
        self.assertTrue(replay["complete"])
        self.assertEqual(replay["outcome"], "success")
        self.assertEqual(
            replay["final_state_hash"],
            history["steps"][-1]["state_after_hash"],
        )
        self.assertEqual(
            replay["final_state"],
            history["steps"][-1]["transition_record"]["state_after"],
        )
        self.assertTrue(
            all(
                record["format"] == "dirps-scenario-progression-result.v1"
                for record in replay["transition_records"]
            )
        )
        print("PASS dirps/scenario-01: Phase H full session history and replay")

    def test_complete_failure_session_replays(self):
        history = self.complete_failure()
        replay = replay_scenario_session_history(
            self.resolved, history, require_complete=True
        )
        self.assertEqual(replay["steps_replayed"], 4)
        self.assertTrue(replay["complete"])
        self.assertEqual(replay["outcome"], "failure")
        self.assertEqual(
            history["steps"][-1]["transition_record"]["progression"]["end_condition_id"],
            "missing-courier-failure",
        )

    def test_first_inconsistent_step_is_reported(self):
        history = self.complete_success()
        tampered = copy.deepcopy(history)
        tampered["steps"][1]["random_evidence"] = {"dice_terms": [6, 6, 6]}
        tampered["steps"][3]["state_after_hash"] = "0" * 64
        with self.assertRaisesRegex(ExecutionError, "Phase H divergence at step 2"):
            replay_scenario_session_history(
                self.resolved, tampered, require_complete=True
            )

    def test_state_hash_tampering_reports_exact_step(self):
        history = self.complete_success()
        tampered = copy.deepcopy(history)
        tampered["steps"][2]["state_after_hash"] = "0" * 64
        with self.assertRaisesRegex(ExecutionError, "Phase H divergence at step 3"):
            replay_scenario_session_history(
                self.resolved, tampered, require_complete=True
            )

    def test_source_identity_drift_fails_before_step_replay(self):
        history = self.complete_success()
        resolved = copy.deepcopy(self.resolved)
        resolved["scenario"]["name"] = "Drifted Missing Courier"
        with self.assertRaisesRegex(ExecutionError, "source identity mismatch"):
            replay_scenario_session_history(
                resolved, history, require_complete=True
            )

    def test_append_rejects_tampered_prior_history_without_mutation(self):
        history = create_scenario_session_history(self.resolved)
        history = self.append(
            history,
            "investigate-tracks",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )
        tampered = copy.deepcopy(history)
        tampered["steps"][0]["state_after_hash"] = "0" * 64
        before = copy.deepcopy(tampered)
        with self.assertRaisesRegex(ExecutionError, "Phase H divergence at step 1"):
            append_scenario_session_step(
                self.resolved,
                tampered,
                action_id="reassure-and-question",
                actor_ref="pc",
                random_inputs={"dice_terms": [3, 3, 3]},
            )
        self.assertEqual(tampered, before)

    def test_append_after_completion_fails_without_mutation(self):
        history = self.complete_failure()
        before = copy.deepcopy(history)
        with self.assertRaisesRegex(ExecutionError, "cannot append after scenario completion"):
            append_scenario_session_step(
                self.resolved,
                history,
                action_id="investigate-tracks",
                actor_ref="pc",
                random_inputs={"dice_terms": [3, 3, 3]},
            )
        self.assertEqual(history, before)

    def test_incomplete_history_requires_explicit_partial_replay(self):
        history = create_scenario_session_history(self.resolved)
        history = self.append(
            history,
            "investigate-tracks",
            "pc",
            {"dice_terms": [3, 3, 3]},
        )
        partial = replay_scenario_session_history(self.resolved, history)
        self.assertFalse(partial["complete"])
        with self.assertRaisesRegex(ExecutionError, "session history is incomplete"):
            replay_scenario_session_history(
                self.resolved, history, require_complete=True
            )

    def test_phase_h_promotes_replay_history_only_to_exercised(self):
        replay_spec = self.sidecar["proto_specs"]["replay_session_history"]
        self.assertEqual(replay_spec["status"], "exercised")
        self.assertEqual(replay_spec["candidate_for_dodge"], "not-yet-candidate")
        self.assertIn("phase_h_evidence", replay_spec)
        self.assertEqual(
            self.sidecar["phase_h_session_history_binding"]["session_format"],
            "dirps-session-history.v1",
        )

    def test_phase_h_binding_drift_fails_semantic_resolution(self):
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["phase_h_session_history_binding"]["append_policy"] = "mutable"
        with self.assertRaisesRegex(
            ResolutionError, "Phase H session-history binding"
        ):
            resolve_documents(self.dodge, self.canonical, sidecar, self.cfg)

    def test_resolved_phase_h_binding_drift_fails_runtime(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["proto_sidecar"]["phase_h_session_history_binding"][
            "divergence_policy"
        ] = "continue-after-divergence"
        with self.assertRaisesRegex(
            ExecutionError, "session-history binding is unsupported or drifted"
        ):
            create_scenario_session_history(resolved)


if __name__ == "__main__":
    unittest.main()
