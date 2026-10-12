#!/usr/bin/env python3
import sys, unittest
from pathlib import Path

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from game_registry import discover_games, scenario_config

class GameRegistryTests(unittest.TestCase):
    def test_game_namespaces_are_discovered(self):
        games=discover_games()
        self.assertIn("the-fountain",games)
        self.assertIn("wretched-demesne",games)
        self.assertIn("dirps",games)
        self.assertNotIn("gurps",games)

    def test_dirps_scenario_01_is_explicit_g2_core_candidate(self):
        cfg=scenario_config("dirps","scenario-01")
        self.assertEqual(cfg["status"],"incubating")
        self.assertTrue(cfg["dodge"].is_file())
        self.assertTrue(cfg["source"].is_file())
        self.assertEqual(cfg["conformance"]["maturity"],"G2")
        self.assertIsNone(cfg["conformance"]["resolver"])

    def test_wretched_scenario_01_paths_exist(self):
        cfg=scenario_config("wretched-demesne","scenario-01")
        self.assertEqual(cfg["status"],"reference")
        self.assertTrue(cfg["dodge"].is_file())
        self.assertTrue(cfg["source"].is_file())
        self.assertTrue(cfg["sidecars"] and all(p.is_file() for p in cfg["sidecars"]))
        self.assertEqual(set(cfg["export_contracts"]),{"pnp","tts"})
        self.assertTrue(all(p.is_file() for p in cfg["export_contracts"].values()))

    def test_wretched_conformance_hook_is_discoverable(self):
        cfg=scenario_config("wretched-demesne","scenario-01")
        self.assertEqual(cfg["conformance"]["maturity"],"G7")
        self.assertTrue(cfg["conformance"]["resolver"].is_file())

    def test_wretched_scenario_02_has_reserved_home(self):
        cfg=scenario_config("wretched-demesne","scenario-02")
        self.assertEqual(cfg["status"],"planned")
        self.assertTrue(cfg["path"].is_dir())
        self.assertIsNone(cfg["source"])
        self.assertIsNone(cfg["dodge"])

if __name__=="__main__":
    unittest.main()
