import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.29.1/full/pyodide.mjs";

const PYODIDE_INDEX = "https://cdn.jsdelivr.net/pyodide/v0.29.1/full/";
const PYTHON_FILES = [
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
];

const $ = (id) => document.getElementById(id);
let pyodide;
let model;

function text(id, value) {
  $(id).textContent = value ?? "";
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function shortHash(value) {
  return typeof value === "string" && value.length > 16
    ? value.slice(0, 12) + "…"
    : value ?? "—";
}

function row(label, value) {
  const wrapper = document.createElement("div");
  wrapper.className = "dirps-kv";
  const key = document.createElement("span");
  key.textContent = label;
  const content = document.createElement("strong");
  content.textContent = String(value ?? "—");
  wrapper.append(key, content);
  return wrapper;
}

function badge(label, value) {
  const chip = document.createElement("span");
  chip.className = "dirps-chip";
  chip.textContent = `${label}: ${value}`;
  return chip;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function renderCharacter() {
  const host = $("character");
  clear(host);
  const character = model.characters?.[0];
  if (!character) {
    host.append(document.createTextNode("No resolved character."));
    return;
  }

  const name = document.createElement("h2");
  name.textContent = character.name || character.id;
  host.append(name);

  const provenance = document.createElement("p");
  provenance.className = "dirps-muted";
  provenance.textContent = `provenance · ${character.provenance || "unspecified"}`;
  host.append(provenance);

  const attrs = document.createElement("div");
  attrs.className = "dirps-stat-grid";
  for (const [key, value] of Object.entries(character.primary_attributes || {})) {
    attrs.append(row(key.toUpperCase(), value));
  }
  host.append(attrs);

  const stateTitle = document.createElement("h3");
  stateTitle.textContent = "Resolved runtime state";
  host.append(stateTitle);
  const state = document.createElement("div");
  state.className = "dirps-stat-grid dirps-character-state";
  for (const [key, value] of Object.entries(character.state || {})) {
    const stateRow = row(key.replaceAll("-", " "), value);
    stateRow.dataset.stateKey = key;
    stateRow.dataset.stateValue = String(value);
    state.append(stateRow);
  }
  host.append(state);

  const skillsTitle = document.createElement("h3");
  skillsTitle.textContent = "Skills";
  host.append(skillsTitle);
  const skills = document.createElement("div");
  skills.className = "dirps-chip-list";
  for (const [key, value] of Object.entries(character.skills || {})) {
    skills.append(badge(key, value));
  }
  host.append(skills);

  const equipmentTitle = document.createElement("h3");
  equipmentTitle.textContent = "Equipment";
  host.append(equipmentTitle);
  const equipment = document.createElement("div");
  equipment.className = "dirps-chip-list";
  for (const item of character.equipment || []) {
    equipment.append(badge("item", item));
  }
  host.append(equipment);
}

function renderCharacterCondition() {
  const host = $("characterCondition");
  clear(host);
  const character = model.characters?.[0];
  if (!character) {
    host.append(document.createTextNode("No character condition available."));
    return;
  }

  const state = character.state || {};
  const grid = document.createElement("div");
  grid.className = "dirps-stat-grid";
  for (const [label, key] of [
    ["HP", "hit-points"],
    ["Fatigue", "fatigue"],
    ["Stunned", "stunned"],
    ["Unconscious", "unconscious"],
  ]) {
    if (state[key] !== undefined) {
      grid.append(row(label, readableValue(state[key])));
    }
  }
  host.append(grid);
}

function renderPlayerProgress() {
  const host = $("playerProgress");
  clear(host);
  const progress = model.scenario?.progress || {};
  const grid = document.createElement("div");
  grid.className = "dirps-stat-grid";
  grid.append(row("Status", readableValue(progress.status)));
  grid.append(row("Actions resolved", model.history?.steps?.length || 0));
  host.append(grid);
}

function renderActions() {
  const host = $("availableActions");
  clear(host);
  const actions = model.presentation?.available_actions || [];

  if (!actions.length) {
    const done = document.createElement("p");
    done.className = "dirps-quiet";
    done.textContent =
      model.scenario?.progress?.status === "complete"
        ? "Scenario complete."
        : "No semantic action is currently available.";
    host.append(done);
    return;
  }

  for (const action of actions) {
    const button = document.createElement("button");
    button.className = "dirps-action";
    const label = document.createElement("strong");
    label.textContent = action.label || action.name || action.id;
    button.append(label);
    button.addEventListener("click", () => executeAction(action, button));
    host.append(button);
  }
}

function renderScenario() {
  const scenario = model.scenario || {};
  const progress = scenario.progress || {};
  const presentation = model.presentation || {};
  const encounter = presentation.encounter || {};

  text("encounterTitle", encounter.title || "Scenario complete");
  text("encounterPurpose", encounter.opening_fiction || "");
  text(
    "progressMeta",
    progress.status === "complete" ? "Complete" : "Investigation in progress"
  );

  const transition = model.transition;
  const transitionHost = $("encounterTransition");
  if (transition) {
    transitionHost.hidden = false;
    text("transitionOutcome", transition.outcome_text || "");
    text("transitionBridge", transition.bridge_text || "");
  } else {
    transitionHost.hidden = true;
    text("transitionOutcome", "");
    text("transitionBridge", "");
  }

  const banner = $("scenarioBanner");
  banner.className = "dirps-banner";
  if (progress.status === "complete") {
    banner.classList.add(progress.outcome === "success" ? "success" : "failure");
    banner.textContent = `SCENARIO COMPLETE · ${String(progress.outcome || "complete").toUpperCase()}`;
  } else {
    banner.textContent = presentation.scenario?.title || model.scenario.title || "The Missing Courier";
  }

  const state = $("scenarioState");
  clear(state);
  for (const [key, value] of Object.entries(progress)) {
    state.append(row(key.replaceAll("_", " "), value));
  }
  const retained = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Retained encounter state";
  const pre = document.createElement("pre");
  pre.className = "dirps-code";
  pre.textContent = pretty(scenario.retained_state || {});
  retained.append(summary, pre);
  state.append(retained);

  renderActions();
}

function readableValue(value) {
  if (value === true) return "Yes";
  if (value === false) return "No";
  if (value === null || value === undefined) return "—";
  return String(value).replaceAll("-", " ");
}

function renderResolutionSection(section) {
  const wrapper = document.createElement("section");
  wrapper.className = "dirps-resolution-section";

  const heading = document.createElement("h3");
  heading.textContent = section.title || "Result";
  wrapper.append(heading);

  const grid = document.createElement("div");
  grid.className = "dirps-stat-grid";
  for (const fact of section.facts || []) {
    if (fact.value !== null && fact.value !== undefined) {
      grid.append(row(fact.label, readableValue(fact.value)));
    }
  }
  wrapper.append(grid);

  if ((section.modifiers || []).length) {
    const list = document.createElement("ul");
    list.className = "dirps-modifier-list";
    for (const modifier of section.modifiers) {
      const item = document.createElement("li");
      const amount = readableValue(modifier.amount);
      item.textContent = modifier.reason
        ? `${amount} · ${modifier.reason}`
        : amount;
      list.append(item);
    }
    wrapper.append(list);
  }

  return wrapper;
}

function renderLatest() {
  const host = $("lastResolution");
  clear(host);
  const record = model.latest_execution;
  const explanation = model.resolution_explanation;
  if (!record || !explanation) {
    const quiet = document.createElement("p");
    quiet.className = "dirps-quiet";
    quiet.textContent = "No action resolved yet.";
    host.append(quiet);
    text("provenance", "No execution trace yet.");
    return;
  }

  const heading = document.createElement("h2");
  heading.className = "dirps-resolution-title";
  heading.textContent = explanation.title || "Resolution";
  host.append(heading);

  for (const section of explanation.sections || []) {
    host.append(renderResolutionSection(section));
  }

  if (explanation.consequence) {
    const consequence = document.createElement("p");
    consequence.className = "dirps-consequence";
    consequence.textContent = explanation.consequence;
    host.append(consequence);
  }

  if ((explanation.skipped_checks || []).length) {
    const skipped = document.createElement("div");
    skipped.className = "dirps-skipped";
    const title = document.createElement("h3");
    title.textContent = "Checks not needed";
    skipped.append(title);
    for (const check of explanation.skipped_checks) {
      const line = document.createElement("p");
      line.textContent = `${readableValue(check.check)}: ${readableValue(check.reason)}`;
      skipped.append(line);
    }
    host.append(skipped);
  }

  const technical = document.createElement("details");
  technical.className = "dirps-resolution-evidence";
  const technicalSummary = document.createElement("summary");
  technicalSummary.textContent = "Technical resolution evidence";

  const randomTitle = document.createElement("h3");
  randomTitle.textContent = "Recorded random evidence";
  const random = document.createElement("pre");
  random.className = "dirps-code";
  random.textContent = pretty(record.random_inputs || {});

  const mechanicTitle = document.createElement("h3");
  mechanicTitle.textContent = "Mechanic result";
  const mechanicJson = document.createElement("pre");
  mechanicJson.className = "dirps-code";
  mechanicJson.textContent = pretty(record.mechanic_result || {});

  technical.append(
    technicalSummary,
    randomTitle,
    random,
    mechanicTitle,
    mechanicJson
  );
  host.append(technical);

  text(
    "provenance",
    pretty({
      scenario_trace: record.trace || null,
      mechanic_trace: record.mechanic_result?.trace || null,
      authority_chain: record.mechanic_result?.authority_chain || null,
    })
  );
}

function renderHistory() {
  const host = $("history");
  clear(host);
  const steps = model.history?.steps || [];
  text("historyCount", `${steps.length} step${steps.length === 1 ? "" : "s"}`);

  if (!steps.length) {
    const quiet = document.createElement("p");
    quiet.className = "dirps-quiet";
    quiet.textContent = "The append-only replay log is empty.";
    host.append(quiet);
    return;
  }

  for (const step of steps) {
    const item = document.createElement("div");
    item.className = "dirps-history-step";
    const heading = document.createElement("strong");
    heading.textContent = `#${step.sequence} · ${step.declared_action?.action_id || "action"}`;
    const seed = document.createElement("span");
    seed.textContent = `seed ${step.random_evidence?.random_seed ?? step.random_evidence?.seed ?? "recorded"}`;
    const hashes = document.createElement("small");
    hashes.textContent =
      `${shortHash(step.state_before_hash)} → ${shortHash(step.state_after_hash)}`;
    item.append(heading, seed, hashes);
    host.append(item);
  }
}

function renderEnding() {
  const ending = model.ending;
  const panel = $("endingPanel");
  const active = $("activeScenario");
  const restartBar = $("restartBar");

  if (!ending) {
    panel.hidden = true;
    panel.className = "dirps-panel dirps-ending";
    active.hidden = false;
    restartBar.hidden = false;
    return;
  }

  panel.hidden = false;
  panel.className = `dirps-panel dirps-ending ${ending.outcome || ""}`;
  active.hidden = true;
  restartBar.hidden = true;

  text(
    "endingTitle",
    ending.outcome === "success" ? "Success" :
      ending.outcome === "failure" ? "Failure" :
        "Scenario complete"
  );
  text("endingConclusion", ending.conclusion_text || "");

  const reason = $("endingReason");
  if (ending.final_reason) {
    reason.hidden = false;
    reason.textContent = ending.final_reason;
  } else {
    reason.hidden = true;
    reason.textContent = "";
  }

  const summary = $("endingSummary");
  clear(summary);
  summary.append(row("Result", readableValue(ending.outcome)));
  summary.append(row("Objective complete", readableValue(ending.objective_complete)));
  summary.append(row("Actions resolved", ending.summary?.actions_resolved ?? 0));
}


function renderFraming() {
  const framing = model.presentation?.scenario || {};
  text("playerIdentity", framing.player_name || "Rook");
  text("playerRole", framing.player_role || "");
  text("scenarioPremise", framing.premise || model.scenario?.premise || "");
  text("scenarioObjective", framing.objective || "");
  text("scenarioScope", framing.scope_note || "");
}


function render() {
  $("play").hidden = false;
  $("fatal").hidden = true;
  text("runtimeStatus", "Game ready.");
  text("runtimeTechnicalStatus", "Shared Python resolver/runtime active in this browser.");
  renderFraming();
  renderCharacter();
  renderCharacterCondition();
  renderScenario();
  renderLatest();
  renderPlayerProgress();
  renderHistory();
  renderEnding();
  text("debugView", pretty(model));
}

function setBusy(isBusy, message) {
  document.querySelectorAll(".dirps-action, #restart, #endingRestart").forEach((button) => {
    button.disabled = isBusy;
  });
  if (message) text("runtimeStatus", message);
}

async function executeAction(action, button) {
  const seedInput = $("seedInput");
  const seed = seedInput.value.trim() || `web-${crypto.randomUUID()}`;
  seedInput.value = seed;
  setBusy(true, `Resolving ${action.label || action.id}…`);
  button.disabled = true;

  try {
    pyodide.globals.set("web_history_json", JSON.stringify(model.history));
    pyodide.globals.set("web_action_id", action.id);
    pyodide.globals.set("web_actor_ref", action.actor_ref);
    pyodide.globals.set("web_seed", seed);
    const raw = await pyodide.runPythonAsync(
      "dirps_web_target.web_execute_json(web_history_json, web_action_id, web_actor_ref, web_seed)"
    );
    model = JSON.parse(raw);
    render();
  } catch (error) {
    showFatal(error);
  } finally {
    for (const name of ["web_history_json", "web_action_id", "web_actor_ref", "web_seed"]) {
      pyodide.globals.delete(name);
    }
    setBusy(false);
  }
}

function repoPath(url) {
  const parsed = new URL(url, window.location.href);
  const marker = "/dirps/";
  const index = parsed.pathname.indexOf(marker);
  if (index < 0) throw new Error(`Cannot map repository path: ${url}`);
  return parsed.pathname.slice(index + marker.length - 1).replace(/^\.\.\//, "");
}

function pythonFsPath(sourceUrl) {
  const normalized = sourceUrl.replace(/^\.\.\//, "");
  return `/home/pyodide/${normalized}`;
}

async function mountRepositoryFiles() {
  const loaded = await Promise.all(
    PYTHON_FILES.map(async (path) => {
      const response = await fetch(path, { cache: "no-cache" });
      if (!response.ok) throw new Error(`Failed to load ${path}: HTTP ${response.status}`);
      return [path, await response.text()];
    })
  );

  for (const [path, source] of loaded) {
    const fsPath = pythonFsPath(path);
    const directory = fsPath.slice(0, fsPath.lastIndexOf("/"));
    pyodide.FS.mkdirTree(directory);
    pyodide.FS.writeFile(fsPath, source);
  }
}

async function startRuntime() {
  text("runtimeStatus", "Loading game…");
  pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX });
  text("runtimeStatus", "Preparing scenario…");
  await mountRepositoryFiles();
  await pyodide.runPythonAsync(`
import os
import sys
os.chdir("/home/pyodide")
if "/home/pyodide/tools" not in sys.path:
    sys.path.insert(0, "/home/pyodide/tools")
import dirps_web_target
`);
  text("runtimeStatus", "Preparing the investigation…");
  const raw = await pyodide.runPythonAsync("dirps_web_target.web_bootstrap_json()");
  model = JSON.parse(raw);
  render();
}

function showFatal(error) {
  $("play").hidden = true;
  const fatal = $("fatal");
  fatal.hidden = false;
  fatal.textContent = `DIRPS Web target failed visibly: ${error?.message || error}`;
  text("runtimeStatus", "Runtime unavailable.");
}

async function restartScenario() {
  setBusy(true, "Restarting scenario…");
  try {
    const raw = await pyodide.runPythonAsync("dirps_web_target.web_bootstrap_json()");
    model = JSON.parse(raw);
    $("seedInput").value = "";
    $("advancedEvidence").open = false;
    render();
  } catch (error) {
    showFatal(error);
  } finally {
    setBusy(false);
  }
}

$("restart").addEventListener("click", restartScenario);
$("endingRestart").addEventListener("click", restartScenario);
$("endingEvidence").addEventListener("click", () => {
  $("advancedEvidence").open = true;
});

startRuntime().catch(showFatal);
