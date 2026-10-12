#!/usr/bin/env python3
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dirps_semantic_validation import validate_resolved_semantics
from game_registry import scenario_config
from resolve_dirps_dodge import ResolutionError, resolve, resolve_documents


class DirpsResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())

    def test_current_source_resolves_and_passes_resolved_semantics(self):
        resolved = resolve()
        self.assertEqual(resolved["format"], "dirps-resolved-game.v1")
        self.assertEqual(
            validate_resolved_semantics(
                resolved, self.dodge, self.canonical, self.sidecar
            ),
            [],
        )
        self.assertEqual(
            [row["id"] for row in resolved["scenario"]["encounters"]],
            [row["id"] for row in self.canonical["encounters"]],
        )

    def test_primary_attribute_perturbation_flows_into_resolved_model(self):
        dodge = copy.deepcopy(self.dodge)
        canonical = copy.deepcopy(self.canonical)
        canonical["player_character"]["attributes"]["dx"] = 12
        pc = next(
            row
            for row in dodge["scenes"]["scenario-01-setup"]["instances"]
            if row["id"] == "pc"
        )
        pc["state"]["dx"] = 12

        resolved = resolve_documents(dodge, canonical, self.sidecar)
        resolved_pc = next(
            row for row in resolved["scene"]["instances"] if row["id"] == "pc"
        )
        self.assertEqual(resolved_pc["character"]["primary_attributes"]["dx"], 12)
        self.assertEqual(resolved_pc["state"]["dx"], 12)

    def test_missing_canonical_primary_fact_fails_before_stale_resolution(self):
        canonical = copy.deepcopy(self.canonical)
        del canonical["player_character"]["attributes"]["dx"]
        with self.assertRaisesRegex(ResolutionError, "missing primary attributes"):
            resolve_documents(self.dodge, canonical, self.sidecar)

    def test_encounter_order_perturbation_flows_into_resolved_model(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["encounters"] = list(reversed(canonical["encounters"]))
        resolved = resolve_documents(self.dodge, canonical, self.sidecar)
        self.assertEqual(
            [row["id"] for row in resolved["scenario"]["encounters"]],
            [row["id"] for row in canonical["encounters"]],
        )

    def test_scenario_assumption_perturbation_flows_into_resolved_model(self):
        dodge = copy.deepcopy(self.dodge)
        changed = [
            "A changed schema-valid unresolved Scenario 01 assumption must survive neutral resolution."
        ]
        dodge["scenarios"]["scenario-01"]["assumptions"] = changed

        resolved = resolve_documents(dodge, self.canonical, self.sidecar)
        self.assertEqual(resolved["scenario"]["assumptions"], changed)
        self.assertEqual(
            resolved["scenario"]["source_ref"],
            dodge["scenarios"]["scenario-01"]["source_ref"],
        )
        self.assertEqual(
            resolved["scenario"]["authority"],
            dodge["scenarios"]["scenario-01"]["authority"],
        )
        self.assertEqual(
            resolved["scenario"]["scene_ref"],
            dodge["scenarios"]["scenario-01"]["scene_ref"],
        )

        corrupted = copy.deepcopy(resolved)
        corrupted["scenario"]["assumptions"] = []
        errors = validate_resolved_semantics(
            corrupted, dodge, self.canonical, self.sidecar
        )
        self.assertTrue(
            any("scenario must preserve" in error for error in errors)
        )

    def test_source_and_provenance_relationships_survive_resolution(self):
        resolved = resolve()
        self.assertEqual(resolved["sources"], self.dodge["sources"])
        self.assertEqual(
            resolved["canonical_source"]["authority"],
            self.canonical["authority"],
        )
        self.assertEqual(
            resolved["canonical_source"]["implementation_boundary"],
            self.canonical["implementation_boundary"],
        )
        pc = next(row for row in resolved["scene"]["instances"] if row["id"] == "pc")
        self.assertEqual(
            pc["character"]["provenance"],
            self.canonical["player_character"]["provenance"],
        )

    def test_proto_semantics_cannot_disappear_from_resolved_model(self):
        resolved = resolve()
        del resolved["proto_sidecar"]["proto_specs"]["dice_resolution"]
        errors = validate_resolved_semantics(
            resolved, self.dodge, self.canonical, self.sidecar
        )
        self.assertTrue(any("proto sidecar semantics" in error for error in errors))

    def test_unresolved_index_is_derived_not_promoted(self):
        resolved = resolve()
        expected = [
            {
                "proto_ref": proto_id,
                "status": spec["status"],
                "candidate_for_dodge": spec["candidate_for_dodge"],
            }
            for proto_id, spec in sorted(self.sidecar["proto_specs"].items())
        ]
        self.assertEqual(resolved["unresolved"], expected)
        self.assertTrue(all(row["status"] == "suspected" for row in resolved["unresolved"]))

        corrupted = copy.deepcopy(resolved)
        corrupted["unresolved"][0]["status"] = "candidate"
        errors = validate_resolved_semantics(
            corrupted, self.dodge, self.canonical, self.sidecar
        )
        self.assertTrue(any("unresolved proto index" in error for error in errors))

    def test_missing_required_action_fails_visibly_before_resolution(self):
        dodge = copy.deepcopy(self.dodge)
        del dodge["rules"]["actions"]["attack"]
        with self.assertRaisesRegex(ResolutionError, "action attack"):
            resolve_documents(dodge, self.canonical, self.sidecar)

    def test_resolved_object_table_drop_is_rejected(self):
        resolved = resolve()
        del resolved["objects"]["tutorial-pc"]
        errors = validate_resolved_semantics(
            resolved, self.dodge, self.canonical, self.sidecar
        )
        self.assertTrue(any("DODGE objects" in error for error in errors))

    def test_resolved_rule_drop_is_rejected(self):
        resolved = resolve()
        del resolved["rules"]["actions"]["attack"]
        errors = validate_resolved_semantics(
            resolved, self.dodge, self.canonical, self.sidecar
        )
        self.assertTrue(any("normalized DODGE rules" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
