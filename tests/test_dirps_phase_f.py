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
from dirps_debug_target import execute_recovery_target, inspect_recovery_target
from dirps_runtime import (
    ExecutionError,
    create_combat_runtime_state,
    describe_recovery,
    execute_combat_exchange,
    execute_recovery,
    replay_recovery,
)
from game_registry import scenario_config
from resolve_dirps_dodge import ResolutionError, resolve, resolve_documents


ENCOUNTER_REF = "bandit-scout"
COMBAT_ACTION = "strike-bandit-scout"
RECOVERY_ACTION = "resolve-bandit-next-turn"


class DirpsPhaseFRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.dodge = json.loads(cls.cfg["dodge"].read_text())
        cls.canonical = json.loads(cls.cfg["source"].read_text())
        cls.sidecar = json.loads(cls.cfg["sidecars"][0].read_text())
        cls.resolved = resolve()

    @staticmethod
    def state_values(state):
        return {row["ref"]: row["value"] for row in state["bindings"]}

    def combat_zero_hp(self, resolved=None):
        resolved = resolved or self.resolved
        state = create_combat_runtime_state(resolved, encounter_ref=ENCOUNTER_REF)
        return execute_combat_exchange(
            resolved,
            state,
            encounter_ref=ENCOUNTER_REF,
            action_id=COMBAT_ACTION,
            actor_ref="pc",
            target_ref="bandit-scout",
            defense_kind="dodge",
            attack_terms=[1, 1, 1],
        )

    def combat_stunned_positive_hp(self, resolved=None):
        resolved = resolved or self.resolved
        state = create_combat_runtime_state(resolved, encounter_ref=ENCOUNTER_REF)
        return execute_combat_exchange(
            resolved,
            state,
            encounter_ref=ENCOUNTER_REF,
            action_id=COMBAT_ACTION,
            actor_ref="pc",
            target_ref="bandit-scout",
            defense_kind="dodge",
            attack_terms=[1, 1, 2],
            damage_terms=[4],
        )

    def execute(
        self,
        state,
        *,
        resolved=None,
        consciousness=(3, 3, 4),
        stun=(3, 3, 4),
        seed=None,
    ):
        resolved = resolved or self.resolved
        return execute_recovery(
            resolved,
            state,
            encounter_ref=ENCOUNTER_REF,
            action_id=RECOVERY_ACTION,
            actor_ref="bandit-scout",
            consciousness_terms=None if seed is not None else (
                None if consciousness is None else list(consciousness)
            ),
            stun_terms=None if seed is not None else (
                None if stun is None else list(stun)
            ),
            random_seed=seed,
        )

    def resolved_with_will_modifier(self, modifier):
        canonical = copy.deepcopy(self.canonical)
        encounter = next(
            row for row in canonical["encounters"] if row["id"] == ENCOUNTER_REF
        )
        encounter["post_combat_recovery"]["consciousness"]["will_modifier"] = modifier
        return resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)

    def resolved_with_ht(self, ht):
        dodge = copy.deepcopy(self.dodge)
        canonical = copy.deepcopy(self.canonical)
        encounter = next(
            row for row in canonical["encounters"] if row["id"] == ENCOUNTER_REF
        )
        encounter["opponent"]["attributes"]["ht"] = ht
        scene_ref = dodge["scenarios"]["scenario-01"]["scene_ref"]
        bandit = next(
            row
            for row in dodge["scenes"][scene_ref]["instances"]
            if row["id"] == "bandit-scout"
        )
        bandit["state"]["ht"] = ht
        return resolve_documents(dodge, canonical, self.sidecar, self.cfg)

    def test_phase_e_state_flows_directly_into_phase_f(self):
        combat = self.combat_zero_hp()
        state = combat["state_after"]
        self.assertEqual(state["revision"], "1")
        self.assertEqual(
            self.state_values(state),
            {
                "hit-points": 0,
                "stunned": True,
                "unconscious": False,
                "consciousness-check-required": True,
            },
        )
        capability = describe_recovery(
            self.resolved,
            state,
            encounter_ref=ENCOUNTER_REF,
        )
        self.assertEqual(
            [row["id"] for row in capability["available_actions"]],
            [RECOVERY_ACTION],
        )
        self.assertTrue(capability["check_plan"]["consciousness"]["required"])
        self.assertTrue(capability["check_plan"]["stun_recovery"]["required"])
        self.assertEqual(capability["check_plan"]["consciousness"]["target"], 10)
        self.assertEqual(capability["check_plan"]["stun_recovery"]["target"], 10)

    def test_consciousness_success_and_stun_recovery_success(self):
        state = self.combat_zero_hp()["state_after"]
        record = self.execute(state)
        self.assertEqual(record["format"], "dirps-recovery-result.v1")
        self.assertEqual(record["consciousness_check"]["format"], "dirps-ht-check-result.v1")
        self.assertTrue(record["consciousness_check"]["outcome"]["success"])
        self.assertTrue(record["stun_recovery_check"]["outcome"]["success"])
        for check in (
            record["consciousness_check"],
            record["stun_recovery_check"],
        ):
            self.assertEqual(
                check["trace"]["dice_resolution_ref"],
                "dice_resolution",
            )
            self.assertEqual(
                check["trace"]["critical_resolution_ref"],
                "phase_a_execution_bindings.attempt-skill.critical_resolution",
            )
            self.assertEqual(
                check["trace"]["random_evidence_ref"],
                "phase_a_execution_bindings.attempt-skill.random_evidence",
            )
        self.assertEqual(
            self.state_values(record["state_after"]),
            {
                "hit-points": 0,
                "stunned": False,
                "unconscious": False,
                "consciousness-check-required": True,
            },
        )
        self.assertTrue(record["outcome"]["can_act_normally"])
        self.assertTrue(record["outcome"]["consciousness_check_required"])
        self.assertEqual(record["state_before"]["revision"], "1")
        self.assertEqual(record["state_after"]["revision"], "2")
        self.assertEqual(
            [row["ref"] for row in record["state_delta"]],
            ["stunned"],
        )
        next_view = describe_recovery(
            self.resolved, record["state_after"], encounter_ref=ENCOUNTER_REF
        )
        self.assertEqual(
            [row["id"] for row in next_view["available_actions"]],
            [RECOVERY_ACTION],
        )
        self.assertTrue(next_view["check_plan"]["consciousness"]["required"])
        self.assertFalse(next_view["check_plan"]["stun_recovery"]["required"])
        print("PASS dirps/scenario-01: Phase F recovery and consciousness")

    def test_failed_consciousness_sets_unconscious_and_skips_stun(self):
        state = self.combat_zero_hp()["state_after"]
        record = self.execute(
            state,
            consciousness=(5, 5, 5),
            stun=None,
        )
        self.assertFalse(record["consciousness_check"]["outcome"]["success"])
        self.assertIsNone(record["stun_recovery_check"])
        self.assertIn(
            {"check": "stun-recovery", "reason": "actor-fell-unconscious"},
            record["skipped_checks"],
        )
        self.assertEqual(
            self.state_values(record["state_after"]),
            {
                "hit-points": 0,
                "stunned": True,
                "unconscious": True,
                "consciousness-check-required": False,
            },
        )
        self.assertFalse(record["outcome"]["can_act_normally"])
        self.assertEqual(
            [row["ref"] for row in record["state_delta"]],
            ["unconscious", "consciousness-check-required"],
        )
        view = describe_recovery(
            self.resolved, record["state_after"], encounter_ref=ENCOUNTER_REF
        )
        self.assertEqual(view["available_actions"], [])
        self.assertEqual(view["unsupported"], "long-term-unconscious-recovery")

    def test_successful_consciousness_failed_stun_remains_stunned(self):
        state = self.combat_zero_hp()["state_after"]
        record = self.execute(
            state,
            consciousness=(3, 3, 4),
            stun=(5, 5, 5),
        )
        self.assertTrue(record["consciousness_check"]["outcome"]["success"])
        self.assertFalse(record["stun_recovery_check"]["outcome"]["success"])
        self.assertEqual(record["state_delta"], [])
        values = self.state_values(record["state_after"])
        self.assertFalse(values["unconscious"])
        self.assertTrue(values["stunned"])
        self.assertTrue(values["consciousness-check-required"])
        self.assertFalse(record["outcome"]["can_act_normally"])

    def test_positive_hp_major_wound_runs_only_stun_recovery(self):
        combat = self.combat_stunned_positive_hp()
        state = combat["state_after"]
        self.assertEqual(self.state_values(state)["hit-points"], 3)
        self.assertTrue(self.state_values(state)["stunned"])
        self.assertFalse(self.state_values(state)["consciousness-check-required"])

        record = self.execute(
            state,
            consciousness=None,
            stun=(3, 3, 4),
        )
        self.assertIsNone(record["consciousness_check"])
        self.assertTrue(record["stun_recovery_check"]["outcome"]["success"])
        self.assertIn(
            {"check": "consciousness", "reason": "consciousness-check-not-required"},
            record["skipped_checks"],
        )
        values = self.state_values(record["state_after"])
        self.assertFalse(values["stunned"])
        self.assertFalse(values["unconscious"])
        self.assertFalse(values["consciousness-check-required"])

    def test_no_pending_recovery_action_fails(self):
        state = create_combat_runtime_state(self.resolved, encounter_ref=ENCOUNTER_REF)
        state["revision"] = "1"
        view = describe_recovery(self.resolved, state, encounter_ref=ENCOUNTER_REF)
        self.assertEqual(view["available_actions"], [])
        with self.assertRaisesRegex(ExecutionError, "unavailable in current state"):
            self.execute(state, consciousness=None, stun=None)

    def test_long_term_unconscious_recovery_is_explicitly_unsupported(self):
        state = self.combat_zero_hp()["state_after"]
        failed = self.execute(state, consciousness=(5, 5, 5), stun=None)
        with self.assertRaisesRegex(
            ExecutionError, "long-term recovery from unconsciousness is unsupported"
        ):
            self.execute(
                failed["state_after"],
                consciousness=None,
                stun=None,
            )

    def test_recovery_rejects_phase_e_initial_state(self):
        state = create_combat_runtime_state(self.resolved, encounter_ref=ENCOUNTER_REF)
        with self.assertRaisesRegex(
            ExecutionError, "requires the post-combat runtime state"
        ):
            self.execute(state, consciousness=None, stun=None)

    def test_inconsistent_obligation_state_fails_visibly(self):
        state = self.combat_zero_hp()["state_after"]
        next(
            row
            for row in state["bindings"]
            if row["ref"] == "consciousness-check-required"
        )["value"] = False
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(
            ExecutionError, "missing the consciousness obligation"
        ):
            self.execute(state, consciousness=None, stun=None)
        self.assertEqual(state, before)

    def test_unused_stun_terms_after_failed_consciousness_are_rejected_without_mutation(self):
        state = self.combat_zero_hp()["state_after"]
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(
            ExecutionError, "supplied after a failed consciousness check"
        ):
            self.execute(
                state,
                consciousness=(5, 5, 5),
                stun=(3, 3, 4),
            )
        self.assertEqual(state, before)

    def test_seeded_recovery_is_deterministic_and_replays(self):
        state = self.combat_zero_hp()["state_after"]
        first = self.execute(state, consciousness=None, stun=None, seed="phase-f-seed")
        second = self.execute(state, consciousness=None, stun=None, seed="phase-f-seed")
        self.assertEqual(first, second)
        self.assertEqual(
            replay_recovery(self.resolved, first),
            first,
        )

    def test_replay_detects_state_tampering(self):
        state = self.combat_zero_hp()["state_after"]
        record = self.execute(state)
        tampered = copy.deepcopy(record)
        next(
            row
            for row in tampered["state_after"]["bindings"]
            if row["ref"] == "stunned"
        )["value"] = True
        with self.assertRaisesRegex(ExecutionError, "recovery record divergence"):
            replay_recovery(self.resolved, tampered)

    def test_scenario_will_modifier_perturbation_changes_consciousness_target(self):
        baseline_state = self.combat_zero_hp()["state_after"]
        baseline = self.execute(
            baseline_state,
            consciousness=(3, 4, 4),
            stun=None,
        )
        self.assertEqual(baseline["consciousness_check"]["target"], 10)
        self.assertFalse(baseline["consciousness_check"]["outcome"]["success"])

        changed_resolved = self.resolved_with_will_modifier(1)
        changed_state = self.combat_zero_hp(changed_resolved)["state_after"]
        changed = self.execute(
            changed_state,
            resolved=changed_resolved,
            consciousness=(3, 4, 4),
            stun=(3, 3, 4),
        )
        self.assertEqual(changed["consciousness_check"]["target"], 11)
        self.assertTrue(changed["consciousness_check"]["outcome"]["success"])

    def test_canonical_ht_perturbation_changes_both_recovery_targets(self):
        changed_resolved = self.resolved_with_ht(11)
        state = self.combat_zero_hp(changed_resolved)["state_after"]
        record = self.execute(
            state,
            resolved=changed_resolved,
            consciousness=(3, 4, 4),
            stun=(3, 4, 4),
        )
        self.assertEqual(record["consciousness_check"]["base_ht"], 11)
        self.assertEqual(record["consciousness_check"]["target"], 11)
        self.assertEqual(record["stun_recovery_check"]["target"], 11)
        self.assertTrue(record["consciousness_check"]["outcome"]["success"])
        self.assertTrue(record["stun_recovery_check"]["outcome"]["success"])

    def test_recovery_binding_drift_fails_before_resolution(self):
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["phase_f_recovery_bindings"]["bandit-scout"]["resolution_order"] = [
            "stun-recovery",
            "consciousness",
        ]
        with self.assertRaisesRegex(
            ResolutionError, "Phase F bandit-scout recovery binding"
        ):
            resolve_documents(self.dodge, self.canonical, sidecar, self.cfg)

    def test_phase_f_dice_resolution_reuse_ref_drift_fails_before_resolution(self):
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["phase_f_recovery_bindings"]["bandit-scout"][
            "dice_resolution_ref"
        ] = "not-the-accepted-dice-contract"
        with self.assertRaisesRegex(
            ResolutionError, "Phase F bandit-scout recovery binding"
        ):
            resolve_documents(self.dodge, self.canonical, sidecar, self.cfg)

    def test_phase_f_critical_resolution_reuse_ref_drift_fails_before_resolution(self):
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["phase_f_recovery_bindings"]["bandit-scout"][
            "critical_resolution_ref"
        ] = "not-the-accepted-critical-contract"
        with self.assertRaisesRegex(
            ResolutionError, "Phase F bandit-scout recovery binding"
        ):
            resolve_documents(self.dodge, self.canonical, sidecar, self.cfg)

    def test_target_consumes_same_post_combat_state_and_runtime(self):
        state = self.combat_zero_hp()["state_after"]
        view = inspect_recovery_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
            state=state,
        )
        self.assertEqual(view["runtime_state"], state)
        self.assertEqual(
            [row["id"] for row in view["capability"]["available_actions"]],
            [RECOVERY_ACTION],
        )

        executed = execute_recovery_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
            action_id=RECOVERY_ACTION,
            actor_ref="bandit-scout",
            state=state,
            consciousness_terms=[3, 3, 4],
            stun_terms=[3, 3, 4],
        )
        self.assertEqual(executed["status"], "ok")
        self.assertEqual(executed["execution"]["format"], "dirps-recovery-result.v1")
        self.assertEqual(
            executed["runtime_state"],
            executed["execution"]["state_after"],
        )
        print("PASS dirps/scenario-01: Phase F debug target consumes recovery runtime")

    def test_target_passes_fake_recovery_result_through(self):
        fake_state = {"revision": "1"}
        fake_capability = {
            "encounter": {"id": "runtime-encounter"},
            "available_actions": [{"id": "runtime-action"}],
        }
        fake_record = {
            "format": "fake-recovery-result",
            "state_after": {"revision": "999"},
            "outcome": {"runtime_owned": True},
        }

        view = execute_recovery_target(
            self.resolved,
            encounter_ref="target-encounter",
            action_id="target-action",
            actor_ref="target-actor",
            state=fake_state,
            consciousness_terms=[42],
            runtime_describe=lambda resolved, state, encounter_ref: fake_capability,
            runtime_execute=lambda *args, **kwargs: fake_record,
        )
        self.assertEqual(view["status"], "ok")
        self.assertIs(view["execution"], fake_record)
        self.assertEqual(view["runtime_state"], fake_record["state_after"])

    def test_registered_cli_continues_real_post_combat_state(self):
        state = self.combat_zero_hp()["state_after"]
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "dirps_debug_target.py"),
                "--recovery",
                "--encounter",
                ENCOUNTER_REF,
                "--action",
                RECOVERY_ACTION,
                "--actor",
                "bandit-scout",
                "--state-json",
                json.dumps(state, separators=(",", ":")),
                "--consciousness-dice",
                "3",
                "3",
                "4",
                "--stun-dice",
                "3",
                "3",
                "4",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        view = json.loads(proc.stdout)
        self.assertEqual(view["status"], "ok")
        self.assertEqual(view["execution"]["format"], "dirps-recovery-result.v1")
        self.assertEqual(view["execution"]["state_before"], state)
        values = self.state_values(view["runtime_state"])
        self.assertEqual(values["hit-points"], 0)
        self.assertFalse(values["stunned"])
        self.assertFalse(values["unconscious"])
        self.assertTrue(values["consciousness-check-required"])

    def test_target_source_contains_no_phase_f_gameplay_literals(self):
        source = inspect.getsource(dirps_debug_target)
        for literal in [
            '"resolve-bandit-next-turn"',
            '"bandit-scout"',
            '"consciousness-check-required"',
            '"phase-f-bandit-set-unconscious"',
            '"phase-f-bandit-clear-stunned"',
        ]:
            self.assertNotIn(literal, source)

    def test_proto_maturity_remains_conservative(self):
        specs = self.resolved["proto_sidecar"]["proto_specs"]
        exercised = {
            proto_id
            for proto_id, spec in specs.items()
            if spec["status"] == "exercised"
        }
        self.assertEqual(
            exercised,
            {
                "dice_resolution",
                "procedure_context",
                "actor_character_model",
                "skill_model",
                "resolution_trace",
                "lookup_tables",
                "reaction_timing",
                "derived_values",
                "expressions",
                "damage_injury",
                "replay_session_history",
            },
        )
        self.assertEqual(specs["replay_session_history"]["status"], "exercised")
        self.assertEqual(
            specs["replay_session_history"]["candidate_for_dodge"],
            "not-yet-candidate",
        )
        self.assertEqual(specs["visibility_and_secret_state"]["status"], "suspected")


if __name__ == "__main__":
    unittest.main()
