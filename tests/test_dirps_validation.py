#!/usr/bin/env python3
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dirps_semantic_validation import validate_source_semantics
from game_registry import scenario_config


class DirpsSemanticValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())

    def errors(self, dodge=None, canonical=None, config=None):
        return validate_source_semantics(
            dodge if dodge is not None else self.dodge,
            canonical if canonical is not None else self.canonical,
            config if config is not None else self.cfg,
        )

    def test_current_source_passes_dirps_profile(self):
        self.assertEqual(self.errors(), [])

    def test_canonical_pc_attribute_drift_fails(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["player_character"]["attributes"]["dx"] = 12
        self.assertTrue(
            any("attribute dx" in error for error in self.errors(canonical=canonical))
        )

    def test_canonical_rules_authority_drift_fails(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["authority"]["rules"] = "Different rules authority"
        self.assertTrue(
            any(
                "authority.rules" in error
                for error in self.errors(canonical=canonical)
            )
        )

    def test_canonical_pc_provenance_drift_fails(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["player_character"]["provenance"] = "authoritative"
        self.assertTrue(
            any(
                "provenance must be prototype_assumption" in error
                for error in self.errors(canonical=canonical)
            )
        )

    def test_canonical_primary_attribute_missing_fails(self):
        canonical = copy.deepcopy(self.canonical)
        del canonical["player_character"]["attributes"]["dx"]
        self.assertTrue(
            any(
                "missing primary attributes" in error and "dx" in error
                for error in self.errors(canonical=canonical)
            )
        )

    def test_canonical_primary_attribute_addition_fails(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["player_character"]["attributes"]["hit-points"] = 10
        self.assertTrue(
            any(
                "unexpected primary attributes" in error and "hit-points" in error
                for error in self.errors(canonical=canonical)
            )
        )

    def test_canonical_pc_skills_drift_fails(self):
        dodge = copy.deepcopy(self.dodge)
        ext = dodge["scenes"]["scenario-01-setup"]["instances"][0]["extensions"]["org.dirps.character"]
        ext["skills"]["tracking"] = 11
        self.assertTrue(
            any("skills disagree" in error for error in self.errors(dodge=dodge))
        )

    def test_canonical_pc_equipment_drift_fails(self):
        dodge = copy.deepcopy(self.dodge)
        ext = dodge["scenes"]["scenario-01-setup"]["instances"][0]["extensions"]["org.dirps.character"]
        ext["equipment"] = ext["equipment"][:-1]
        self.assertTrue(
            any("equipment disagree" in error for error in self.errors(dodge=dodge))
        )

    def test_actor_conscious_semantic_drift_fails(self):
        dodge = copy.deepcopy(self.dodge)
        dodge["rules"]["conditions"]["actor-conscious"]["left"]["ref"] = "stunned"
        self.assertTrue(
            any(
                "actor-conscious" in error and "unconscious value" in error
                for error in self.errors(dodge=dodge)
            )
        )

    def test_actor_missing_explicit_state_binding_fails(self):
        dodge = copy.deepcopy(self.dodge)
        opponent = dodge["scenes"]["scenario-01-setup"]["instances"][1]
        del opponent["state"]["unconscious"]
        self.assertTrue(
            any(
                "bandit-scout" in error and "actor-state bindings" in error
                for error in self.errors(dodge=dodge)
            )
        )

    def test_action_bound_to_wrong_dirps_procedure_fails(self):
        dodge = copy.deepcopy(self.dodge)
        dodge["rules"]["actions"]["attack"]["procedure_ref"] = "success-roll"
        self.assertTrue(
            any(
                "action attack" in error and "attack-resolution" in error
                for error in self.errors(dodge=dodge)
            )
        )

    def test_tutorial_action_and_choice_drift_fails(self):
        dodge = copy.deepcopy(self.dodge)
        choices = dodge["rules"]["procedures"]["tutorial-turn"]["steps"][0]["choice_options"]
        dodge["rules"]["procedures"]["tutorial-turn"]["steps"][0]["choice_options"] = choices[:-1]
        self.assertTrue(
            any("choices must expose" in error for error in self.errors(dodge=dodge))
        )

    def test_combat_encounter_without_concrete_opponent_fails(self):
        dodge = copy.deepcopy(self.dodge)
        scene = dodge["scenes"]["scenario-01-setup"]
        scene["instances"] = [
            row for row in scene["instances"] if row["id"] != "bandit-scout"
        ]
        self.assertTrue(
            any(
                "combat encounter bandit-scout" in error
                and "missing concrete DODGE opponent" in error
                for error in self.errors(dodge=dodge)
            )
        )

    def test_target_duration_duplication_drift_fails(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["tutorial"]["target_minutes"]["max"] = 75
        self.assertTrue(
            any("target duration disagrees" in error for error in self.errors(canonical=canonical))
        )

    def test_gurps_rule_authority_drift_fails(self):
        dodge = copy.deepcopy(self.dodge)
        dodge["rules"]["actions"]["attack"]["source_ref"] = "scenario-01-source"
        self.assertTrue(
            any(
                "action attack" in error and "source_ref must be gurps-lite" in error
                for error in self.errors(dodge=dodge)
            )
        )

    def test_proto_sidecar_bridge_drift_fails(self):
        dodge = copy.deepcopy(self.dodge)
        dodge["extensions"]["org.dirps.proto"]["sidecar_ref"] = "scenario-01-source"
        self.assertTrue(
            any(
                "org.dirps.proto" in error and "dirps-proto" in error
                for error in self.errors(dodge=dodge)
            )
        )

    def test_registered_authority_path_drift_fails(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["authority"]["proto_sidecar"] = "game/dirps/sidecars/not-the-sidecar.json"
        self.assertTrue(
            any(
                "authority.proto_sidecar" in error
                for error in self.errors(canonical=canonical)
            )
        )


if __name__ == "__main__":
    unittest.main()
