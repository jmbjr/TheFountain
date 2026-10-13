#!/usr/bin/env python3
import copy
import inspect
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dirps_debug_target
from dirps_debug_target import execute_encounter_target, inspect_encounter_target
from dirps_runtime import (
    ExecutionError,
    create_environment_runtime_state,
    describe_environment_challenge,
    execute_environment_challenge,
    replay_environment_challenge,
)
from game_registry import scenario_config
from resolve_dirps_dodge import ResolutionError, resolve, resolve_documents

ENCOUNTER_REF = "washed-out-path"
ACTION_ID = "cross-washed-out-path"


class DirpsPhaseDWashedOutPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())
        cls.resolved = resolve()

    @staticmethod
    def values(state):
        return {row["ref"]: row["value"] for row in state["bindings"]}

    def execute(self, resolved=None, state=None, terms=None, seed=None):
        resolved = resolved or self.resolved
        state = state or create_environment_runtime_state(resolved, encounter_ref=ENCOUNTER_REF)
        return execute_environment_challenge(
            resolved, state, encounter_ref=ENCOUNTER_REF, action_id=ACTION_ID,
            actor_ref="pc", dice_terms=terms, random_seed=seed,
        )

    def test_initial_state_and_action_are_runtime_described(self):
        state = create_environment_runtime_state(self.resolved, encounter_ref=ENCOUNTER_REF)
        self.assertEqual(self.values(state), {
            "washed-out-path-status":"ready",
            "washed-out-path-outcome":"unresolved",
            "washed-out-path-progress":"not-crossed",
        })
        view = describe_environment_challenge(self.resolved, state, encounter_ref=ENCOUNTER_REF)
        self.assertEqual([x["id"] for x in view["available_actions"]], [ACTION_ID])
        self.assertEqual(view["check"]["attribute_ref"], "dx")
        self.assertEqual(view["check"]["modifiers"][0]["amount"], -1)

    def test_success_uses_dx_modifier_and_persists_crossed_progress(self):
        record = self.execute(terms=[3,3,4])
        self.assertEqual(record["format"], "dirps-environment-encounter-result.v1")
        roll = record["attribute_resolution"]
        self.assertEqual(roll["format"], "dirps-attribute-result.v1")
        self.assertEqual(
            roll["semantic_path"],
            {"action_ref": "attempt-attribute", "procedure_ref": "success-roll"},
        )
        self.assertEqual(roll["target"]["attribute_ref"], "dx")
        self.assertEqual(roll["target"]["base_target"], 11)
        self.assertEqual(roll["target"]["modifier_total"], -1)
        self.assertEqual(roll["target"]["effective_target"], 10)
        self.assertTrue(roll["outcome"]["success"])
        self.assertEqual(self.values(record["state_after"]), {
            "washed-out-path-status":"resolved",
            "washed-out-path-outcome":"success",
            "washed-out-path-progress":"crossed",
        })
        self.assertEqual(record["state_after"]["revision"], "1")
        print("PASS dirps/scenario-01: Phase D Washed-Out Path environmental challenge")

    def test_failure_persists_detour_required(self):
        record = self.execute(terms=[5,5,5])
        self.assertFalse(record["attribute_resolution"]["outcome"]["success"])
        self.assertEqual(record["outcome_branch"], "failure")
        self.assertEqual(self.values(record["state_after"])["washed-out-path-progress"], "detour-required")
        self.assertIn("detour", record["consequence"]["consequence_text"].lower())

    def test_resolved_environment_action_cannot_repeat(self):
        first = self.execute(terms=[3,3,4])
        state = copy.deepcopy(first["state_after"])
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(ExecutionError, "unavailable"):
            self.execute(state=state, terms=[3,3,4])
        self.assertEqual(state, before)
        view = describe_environment_challenge(self.resolved, state, encounter_ref=ENCOUNTER_REF)
        self.assertEqual(view["available_actions"], [])

    def test_seeded_environment_roll_is_deterministic_and_replays(self):
        first = self.execute(seed="phase-d-seed")
        second = self.execute(seed="phase-d-seed")
        self.assertEqual(first, second)
        self.assertEqual(replay_environment_challenge(self.resolved, first), first)

    def test_replay_detects_state_tampering(self):
        record = self.execute(terms=[3,3,4])
        tampered = copy.deepcopy(record)
        tampered["state_delta"][2]["after"] = "detour-required"
        with self.assertRaisesRegex(ExecutionError, "environment encounter record divergence"):
            replay_environment_challenge(self.resolved, tampered)

    def test_attribute_perturbation_flows_to_effective_target_and_outcome(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["player_character"]["attributes"]["dx"] = 12
        dodge = copy.deepcopy(self.dodge)
        scene_ref = dodge["scenarios"]["scenario-01"]["scene_ref"]
        pc = next(
            x for x in dodge["scenes"][scene_ref]["instances"] if x["id"] == "pc"
        )
        pc["state"]["dx"] = 12
        resolved = resolve_documents(dodge, canonical, self.sidecar, self.cfg)
        baseline = self.execute(terms=[3,3,5])
        changed = self.execute(resolved=resolved, terms=[3,3,5])
        self.assertEqual(baseline["attribute_resolution"]["target"]["effective_target"], 10)
        self.assertFalse(baseline["attribute_resolution"]["outcome"]["success"])
        self.assertEqual(changed["attribute_resolution"]["target"]["effective_target"], 11)
        self.assertTrue(changed["attribute_resolution"]["outcome"]["success"])

    def test_modifier_perturbation_flows_to_effective_target(self):
        canonical = copy.deepcopy(self.canonical)
        canonical["contextual_checks"]["washed-out-path-dx"]["modifiers"][0]["amount"] = -2
        resolved = resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)
        changed = self.execute(resolved=resolved, terms=[3,3,4])
        self.assertEqual(changed["attribute_resolution"]["target"]["effective_target"], 9)
        self.assertFalse(changed["attribute_resolution"]["outcome"]["success"])

    def test_stale_dodge_progress_normalization_is_rejected(self):
        canonical = copy.deepcopy(self.canonical)
        encounter = next(x for x in canonical["encounters"] if x["id"] == ENCOUNTER_REF)
        encounter["actions"][0]["consequences"]["success"]["progress"] = "other-progress"
        with self.assertRaisesRegex(ResolutionError, "washed-out-path-progress must normalize canonical progress state exactly"):
            resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)

    def test_normalized_consequence_perturbation_flows_into_runtime_state(self):
        dodge = copy.deepcopy(self.dodge)
        canonical = copy.deepcopy(self.canonical)
        sidecar = copy.deepcopy(self.sidecar)
        encounter = next(
            x for x in canonical["encounters"] if x["id"] == ENCOUNTER_REF
        )
        encounter["actions"][0]["consequences"]["success"]["progress"] = (
            "crossed-alternate"
        )

        progress = dodge["rules"]["values"]["washed-out-path-progress"]
        progress["enum_values"][1] = "crossed-alternate"
        dodge["rules"]["effects"][
            "washed-out-path-set-progress-crossed-alternate"
        ] = {
            "op": "set",
            "target_ref": "washed-out-path-progress",
            "subject": {"relative": "scenario"},
            "value": "crossed-alternate",
            "source_ref": "scenario-01-source",
            "authority": "provisional",
        }
        sidecar["phase_d_environment_bindings"][ENCOUNTER_REF]["consequences"][
            "success"
        ]["effect_refs"][2] = "washed-out-path-set-progress-crossed-alternate"

        resolved = resolve_documents(dodge, canonical, sidecar, self.cfg)
        record = self.execute(resolved=resolved, terms=[3, 3, 4])
        self.assertEqual(
            self.values(record["state_after"])["washed-out-path-progress"],
            "crossed-alternate",
        )

    def test_inherited_success_roll_binding_refs_cannot_drift(self):
        for field in ("critical_resolution_ref", "random_evidence_ref"):
            resolved = copy.deepcopy(self.resolved)
            resolved["proto_sidecar"]["phase_d_environment_bindings"][ENCOUNTER_REF][
                field
            ] = "not-the-accepted-phase-a-contract"
            with self.assertRaisesRegex(ExecutionError, "reuse binding is malformed"):
                self.execute(resolved=resolved, terms=[3, 3, 4])

    def test_attempt_attribute_authority_drift_is_rejected(self):
        dodge = copy.deepcopy(self.dodge)
        dodge["rules"]["actions"]["attempt-attribute"]["authority"] = "provisional"
        with self.assertRaisesRegex(
            ResolutionError,
            "attempt-attribute action must preserve the authoritative success-roll binding",
        ):
            resolve_documents(dodge, self.canonical, self.sidecar, self.cfg)

    def test_target_source_binding_drift_fails_at_runtime(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["proto_sidecar"]["phase_d_environment_bindings"][ENCOUNTER_REF]["target_source"]["path"] = "scene.invalid"
        state = create_environment_runtime_state(self.resolved, encounter_ref=ENCOUNTER_REF)
        with self.assertRaisesRegex(ExecutionError, "target-source binding"):
            execute_environment_challenge(
                resolved, state, encounter_ref=ENCOUNTER_REF, action_id=ACTION_ID,
                actor_ref="pc", dice_terms=[3,3,4],
            )

    def test_phase_d_promotes_no_new_proto_concept(self):
        specs = self.resolved["proto_sidecar"]["proto_specs"]
        exercised = {k for k,v in specs.items() if v["status"] == "exercised"}
        self.assertEqual(exercised, {
            "dice_resolution","procedure_context","actor_character_model",
            "skill_model","resolution_trace","lookup_tables",
        })
        self.assertEqual(specs["reaction_timing"]["status"], "suspected")
        self.assertEqual(specs["replay_session_history"]["status"], "suspected")

    def test_generic_target_dispatches_environment(self):
        view = inspect_encounter_target(self.resolved, encounter_ref=ENCOUNTER_REF)
        self.assertEqual(view["target"]["format"], "dirps-debug-environment-target.v1")
        executed = execute_encounter_target(
            self.resolved, encounter_ref=ENCOUNTER_REF, action_id=ACTION_ID,
            actor_ref="pc", dice_terms=[3,3,4],
        )
        self.assertEqual(executed["status"], "ok")
        self.assertEqual(executed["execution"]["outcome_branch"], "success")
        self.assertEqual(executed["capability"]["available_actions"], [])
        print("PASS dirps/scenario-01: Phase D debug target consumes environmental runtime")

    def test_target_source_has_no_phase_d_gameplay_literals(self):
        source = inspect.getsource(dirps_debug_target)
        for literal in ['"washed-out-path"','"cross-washed-out-path"','"detour-required"','"washed-out-path-progress"']:
            self.assertNotIn(literal, source)

    def test_cli_executes_environment_encounter(self):
        proc = subprocess.run([
            sys.executable, str(ROOT/"tools"/"dirps_debug_target.py"),
            "--encounter",ENCOUNTER_REF,"--action",ACTION_ID,"--actor","pc",
            "--dice","3","3","4",
        ], check=True, capture_output=True, text=True)
        view = json.loads(proc.stdout)
        self.assertEqual(view["status"], "ok")
        self.assertEqual(view["execution"]["format"], "dirps-environment-encounter-result.v1")
        self.assertEqual(self.values(view["runtime_state"])["washed-out-path-progress"], "crossed")


if __name__ == "__main__":
    unittest.main()
