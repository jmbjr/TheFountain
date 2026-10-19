#!/usr/bin/env python3
import copy
import inspect
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dirps_web_target
from dirps_runtime import (
    append_scenario_session_step,
    create_scenario_session_history,
    describe_scenario,
    replay_scenario_session_history,
)
from dirps_web_target import execute_web_target, inspect_web_target
from game_registry import scenario_config
from resolve_dirps_dodge import resolve


class DirpsPhaseIWebTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = scenario_config("dirps", "scenario-01")
        cls.resolved = resolve()
        cls.web_js = (ROOT / "src/renderers/dirps-web.js").read_text()
        cls.web_html = (ROOT / "dirps/index.html").read_text()
        cls.root_html = (ROOT / "index.html").read_text()

    def test_initial_web_view_is_runtime_described(self):
        view = inspect_web_target(self.resolved)
        history = create_scenario_session_history(self.resolved)
        replay = replay_scenario_session_history(
            self.resolved, history, require_complete=False
        )
        expected = describe_scenario(self.resolved, replay["final_state"])

        self.assertEqual(
            view["target"],
            {
                "id": "dirps-web",
                "format": "dirps-web-target.v1",
                "kind": "web",
            },
        )
        self.assertEqual(view["status"], "ready")
        self.assertEqual(view["scenario"], expected)
        self.assertEqual(view["history"], history)
        self.assertEqual(view["history_summary"]["steps"], 0)
        self.assertEqual(view["characters"][0]["name"], "Rook")
        self.assertEqual(view["presentation"]["scenario"]["player_name"], "Rook")
        self.assertEqual(
            view["presentation"]["scenario"]["objective"],
            "Follow the courier's route, discover what happened, and return with an answer.",
        )
        self.assertEqual(
            view["presentation"]["encounter"]["title"],
            "Roadside Tracks",
        )
        self.assertEqual(
            view["presentation"]["available_actions"],
            [
                {
                    "id": expected["available_actions"][0]["id"],
                    "actor_ref": expected["available_actions"][0]["actor_ref"],
                    "label": "Examine the tracks",
                }
            ],
        )
        resolved_pc = next(
            row for row in self.resolved["scene"]["instances"] if row["id"] == "pc"
        )
        self.assertEqual(view["characters"][0]["state"], resolved_pc["state"])
        self.assertEqual(
            view["characters"][0]["state"],
            {
                "st": 10,
                "dx": 11,
                "iq": 11,
                "ht": 10,
                "hit-points": 10,
                "fatigue": 10,
                "stunned": False,
                "unconscious": False,
                "consciousness-check-required": False,
            },
        )
        self.assertEqual(
            view["scenario"]["available_actions"],
            expected["available_actions"],
        )

    def test_px_a_presentation_cannot_add_runtime_actions(self):
        view = inspect_web_target(
            self.resolved,
            presentation_contract={
                "format": "dirps-web-presentation.v1",
                "scenario": {"title": "Presentation only"},
                "encounters": {
                    "roadside-tracks": {"title": "Readable scene"}
                },
                "actions": {
                    "investigate-tracks": {"label": "Readable action"},
                    "invented-action": {"label": "This must never appear"},
                },
            },
        )

        runtime_actions = view["scenario"]["available_actions"]
        presented_actions = view["presentation"]["available_actions"]
        self.assertEqual(
            [action["id"] for action in presented_actions],
            [action["id"] for action in runtime_actions],
        )
        self.assertNotIn(
            "invented-action",
            [action["id"] for action in presented_actions],
        )

    def test_web_execution_is_phase_h_append_result_with_seed_evidence(self):
        history = create_scenario_session_history(self.resolved)
        action = describe_scenario(
            self.resolved,
            replay_scenario_session_history(self.resolved, history)["final_state"],
        )["available_actions"][0]
        seed = "phase-i-web-seed"

        direct = append_scenario_session_step(
            self.resolved,
            history,
            action_id=action["id"],
            actor_ref=action["actor_ref"],
            random_inputs={"random_seed": seed},
        )
        view = execute_web_target(
            self.resolved,
            history,
            action_id=action["id"],
            actor_ref=action["actor_ref"],
            random_seed=seed,
        )

        self.assertEqual(view["history"], direct)
        self.assertEqual(view["history_summary"]["steps"], 1)
        self.assertEqual(
            view["latest_execution"],
            direct["steps"][-1]["transition_record"],
        )
        self.assertEqual(
            view["latest_execution"]["random_inputs"],
            {"random_seed": seed},
        )
        self.assertEqual(
            view["latest_execution"]["mechanic_result"]["skill_resolution"][
                "random_evidence"
            ]["algorithm"],
            "sha256-rejection-v1",
        )

    def test_px_b_encounter_fiction_and_transitions_follow_runtime_progression(self):
        view = inspect_web_target(self.resolved)
        self.assertEqual(
            view["presentation"]["encounter"]["opening_fiction"],
            "At a bend in the old road, Rook finds churned mud, a broken strap, and tracks leading away from the road.",
        )
        self.assertIsNone(view["transition"])

        history = create_scenario_session_history(self.resolved)
        steps = (
            (
                "investigate-tracks",
                "pc",
                {"dice_terms": [3, 3, 4]},
                "frightened-witness",
                "Farther along the road",
            ),
            (
                "reassure-and-question",
                "pc",
                {"dice_terms": [4, 4, 4]},
                "washed-out-path",
                "washed-out stretch",
            ),
            (
                "cross-washed-out-path",
                "pc",
                {"dice_terms": [3, 3, 4]},
                "bandit-scout",
                "bandit scout",
            ),
        )
        for action_id, actor_ref, random_inputs, next_ref, opening_fragment in steps:
            history = append_scenario_session_step(
                self.resolved,
                history,
                action_id=action_id,
                actor_ref=actor_ref,
                random_inputs=random_inputs,
            )
            view = inspect_web_target(self.resolved, history)
            latest = view["latest_execution"]
            self.assertEqual(view["transition"]["to_encounter"], next_ref)
            self.assertEqual(
                view["transition"]["outcome_text"],
                view["resolution_explanation"]["consequence"],
            )
            self.assertIn(
                opening_fragment,
                view["presentation"]["encounter"]["opening_fiction"],
            )
            self.assertEqual(
                [row["id"] for row in view["scenario"]["available_actions"]],
                [row["id"] for row in view["presentation"]["available_actions"]],
            )
            self.assertEqual(
                view["transition"]["to_encounter"],
                latest["progression"]["advanced_to"],
            )

        history = append_scenario_session_step(
            self.resolved,
            history,
            action_id="strike-bandit-scout",
            actor_ref="pc",
            random_inputs={"attack_terms": [1, 1, 1]},
        )
        view = inspect_web_target(self.resolved, history)
        self.assertEqual(
            view["transition"]["key"],
            "bandit-scout:action->bandit-scout:recovery",
        )
        self.assertEqual(
            view["scenario"]["progress"]["step"],
            "recovery",
        )
        self.assertIn("determine whether", view["transition"]["bridge_text"])

        history = append_scenario_session_step(
            self.resolved,
            history,
            action_id="resolve-bandit-next-turn",
            actor_ref="bandit-scout",
            random_inputs={"consciousness_terms": [6, 6, 6]},
        )
        view = inspect_web_target(self.resolved, history)
        self.assertEqual(
            view["transition"]["key"],
            "bandit-scout:recovery->complete:complete",
        )
        self.assertEqual(
            view["transition"]["outcome_text"],
            view["latest_execution"]["progression"]["conclusion_text"],
        )

    def test_px_b_direct_combat_failure_has_terminal_transition(self):
        history = create_scenario_session_history(self.resolved)
        for action_id, actor_ref, random_inputs in (
            ("investigate-tracks", "pc", {"dice_terms": [3, 3, 4]}),
            ("reassure-and-question", "pc", {"dice_terms": [4, 4, 4]}),
            ("cross-washed-out-path", "pc", {"dice_terms": [3, 3, 4]}),
        ):
            history = append_scenario_session_step(
                self.resolved,
                history,
                action_id=action_id,
                actor_ref=actor_ref,
                random_inputs=random_inputs,
            )

        history = append_scenario_session_step(
            self.resolved,
            history,
            action_id="strike-bandit-scout",
            actor_ref="pc",
            random_inputs={"attack_terms": [6, 6, 6]},
        )
        view = inspect_web_target(self.resolved, history)
        latest = view["latest_execution"]
        self.assertTrue(latest["progression"]["terminal"])
        self.assertEqual(latest["progression"]["advanced_to"], "complete")
        self.assertEqual(
            view["transition"]["key"],
            "bandit-scout:action->complete:complete",
        )
        self.assertEqual(view["transition"]["to_encounter"], "complete")
        self.assertEqual(
            view["transition"]["outcome_text"],
            latest["progression"]["conclusion_text"],
        )
        self.assertEqual(
            view["transition"]["bridge_text"],
            "The confrontation ends here.",
        )

    def test_px_b_transition_dom_precedes_next_encounter_fiction(self):
        transition_index = self.web_html.index('id="encounterTransition"')
        title_index = self.web_html.index('id="encounterTitle"')
        purpose_index = self.web_html.index('id="encounterPurpose"')
        actions_index = self.web_html.index('id="availableActions"')
        self.assertLess(transition_index, title_index)
        self.assertLess(title_index, purpose_index)
        self.assertLess(purpose_index, actions_index)

    def test_px_b_transition_projection_cannot_choose_progression(self):
        record = {
            "encounter_ref": "from",
            "step": "action",
            "progression": {
                "advanced_to": "runtime-next",
                "terminal": False,
            },
        }
        scenario = {"progress": {"step": "action"}}
        contract = {
            "transitions": {
                "from:action->presentation-next:action": {
                    "bridge_text": "Wrong destination."
                },
                "from:action->runtime-next:action": {
                    "bridge_text": "Runtime destination."
                },
            }
        }
        transition = dirps_web_target._transition_view(
            scenario,
            record,
            contract,
            {"consequence": "Recorded result."},
        )
        self.assertEqual(transition["to_encounter"], "runtime-next")
        self.assertEqual(transition["bridge_text"], "Runtime destination.")

    def test_px_c_resolution_explanations_copy_runtime_values_without_recalculation(self):
        def facts(section):
            return {row["label"]: row["value"] for row in section["facts"]}

        history = create_scenario_session_history(self.resolved)

        history = append_scenario_session_step(
            self.resolved,
            history,
            action_id="investigate-tracks",
            actor_ref="pc",
            random_inputs={"dice_terms": [3, 3, 4]},
        )
        view = inspect_web_target(self.resolved, history)
        mechanic = view["latest_execution"]["mechanic_result"]
        skill = mechanic["skill_resolution"]
        explanation = view["resolution_explanation"]
        check = facts(explanation["sections"][0])
        self.assertEqual(explanation["title"], "Skill check")
        self.assertEqual(check["Skill"], skill["target"]["skill_ref"])
        self.assertEqual(check["Base"], skill["target"]["base_target"])
        self.assertEqual(check["Modifier"], skill["target"]["modifier_total"])
        self.assertEqual(check["Effective target"], skill["target"]["effective_target"])
        self.assertEqual(check["Roll"], skill["random_evidence"]["total"])
        self.assertEqual(check["Result"], skill["outcome"]["classification"])
        self.assertEqual(check["Success"], skill["outcome"]["success"])
        self.assertEqual(check["Margin"], skill["outcome"]["margin"])
        self.assertEqual(
            explanation["consequence"],
            mechanic["consequence"]["information_text"],
        )

        history = append_scenario_session_step(
            self.resolved,
            history,
            action_id="reassure-and-question",
            actor_ref="pc",
            random_inputs={"dice_terms": [4, 4, 4]},
        )
        view = inspect_web_target(self.resolved, history)
        mechanic = view["latest_execution"]["mechanic_result"]
        reaction = mechanic["reaction_resolution"]
        reaction_facts = facts(view["resolution_explanation"]["sections"][0])
        self.assertEqual(reaction_facts["Roll"], reaction["random_evidence"]["raw_total"])
        self.assertEqual(reaction_facts["Modifier"], reaction["modifier_total"])
        self.assertEqual(reaction_facts["Modified total"], reaction["modified_total"])
        self.assertEqual(reaction_facts["Reaction"], mechanic["reaction"])
        self.assertEqual(
            view["resolution_explanation"]["consequence"],
            mechanic["consequence"]["information_text"],
        )

        history = append_scenario_session_step(
            self.resolved,
            history,
            action_id="cross-washed-out-path",
            actor_ref="pc",
            random_inputs={"dice_terms": [3, 3, 4]},
        )
        view = inspect_web_target(self.resolved, history)
        mechanic = view["latest_execution"]["mechanic_result"]
        attribute = mechanic["attribute_resolution"]
        attribute_facts = facts(view["resolution_explanation"]["sections"][0])
        self.assertEqual(attribute_facts["Attribute"], attribute["target"]["attribute_ref"])
        self.assertEqual(attribute_facts["Base"], attribute["target"]["base_target"])
        self.assertEqual(attribute_facts["Modifier"], attribute["target"]["modifier_total"])
        self.assertEqual(
            attribute_facts["Effective target"],
            attribute["target"]["effective_target"],
        )
        self.assertEqual(attribute_facts["Roll"], attribute["random_evidence"]["total"])
        self.assertEqual(attribute_facts["Margin"], attribute["outcome"]["margin"])
        self.assertEqual(
            view["resolution_explanation"]["consequence"],
            mechanic["consequence"]["consequence_text"],
        )

        before_combat = history
        hit_history = append_scenario_session_step(
            self.resolved,
            before_combat,
            action_id="strike-bandit-scout",
            actor_ref="pc",
            random_inputs={
                "attack_terms": [4, 4, 4],
                "defense_terms": [3, 3, 3],
                "damage_terms": [1],
            },
        )
        hit_view = inspect_web_target(self.resolved, hit_history)
        combat = hit_view["latest_execution"]["mechanic_result"]
        sections = {section["title"]: facts(section) for section in hit_view["resolution_explanation"]["sections"]}
        self.assertEqual(sections["Rook attacks"]["Target"], combat["attack_resolution"]["target"])
        self.assertEqual(sections["Rook attacks"]["Roll"], combat["attack_resolution"]["random_evidence"]["total"])
        self.assertEqual(sections["Bandit defends"]["Target"], combat["defense_resolution"]["target"])
        self.assertEqual(sections["Bandit defends"]["Roll"], combat["defense_resolution"]["random_evidence"]["total"])
        self.assertEqual(sections["Damage and injury"]["Basic damage"], combat["damage_resolution"]["basic_damage"])
        self.assertEqual(sections["Damage and injury"]["Armor DR"], combat["damage_resolution"]["armor_dr"])
        self.assertEqual(sections["Damage and injury"]["Penetrating damage"], combat["damage_resolution"]["penetrating_damage"])
        self.assertEqual(sections["Damage and injury"]["Injury"], combat["damage_resolution"]["injury"])
        self.assertEqual(sections["Bandit condition"]["HP remaining"], combat["injury_effects"]["remaining_hp"])
        self.assertEqual(sections["Bandit condition"]["Stunned"], combat["injury_effects"]["stunned"])

        recovery_history = append_scenario_session_step(
            self.resolved,
            before_combat,
            action_id="strike-bandit-scout",
            actor_ref="pc",
            random_inputs={"attack_terms": [1, 1, 1]},
        )
        recovery_history = append_scenario_session_step(
            self.resolved,
            recovery_history,
            action_id="resolve-bandit-next-turn",
            actor_ref="bandit-scout",
            random_inputs={"consciousness_terms": [6, 6, 6]},
        )
        recovery_view = inspect_web_target(self.resolved, recovery_history)
        recovery = recovery_view["latest_execution"]["mechanic_result"]
        recovery_sections = {
            section["title"]: facts(section)
            for section in recovery_view["resolution_explanation"]["sections"]
        }
        self.assertEqual(
            recovery_sections["Consciousness"]["Target"],
            recovery["consciousness_check"]["target"],
        )
        self.assertEqual(
            recovery_sections["Consciousness"]["Roll"],
            recovery["consciousness_check"]["random_evidence"]["total"],
        )
        self.assertEqual(
            recovery_sections["Consciousness"]["Result"],
            recovery["consciousness_check"]["outcome"]["classification"],
        )
        self.assertEqual(
            recovery_sections["Resulting condition"]["Can act normally"],
            recovery["outcome"]["can_act_normally"],
        )

    def test_px_c_projection_does_not_recompute_recorded_numbers(self):
        record = {
            "mechanic_result": {
                "format": "dirps-encounter-result.v1",
                "skill_resolution": {
                    "target": {
                        "skill_ref": "tracking",
                        "base_target": 91,
                        "modifier_total": -37,
                        "effective_target": 12,
                        "modifiers": [
                            {"amount": -37, "reason": "deliberately inconsistent fixture"}
                        ],
                    },
                    "random_evidence": {"total": 17},
                    "outcome": {
                        "classification": "fixture-result",
                        "success": False,
                        "margin": -123,
                    },
                },
                "consequence": {"information_text": "Recorded consequence."},
                "state_delta": [],
            },
            "progression": {
                "advanced_to": "fixture-next",
                "terminal": False,
                "outcome": None,
            },
        }
        explanation = dirps_web_target._resolution_explanation(record)
        values = {
            row["label"]: row["value"]
            for row in explanation["sections"][0]["facts"]
        }
        self.assertEqual(values["Base"], 91)
        self.assertEqual(values["Modifier"], -37)
        self.assertEqual(values["Effective target"], 12)
        self.assertEqual(values["Roll"], 17)
        self.assertEqual(values["Margin"], -123)
        self.assertEqual(values["Result"], "fixture-result")
        self.assertEqual(explanation["consequence"], "Recorded consequence.")

    def test_px_c_javascript_has_no_mechanic_calculation(self):
        for calculation in (
            "effective_target",
            "modifier_total",
            "basic_damage",
            "penetrating_damage",
            "remaining_hp",
            "consciousness_check_required",
        ):
            self.assertNotIn(calculation, self.web_js)

    def test_px_d_default_hierarchy_demotes_technical_evidence(self):
        framing_index = self.web_html.index('class="dirps-panel dirps-framing"')
        encounter_index = self.web_html.index('id="encounterTitle"')
        actions_index = self.web_html.index('id="availableActions"')
        resolution_index = self.web_html.index('id="lastResolution"')
        condition_index = self.web_html.index('id="characterCondition"')
        progress_index = self.web_html.index('id="playerProgress"')
        advanced_index = self.web_html.index('id="advancedEvidence"')

        self.assertLess(framing_index, encounter_index)
        self.assertLess(encounter_index, actions_index)
        self.assertLess(actions_index, resolution_index)
        self.assertLess(resolution_index, condition_index)
        self.assertLess(condition_index, progress_index)
        self.assertLess(progress_index, advanced_index)

        advanced_open = self.web_html[
            self.web_html.index("<details id=\"advancedEvidence\""):
            self.web_html.index("<summary>Advanced evidence and debug tools</summary>")
        ]
        self.assertNotIn(" open", advanced_open)

        advanced_end = self.web_html.index("</details>", advanced_index)
        advanced_block = self.web_html[advanced_index:advanced_end]
        for element_id in (
            'id="seedInput"',
            'id="character"',
            'id="scenarioState"',
            'id="history"',
            'id="provenance"',
            'id="debugView"',
        ):
            self.assertIn(element_id, advanced_block)

    def test_px_d_renderer_keeps_resolution_evidence_collapsible(self):
        self.assertIn('technicalSummary.textContent = "Technical resolution evidence"', self.web_js)
        self.assertIn('randomTitle.textContent = "Recorded random evidence"', self.web_js)
        self.assertIn('mechanicTitle.textContent = "Mechanic result"', self.web_js)
        self.assertIn('text("runtimeStatus", "Game ready.")', self.web_js)
        self.assertIn(
            'text("runtimeTechnicalStatus", "Shared Python resolver/runtime active in this browser.")',
            self.web_js,
        )

    def test_px_e_ending_copies_both_accepted_terminal_routes(self):
        self.assertIsNone(inspect_web_target(self.resolved)["ending"])

        def advance_to_bandit():
            history = create_scenario_session_history(self.resolved)
            for action_id, actor_ref, random_inputs in (
                ("investigate-tracks", "pc", {"dice_terms": [3, 3, 3]}),
                ("reassure-and-question", "pc", {"dice_terms": [3, 3, 3]}),
                ("cross-washed-out-path", "pc", {"dice_terms": [3, 3, 3]}),
            ):
                history = append_scenario_session_step(
                    self.resolved,
                    history,
                    action_id=action_id,
                    actor_ref=actor_ref,
                    random_inputs=random_inputs,
                )
            return history

        failure_history = append_scenario_session_step(
            self.resolved,
            advance_to_bandit(),
            action_id="strike-bandit-scout",
            actor_ref="pc",
            random_inputs={"attack_terms": [6, 6, 6]},
        )
        failure_view = inspect_web_target(self.resolved, failure_history)
        failure_progression = failure_view["latest_execution"]["progression"]
        self.assertTrue(failure_progression["terminal"])
        self.assertEqual(failure_progression["outcome"], "failure")
        self.assertEqual(
            failure_view["ending"],
            {
                "outcome": failure_progression["outcome"],
                "objective_complete": failure_progression["objective_complete"],
                "conclusion_text": failure_progression["conclusion_text"],
                "actions_resolved": len(failure_history["steps"]),
            },
        )

        success_history = append_scenario_session_step(
            self.resolved,
            advance_to_bandit(),
            action_id="strike-bandit-scout",
            actor_ref="pc",
            random_inputs={"attack_terms": [1, 1, 1]},
        )
        success_history = append_scenario_session_step(
            self.resolved,
            success_history,
            action_id="resolve-bandit-next-turn",
            actor_ref="bandit-scout",
            random_inputs={"consciousness_terms": [6, 6, 6]},
        )
        success_view = inspect_web_target(self.resolved, success_history)
        success_progression = success_view["latest_execution"]["progression"]
        self.assertTrue(success_progression["terminal"])
        self.assertEqual(success_progression["outcome"], "success")
        self.assertEqual(success_view["ending"]["outcome"], success_progression["outcome"])
        self.assertEqual(
            success_view["ending"]["objective_complete"],
            success_progression["objective_complete"],
        )
        self.assertEqual(
            success_view["ending"]["conclusion_text"],
            success_progression["conclusion_text"],
        )
        self.assertEqual(
            success_view["ending"]["actions_resolved"],
            len(success_history["steps"]),
        )

    def test_px_e_hidden_restart_bar_overrides_turnbar_display(self):
        css = (ROOT / "dirps/style.css").read_text()
        self.assertIn(".dirps-turnbar{display:flex", css)
        self.assertIn(".dirps-turnbar[hidden]{display:none}", css)

    def test_px_e_static_page_has_dedicated_terminal_controls(self):
        for element_id in (
            'id="endingPanel"',
            'id="endingTitle"',
            'id="endingConclusion"',
            'id="endingSummary"',
            'id="endingRestart"',
            'id="endingEvidence"',
            'id="activeScenario"',
            'id="restartBar"',
        ):
            self.assertIn(element_id, self.web_html)
        self.assertIn(
            '$("endingRestart").addEventListener("click", restartScenario)',
            self.web_js,
        )
        self.assertIn(
            '$("endingEvidence").addEventListener("click", () => {',
            self.web_js,
        )
        self.assertIn('$("advancedEvidence").open = true', self.web_js)

    def test_px_f_mobile_accessibility_contract_is_explicit(self):
        css = (ROOT / "dirps/style.css").read_text()

        self.assertIn('content="width=device-width, initial-scale=1"', self.web_html)
        self.assertIn(
            'id="runtimeStatus" class="dirps-runtime-status" role="status" aria-live="polite"',
            self.web_html,
        )
        self.assertIn('id="fatal" class="dirps-panel dirps-error" role="alert"', self.web_html)
        self.assertIn(
            'id="lastResolutionPanel" class="dirps-panel" tabindex="-1"',
            self.web_html,
        )
        self.assertIn(
            'id="endingPanel" class="dirps-panel dirps-ending" tabindex="-1"',
            self.web_html,
        )

        for rule in (
            "min-height:48px",
            "min-height:44px",
            "button:focus-visible",
            '@media(max-width:520px)',
            ".dirps-condition-grid{grid-template-columns:repeat(2,minmax(0,1fr))}",
        ):
            self.assertIn(rule, css)

        self.assertIn('button.type = "button"', self.web_js)
        self.assertIn('function focusAfterAction()', self.web_js)
        self.assertIn('target.focus()', self.web_js)
        self.assertIn('function focusCurrentAction()', self.web_js)
        self.assertIn('if (action) action.focus()', self.web_js)

    def test_web_target_can_drive_complete_scenario_without_owning_choices(self):
        view = inspect_web_target(self.resolved)
        for index in range(1, 8):
            if view["status"] == "complete":
                break
            actions = view["scenario"]["available_actions"]
            self.assertTrue(actions)
            action = actions[0]
            view = execute_web_target(
                self.resolved,
                view["history"],
                action_id=action["id"],
                actor_ref=action["actor_ref"],
                random_seed=f"phase-i-step-{index}",
            )

        self.assertEqual(view["status"], "complete")
        self.assertIn(view["scenario"]["progress"]["outcome"], {"success", "failure"})
        replay = replay_scenario_session_history(
            self.resolved,
            view["history"],
            require_complete=True,
        )
        self.assertEqual(replay["final_state_hash"], view["history_summary"]["final_state_hash"])
        print("PASS dirps/scenario-01: Phase I player-facing Web target consumes shared runtime")

    def test_web_error_is_visible_and_preserves_input_history(self):
        history = create_scenario_session_history(self.resolved)
        before = copy.deepcopy(history)
        view = execute_web_target(
            self.resolved,
            history,
            action_id="unavailable-action",
            actor_ref="pc",
            random_seed="phase-i-error",
        )
        self.assertEqual(view["status"], "error")
        self.assertEqual(view["history"], before)
        self.assertEqual(history, before)
        self.assertIn("unavailable", view["error"]["message"])

    def test_web_adapter_contains_no_scenario_gameplay_literals(self):
        source = inspect.getsource(dirps_web_target)
        for literal in (
            '"roadside-tracks"',
            '"frightened-witness"',
            '"washed-out-path"',
            '"bandit-scout"',
            '"investigate-tracks"',
            '"reassure-and-question"',
            '"cross-washed-out-path"',
            '"strike-bandit-scout"',
            '"resolve-bandit-next-turn"',
        ):
            self.assertNotIn(literal, source)

    def test_javascript_is_presentation_and_python_bootstrap_only(self):
        self.assertIn(
            'https://cdn.jsdelivr.net/pyodide/v0.29.1/full/pyodide.mjs',
            self.web_js,
        )
        for path in (
            "../tools/game_registry.py",
            "../tools/dirps_semantic_validation.py",
            "../tools/resolve_dirps_dodge.py",
            "../tools/dirps_runtime.py",
            "../tools/dirps_web_target.py",
            "../game/dirps/game.json",
            "../game/dirps/dodge/dirps-scenario-01.dodge.v0.2.1.json",
            "../game/dirps/scenarios/scenario-01/scenario.json",
            "../game/dirps/scenarios/scenario-01/export-contracts/web-presentation.json",
            "../game/dirps/sidecars/dirps.proto.sidecar.v0.1.json",
        ):
            self.assertIn(path, self.web_js)

        for literal in (
            "roadside-tracks",
            "frightened-witness",
            "washed-out-path",
            "bandit-scout",
            "investigate-tracks",
            "reassure-and-question",
            "cross-washed-out-path",
            "strike-bandit-scout",
            "resolve-bandit-next-turn",
            "attack_terms",
            "defense_terms",
            "damage_terms",
            "consciousness_terms",
            "stun_terms",
        ):
            self.assertNotIn(literal, self.web_js)

        self.assertIn('{"random_seed": random_seed}', inspect.getsource(dirps_web_target))
        self.assertIn("character.state || {}", self.web_js)
        self.assertIn("stateRow.dataset.stateKey = key", self.web_js)
        self.assertNotIn("Math.random", self.web_js)

    def test_static_page_exposes_player_and_debug_views(self):
        for element_id in (
            'id="runtimeStatus"',
            'id="playerIdentity"',
            'id="playerRole"',
            'id="scenarioPremise"',
            'id="scenarioObjective"',
            'id="scenarioScope"',
            'id="encounterTitle"',
            'id="encounterTransition"',
            'id="transitionOutcome"',
            'id="transitionBridge"',
            'id="availableActions"',
            'id="characterCondition"',
            'id="playerProgress"',
            'id="advancedEvidence"',
            'id="endingPanel"',
            'id="endingTitle"',
            'id="endingConclusion"',
            'id="endingSummary"',
            'id="endingRestart"',
            'id="endingEvidence"',
            'id="runtimeTechnicalStatus"',
            'id="character"',
            'id="scenarioState"',
            'id="lastResolutionPanel"',
            'id="lastResolution"',
            'id="provenance"',
            'id="history"',
            'id="debugView"',
        ):
            self.assertIn(element_id, self.web_html)
        self.assertIn('../src/renderers/dirps-web.js', self.web_html)
        self.assertIn('href="dirps/"', self.root_html)

    def test_game_registry_declares_both_debug_and_web_targets(self):
        descriptor = json.loads((ROOT / "game/dirps/game.json").read_text())
        targets = descriptor["scenarios"]["scenario-01"]["generated_targets"]
        self.assertEqual(targets["debug-cli"], "../../tools/dirps_debug_target.py")
        self.assertEqual(targets["web"], "../../dirps/index.html")


if __name__ == "__main__":
    unittest.main()
