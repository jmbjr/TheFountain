#!/usr/bin/env python3
import copy,json,sys,unittest
from unittest.mock import patch
from pathlib import Path

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from game_registry import scenario_config
from validate_registered_dodge import ConformanceError,discovered_dodge_scenarios,load_module,profile_modules

class RegisteredConformanceTests(unittest.TestCase):
    def test_wretched_is_discovered_as_active_dodge_scenario(self):
        rows={(x["game_id"],x["scenario_id"]):x for x in discovered_dodge_scenarios()}
        self.assertIn(("wretched-demesne","scenario-01"),rows)
        cfg=rows[("wretched-demesne","scenario-01")]
        self.assertEqual(cfg["conformance"]["maturity"],"G7")
        self.assertTrue(cfg["conformance"]["resolver"].is_file())

    def test_wretched_dodge_declares_semantic_profile(self):
        cfg=scenario_config("wretched-demesne","scenario-01")
        dodge=json.loads(cfg["dodge"].read_text())
        validation=dodge["validation"]
        self.assertEqual(validation["core_profile"],{"profile_id":"dodge-core","version":"0.2.1"})
        profiles=validation["required_profiles"]
        self.assertEqual(len(profiles),1)
        self.assertEqual(profiles[0]["profile_id"],"wretched-demesne")
        self.assertEqual(profiles[0]["stages"],["source","resolved-game"])
        source=dodge["sources"][profiles[0]["validator_source_ref"]]
        self.assertEqual(source["kind"],"semantic_validator")

    def test_semantic_validator_source_version_mismatch_fails_before_import(self):
        cfg=scenario_config("dirps","scenario-01")
        dodge=json.loads(cfg["dodge"].read_text())
        profile=dodge["validation"]["required_profiles"][0]
        source=dodge["sources"][profile["validator_source_ref"]]
        source["version"]="9.9.9"
        with patch("validate_registered_dodge.load_module") as mocked_load:
            with self.assertRaisesRegex(
                ConformanceError,
                r"dirps@0\.1\.0: semantic validator source .* declares version '9\.9\.9'"
            ):
                profile_modules(dodge)
            mocked_load.assert_not_called()

    def test_declared_hooks_are_importable(self):
        cfg=scenario_config("wretched-demesne","scenario-01")
        dodge=json.loads(cfg["dodge"].read_text())
        profile=dodge["validation"]["required_profiles"][0]
        source=dodge["sources"][profile["validator_source_ref"]]
        validator=load_module(ROOT/source["uri"],"test-validator")
        self.assertTrue(callable(getattr(validator,"validate_source_context",None)))
        self.assertTrue(callable(getattr(validator,"validate_resolved_context",None)))
        resolver=load_module(cfg["conformance"]["resolver"],"test-resolver")
        self.assertTrue(callable(getattr(resolver,"resolve_context",None)))

if __name__=="__main__":
    unittest.main()
