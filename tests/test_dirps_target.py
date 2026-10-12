#!/usr/bin/env python3
import copy
import inspect
import json
import sys
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dirps_debug_target
from dirps_debug_target import execute_target, inspect_target
from dirps_runtime import ExecutionError, describe_attempt_skill
from game_registry import scenario_config
from resolve_dirps_dodge import resolve, resolve_documents


class DirpsTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())
        cls.resolved = resolve()

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

    def test_inspection_exposes_runtime_capability_and_resolved_choices(self):
        view = inspect_target(self.resolved)
        self.assertEqual(view["status"], "ready")
        self.assertEqual(view["scenario"]["id"], "scenario-01")
        capability = view["capability"]
        self.assertEqual(
            capability["semantic_path"],
            {"action_ref": "attempt-skill", "procedure_ref": "success-roll"},
        )
        self.assertEqual(
            capability["target"]["supported_domain"],
            {"minimum": 4, "maximum": 16},
        )
        self.assertEqual(capability["dice"]["count"], 3)
        self.assertEqual(capability["dice"]["sides"], 6)
        pc = next(row for row in capability["actors"] if row["id"] == "pc")
        self.assertEqual(pc["skills"]["tracking"], 12)
        self.assertEqual(pc["character_provenance"], "prototype_assumption")

    def test_successful_target_consumes_real_runtime_result(self):
        view = execute_target(
            self.resolved,
            actor_ref="pc",
            skill_ref="tracking",
            dice_terms=[2, 3, 4],
        )
        self.assertEqual(view["status"], "ok")
        result = view["execution"]
        self.assertEqual(result["target"]["effective_target"], 12)
        self.assertEqual(result["random_evidence"]["terms"], [2, 3, 4])
        self.assertEqual(result["random_evidence"]["total"], 9)
        self.assertEqual(result["outcome"], {"success": True, "margin": 3})
        self.assertEqual(result["state_delta"], [])
        print("PASS dirps/scenario-01: debug-cli target consumes DIRPS runtime")

    def test_prototype_skill_perturbation_flows_source_to_target(self):
        baseline = execute_target(
            self.resolved,
            actor_ref="pc",
            skill_ref="tracking",
            dice_terms=[4, 4, 3],
        )
        changed = execute_target(
            self.resolved_with_tracking(10),
            actor_ref="pc",
            skill_ref="tracking",
            dice_terms=[4, 4, 3],
        )
        self.assertEqual(baseline["execution"]["target"]["effective_target"], 12)
        self.assertEqual(baseline["execution"]["outcome"], {"success": True, "margin": 1})
        self.assertEqual(changed["execution"]["target"]["effective_target"], 10)
        self.assertEqual(changed["execution"]["outcome"], {"success": False, "margin": -1})

    def test_adapter_passes_runtime_result_through_without_recomputing(self):
        fake_result = {
            "format": "fake-runtime-result",
            "target": {"effective_target": 999},
            "random_evidence": {"terms": [1], "total": 777},
            "outcome": {"success": False, "margin": 12345},
            "trace": {"runtime_owned": True},
            "state_delta": ["fake"],
        }

        def fake_execute(*args, **kwargs):
            return fake_result

        view = execute_target(
            self.resolved,
            actor_ref="presented-actor",
            skill_ref="presented-skill",
            dice_terms=[42],
            runtime_execute=fake_execute,
        )
        self.assertEqual(view["status"], "ok")
        self.assertIs(view["execution"], fake_result)
        self.assertEqual(view["execution"]["random_evidence"]["total"], 777)
        self.assertEqual(view["execution"]["target"]["effective_target"], 999)
        self.assertEqual(view["execution"]["outcome"]["margin"], 12345)

    def test_adapter_uses_runtime_description_without_reconstructing_capability(self):
        fake_capability = {
            "scenario": {"id": "runtime-scenario", "name": "Runtime supplied"},
            "semantic_path": {"action_ref": "runtime-action", "procedure_ref": "runtime-procedure"},
            "target": {"supported_domain": {"minimum": -999, "maximum": 999}},
            "dice": {"count": 91, "sides": 37},
            "actors": [{"id": "runtime-actor", "skills": {"runtime-skill": 222}}],
            "trace": {"runtime_owned": True},
        }
        view = inspect_target(
            self.resolved,
            runtime_describe=lambda resolved: fake_capability,
        )
        self.assertIs(view["capability"], fake_capability)
        self.assertEqual(view["scenario"], fake_capability["scenario"])

    def test_out_of_domain_runtime_error_is_visible_not_guessed(self):
        view = execute_target(
            self.resolved_with_tracking(17),
            actor_ref="pc",
            skill_ref="tracking",
            dice_terms=[5, 6, 6],
        )
        self.assertEqual(view["status"], "error")
        self.assertNotIn("execution", view)
        self.assertIn("outside supported G5 domain", view["error"]["message"])

    def test_malformed_dice_runtime_error_is_visible_not_guessed(self):
        view = execute_target(
            self.resolved,
            actor_ref="pc",
            skill_ref="tracking",
            dice_terms=[1, 2],
        )
        self.assertEqual(view["status"], "error")
        self.assertNotIn("execution", view)
        self.assertIn("exactly 3 terms", view["error"]["message"])

    def test_missing_skill_runtime_error_is_visible_not_guessed(self):
        view = execute_target(
            self.resolved,
            actor_ref="pc",
            skill_ref="not-a-skill",
            dice_terms=[2, 3, 4],
        )
        self.assertEqual(view["status"], "error")
        self.assertNotIn("execution", view)
        self.assertIn("required resolved skill target is missing", view["error"]["message"])

    def test_unavailable_actor_runtime_error_is_visible_not_guessed(self):
        view = execute_target(
            self.resolved,
            actor_ref="not-an-actor",
            skill_ref="tracking",
            dice_terms=[2, 3, 4],
        )
        self.assertEqual(view["status"], "error")
        self.assertNotIn("execution", view)
        self.assertIn("actor is not available", view["error"]["message"])

    def test_registered_cli_entry_point_executes(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "dirps_debug_target.py"),
                "--actor",
                "pc",
                "--skill",
                "tracking",
                "--dice",
                "2",
                "3",
                "4",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        view = json.loads(proc.stdout)
        self.assertEqual(view["status"], "ok")
        self.assertEqual(view["execution"]["random_evidence"]["total"], 9)
        self.assertEqual(view["execution"]["outcome"], {"success": True, "margin": 3})

    def test_target_exposes_all_three_authority_layers_from_runtime(self):
        view = execute_target(
            self.resolved,
            actor_ref="pc",
            skill_ref="tracking",
            dice_terms=[2, 3, 4],
        )
        trace = view["execution"]["trace"]
        self.assertEqual(trace["action"]["authority"], "authoritative")
        self.assertEqual(trace["execution_binding"]["authority"], "provisional")
        self.assertEqual(trace["effective_target"]["authority"], "provisional")
        self.assertEqual(
            trace["effective_target"]["character_provenance"],
            "prototype_assumption",
        )
        self.assertEqual(
            set(trace["sources"]),
            {"gurps-lite", "dirps-proto", "scenario-01-source"},
        )

    def test_target_source_contains_no_private_gameplay_literals(self):
        source = inspect.getsource(dirps_debug_target)
        forbidden_literals = [
            '"attempt-skill"',
            '"success-roll"',
            '"tracking"',
            '"gurps-lite"',
            '"dirps-proto"',
            '"scenario-01-source"',
            '"prototype_assumption"',
            '"minimum": 4',
            '"maximum": 16',
        ]
        for literal in forbidden_literals:
            self.assertNotIn(literal, source)

    def test_target_offers_no_other_gameplay_action_surface(self):
        view = inspect_target(self.resolved)
        serialized = json.dumps(view, sort_keys=True)
        self.assertNotIn('"attack"', serialized)
        self.assertNotIn('"recover"', serialized)
        self.assertNotIn("damage", serialized.lower())
        self.assertNotIn("active defense", serialized.lower())


if __name__ == "__main__":
    unittest.main()
