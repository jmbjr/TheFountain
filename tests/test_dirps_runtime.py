#!/usr/bin/env python3
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dirps_runtime import ExecutionError, execute_attempt_skill, replay_attempt_skill
from game_registry import scenario_config
from resolve_dirps_dodge import resolve, resolve_documents


class DirpsRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())
        cls.resolved = resolve()

    def execute(self, resolved=None, terms=None, skill_ref="tracking"):
        return execute_attempt_skill(
            resolved if resolved is not None else self.resolved,
            actor_ref="pc",
            skill_ref=skill_ref,
            dice_terms=[2, 3, 4] if terms is None else terms,
        )

    def resolved_with_tracking(self, level):
        dodge = copy.deepcopy(self.dodge)
        canonical = copy.deepcopy(self.canonical)
        canonical["player_character"]["skills"]["tracking"] = level
        pc = next(
            row
            for row in dodge["scenes"]["scenario-01-setup"]["instances"]
            if row["id"] == "pc"
        )
        pc["extensions"]["org.dirps.character"]["skills"]["tracking"] = level
        return resolve_documents(dodge, canonical, self.sidecar, self.cfg)

    def test_known_success_preserves_structured_evidence(self):
        result = self.execute()
        self.assertEqual(result["semantic_path"], {
            "action_ref": "attempt-skill",
            "procedure_ref": "success-roll",
        })
        self.assertEqual(result["result_scope"], "success-failure-margin-and-critical-classification")
        self.assertEqual(result["target"]["skill_ref"], "tracking")
        self.assertEqual(
            result["target"]["supported_domain"],
            {"minimum": 3, "maximum": None},
        )
        self.assertEqual(result["target"]["effective_target"], 12)
        self.assertEqual(result["random_evidence"]["terms"], [2, 3, 4])
        self.assertEqual(result["random_evidence"]["total"], 9)
        self.assertEqual(result["outcome"], {"classification": "success", "success": True, "margin": 3})
        self.assertEqual(result["trace"]["action"]["source_ref"], "gurps-lite")
        self.assertEqual(result["trace"]["procedure"]["source_ref"], "gurps-lite")
        self.assertEqual(result["trace"]["action"]["authority"], "authoritative")
        self.assertEqual(result["trace"]["procedure"]["authority"], "authoritative")
        self.assertEqual(
            result["trace"]["execution_binding"],
            {
                "ref": "proto_sidecar.g5_execution_bindings.attempt-skill",
                "source_ref": "dirps-proto",
                "authority": "provisional",
            },
        )
        self.assertEqual(result["trace"]["effective_target"]["actor_ref"], "pc")
        self.assertEqual(result["trace"]["effective_target"]["skill_ref"], "tracking")
        self.assertEqual(result["trace"]["effective_target"]["base_value"], 12)
        self.assertEqual(result["trace"]["effective_target"]["modifier_total"], 0)
        self.assertEqual(result["trace"]["effective_target"]["value"], 12)
        self.assertEqual(
            result["trace"]["effective_target"]["target_source_ref"],
            "scenario-01-source",
        )
        self.assertEqual(
            result["trace"]["effective_target"]["target_authority"],
            "provisional",
        )
        self.assertEqual(
            result["trace"]["effective_target"]["character_provenance"],
            "prototype_assumption",
        )
        self.assertEqual(
            result["trace"]["effective_target"]["modifier_rule_source_ref"],
            "gurps-lite",
        )
        self.assertEqual(
            set(result["trace"]["sources"]),
            {"gurps-lite", "dirps-proto", "scenario-01-source"},
        )
        self.assertEqual(
            result["trace"]["sources"]["gurps-lite"]["authority"],
            "authoritative",
        )
        self.assertEqual(
            result["trace"]["sources"]["dirps-proto"]["authority"],
            "provisional",
        )
        self.assertEqual(
            result["trace"]["sources"]["scenario-01-source"]["authority"],
            "provisional",
        )
        self.assertEqual(result["state_delta"], [])
        print("PASS dirps/scenario-01: executable attempt-skill -> success-roll")

    def test_known_failure(self):
        result = self.execute(terms=[5, 5, 5])
        self.assertEqual(result["random_evidence"]["total"], 15)
        self.assertEqual(result["outcome"], {"classification": "failure", "success": False, "margin": -3})

    def test_same_inputs_and_evidence_are_deterministic(self):
        first = self.execute(terms=[1, 4, 6])
        second = self.execute(terms=[1, 4, 6])
        self.assertEqual(first, second)

    def test_die_evidence_perturbation_changes_result(self):
        success = self.execute(terms=[4, 4, 4])
        failure = self.execute(terms=[4, 4, 5])
        self.assertEqual(success["random_evidence"]["total"], 12)
        self.assertTrue(success["outcome"]["success"])
        self.assertEqual(success["outcome"]["margin"], 0)
        self.assertEqual(failure["random_evidence"]["total"], 13)
        self.assertFalse(failure["outcome"]["success"])
        self.assertEqual(failure["outcome"]["margin"], -1)

    def test_prototype_skill_perturbation_flows_through_resolver_to_runtime(self):
        baseline = self.execute(terms=[4, 4, 3])
        self.assertEqual(baseline["target"]["effective_target"], 12)
        self.assertTrue(baseline["outcome"]["success"])
        self.assertEqual(baseline["outcome"]["margin"], 1)

        changed_resolved = self.resolved_with_tracking(10)
        changed = self.execute(resolved=changed_resolved, terms=[4, 4, 3])
        self.assertEqual(changed["target"]["effective_target"], 10)
        self.assertFalse(changed["outcome"]["success"])
        self.assertEqual(changed["outcome"]["margin"], -1)

    def test_unmodified_target_three_is_supported(self):
        resolved = copy.deepcopy(self.resolved)
        pc = next(row for row in resolved["scene"]["instances"] if row["id"] == "pc")
        pc["character"]["skills"]["tracking"] = 3
        result = self.execute(resolved=resolved, terms=[1, 1, 2])
        self.assertEqual(result["target"]["effective_target"], 3)
        self.assertEqual(result["outcome"]["classification"], "critical-success")
        self.assertTrue(result["outcome"]["success"])

    def test_unmodified_target_two_fails_visibly(self):
        resolved = copy.deepcopy(self.resolved)
        pc = next(row for row in resolved["scene"]["instances"] if row["id"] == "pc")
        pc["character"]["skills"]["tracking"] = 2
        with self.assertRaisesRegex(
            ExecutionError, r"below minimum rollable target 3"
        ):
            self.execute(resolved=resolved, terms=[1, 1, 1])

    def test_high_unmodified_target_uses_critical_failure_rules(self):
        resolved = self.resolved_with_tracking(17)
        result = self.execute(resolved=resolved, terms=[5, 6, 6])
        self.assertEqual(result["target"]["effective_target"], 17)
        self.assertEqual(result["random_evidence"]["total"], 17)
        self.assertEqual(
            result["outcome"],
            {"classification": "failure", "success": False, "margin": 0},
        )

    def test_runtime_does_not_mutate_resolved_model(self):
        resolved = copy.deepcopy(self.resolved)
        before = copy.deepcopy(resolved)
        self.execute(resolved=resolved)
        self.assertEqual(resolved, before)

    def test_wrong_number_of_dice_fails(self):
        with self.assertRaisesRegex(ExecutionError, "exactly 3 terms"):
            self.execute(terms=[3, 4])

    def test_out_of_range_die_fails(self):
        with self.assertRaisesRegex(ExecutionError, "outside 1..6"):
            self.execute(terms=[2, 3, 7])

    def test_unavailable_action_fails(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["scenario"]["action_refs"].remove("attempt-skill")
        with self.assertRaisesRegex(ExecutionError, "action is not available"):
            self.execute(resolved=resolved)

    def test_execution_binding_drift_fails(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["proto_sidecar"]["g5_execution_bindings"]["attempt-skill"]["target_input"] = "attribute_ref"
        with self.assertRaisesRegex(ExecutionError, "runtime input binding"):
            self.execute(resolved=resolved)

    def test_wrong_procedure_binding_fails(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["rules"]["actions"]["attempt-skill"]["procedure_ref"] = "recovery-check"
        with self.assertRaisesRegex(ExecutionError, "must resolve procedure success-roll"):
            self.execute(resolved=resolved)

    def test_missing_required_skill_target_fails(self):
        resolved = copy.deepcopy(self.resolved)
        pc = next(row for row in resolved["scene"]["instances"] if row["id"] == "pc")
        del pc["character"]["skills"]["tracking"]
        with self.assertRaisesRegex(ExecutionError, "required resolved skill target is missing"):
            self.execute(resolved=resolved)

    def test_unconscious_actor_cannot_attempt_skill(self):
        resolved = copy.deepcopy(self.resolved)
        pc = next(row for row in resolved["scene"]["instances"] if row["id"] == "pc")
        pc["state"]["unconscious"] = True
        with self.assertRaisesRegex(ExecutionError, "actor is unconscious"):
            self.execute(resolved=resolved)

    def test_malformed_executable_dice_contract_fails(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["proto_sidecar"]["proto_specs"]["dice_resolution"]["proposed_shape"]["randomizer"]["sides"] = 8
        # Force an unsupported combine to prove the runtime refuses drift in
        # executable proto authority rather than inventing behavior.
        resolved["proto_sidecar"]["proto_specs"]["dice_resolution"]["proposed_shape"]["randomizer"]["combine"] = "max"
        with self.assertRaisesRegex(ExecutionError, "combine=sum"):
            self.execute(resolved=resolved)

    def test_record_replay_matches_and_detects_divergence(self):
        record = self.execute(terms=[2, 5, 5])
        self.assertEqual(replay_attempt_skill(self.resolved, record), record)

        tampered = copy.deepcopy(record)
        tampered["outcome"]["margin"] = 99
        with self.assertRaisesRegex(ExecutionError, "divergence"):
            replay_attempt_skill(self.resolved, tampered)

    def test_record_replay_detects_authority_trace_tampering(self):
        record = self.execute(terms=[2, 5, 5])
        tampered = copy.deepcopy(record)
        tampered["trace"]["execution_binding"]["authority"] = "authoritative"
        with self.assertRaisesRegex(ExecutionError, "divergence"):
            replay_attempt_skill(self.resolved, tampered)

        tampered = copy.deepcopy(record)
        tampered["trace"]["effective_target"]["character_provenance"] = "authoritative"
        with self.assertRaisesRegex(ExecutionError, "divergence"):
            replay_attempt_skill(self.resolved, tampered)


if __name__ == "__main__":
    unittest.main()
