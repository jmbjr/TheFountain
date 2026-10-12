import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "game/dirps/dodge/dirps-scenario-01.dodge.v0.2.1.json"
GAME_PATH = ROOT / "game/dirps/game.json"


def load_doc():
    return json.loads(DOC_PATH.read_text())


def walk_steps(steps):
    for step in steps or []:
        yield step
        for key in ("steps", "options", "else_steps"):
            yield from walk_steps(step.get(key, []))
        for option in step.get("choice_options", []) or []:
            yield from walk_steps(option.get("steps", []))
        for branch in step.get("branches", []) or []:
            yield from walk_steps(branch.get("steps", []))


def duplicate_values(values):
    seen = set()
    dup = set()
    for value in values:
        if value in seen:
            dup.add(value)
        seen.add(value)
    return dup


def validate_dirps_core(doc):
    failures = []
    sources = doc.get("sources", {})
    archetypes = doc.get("archetypes", {})
    objects = doc.get("objects", {})
    scenes = doc.get("scenes", {})
    rules = doc.get("rules", {})
    scenarios = doc.get("scenarios", {})
    topologies = doc.get("topologies", {})
    representations = doc.get("representations", {})
    entity_invocations = doc.get("entity_invocations", {})

    values = rules.get("values", {})
    resources = rules.get("resources", {})
    requirements = rules.get("requirements", {})
    modifiers = rules.get("modifiers", {})
    conditions = rules.get("conditions", {})
    effects = rules.get("effects", {})
    actions = rules.get("actions", {})
    procedures = rules.get("procedures", {})
    phases = rules.get("phases", {})
    ai_profiles = rules.get("ai_profiles", {})

    rule_tables = {
        "value": values,
        "resource": resources,
        "requirement": requirements,
        "modifier": modifiers,
        "condition": conditions,
        "effect": effects,
        "action": actions,
        "procedure": procedures,
        "phase": phases,
        "ai": ai_profiles,
    }

    def rule_ref_owner(ref):
        return [kind for kind, table in rule_tables.items() if ref in table]

    def require_rule_ref(owner, ref, expected_kinds):
        if not ref:
            return
        expected = tuple(expected_kinds)
        if any(ref in rule_tables[kind] for kind in expected):
            return
        actual = rule_ref_owner(ref)
        if actual:
            failures.append(
                f"15.3.8 {owner} expected {expected} ref but {ref} belongs to {tuple(actual)}"
            )
        else:
            failures.append(f"15.3.1 {owner} unresolved rule ref: {ref}")

    def require_source_ref(owner, ref):
        if ref and ref not in sources:
            failures.append(f"15.3.1 {owner} unresolved source_ref: {ref}")

    def walk_source_refs(node, path="$"):
        if isinstance(node, dict):
            for key, value in node.items():
                current = f"{path}.{key}"
                if key == "source_ref":
                    require_source_ref(current, value)
                elif key != "extensions":
                    walk_source_refs(value, current)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk_source_refs(value, f"{path}[{index}]")

    def validate_operand(owner, operand):
        if isinstance(operand, dict) and "ref" in operand:
            require_rule_ref(owner, operand["ref"], ("value", "resource"))

    def validate_condition(owner, condition):
        if isinstance(condition, str):
            require_rule_ref(owner, condition, ("condition",))
            return
        if not isinstance(condition, dict):
            return
        validate_operand(f"{owner}.left", condition.get("left"))
        validate_operand(f"{owner}.right", condition.get("right"))
        for index, nested in enumerate(condition.get("conditions", []) or []):
            validate_condition(f"{owner}.conditions[{index}]", nested)
        require_source_ref(f"{owner}.source_ref", condition.get("source_ref"))

    for source_id, source in sources.items():
        uri = source.get("uri", "")
        if uri and not uri.startswith(("http://", "https://")) and not (ROOT / uri).exists():
            failures.append(f"15.3.1 missing local source URI {source_id}: {uri}")

    # Every normative source_ref in the candidate is checked, including sidecars
    # and rule/value/condition/action/procedure declarations. Extensions are
    # intentionally opaque to DODGE core.
    walk_source_refs({key: value for key, value in doc.items() if key != "extensions"})

    for sidecar_index, sidecar in enumerate(doc.get("sidecars", [])):
        require_source_ref(f"sidecars[{sidecar_index}].source_ref", sidecar.get("source_ref"))

    for object_id, obj in objects.items():
        archetype_ref = obj.get("archetype_ref")
        if archetype_ref not in archetypes:
            failures.append(f"15.3.1 object {object_id} unresolved archetype_ref: {archetype_ref}")

    for scene_id, scene in scenes.items():
        for instance_index, instance in enumerate(scene.get("instances", [])):
            object_ref = instance.get("object_ref")
            if object_ref not in objects:
                failures.append(
                    f"15.3.1 scene {scene_id} instance[{instance_index}] unresolved object_ref: {object_ref}"
                )

    for condition_id, condition in conditions.items():
        validate_condition(f"condition {condition_id}", condition)

    for action_id, action in actions.items():
        for ref in action.get("condition_refs", []):
            require_rule_ref(f"action {action_id}.condition_refs", ref, ("condition",))
        require_rule_ref(f"action {action_id}.procedure_ref", action.get("procedure_ref"), ("procedure",))
        for ref in action.get("effect_refs", []):
            require_rule_ref(f"action {action_id}.effect_refs", ref, ("effect",))

    step_expected_kinds = {
        "action": ("action",),
        "condition": ("condition",),
        "effect": ("effect",),
        "procedure": ("procedure",),
        "phase": ("phase",),
        "ai": ("ai",),
    }
    for proc_id, proc in procedures.items():
        for step in walk_steps(proc.get("steps", [])):
            kind, ref = step.get("kind"), step.get("ref")
            if kind in step_expected_kinds and ref:
                require_rule_ref(
                    f"procedure {proc_id} step[{kind}]", ref, step_expected_kinds[kind]
                )
            if step.get("condition_ref"):
                require_rule_ref(
                    f"procedure {proc_id}.condition_ref",
                    step["condition_ref"],
                    ("condition",),
                )
            if step.get("condition"):
                validate_condition(f"procedure {proc_id}.condition", step["condition"])

    for scenario_id, scenario in scenarios.items():
        scene_ref = scenario.get("scene_ref")
        if scene_ref not in scenes:
            failures.append(f"15.3.1 scenario {scenario_id} unresolved scene_ref: {scene_ref}")
        for ref in scenario.get("action_refs", []):
            require_rule_ref(f"scenario {scenario_id}.action_refs", ref, ("action",))
        require_rule_ref(
            f"scenario {scenario_id}.turn_procedure_ref",
            scenario.get("turn_procedure_ref"),
            ("procedure",),
        )
        for objective_index, objective in enumerate(scenario.get("objectives", [])):
            validate_condition(
                f"scenario {scenario_id}.objectives[{objective_index}].completion",
                objective.get("completion"),
            )
        for end_index, end_condition in enumerate(scenario.get("end_conditions", [])):
            validate_condition(
                f"scenario {scenario_id}.end_conditions[{end_index}].condition",
                end_condition.get("condition"),
            )

    for object_id, obj in objects.items():
        arch = archetypes.get(obj.get("archetype_ref"), {})
        if obj.get("kind") != arch.get("kind"):
            failures.append(f"15.3.2 object/archetype kind mismatch: {object_id}")
        slots = [slot.get("id") for slot in arch.get("face_slots", [])]
        if duplicate_values(slots):
            failures.append(f"15.3.2 duplicate archetype face slot: {object_id}")
        for face in obj.get("faces", []):
            if face.get("slot") not in slots:
                failures.append(f"15.3.2 face slot missing from archetype: {object_id}")

    collection_graph = {
        oid: {m.get("object_ref") for m in obj.get("members", []) if m.get("object_ref")}
        for oid, obj in objects.items() if obj.get("kind") == "collection"
    }
    proc_graph = {pid: set() for pid in procedures}
    for pid, proc in procedures.items():
        for step in walk_steps(proc.get("steps", [])):
            if step.get("kind") == "procedure" and step.get("ref"):
                proc_graph[pid].add(step["ref"])

    def cycle(graph):
        visiting, visited = set(), set()

        def visit(node):
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for nxt in graph.get(node, set()):
                if nxt in graph and visit(nxt):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in graph)

    if cycle(collection_graph):
        failures.append("15.3.3 collection nesting cycle")
    if cycle(proc_graph):
        failures.append("15.3.3 procedure reference cycle")

    explicit_quantities = []
    for scene in scenes.values():
        explicit_quantities.extend(i["quantity"] for i in scene.get("instances", []) if "quantity" in i)
    for obj in objects.values():
        explicit_quantities.extend(m["quantity"] for m in obj.get("members", []) if "quantity" in m)
    dimensions = [obj.get("component", {}).get("dimensions") for obj in objects.values()]
    dimensions = [d for d in dimensions if d]
    if explicit_quantities or dimensions:
        failures.append("15.3.4 audit assumption changed: explicit quantities/dimensions are now present")

    if any(source.get("sha256") for source in sources.values()):
        failures.append("15.3.5 audit assumption changed: source hashes are now declared")

    for scene_id, scene in scenes.items():
        ids = [i.get("id") for i in scene.get("instances", [])]
        if duplicate_values(ids):
            failures.append(f"15.3.6 duplicate scene instance id in {scene_id}")
    for topology_id, topology in topologies.items():
        ids = [n.get("id") for n in topology.get("nodes", [])]
        if duplicate_values(ids):
            failures.append(f"15.3.6 duplicate topology node id in {topology_id}")

    if any(topology.get("edges") for topology in topologies.values()):
        failures.append("15.3.7 audit assumption changed: topology edges are now present")

    for family_name, family in (("value", values), ("resource", resources)):
        for item_id, definition in family.items():
            if "default" not in definition:
                continue
            value = definition["default"]
            typ = definition.get("type")
            ok = True
            if typ == "boolean":
                ok = isinstance(value, bool)
            elif typ == "integer":
                ok = isinstance(value, int) and not isinstance(value, bool)
            elif typ == "number":
                ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            elif typ == "string":
                ok = isinstance(value, str)
            if ok and "minimum" in definition:
                ok = value >= definition["minimum"]
            if ok and "maximum" in definition:
                ok = value <= definition["maximum"]
            if not ok:
                failures.append(f"15.3.9 invalid default for {family_name} {item_id}")

    if phases:
        failures.append("15.3.10 audit assumption changed: phases are now present")
    if any(scenario.get("end_conditions") for scenario in scenarios.values()):
        failures.append("15.3.10 executable end conditions are present and require deterministic validation")

    if ai_profiles:
        failures.append("15.3.11 audit assumption changed: AI profiles are now present")

    game = json.loads(GAME_PATH.read_text())
    scenario_descriptor = game["scenarios"]["scenario-01"]
    if scenario_descriptor.get("export_contracts") or scenario_descriptor.get("targets"):
        failures.append("15.3.12 audit assumption changed: a target contract/target is now registered")

    if representations:
        failures.append("15.3 representations audit assumption changed: representations are now present")

    object_invocations = any(obj.get("invocations") for obj in objects.values())
    member_invocations = any(
        member.get("invocations")
        for obj in objects.values()
        for member in obj.get("members", [])
    )
    if object_invocations or member_invocations or entity_invocations:
        failures.append("15.3 invocations audit assumption changed: invocations are now present")

    if requirements or modifiers:
        failures.append("15.3 conditional audit assumption changed: requirements/modifiers are now present")
    if any(obj.get("equipment") for obj in objects.values()):
        failures.append("15.3 conditional audit assumption changed: normalized equipment is now present")

    choices = []
    for proc_id, proc in procedures.items():
        for step in walk_steps(proc.get("steps", [])):
            if step.get("kind") == "choice":
                choices.append((proc_id, step))
    if not choices:
        failures.append("15.3 conditional choice evidence missing: expected tutorial-turn choice")
    for proc_id, step in choices:
        options = step.get("choice_options")
        if not options or len(options) < 2:
            failures.append(f"15.3 choice {proc_id} must use at least two named choice_options")
            continue
        ids = [option.get("id") for option in options]
        if any(not option_id for option_id in ids) or duplicate_values(ids):
            failures.append(f"15.3 choice {proc_id} option ids must be present and unique")
        for option in options:
            for ref in option.get("condition_refs", []):
                require_rule_ref(
                    f"choice {proc_id}/{option.get('id')}.condition_refs",
                    ref,
                    ("condition",),
                )
            for nested in walk_steps(option.get("steps", [])):
                kind, ref = nested.get("kind"), nested.get("ref")
                if kind in step_expected_kinds and ref:
                    require_rule_ref(
                        f"choice {proc_id}/{option.get('id')} step[{kind}]",
                        ref,
                        step_expected_kinds[kind],
                    )

    return failures


