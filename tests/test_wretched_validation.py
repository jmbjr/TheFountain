#!/usr/bin/env python3
import copy,json,unittest
from pathlib import Path
import sys
ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from wretched_semantic_validation import validate_source_semantics,validate_resolved_semantics
from resolve_wretched_dodge import resolve

class SemanticValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dodge=json.loads((ROOT/"game/wretched-demesne.dodge.v0.2.1.json").read_text())
        cls.canonical=json.loads((ROOT/"game/wretched-demesne.scenario-01.mvp.v0.1.json").read_text())
    def test_current_source_and_resolved_game_pass(self):
        self.assertEqual(validate_source_semantics(self.dodge,self.canonical),[])
        self.assertEqual(validate_resolved_semantics(resolve()),[])
    def test_searchable_room_without_search_semantics_fails(self):
        dodge=copy.deepcopy(self.dodge);key="scenario-mvp:rooms:fungal-vault"
        dodge["entity_invocations"][key]=[x for x in dodge["entity_invocations"][key] if x["trigger"]!="search"]
        self.assertTrue(any("fungal-vault" in e and "search" in e for e in validate_source_semantics(dodge,self.canonical)))
    def test_invalid_canonical_runtime_room_ref_fails(self):
        canonical=copy.deepcopy(self.canonical)
        canonical["scenario"]["runtime"]["start_room_ref"]="not-a-room"
        self.assertTrue(any("not-a-room" in e for e in validate_source_semantics(self.dodge,canonical)))
    def test_broken_invocation_reference_fails(self):
        dodge=copy.deepcopy(self.dodge);key="scenario-mvp:rooms:bone-pit";dodge["entity_invocations"][key][0]["steps"][0]["ref"]="missing-effect"
        self.assertTrue(any("missing-effect" in e for e in validate_source_semantics(dodge,self.canonical)))
    def test_broken_collection_member_fails_resolved_gate(self):
        resolved=copy.deepcopy(resolve());resolved["semantic_collections"]["scenario-room-cards-1"]["members"][0]["entity_ref"]="scenario-mvp:rooms:not-a-room"
        self.assertTrue(any("not-a-room" in e for e in validate_resolved_semantics(resolved)))
if __name__=="__main__": unittest.main()
