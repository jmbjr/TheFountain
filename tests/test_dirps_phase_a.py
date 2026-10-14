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
    describe_contextual_skill,
    execute_attempt_skill,
    execute_contextual_skill,
    replay_attempt_skill,
    replay_contextual_skill,
)
from game_registry import scenario_config
from resolve_dirps_dodge import ResolutionError, resolve, resolve_documents


CONTEXT_REF = "roadside-tracks-tracking"


class DirpsPhaseAContextualSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())
        cls.resolved = resolve()

    def resolved_with_modifier(self, amount):
        canonical = copy.deepcopy(self.canonical)
        canonical["contextual_checks"][CONTEXT_REF]["modifiers"][0]["amount"] = amount
        return resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)

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

    def execute(self, resolved=None, terms=None, seed=None):
        return execute_contextual_skill(
            resolved if resolved is not None else self.resolved,
            actor_ref="pc",
            context_ref=CONTEXT_REF,
            dice_terms=terms,
            random_seed=seed,
        )

    def test_contextual_tracking_uses_source_owned_modifier(self):
        result = self.execute(terms=[3, 3, 4])
        self.assertEqual(result["input"]["context_ref"], CONTEXT_REF)
        self.assertEqual(result["target"]["skill_ref"], "tracking")
        self.assertEqual(result["target"]["base_target"], 12)
        self.assertEqual(result["target"]["modifier_total"], -2)
        self.assertEqual(result["target"]["effective_target"], 10)
        self.assertEqual(
            result["outcome"],
            {"classification": "success", "success": True, "margin": 0},
        )
        modifier = result["target"]["modifiers"][0]
        self.assertEqual(modifier["amount"], -2)
        self.assertEqual(modifier["source_ref"], "scenario-01-source")
        self.assertEqual(modifier["authority"], "provisional")
        self.assertEqual(modifier["provenance"], "prototype_assumption")
        self.assertEqual(
            result["trace"]["effective_target"]["modifier_rule_source_ref"],
            "gurps-lite",
        )
        self.assertEqual(
            result["trace"]["effective_target"]["modifier_rule_authority"],
            "authoritative",
        )
        self.assertEqual(
            result["trace"]["critical_resolution"]["source_ref"],
            "gurps-lite",
        )
        self.assertEqual(
            result["trace"]["critical_resolution"]["authority"],
            "authoritative",
        )
        self.assertEqual(result["state_delta"], [])
        print("PASS dirps/scenario-01: Phase A contextual skill check")

    def test_modifier_perturbation_flows_source_resolver_runtime(self):
        baseline = self.execute(terms=[3, 3, 4])
        changed = self.execute(
            resolved=self.resolved_with_modifier(-1),
            terms=[3, 3, 4],
        )
        self.assertEqual(baseline["target"]["modifier_total"], -2)
        self.assertEqual(baseline["target"]["effective_target"], 10)
        self.assertEqual(changed["target"]["modifier_total"], -1)
        self.assertEqual(changed["target"]["effective_target"], 11)
        self.assertEqual(baseline["outcome"]["margin"], 0)
        self.assertEqual(changed["outcome"]["margin"], 1)

    def test_modifier_authority_drift_fails_before_resolution(self):
        canonical = copy.deepcopy(self.canonical)
        modifier = canonical["contextual_checks"][CONTEXT_REF]["modifiers"][0]
        modifier["source_ref"] = "gurps-lite"
        modifier["authority"] = "authoritative"
        with self.assertRaisesRegex(ResolutionError, "source_ref must be scenario-01-source"):
            resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)

    def test_effective_target_below_three_fails_before_resolution(self):
        dodge = copy.deepcopy(self.dodge)
        canonical = copy.deepcopy(self.canonical)
        canonical["player_character"]["skills"]["tracking"] = 4
        pc = next(
            row
            for row in dodge["scenes"]["scenario-01-setup"]["instances"]
            if row["id"] == "pc"
        )
        pc["extensions"]["org.dirps.character"]["skills"]["tracking"] = 4
        with self.assertRaisesRegex(ResolutionError, "effective target must be at least 3"):
            resolve_documents(dodge, canonical, self.sidecar, self.cfg)

    def test_generated_dice_are_deterministic_and_recorded(self):
        first = self.execute(seed="phase-a-seed")
        second = self.execute(seed="phase-a-seed")
        self.assertEqual(first, second)
        self.assertEqual(first["random_evidence"]["kind"], "generated-seeded-dice-terms")
        self.assertEqual(first["random_evidence"]["algorithm"], "sha256-rejection-v1")
        self.assertEqual(first["random_evidence"]["seed"], "phase-a-seed")
        self.assertEqual(first["random_evidence"]["terms"], [2, 5, 6])
        self.assertEqual(first["random_evidence"]["total"], 13)
        self.assertEqual(
            first["outcome"],
            {"classification": "failure", "success": False, "margin": -3},
        )

    def test_generated_seed_perturbation_changes_preserved_evidence(self):
        first = self.execute(seed="phase-a-seed")
        changed = self.execute(seed="phase-a-seed-2")
        self.assertEqual(first["random_evidence"]["terms"], [2, 5, 6])
        self.assertEqual(changed["random_evidence"]["terms"], [1, 3, 6])
        self.assertEqual(changed["random_evidence"]["total"], 10)
        self.assertEqual(
            changed["outcome"],
            {"classification": "success", "success": True, "margin": 0},
        )

    def test_generated_record_replays_and_detects_seed_tampering(self):
        record = self.execute(seed="phase-a-seed")
        self.assertEqual(replay_contextual_skill(self.resolved, record), record)

        tampered = copy.deepcopy(record)
        tampered["random_evidence"]["seed"] = "phase-a-seed-2"
        with self.assertRaisesRegex(ExecutionError, "divergence"):
            replay_contextual_skill(self.resolved, tampered)

    def test_random_evidence_requires_exactly_one_mode(self):
        with self.assertRaisesRegex(ExecutionError, "either supplied dice terms or random_seed"):
            self.execute(terms=[2, 3, 4], seed="also-seeded")
        with self.assertRaisesRegex(ExecutionError, "requires supplied terms or random_seed"):
            self.execute()

    def test_critical_success_three_and_four_are_classified(self):
        roll_three = self.execute(terms=[1, 1, 1])
        roll_four = self.execute(terms=[1, 1, 2])
        self.assertEqual(roll_three["outcome"]["classification"], "critical-success")
        self.assertEqual(roll_four["outcome"]["classification"], "critical-success")
        self.assertTrue(roll_three["outcome"]["success"])
        self.assertTrue(roll_four["outcome"]["success"])

    def test_roll_five_requires_effective_target_fifteen_for_critical_success(self):
        ordinary = self.execute(terms=[1, 1, 3])
        high_skill = self.execute(
            resolved=self.resolved_with_tracking(17),
            terms=[1, 1, 3],
        )
        self.assertEqual(ordinary["target"]["effective_target"], 10)
        self.assertEqual(ordinary["outcome"]["classification"], "success")
        self.assertEqual(high_skill["target"]["effective_target"], 15)
        self.assertEqual(high_skill["outcome"]["classification"], "critical-success")

    def test_roll_six_requires_effective_target_sixteen_for_critical_success(self):
        target_fifteen = self.execute(
            resolved=self.resolved_with_tracking(17),
            terms=[1, 1, 4],
        )
        target_sixteen = self.execute(
            resolved=self.resolved_with_tracking(18),
            terms=[1, 1, 4],
        )
        self.assertEqual(target_fifteen["target"]["effective_target"], 15)
        self.assertEqual(target_fifteen["outcome"]["classification"], "success")
        self.assertEqual(target_sixteen["target"]["effective_target"], 16)
        self.assertEqual(target_sixteen["outcome"]["classification"], "critical-success")

    def test_roll_eighteen_is_always_critical_failure(self):
        result = self.execute(
            resolved=self.resolved_with_tracking(30),
            terms=[6, 6, 6],
        )
        self.assertEqual(result["target"]["effective_target"], 28)
        self.assertEqual(result["outcome"]["classification"], "critical-failure")
        self.assertFalse(result["outcome"]["success"])

    def test_roll_seventeen_boundary_uses_effective_target_sixteen(self):
        under = self.execute(terms=[5, 6, 6])
        high = self.execute(
            resolved=self.resolved_with_tracking(18),
            terms=[5, 6, 6],
        )
        self.assertEqual(under["target"]["effective_target"], 10)
        self.assertEqual(under["outcome"]["classification"], "critical-failure")
        self.assertEqual(high["target"]["effective_target"], 16)
        self.assertEqual(high["outcome"]["classification"], "failure")
        self.assertFalse(high["outcome"]["success"])

    def test_ten_over_effective_target_is_critical_failure(self):
        result = self.execute(
            resolved=self.resolved_with_tracking(8),
            terms=[5, 5, 6],
        )
        self.assertEqual(result["target"]["effective_target"], 6)
        self.assertEqual(result["random_evidence"]["total"], 16)
        self.assertEqual(result["outcome"]["margin"], -10)
        self.assertEqual(result["outcome"]["classification"], "critical-failure")

    def test_capability_exposes_context_rng_and_critical_contract(self):
        capability = describe_contextual_skill(self.resolved)
        self.assertIn(CONTEXT_REF, capability["contextual_checks"])
        self.assertEqual(
            capability["target"]["modifier_policy"],
            "sum-resolved-context-modifiers",
        )
        self.assertEqual(
            capability["target"]["supported_domain"],
            {"minimum": 3, "maximum": None},
        )
        self.assertEqual(
            capability["dice"]["random_evidence"]["generated"]["algorithm"],
            "sha256-rejection-v1",
        )
        self.assertEqual(
            capability["critical_resolution"]["rule_source_ref"],
            "gurps-lite",
        )

    def test_record_versions_are_explicit_and_not_confused(self):
        legacy = execute_attempt_skill(
            self.resolved,
            actor_ref="pc",
            skill_ref="tracking",
            dice_terms=[2, 3, 4],
        )
        current = self.execute(terms=[2, 3, 4])

        self.assertEqual(legacy["format"], "dirps-execution-result.v1")
        self.assertEqual(
            legacy["result_scope"],
            "binary-success-and-margin-only",
        )
        self.assertNotIn("classification", legacy["outcome"])

        self.assertEqual(current["format"], "dirps-execution-result.v2")
        self.assertEqual(
            current["result_scope"],
            "success-failure-margin-and-critical-classification",
        )
        self.assertIn("classification", current["outcome"])

        self.assertEqual(replay_attempt_skill(self.resolved, legacy), legacy)
        self.assertEqual(replay_contextual_skill(self.resolved, current), current)

        with self.assertRaisesRegex(
            ExecutionError,
            r"v1 is a legacy G5 record, not a Phase A/v2 record",
        ):
            replay_contextual_skill(self.resolved, legacy)

        with self.assertRaisesRegex(
            ExecutionError,
            r"v2 is a Phase A record, not a legacy G5/v1 record",
        ):
            replay_attempt_skill(self.resolved, current)

    def test_accepted_g5_binding_remains_v1_and_phase_a_binding_is_v2(self):
        sidecar = self.resolved["proto_sidecar"]
        legacy = sidecar["g5_execution_bindings"]["attempt-skill"]
        current = sidecar["phase_a_execution_bindings"]["attempt-skill"]

        self.assertEqual(legacy["result_format"], "dirps-execution-result.v1")
        self.assertEqual(
            legacy["effective_target"]["supported_domain"],
            {"minimum": 4, "maximum": 16},
        )
        self.assertEqual(legacy["effective_target"]["modifier_policy"], "unsupported")

        self.assertEqual(current["result_format"], "dirps-execution-result.v2")
        self.assertEqual(current["effective_target"]["minimum"], 3)
        self.assertEqual(
            current["effective_target"]["modifier_policy"],
            "sum-resolved-context-modifiers",
        )

    def test_phase_a_proto_gaps_remain_non_candidates(self):
        specs = self.resolved["proto_sidecar"]["proto_specs"]
        for proto_id in ("derived_values", "expressions"):
            self.assertEqual(
                specs[proto_id]["candidate_for_dodge"],
                "not-yet-candidate",
            )
        self.assertEqual(specs["replay_session_history"]["status"], "exercised")\n        self.assertEqual(specs["replay_session_history"]["candidate_for_dodge"], "not-yet-candidate")


if __name__ == "__main__":
    unittest.main()
