#!/usr/bin/env python3
import copy
import inspect
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dirps_web_target
from dirps_runtime import (
    append_scenario_session_step,
    create_scenario_session_history,
    describe_scenario,
    replay_scenario_session_history,
)
from dirps_web_target import execute_web_target, inspect_web_target
from game_registry import scenario_config
from resolve_dirps_dodge import resolve


class DirpsPhaseIWebTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.resolved = resolve()
        cls.web_js = (ROOT / "src/renderers/dirps-web.js").read_text()
        cls.web_html = (ROOT / "dirps/index.html").read_text()
        cls.root_html = (ROOT / "index.html").read_text()

    def test_initial_web_view_is_runtime_described(self):
        view = inspect_web_target(self.resolved)
        history = create_scenario_session_history(self.resolved)
        replay = replay_scenario_session_history(
            self.resolved, history, require_complete=False
        )
        expected = describe_scenario(self.resolved, replay["final_state"])

        self.assertEqual(
            view["target"],
            {
                "id": "dirps-web",
                "format": "dirps-web-target.v1",
                "kind": "web",
            },
        )
        self.assertEqual(view["status"], "ready")
        self.assertEqual(view["scenario"], expected)
        self.assertEqual(view["history"], history)
        self.assertEqual(view["history_summary"]["steps"], 0)
        self.assertEqual(view["characters"][0]["name"], "Rook")
        resolved_pc = next(
            row for row in self.resolved["scene"]["instances"] if row["id"] == "pc"
        )
        self.assertEqual(view["characters"][0]["state"], resolved_pc["state"])
        self.assertEqual(
            view["characters"][0]["state"],
            {
                "st": 10,
                "dx": 11,
                "iq": 11,
                "ht": 10,
                "hit-points": 10,
                "fatigue": 10,
                "stunned": False,
                "unconscious": False,
                "consciousness-check-required": False,
            },
        )
        self.assertEqual(
            view["scenario"]["available_actions"],
            expected["available_actions"],
        )

    def test_web_execution_is_phase_h_append_result_with_seed_evidence(self):
        history = create_scenario_session_history(self.resolved)
        action = describe_scenario(
            self.resolved,
            replay_scenario_session_history(self.resolved, history)["final_state"],
        )["available_actions"][0]
        seed = "phase-i-web-seed"

        direct = append_scenario_session_step(
            self.resolved,
            history,
            action_id=action["id"],
            actor_ref=action["actor_ref"],
            random_inputs={"random_seed": seed},
        )
        view = execute_web_target(
            self.resolved,
            history,
            action_id=action["id"],
            actor_ref=action["actor_ref"],
            random_seed=seed,
        )

        self.assertEqual(view["history"], direct)
        self.assertEqual(view["history_summary"]["steps"], 1)
        self.assertEqual(
            view["latest_execution"],
            direct["steps"][-1]["transition_record"],
        )
        self.assertEqual(
            view["latest_execution"]["random_inputs"],
            {"random_seed": seed},
        )
        self.assertEqual(
            view["latest_execution"]["mechanic_result"]["skill_resolution"][
                "random_evidence"
            ]["algorithm"],
            "sha256-rejection-v1",
        )

    def test_web_target_can_drive_complete_scenario_without_owning_choices(self):
        view = inspect_web_target(self.resolved)
        for index in range(1, 8):
            if view["status"] == "complete":
                break
            actions = view["scenario"]["available_actions"]
            self.assertTrue(actions)
            action = actions[0]
            view = execute_web_target(
                self.resolved,
                view["history"],
                action_id=action["id"],
                actor_ref=action["actor_ref"],
                random_seed=f"phase-i-step-{index}",
            )

        self.assertEqual(view["status"], "complete")
        self.assertIn(view["scenario"]["progress"]["outcome"], {"success", "failure"})
        replay = replay_scenario_session_history(
            self.resolved,
            view["history"],
            require_complete=True,
        )
        self.assertEqual(replay["final_state_hash"], view["history_summary"]["final_state_hash"])
        print("PASS dirps/scenario-01: Phase I player-facing Web target consumes shared runtime")

    def test_web_error_is_visible_and_preserves_input_history(self):
        history = create_scenario_session_history(self.resolved)
        before = copy.deepcopy(history)
        view = execute_web_target(
            self.resolved,
            history,
            action_id="unavailable-action",
            actor_ref="pc",
            random_seed="phase-i-error",
        )
        self.assertEqual(view["status"], "error")
        self.assertEqual(view["history"], before)
        self.assertEqual(history, before)
        self.assertIn("unavailable", view["error"]["message"])

    def test_web_adapter_contains_no_scenario_gameplay_literals(self):
        source = inspect.getsource(dirps_web_target)
        for literal in (
            '"roadside-tracks"',
            '"frightened-witness"',
            '"washed-out-path"',
            '"bandit-scout"',
            '"investigate-tracks"',
            '"reassure-and-question"',
            '"cross-washed-out-path"',
            '"strike-bandit-scout"',
            '"resolve-bandit-next-turn"',
        ):
            self.assertNotIn(literal, source)

    def test_javascript_is_presentation_and_python_bootstrap_only(self):
        self.assertIn(
            'https://cdn.jsdelivr.net/pyodide/v0.29.1/full/pyodide.mjs',
            self.web_js,
        )
        for path in (
            "../tools/game_registry.py",
            "../tools/dirps_semantic_validation.py",
            "../tools/resolve_dirps_dodge.py",
            "../tools/dirps_runtime.py",
            "../tools/dirps_web_target.py",
            "../game/dirps/game.json",
            "../game/dirps/dodge/dirps-scenario-01.dodge.v0.2.1.json",
            "../game/dirps/scenarios/scenario-01/scenario.json",
            "../game/dirps/sidecars/dirps.proto.sidecar.v0.1.json",
        ):
            self.assertIn(path, self.web_js)

        for literal in (
            "roadside-tracks",
            "frightened-witness",
            "washed-out-path",
            "bandit-scout",
            "investigate-tracks",
            "reassure-and-question",
            "cross-washed-out-path",
            "strike-bandit-scout",
            "resolve-bandit-next-turn",
            "attack_terms",
            "defense_terms",
            "damage_terms",
            "consciousness_terms",
            "stun_terms",
        ):
            self.assertNotIn(literal, self.web_js)

        self.assertIn('{"random_seed": random_seed}', inspect.getsource(dirps_web_target))
        self.assertIn("character.state || {}", self.web_js)
        self.assertIn("stateRow.dataset.stateKey = key", self.web_js)
        self.assertNotIn("Math.random", self.web_js)

    def test_static_page_exposes_player_and_debug_views(self):
        for element_id in (
            'id="runtimeStatus"',
            'id="encounterTitle"',
            'id="availableActions"',
            'id="character"',
            'id="scenarioState"',
            'id="lastResolution"',
            'id="provenance"',
            'id="history"',
            'id="debugView"',
        ):
            self.assertIn(element_id, self.web_html)
        self.assertIn('../src/renderers/dirps-web.js', self.web_html)
        self.assertIn('href="dirps/"', self.root_html)

    def test_game_registry_declares_both_debug_and_web_targets(self):
        descriptor = json.loads((ROOT / "game/dirps/game.json").read_text())
        targets = descriptor["scenarios"]["scenario-01"]["generated_targets"]
        self.assertEqual(targets["debug-cli"], "../../tools/dirps_debug_target.py")
        self.assertEqual(targets["web"], "../../dirps/index.html")


if __name__ == "__main__":
    unittest.main()
