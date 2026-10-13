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
from dirps_debug_target import (
    execute_investigation_target,
    inspect_investigation_target,
)
from dirps_runtime import (
    ExecutionError,
    create_runtime_state,
    describe_investigation,
    execute_investigation,
    replay_investigation,
)
from game_registry import scenario_config
from resolve_dirps_dodge import ResolutionError, resolve, resolve_documents


ENCOUNTER_REF = "roadside-tracks"
ACTION_ID = "investigate-tracks"


class DirpsPhaseBRoadsideInvestigationTests(unittest.TestCase):
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

    def execute(self, state=None, terms=None, seed=None, resolved=None):
        resolved = resolved if resolved is not None else self.resolved
        state = state if state is not None else create_runtime_state(
            resolved, encounter_ref=ENCOUNTER_REF
        )
        return execute_investigation(
            resolved,
            state,
            encounter_ref=ENCOUNTER_REF,
            action_id=ACTION_ID,
            actor_ref="pc",
            dice_terms=terms,
            random_seed=seed,
        )

    def normalized_success_information(self, value):
        dodge = copy.deepcopy(self.dodge)
        canonical = copy.deepcopy(self.canonical)

        encounter = next(
            row for row in canonical["encounters"] if row["id"] == ENCOUNTER_REF
        )
        action = encounter["actions"][0]
        action["consequences"]["success"]["information"] = value

        definition = dodge["rules"]["values"]["roadside-tracks-information"]
        definition["enum_values"][1] = value
        dodge["rules"]["effects"][
            "roadside-tracks-set-information-clear-trail"
        ]["value"] = value
        return dodge, canonical

    def test_initial_runtime_state_and_action_are_neutral_and_available(self):
        state = create_runtime_state(self.resolved, encounter_ref=ENCOUNTER_REF)
        self.assertEqual(state["scenario_ref"], "scenario-01")
        self.assertEqual(state["revision"], "0")
        self.assertEqual(
            self.state_values(state),
            {
                "roadside-tracks-status": "ready",
                "roadside-tracks-outcome": "unresolved",
                "roadside-tracks-information": "undiscovered",
            },
        )
        capability = describe_investigation(
            self.resolved, state, encounter_ref=ENCOUNTER_REF
        )
        self.assertEqual(capability["state"], {
            "status": "ready",
            "outcome": "unresolved",
            "information": "undiscovered",
        })
        self.assertEqual(
            [row["id"] for row in capability["available_actions"]],
            [ACTION_ID],
        )

    def test_success_applies_normalized_dodge_consequences(self):
        record = self.execute(terms=[3, 3, 4])
        self.assertEqual(record["format"], "dirps-encounter-result.v1")
        self.assertEqual(record["outcome_branch"], "success")
        self.assertEqual(
            record["skill_resolution"]["format"],
            "dirps-execution-result.v2",
        )
        self.assertEqual(
            record["skill_resolution"]["outcome"],
            {"classification": "success", "success": True, "margin": 0},
        )
        self.assertEqual(
            self.state_values(record["state_before"]),
            {
                "roadside-tracks-status": "ready",
                "roadside-tracks-outcome": "unresolved",
                "roadside-tracks-information": "undiscovered",
            },
        )
        self.assertEqual(
            self.state_values(record["state_after"]),
            {
                "roadside-tracks-status": "resolved",
                "roadside-tracks-outcome": "success",
                "roadside-tracks-information": "clear-trail",
            },
        )
        self.assertEqual(record["state_before"]["revision"], "0")
        self.assertEqual(record["state_after"]["revision"], "1")
        self.assertEqual(
            [row["ref"] for row in record["state_delta"]],
            [
                "roadside-tracks-status",
                "roadside-tracks-outcome",
                "roadside-tracks-information",
            ],
        )
        self.assertEqual(
            record["consequence"]["information_text"],
            "Rook identifies a clear trail leading away from the road.",
        )
        self.assertEqual(
            record["trace"]["consequence_source"]["effect_refs"],
            [
                "roadside-tracks-set-status-resolved",
                "roadside-tracks-set-outcome-success",
                "roadside-tracks-set-information-clear-trail",
            ],
        )
        print("PASS dirps/scenario-01: Phase B Roadside investigation encounter")

    def test_failure_applies_meaningful_failure_consequence(self):
        record = self.execute(terms=[5, 5, 5])
        self.assertEqual(record["outcome_branch"], "failure")
        self.assertFalse(record["skill_resolution"]["outcome"]["success"])
        self.assertEqual(
            self.state_values(record["state_after"]),
            {
                "roadside-tracks-status": "resolved",
                "roadside-tracks-outcome": "failure",
                "roadside-tracks-information": "trail-inconclusive",
            },
        )
        self.assertEqual(
            record["consequence"]["information_text"],
            "Rook cannot establish a reliable trail from the disturbed roadside signs.",
        )

    def test_resolved_encounter_cannot_be_repeated_and_state_is_not_mutated(self):
        first = self.execute(terms=[3, 3, 4])
        state = copy.deepcopy(first["state_after"])
        before_retry = copy.deepcopy(state)
        with self.assertRaisesRegex(ExecutionError, "unavailable in current runtime state"):
            self.execute(state=state, terms=[3, 3, 4])
        self.assertEqual(state, before_retry)

        capability = describe_investigation(
            self.resolved, state, encounter_ref=ENCOUNTER_REF
        )
        self.assertEqual(capability["available_actions"], [])

    def test_wrong_action_fails_without_mutating_state(self):
        state = create_runtime_state(self.resolved, encounter_ref=ENCOUNTER_REF)
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(ExecutionError, "action is not available"):
            execute_investigation(
                self.resolved,
                state,
                encounter_ref=ENCOUNTER_REF,
                action_id="not-an-action",
                actor_ref="pc",
                dice_terms=[3, 3, 4],
            )
        self.assertEqual(state, before)

    def test_malformed_runtime_state_fails_visibly(self):
        state = create_runtime_state(self.resolved, encounter_ref=ENCOUNTER_REF)
        next(
            row
            for row in state["bindings"]
            if row["ref"] == "roadside-tracks-status"
        )["value"] = "impossible"
        with self.assertRaisesRegex(ExecutionError, "outside declared enum_values"):
            self.execute(state=state, terms=[3, 3, 4])

    def test_seeded_encounter_is_deterministic_and_replays(self):
        first = self.execute(seed="phase-b-seed")
        second = self.execute(seed="phase-b-seed")
        self.assertEqual(first, second)
        self.assertEqual(
            first["skill_resolution"]["random_evidence"]["kind"],
            "generated-seeded-dice-terms",
        )
        self.assertEqual(replay_investigation(self.resolved, first), first)

    def test_replay_detects_state_delta_tampering(self):
        record = self.execute(terms=[3, 3, 4])
        tampered = copy.deepcopy(record)
        tampered["state_delta"][0]["after"] = "ready"
        with self.assertRaisesRegex(ExecutionError, "encounter record divergence"):
            replay_investigation(self.resolved, tampered)

    def test_canonical_consequence_change_without_normalization_is_rejected(self):
        canonical = copy.deepcopy(self.canonical)
        encounter = next(
            row for row in canonical["encounters"] if row["id"] == ENCOUNTER_REF
        )
        encounter["actions"][0]["consequences"]["success"]["information"] = (
            "clear-trail-changed"
        )
        with self.assertRaisesRegex(
            ResolutionError,
            "roadside-tracks-information must normalize canonical information state exactly",
        ):
            resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)

    def test_normalized_consequence_perturbation_flows_to_runtime(self):
        dodge, canonical = self.normalized_success_information(
            "clear-trail-perturbed"
        )
        resolved = resolve_documents(dodge, canonical, self.sidecar, self.cfg)
        record = self.execute(
            resolved=resolved,
            terms=[3, 3, 4],
        )
        self.assertEqual(
            self.state_values(record["state_after"])[
                "roadside-tracks-information"
            ],
            "clear-trail-perturbed",
        )

    def test_phase_b_standard_state_gaps_remain_unpromoted(self):
        specs = self.resolved["proto_sidecar"]["proto_specs"]
        self.assertEqual(specs["replay_session_history"]["status"], "suspected")
        self.assertEqual(specs["visibility_and_secret_state"]["status"], "suspected")

    def test_target_inspects_and_executes_same_runtime_state(self):
        view = inspect_investigation_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
        )
        self.assertEqual(view["status"], "ready")
        self.assertEqual(
            [row["id"] for row in view["capability"]["available_actions"]],
            [ACTION_ID],
        )

        executed = execute_investigation_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
            action_id=ACTION_ID,
            actor_ref="pc",
            dice_terms=[3, 3, 4],
        )
        self.assertEqual(executed["status"], "ok")
        self.assertEqual(executed["execution"]["outcome_branch"], "success")
        self.assertEqual(
            executed["runtime_state"],
            executed["execution"]["state_after"],
        )
        self.assertEqual(
            executed["capability"]["state"],
            {
                "status": "resolved",
                "outcome": "success",
                "information": "clear-trail",
            },
        )
        self.assertEqual(executed["capability"]["available_actions"], [])
        print("PASS dirps/scenario-01: Phase B debug target consumes encounter runtime")

    def test_target_failure_refreshes_post_action_capability(self):
        executed = execute_investigation_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
            action_id=ACTION_ID,
            actor_ref="pc",
            dice_terms=[5, 5, 5],
        )
        self.assertEqual(executed["status"], "ok")
        self.assertEqual(executed["execution"]["outcome_branch"], "failure")
        self.assertEqual(
            executed["capability"]["state"],
            {
                "status": "resolved",
                "outcome": "failure",
                "information": "trail-inconclusive",
            },
        )
        self.assertEqual(executed["capability"]["available_actions"], [])

    def test_target_passes_runtime_result_and_refreshed_capability_without_recomputing(self):
        fake_state = {
            "scenario_ref": "fake",
            "bindings": [],
            "events": [],
            "revision": "88",
        }
        fake_record = {
            "format": "fake-encounter-result",
            "state_after": {"revision": "999"},
            "state_delta": [{"fake": True}],
            "outcome_branch": "impossible-but-runtime-owned",
        }
        described_states = []
        pre_capability = {
            "encounter": {"id": "fake-encounter"},
            "state": {"phase": "pre"},
            "available_actions": [{"id": "fake-action"}],
        }
        post_capability = {
            "encounter": {"id": "fake-encounter"},
            "state": {"phase": "post"},
            "available_actions": [],
        }

        def fake_describe(resolved, state, encounter_ref):
            described_states.append(state)
            return pre_capability if len(described_states) == 1 else post_capability

        view = execute_investigation_target(
            self.resolved,
            encounter_ref="target-input-encounter",
            action_id="target-input-action",
            actor_ref="target-input-actor",
            dice_terms=[99],
            runtime_create=lambda resolved, encounter_ref: fake_state,
            runtime_describe=fake_describe,
            runtime_execute=lambda *args, **kwargs: fake_record,
        )
        self.assertEqual(view["status"], "ok")
        self.assertIs(view["execution"], fake_record)
        self.assertEqual(view["runtime_state"], fake_record["state_after"])
        self.assertIs(view["capability"], post_capability)
        self.assertEqual(described_states, [fake_state, fake_record["state_after"]])

    def test_rejected_target_execution_keeps_pre_action_capability_and_state(self):
        view = execute_investigation_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
            action_id="not-an-action",
            actor_ref="pc",
            dice_terms=[3, 3, 4],
        )
        self.assertEqual(view["status"], "error")
        self.assertEqual(
            self.state_values(view["runtime_state"]),
            {
                "roadside-tracks-status": "ready",
                "roadside-tracks-outcome": "unresolved",
                "roadside-tracks-information": "undiscovered",
            },
        )
        self.assertEqual(
            view["capability"]["state"],
            {
                "status": "ready",
                "outcome": "unresolved",
                "information": "undiscovered",
            },
        )
        self.assertEqual(
            [row["id"] for row in view["capability"]["available_actions"]],
            [ACTION_ID],
        )

    def test_target_source_contains_no_phase_b_gameplay_literals(self):
        source = inspect.getsource(dirps_debug_target)
        for literal in [
            '"roadside-tracks"',
            '"investigate-tracks"',
            '"roadside-tracks-status"',
            '"roadside-tracks-outcome"',
            '"roadside-tracks-information"',
            '"clear-trail"',
            '"trail-inconclusive"',
        ]:
            self.assertNotIn(literal, source)

    def test_registered_cli_executes_roadside_encounter(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "dirps_debug_target.py"),
                "--encounter",
                ENCOUNTER_REF,
                "--action",
                ACTION_ID,
                "--actor",
                "pc",
                "--dice",
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
        self.assertEqual(view["execution"]["format"], "dirps-encounter-result.v1")
        self.assertEqual(view["execution"]["outcome_branch"], "success")
        self.assertEqual(
            self.state_values(view["runtime_state"])["roadside-tracks-status"],
            "resolved",
        )
        self.assertEqual(view["capability"]["state"]["status"], "resolved")
        self.assertEqual(view["capability"]["available_actions"], [])


if __name__ == "__main__":
    unittest.main()
