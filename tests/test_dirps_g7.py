#!/usr/bin/env python3
"""Whole-system DIRPS G7 convergence evidence.

This suite does not add gameplay. It audits the accepted Phase A-I system as one
reference candidate and guards the scope/maturity claims that make G7 meaningful.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dirps_runtime import (
    append_scenario_session_step,
    create_scenario_session_history,
    replay_scenario_session_history,
)
from game_registry import discover_games, scenario_config
from resolve_dirps_dodge import resolve


class DirpsG7ReferenceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.game = discover_games()["dirps"]["descriptor"]
        cls.scenario = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())
        cls.resolved = resolve()

    def complete_success(self):
        history = create_scenario_session_history(self.resolved)
        for action_id, actor_ref, random_inputs in (
            ("investigate-tracks", "pc", {"dice_terms": [3, 3, 3]}),
            ("reassure-and-question", "pc", {"dice_terms": [3, 3, 3]}),
            ("cross-washed-out-path", "pc", {"dice_terms": [3, 3, 3]}),
            ("strike-bandit-scout", "pc", {"attack_terms": [1, 1, 1]}),
            (
                "resolve-bandit-next-turn",
                "bandit-scout",
                {"consciousness_terms": [6, 6, 6]},
            ),
        ):
            history = append_scenario_session_step(
                self.resolved,
                history,
                action_id=action_id,
                actor_ref=actor_ref,
                random_inputs=random_inputs,
            )
        return history

    def test_registry_declares_reference_candidate(self):
        self.assertEqual(self.game["status"], "active")
        self.assertEqual(self.cfg["status"], "reference")
        self.assertEqual(self.cfg["conformance"]["maturity"], "G7")
        self.assertEqual(
            self.cfg["generated_targets"],
            {
                "debug-cli": "../../tools/dirps_debug_target.py",
                "web": "../../dirps/index.html",
            },
        )
        self.assertTrue(self.cfg["conformance"]["resolver"].is_file())
        self.assertTrue(all(path.is_file() for path in self.cfg["sidecars"]))

    def test_every_canonical_encounter_claim_executes_in_one_audited_run(self):
        history = self.complete_success()
        replay = replay_scenario_session_history(
            self.resolved, history, require_complete=True
        )
        transitions = [
            step["transition_record"]
            for step in history["steps"]
        ]

        canonical = self.scenario["encounters"]
        self.assertEqual(
            [record["encounter_ref"] for record in transitions[:4]],
            [encounter["id"] for encounter in canonical],
        )
        self.assertEqual(
            [encounter["type"] for encounter in canonical],
            ["investigation", "social", "environmental", "combat"],
        )

        format_by_type = {
            "investigation": "dirps-encounter-result.v1",
            "social": "dirps-social-encounter-result.v1",
            "environmental": "dirps-environment-encounter-result.v1",
            "combat": "dirps-combat-exchange-result.v1",
        }
        for encounter, record in zip(canonical, transitions[:4]):
            self.assertEqual(
                record["mechanic_result"]["format"],
                format_by_type[encounter["type"]],
            )
            self.assertEqual(
                record["trace"]["canonical_order"]["source_ref"],
                "scenario-01-source",
            )
            self.assertEqual(
                record["trace"]["progression_binding"]["source_ref"],
                "dirps-proto",
            )
            self.assertEqual(
                record["trace"]["mechanic_result_format"],
                record["mechanic_result"]["format"],
            )

        recovery = transitions[4]
        self.assertEqual(recovery["encounter_ref"], "bandit-scout")
        self.assertEqual(recovery["step"], "recovery")
        self.assertEqual(
            recovery["mechanic_result"]["format"],
            "dirps-recovery-result.v1",
        )

        self.assertTrue(replay["complete"])
        self.assertEqual(replay["outcome"], "success")
        self.assertEqual(replay["steps_replayed"], 5)
        self.assertEqual(
            replay["final_state_hash"],
            history["steps"][-1]["state_after_hash"],
        )
        self.assertTrue(
            all(
                step["random_evidence"]
                == step["transition_record"]["random_inputs"]
                for step in history["steps"]
            )
        )
        print(
            "PASS dirps/scenario-01: G7 whole-system reference convergence audit"
        )

    def test_reference_claim_remains_bounded_and_unsupported_scope_explicit(self):
        unsupported = set(self.scenario["progression"]["unsupported"])
        self.assertEqual(
            unsupported,
            {
                "skipping or reordering encounters outside the canonical encounter_order",
                "repeating an already-resolved encounter",
                "continuing after a terminal scenario outcome",
                "long-term recovery after the bandit scout becomes unconscious",
            },
        )
        self.assertIn(
            "Unsupported or uncertain rules fail visibly rather than being guessed.",
            self.scenario["artifact_note"]["acceptance"],
        )
        self.assertIn(
            "Long-term unconscious recovery/healing remains explicitly unsupported.",
            self.scenario["artifact_note"]["acceptance_note"],
        )

    def test_proto_maturity_is_evidence_backed_and_conservative(self):
        specs = self.sidecar["proto_specs"]
        self.assertTrue(specs)
        self.assertEqual(
            {
                proto_id
                for proto_id, spec in specs.items()
                if spec["status"] == "suspected"
            },
            {"visibility_and_secret_state"},
        )
        self.assertEqual(
            {
                proto_id
                for proto_id, spec in specs.items()
                if spec["status"] == "exercised"
            },
            set(specs) - {"visibility_and_secret_state"},
        )
        self.assertTrue(
            all(
                spec["candidate_for_dodge"] == "not-yet-candidate"
                for spec in specs.values()
            )
        )

    def test_aggregate_compatibility_audit_describes_current_g7_candidate(self):
        audit = (
            ROOT / "game/dirps/docs/compatibility-audit.md"
        ).read_text()
        current_state = audit.split("| Requirement |", 1)[0]
        self.assertIn("G7 — Reference candidate under Phase J", current_state)
        self.assertIn(
            "currently merged `main` remains **G6 — Targeted** until #188",
            current_state,
        )
        self.assertNotIn(
            "The candidate remains **G6 — Targeted** and has now reached gameplay Phase G",
            current_state,
        )

    def test_reference_evidence_set_is_complete(self):
        required_docs = {
            "compatibility-audit.md",
            "g2-core-validation.md",
            "g3-semantic-validation.md",
            "g4-resolved-validation.md",
            "g5-executable-validation.md",
            "g6-target-validation.md",
            "g7-reference-validation.md",
            "phase-a-contextual-skill-validation.md",
            "phase-b-roadside-investigation-validation.md",
            "phase-c-frightened-witness-validation.md",
            "phase-d-washed-out-path-validation.md",
            "phase-e-bounded-combat-validation.md",
            "phase-f-recovery-consciousness-validation.md",
            "phase-g-scenario-progression-validation.md",
            "phase-h-session-history-validation.md",
            "phase-i-web-target-validation.md",
        }
        docs = ROOT / "game/dirps/docs"
        self.assertEqual(
            {path.name for path in docs.glob("*.md")} & required_docs,
            required_docs,
        )


if __name__ == "__main__":
    unittest.main()