class DirpsG2CoreValidationTests(unittest.TestCase):
    def test_every_applicable_15_3_rule_passes(self):
        self.assertEqual(validate_dirps_core(load_doc()), [])

    def test_negative_missing_reference_is_rejected(self):
        doc = load_doc()
        doc["objects"]["tutorial-pc"]["archetype_ref"] = "missing-archetype"
        self.assertTrue(any("15.3.1" in x for x in validate_dirps_core(doc)))

    def test_negative_rule_source_ref_is_rejected(self):
        doc = load_doc()
        doc["rules"]["values"]["st"]["source_ref"] = "missing-source"
        self.assertTrue(any("15.3.1" in x for x in validate_dirps_core(doc)))

    def test_negative_operand_ref_is_rejected(self):
        doc = load_doc()
        doc["rules"]["conditions"]["actor-conscious"]["left"]["ref"] = "missing-value"
        self.assertTrue(any("15.3.1" in x for x in validate_dirps_core(doc)))

    def test_negative_operand_wrong_kind_is_rejected(self):
        doc = load_doc()
        doc["rules"]["conditions"]["actor-conscious"]["left"]["ref"] = "attempt-skill"
        self.assertTrue(any("15.3.8" in x for x in validate_dirps_core(doc)))

    def test_negative_sidecar_source_ref_is_rejected(self):
        doc = load_doc()
        doc["sidecars"][0]["source_ref"] = "missing-sidecar-source"
        self.assertTrue(any("15.3.1" in x for x in validate_dirps_core(doc)))

    def test_negative_face_slot_mismatch_is_rejected(self):
        doc = load_doc()
        doc["objects"]["tutorial-pc"]["faces"][0]["slot"] = "missing-slot"
        self.assertTrue(any("15.3.2" in x for x in validate_dirps_core(doc)))

    def test_negative_procedure_cycle_is_rejected(self):
        doc = load_doc()
        doc["rules"]["procedures"]["success-roll"]["steps"] = [
            {"kind": "procedure", "ref": "success-roll"}
        ]
        self.assertTrue(any("15.3.3" in x for x in validate_dirps_core(doc)))

    def test_negative_duplicate_instance_id_is_rejected(self):
        doc = load_doc()
        instances = doc["scenes"]["scenario-01-setup"]["instances"]
        instances[1]["id"] = instances[0]["id"]
        self.assertTrue(any("15.3.6" in x for x in validate_dirps_core(doc)))

    def test_negative_wrong_rule_kind_is_rejected(self):
        doc = load_doc()
        doc["rules"]["actions"]["attempt-skill"]["procedure_ref"] = "actor-conscious"
        self.assertTrue(any("15.3.8" in x for x in validate_dirps_core(doc)))

    def test_negative_default_type_is_rejected(self):
        doc = load_doc()
        doc["rules"]["values"]["stunned"]["default"] = 1
        self.assertTrue(any("15.3.9" in x for x in validate_dirps_core(doc)))

    def test_negative_prose_end_condition_is_rejected_at_g2(self):
        doc = load_doc()
        doc["scenarios"]["scenario-01"]["end_conditions"] = [{
            "id": "prose-end",
            "outcome": "win",
            "condition": {"prose": "Done."},
            "priority": 1,
        }]
        self.assertTrue(any("15.3.10" in x for x in validate_dirps_core(doc)))

    def test_negative_duplicate_choice_option_id_is_rejected(self):
        doc = load_doc()
        options = doc["rules"]["procedures"]["tutorial-turn"]["steps"][0]["choice_options"]
        options[1]["id"] = options[0]["id"]
        self.assertTrue(any("15.3 choice" in x for x in validate_dirps_core(doc)))


if __name__ == "__main__":
    unittest.main()
