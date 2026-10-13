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
    execute_encounter_target,
    execute_social_target,
    inspect_encounter_target,
    inspect_social_target,
)
from dirps_runtime import (
    ExecutionError,
    create_social_runtime_state,
    describe_social_interaction,
    execute_social_interaction,
    replay_social_interaction,
)
from game_registry import scenario_config
from resolve_dirps_dodge import ResolutionError, resolve, resolve_documents


ENCOUNTER_REF = "frightened-witness"
ACTION_ID = "reassure-and-question"


class DirpsPhaseCFrightenedWitnessTests(unittest.TestCase):
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

    def action(self, canonical):
        encounter = next(
            row for row in canonical["encounters"] if row["id"] == ENCOUNTER_REF
        )
        return encounter["actions"][0]

    def resolved_with_modifier(self, amount):
        canonical = copy.deepcopy(self.canonical)
        self.action(canonical)["reaction_modifiers"][0]["amount"] = amount
        return resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)

    def resolved_with_good_information(self, information):
        canonical = copy.deepcopy(self.canonical)
        sidecar = copy.deepcopy(self.sidecar)
        self.action(canonical)["consequences"]["good"]["information"] = information
        sidecar["phase_c_social_bindings"][ENCOUNTER_REF]["consequences"]["good"][
            "effect_refs"
        ][2] = f"frightened-witness-set-information-{information}"
        return resolve_documents(self.dodge, canonical, sidecar, self.cfg)

    def execute(self, resolved=None, state=None, terms=None, seed=None):
        resolved = resolved if resolved is not None else self.resolved
        state = state if state is not None else create_social_runtime_state(
            resolved, encounter_ref=ENCOUNTER_REF
        )
        return execute_social_interaction(
            resolved,
            state,
            encounter_ref=ENCOUNTER_REF,
            action_id=ACTION_ID,
            actor_ref="pc",
            dice_terms=terms,
            random_seed=seed,
        )

    def test_initial_social_state_and_action_are_runtime_described(self):
        state = create_social_runtime_state(
            self.resolved, encounter_ref=ENCOUNTER_REF
        )
        self.assertEqual(state["scenario_ref"], "scenario-01")
        self.assertEqual(state["revision"], "0")
        self.assertEqual(
            self.state_values(state),
            {
                "frightened-witness-status": "ready",
                "frightened-witness-reaction": "unresolved",
                "frightened-witness-information": "unknown",
            },
        )
        capability = describe_social_interaction(
            self.resolved, state, encounter_ref=ENCOUNTER_REF
        )
        self.assertEqual(
            capability["state"],
            {
                "status": "ready",
                "reaction": "unresolved",
                "information": "unknown",
            },
        )
        self.assertEqual(
            [row["id"] for row in capability["available_actions"]],
            [ACTION_ID],
        )
        self.assertEqual(
            capability["reaction_capability"]["procedure_ref"],
            "reaction-roll",
        )
        self.assertEqual(
            capability["reaction_capability"]["procedure_authority"],
            "authoritative",
        )
        table = capability["reaction_capability"]["lookup_table"]
        self.assertEqual(table["source_ref"], "gurps-lite")
        self.assertEqual(table["authority"], "authoritative")
        self.assertEqual(len(table["rows"]), 8)

    def test_good_reaction_produces_useful_information_and_state_delta(self):
        record = self.execute(terms=[4, 4, 4])
        self.assertEqual(record["format"], "dirps-social-encounter-result.v1")
        self.assertEqual(
            record["reaction_resolution"]["format"],
            "dirps-reaction-result.v1",
        )
        self.assertEqual(
            record["reaction_resolution"]["random_evidence"]["terms"],
            [4, 4, 4],
        )
        self.assertEqual(record["reaction_resolution"]["random_evidence"]["raw_total"], 12)
        self.assertEqual(record["reaction_resolution"]["modifier_total"], 1)
        self.assertEqual(record["reaction_resolution"]["modified_total"], 13)
        self.assertEqual(record["reaction"], "good")
        self.assertEqual(
            self.state_values(record["state_after"]),
            {
                "frightened-witness-status": "resolved",
                "frightened-witness-reaction": "good",
                "frightened-witness-information": "useful-lead",
            },
        )
        self.assertEqual(
            record["consequence"]["information_text"],
            "The witness gives a useful direction for continuing the search toward the washed-out path.",
        )
        self.assertEqual(
            [row["ref"] for row in record["state_delta"]],
            [
                "frightened-witness-status",
                "frightened-witness-reaction",
                "frightened-witness-information",
            ],
        )
        self.assertEqual(record["state_before"]["revision"], "0")
        self.assertEqual(record["state_after"]["revision"], "1")
        print("PASS dirps/scenario-01: Phase C Frightened Witness social encounter")

    def test_neutral_and_poor_reactions_have_distinct_information_consequences(self):
        neutral = self.execute(terms=[3, 3, 4])
        poor = self.execute(terms=[2, 3, 3])
        self.assertEqual(neutral["reaction"], "neutral")
        self.assertEqual(
            self.state_values(neutral["state_after"])["frightened-witness-information"],
            "partial-account",
        )
        self.assertEqual(poor["reaction"], "poor")
        self.assertEqual(
            self.state_values(poor["state_after"])["frightened-witness-information"],
            "no-useful-account",
        )

    def test_reaction_lookup_executes_all_eight_authoritative_bands(self):
        cases = [
            (-4, [1, 1, 1], "disastrous"),
            (-2, [1, 1, 1], "very-bad"),
            (1, [1, 1, 1], "bad"),
            (1, [2, 3, 3], "poor"),
            (1, [3, 3, 4], "neutral"),
            (1, [4, 4, 4], "good"),
            (1, [5, 5, 5], "very-good"),
            (1, [6, 6, 6], "excellent"),
        ]
        for modifier, terms, expected in cases:
            with self.subTest(expected=expected):
                resolved = (
                    self.resolved
                    if modifier == 1
                    else self.resolved_with_modifier(modifier)
                )
                record = self.execute(resolved=resolved, terms=terms)
                self.assertEqual(record["reaction"], expected)

    def test_modifier_perturbation_flows_canonical_source_to_reaction_result(self):
        baseline = self.execute(terms=[1, 1, 1])
        changed = self.execute(
            resolved=self.resolved_with_modifier(-4),
            terms=[1, 1, 1],
        )
        self.assertEqual(baseline["reaction_resolution"]["modifier_total"], 1)
        self.assertEqual(baseline["reaction"], "bad")
        self.assertEqual(changed["reaction_resolution"]["modifier_total"], -4)
        self.assertEqual(changed["reaction"], "disastrous")

    def test_modifier_rule_authority_drift_is_rejected_before_runtime(self):
        canonical = copy.deepcopy(self.canonical)
        modifier = self.action(canonical)["reaction_modifiers"][0]
        modifier["rule_source_ref"] = "scenario-01-source"
        with self.assertRaisesRegex(
            ResolutionError,
            "reaction modifier rule_source_ref must be gurps-lite",
        ):
            resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)

    def test_modifier_source_binding_drift_is_rejected_at_runtime(self):
        resolved = copy.deepcopy(self.resolved)
        resolved["proto_sidecar"]["phase_c_social_bindings"][ENCOUNTER_REF][
            "modifier_source"
        ]["path"] = "scenario.invalid[].modifiers"

        state = create_social_runtime_state(
            self.resolved, encounter_ref=ENCOUNTER_REF
        )
        with self.assertRaisesRegex(
            ExecutionError,
            "reaction-modifier source binding is unsupported or malformed",
        ):
            execute_social_interaction(
                resolved,
                state,
                encounter_ref=ENCOUNTER_REF,
                action_id=ACTION_ID,
                actor_ref="pc",
                dice_terms=[4, 4, 4],
            )

    def test_authoritative_lookup_table_drift_is_rejected(self):
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["phase_c_lookup_tables"]["gurps-lite-reaction-table"]["rows"][4][
            "when"
        ]["max"] = 11
        with self.assertRaisesRegex(
            ResolutionError,
            "Reaction Table lookup exactly",
        ):
            resolve_documents(self.dodge, self.canonical, sidecar, self.cfg)

    def test_canonical_consequence_change_with_stale_bridge_is_rejected(self):
        canonical = copy.deepcopy(self.canonical)
        self.action(canonical)["consequences"]["good"]["information"] = "partial-account"
        with self.assertRaisesRegex(
            ResolutionError,
            "social binding must match the declared reaction contract",
        ):
            resolve_documents(self.dodge, canonical, self.sidecar, self.cfg)

    def test_normalized_consequence_bridge_perturbation_flows_to_state(self):
        resolved = self.resolved_with_good_information("partial-account")
        record = self.execute(resolved=resolved, terms=[4, 4, 4])
        self.assertEqual(record["reaction"], "good")
        self.assertEqual(
            self.state_values(record["state_after"])["frightened-witness-information"],
            "partial-account",
        )

    def test_seeded_social_roll_is_deterministic_and_replays(self):
        first = self.execute(seed="phase-c-seed")
        second = self.execute(seed="phase-c-seed")
        changed = self.execute(seed="phase-c-seed-2")
        self.assertEqual(first, second)
        self.assertEqual(
            first["reaction_resolution"]["random_evidence"]["terms"],
            [2, 3, 2],
        )
        self.assertEqual(first["reaction"], "poor")
        self.assertEqual(
            changed["reaction_resolution"]["random_evidence"]["terms"],
            [4, 6, 6],
        )
        self.assertEqual(changed["reaction"], "very-good")
        self.assertEqual(replay_social_interaction(self.resolved, first), first)

    def test_social_replay_detects_tampered_reaction_and_state(self):
        record = self.execute(terms=[4, 4, 4])
        tampered = copy.deepcopy(record)
        tampered["reaction_resolution"]["reaction"] = "excellent"
        with self.assertRaisesRegex(ExecutionError, "social encounter record divergence"):
            replay_social_interaction(self.resolved, tampered)

        tampered = copy.deepcopy(record)
        tampered["state_delta"][1]["after"] = "neutral"
        with self.assertRaisesRegex(ExecutionError, "social encounter record divergence"):
            replay_social_interaction(self.resolved, tampered)

    def test_resolved_social_encounter_cannot_be_repeated(self):
        first = self.execute(terms=[4, 4, 4])
        state = copy.deepcopy(first["state_after"])
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(ExecutionError, "unavailable in current runtime state"):
            self.execute(state=state, terms=[4, 4, 4])
        self.assertEqual(state, before)
        capability = describe_social_interaction(
            self.resolved, state, encounter_ref=ENCOUNTER_REF
        )
        self.assertEqual(capability["available_actions"], [])

    def test_phase_c_lookup_evidence_remains_non_candidate(self):
        specs = self.resolved["proto_sidecar"]["proto_specs"]
        self.assertEqual(specs["lookup_tables"]["status"], "exercised")
        self.assertEqual(
            specs["lookup_tables"]["candidate_for_dodge"],
            "not-yet-candidate",
        )
        self.assertEqual(
            specs["reaction_timing"]["candidate_for_dodge"],
            "not-yet-candidate",
        )
        self.assertEqual(specs["replay_session_history"]["status"], "suspected")

    def test_social_target_inspects_executes_and_refreshes_post_state(self):
        view = inspect_social_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
        )
        self.assertEqual(view["status"], "ready")
        self.assertEqual(
            [row["id"] for row in view["capability"]["available_actions"]],
            [ACTION_ID],
        )

        executed = execute_social_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
            action_id=ACTION_ID,
            actor_ref="pc",
            dice_terms=[4, 4, 4],
        )
        self.assertEqual(executed["status"], "ok")
        self.assertEqual(executed["execution"]["reaction"], "good")
        self.assertEqual(executed["runtime_state"], executed["execution"]["state_after"])
        self.assertEqual(
            executed["capability"]["state"],
            {
                "status": "resolved",
                "reaction": "good",
                "information": "useful-lead",
            },
        )
        self.assertEqual(executed["capability"]["available_actions"], [])
        print("PASS dirps/scenario-01: Phase C debug target consumes social runtime")

    def test_generic_target_dispatches_both_accepted_encounter_kinds(self):
        social = inspect_encounter_target(self.resolved, encounter_ref=ENCOUNTER_REF)
        roadside = inspect_encounter_target(self.resolved, encounter_ref="roadside-tracks")
        self.assertEqual(social["target"]["format"], "dirps-debug-social-target.v1")
        self.assertEqual(roadside["target"]["format"], "dirps-debug-encounter-target.v1")

        executed = execute_encounter_target(
            self.resolved,
            encounter_ref=ENCOUNTER_REF,
            action_id=ACTION_ID,
            actor_ref="pc",
            dice_terms=[4, 4, 4],
        )
        self.assertEqual(executed["execution"]["reaction"], "good")

    def test_social_target_passes_fake_result_and_runtime_capability_through(self):
        fake_state = {
            "scenario_ref": "fake",
            "bindings": [],
            "events": [],
            "revision": "8",
        }
        fake_record = {
            "format": "fake-social-result",
            "state_after": {"revision": "9"},
            "reaction": "runtime-owned",
        }
        pre_capability = {
            "encounter": {"id": "fake"},
            "state": {"phase": "pre"},
            "available_actions": [{"id": "fake-action"}],
        }
        post_capability = {
            "encounter": {"id": "fake"},
            "state": {"phase": "post"},
            "available_actions": [],
        }
        described = []

        def fake_describe(resolved, state, encounter_ref):
            described.append(state)
            return pre_capability if len(described) == 1 else post_capability

        view = execute_social_target(
            self.resolved,
            encounter_ref="input-encounter",
            action_id="input-action",
            actor_ref="input-actor",
            dice_terms=[99],
            runtime_create=lambda resolved, encounter_ref: fake_state,
            runtime_describe=fake_describe,
            runtime_execute=lambda *args, **kwargs: fake_record,
        )
        self.assertEqual(view["status"], "ok")
        self.assertIs(view["execution"], fake_record)
        self.assertEqual(view["runtime_state"], fake_record["state_after"])
        self.assertIs(view["capability"], post_capability)
        self.assertEqual(described, [fake_state, fake_record["state_after"]])

    def test_target_source_contains_no_phase_c_gameplay_literals(self):
        source = inspect.getsource(dirps_debug_target)
        for literal in [
            '"frightened-witness"',
            '"reassure-and-question"',
            '"frightened-witness-status"',
            '"frightened-witness-reaction"',
            '"frightened-witness-information"',
            '"useful-lead"',
            '"partial-account"',
            '"no-useful-account"',
        ]:
            self.assertNotIn(literal, source)

    def test_registered_cli_executes_social_encounter(self):
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
                "4",
                "4",
                "4",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        view = json.loads(proc.stdout)
        self.assertEqual(view["status"], "ok")
        self.assertEqual(
            view["execution"]["format"],
            "dirps-social-encounter-result.v1",
        )
        self.assertEqual(view["execution"]["reaction"], "good")
        self.assertEqual(view["capability"]["state"]["status"], "resolved")
        self.assertEqual(view["capability"]["available_actions"], [])


if __name__ == "__main__":
    unittest.main()
