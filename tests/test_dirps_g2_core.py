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

    for source_id, source in sources.items():
        uri = source.get("uri", "")
        if uri and not uri.startswith(("http://", "https://")) and not (ROOT / uri).exists():
            failures.append(f"15.3.1 missing local source URI {source_id}: {uri}")
    for object_id, obj in objects.items():
        if obj.get("archetype_ref") not in archetypes:
            failures.append(f"15.3.1 object {object_id} archetype_ref missing")
    for scene_id, scene in scenes.items():
        if scene.get("source_ref") and scene["source_ref"] not in sources:
            failures.append(f"15.3.1 scene {scene_id} source_ref missing")
        for instance in scene.get("instances", []):
            if instance.get("object_ref") not in objects:
                failures.append(f"15.3.1 scene {scene_id} object_ref missing")
    for scenario_id, scenario in scenarios.items():
        if scenario.get("scene_ref") not in scenes:
            failures.append(f"15.3.1 scenario {scenario_id} scene_ref missing")
        if scenario.get("source_ref") and scenario["source_ref"] not in sources:
            failures.append(f"15.3.1 scenario {scenario_id} source_ref missing")

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

    def require(owner, ref, table, kind):
        if ref and ref not in table:
            failures.append(f"15.3.8 {owner} {kind} ref does not resolve: {ref}")

    for action_id, action in actions.items():
        for ref in action.get("condition_refs", []):
            require(f"action {action_id}", ref, conditions, "condition")
        require(f"action {action_id}", action.get("procedure_ref"), procedures, "procedure")
        for ref in action.get("effect_refs", []):
            require(f"action {action_id}", ref, effects, "effect")
    step_tables = {
        "action": actions,
        "condition": conditions,
        "effect": effects,
        "procedure": procedures,
        "phase": phases,
        "ai": ai_profiles,
    }
    for proc_id, proc in procedures.items():
        for step in walk_steps(proc.get("steps", [])):
            kind, ref = step.get("kind"), step.get("ref")
            if kind in step_tables and ref:
                require(f"procedure {proc_id}", ref, step_tables[kind], kind)
    for scenario_id, scenario in scenarios.items():
        for ref in scenario.get("action_refs", []):
            require(f"scenario {scenario_id}", ref, actions, "action")
        require(f"scenario {scenario_id}", scenario.get("turn_procedure_ref"), procedures, "procedure")

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
                require(f"choice {proc_id}/{option.get('id')}", ref, conditions, "condition")
            for nested in walk_steps(option.get("steps", [])):
                kind, ref = nested.get("kind"), nested.get("ref")
                if kind in step_tables and ref:
                    require(f"choice {proc_id}/{option.get('id')}", ref, step_tables[kind], kind)

    return failures


class DirpsG2CoreValidationTests(unittest.TestCase):
    def test_every_applicable_15_3_rule_passes(self):
        self.assertEqual(validate_dirps_core(load_doc()), [])

    def test_negative_missing_reference_is_rejected(self):
        doc = load_doc()
        doc["objects"]["tutorial-pc"]["archetype_ref"] = "missing-archetype"
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
