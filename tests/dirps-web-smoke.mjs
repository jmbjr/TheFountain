import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const ROOT = fileURLToPath(new URL("../", import.meta.url));
const PORT = 8765;
const BASE = `http://127.0.0.1:${PORT}`;
const serverLog = [];

function startServer() {
  const server = spawn(
    "python",
    ["-m", "http.server", String(PORT), "--bind", "127.0.0.1"],
    { cwd: ROOT, stdio: ["ignore", "pipe", "pipe"] },
  );
  server.stdout.on("data", (chunk) => serverLog.push(chunk.toString()));
  server.stderr.on("data", (chunk) => serverLog.push(chunk.toString()));
  return server;
}

async function waitForServer() {
  let lastError;
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(`${BASE}/dirps/`);
      if (response.ok) return;
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(
    `local server did not become ready: ${lastError?.message || lastError}\n${serverLog.join("")}`,
  );
}

const server = startServer();
let browser;
const browserErrors = [];

try {
  await waitForServer();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(180_000);
  page.on("pageerror", (error) => browserErrors.push(`pageerror: ${error.message}`));
  page.on("requestfailed", (request) => {
    browserErrors.push(
      `requestfailed: ${request.url()} :: ${request.failure()?.errorText || "unknown"}`,
    );
  });

  await page.goto(`${BASE}/dirps/`, { waitUntil: "domcontentloaded" });

  await page.waitForFunction(() =>
    document.querySelector("#runtimeStatus")?.textContent?.trim() === "Game ready.",
  );

  assert.equal(await page.locator("#fatal").isHidden(), true, "fatal runtime panel is visible");
  assert.ok(
    (await page.locator(".dirps-action").count()) >= 1,
    "no runtime-described action button rendered",
  );
  assert.equal(
    (await page.locator("#playerIdentity").textContent())?.trim(),
    "Rook",
    "PX-A player identity did not render",
  );
  assert.match(
    await page.locator("#scenarioObjective").innerText(),
    /discover what happened/i,
    "PX-A scenario objective did not render",
  );
  assert.equal(
    (await page.locator("#encounterTitle").textContent())?.trim(),
    "Roadside Tracks",
    "PX-A player-facing encounter title did not render",
  );
  assert.equal(
    (await page.locator(".dirps-action").first().innerText()).trim(),
    "Examine the tracks",
    "PX-A player-facing action phrasing did not render",
  );

  assert.equal(
    await page.locator("#advancedEvidence").getAttribute("open"),
    null,
    "PX-D advanced evidence should be closed by default",
  );
  assert.equal(
    await page.locator("#endingPanel").isHidden(),
    true,
    "PX-E ending must stay hidden before the runtime reaches a terminal state",
  );
  assert.equal(
    await page.locator("#seedInput").isVisible(),
    false,
    "PX-D deterministic seed control should not dominate the player view",
  );
  assert.match(
    await page.locator("#characterCondition").innerText(),
    /HP[\s\S]*10/i,
    "PX-D player condition summary did not render",
  );
  assert.match(
    await page.locator("#playerProgress").innerText(),
    /Actions resolved[\s\S]*0/i,
    "PX-D player progress summary did not render",
  );

  const exactCharacterState = {
    "hit-points": "10",
    fatigue: "10",
    stunned: "false",
    unconscious: "false",
    "consciousness-check-required": "false",
  };
  for (const [key, expected] of Object.entries(exactCharacterState)) {
    const state = page.locator(`[data-state-key="${key}"]`);
    assert.equal(await state.count(), 1, `missing rendered character state: ${key}`);
    assert.equal(
      (await state.locator("strong").textContent())?.trim(),
      expected,
      `rendered character state drifted: ${key}`,
    );
  }

  await page.evaluate(() => {
    document.querySelector("#seedInput").value = "phase-i-browser-smoke";
  });
  await page.locator(".dirps-action").first().click();

  await page.waitForFunction(() =>
    document.querySelector("#historyCount")?.textContent?.trim() === "1 step",
  );

  assert.equal(await page.locator("#fatal").isHidden(), true, "fatal panel appeared after action");
  assert.match(
    await page.locator("#lastResolution").innerText(),
    /Skill check/i,
    "PX-C human-readable skill explanation did not render",
  );
  assert.match(
    await page.locator("#lastResolution").innerText(),
    /Effective target/i,
    "PX-C effective target was not explained",
  );
  assert.match(
    await page.locator("#lastResolution").innerText(),
    /Margin/i,
    "PX-C roll margin was not explained",
  );
  assert.match(
    await page.locator("#lastResolution").innerText(),
    /Rook (identifies|cannot establish)/i,
    "PX-C runtime consequence was not surfaced in player language",
  );
  assert.match(
    await page.locator("#lastResolution").innerText(),
    /Technical resolution evidence/i,
    "PX-D technical resolution disclosure did not render",
  );
  assert.doesNotMatch(
    await page.locator("#lastResolution").innerText(),
    /Recorded random evidence/i,
    "PX-D random evidence should remain collapsed during normal play",
  );
  assert.equal(
    await page.locator("#advancedEvidence").getAttribute("open"),
    null,
    "PX-D advanced evidence opened during normal play",
  );
  assert.equal(
    (await page.locator("#encounterTitle").textContent())?.trim(),
    "Frightened Witness",
    "PX-B did not present the runtime-selected next encounter",
  );
  assert.match(
    await page.locator("#transitionOutcome").innerText(),
    /Rook (identifies|cannot establish)/i,
    "PX-B did not carry the accepted runtime consequence into the transition",
  );
  assert.match(
    await page.locator("#transitionBridge").innerText(),
    /frightened witness/i,
    "PX-B connective fiction did not render",
  );
  assert.match(
    await page.locator("#encounterPurpose").innerText(),
    /shaken witness/i,
    "PX-B next-encounter opening fiction did not render",
  );
  assert.equal(
    await page.evaluate(() => {
      const transition = document.querySelector("#encounterTransition");
      const opening = document.querySelector("#encounterPurpose");
      return Boolean(
        transition &&
        opening &&
        (transition.compareDocumentPosition(opening) & Node.DOCUMENT_POSITION_FOLLOWING)
      );
    }),
    true,
    "PX-B transition must appear before the next encounter opening fiction",
  );
  assert.match(
    await page.locator("#playerProgress").innerText(),
    /Actions resolved[\s\S]*1/i,
    "PX-D player progress did not update after the action",
  );

  await page.locator(".dirps-resolution-evidence > summary").click();
  assert.match(
    await page.locator("#lastResolution").innerText(),
    /Recorded random evidence/i,
    "PX-D technical resolution evidence could not be disclosed",
  );
  assert.match(
    await page.locator("#lastResolution").innerText(),
    /phase-i-browser-smoke/,
    "browser-selected deterministic seed was not preserved in resolution evidence",
  );

  await page.locator("#advancedEvidence > summary").click();
  assert.equal(
    await page.locator("#seedInput").isVisible(),
    true,
    "PX-D deterministic controls were not recoverable through disclosure",
  );
  assert.match(
    await page.locator("#history").innerText(),
    /#1/,
    "Phase H history did not advance after browser action",
  );
  assert.match(
    await page.locator("#history").innerText(),
    /phase-i-browser-smoke/,
    "PX-D replay evidence lost the deterministic seed",
  );
  assert.match(
    await page.locator("#history").innerText(),
    /→/,
    "PX-D replay hashes were not retained",
  );
  assert.match(
    await page.locator("#provenance").innerText(),
    /scenario_trace/i,
    "PX-D rule/source trace was not retained",
  );
  assert.match(
    await page.locator("#debugView").innerText(),
    /dirps-web-target\.v1/i,
    "PX-D runtime debug view was not retained",
  );

  await page.locator("#advancedEvidence > summary").click();
  assert.equal(
    await page.locator("#advancedEvidence").getAttribute("open"),
    null,
    "advanced evidence did not close before continuing normal play",
  );

  for (let expectedSteps = 2; expectedSteps <= 6; expectedSteps += 1) {
    if (!(await page.locator("#endingPanel").isHidden())) break;

    await page.evaluate((seed) => {
      document.querySelector("#seedInput").value = seed;
    }, `phase-i-browser-ending-${expectedSteps}`);

    const action = page.locator(".dirps-action").first();
    assert.equal(
      await action.count(),
      1,
      "runtime did not expose the next bounded Scenario 01 action",
    );
    await action.click();

    await page.waitForFunction((steps) => {
      const value = document.querySelector("#historyCount")?.textContent?.trim();
      return value === `${steps} step` || value === `${steps} steps`;
    }, expectedSteps);
  }

  assert.equal(
    await page.locator("#endingPanel").isHidden(),
    false,
    "PX-E dedicated ending did not appear at the accepted terminal state",
  );
  assert.match(
    (await page.locator("#endingTitle").innerText()).trim(),
    /^(Success|Failure)$/,
    "PX-E ending did not state the accepted terminal outcome",
  );
  assert.match(
    await page.locator("#endingConclusion").innerText(),
    /courier/i,
    "PX-E ending did not surface the accepted runtime conclusion",
  );
  assert.match(
    await page.locator("#endingConclusion").innerText(),
    /(return with an answer|withdrawing without enough information)/i,
    "PX-E ending conclusion drifted from accepted terminal wording",
  );
  assert.match(
    await page.locator("#endingSummary").innerText(),
    /Result[\s\S]*(success|failure)/i,
    "PX-E run summary omitted the terminal result",
  );
  assert.match(
    await page.locator("#endingSummary").innerText(),
    /Objective complete[\s\S]*(Yes|No)/i,
    "PX-E run summary omitted objective completion",
  );
  assert.match(
    await page.locator("#endingSummary").innerText(),
    /Actions resolved[\s\S]*[45]/i,
    "PX-E run summary omitted the bounded action count",
  );
  assert.equal(
    await page.locator("#activeScenario").isHidden(),
    true,
    "PX-E active encounter UI remained visible after completion",
  );
  assert.equal(
    await page.locator("#restartBar").isHidden(),
    true,
    "PX-E duplicate normal restart control remained visible after completion",
  );

  await page.locator("#endingEvidence").click();
  assert.equal(
    await page.locator("#advancedEvidence").getAttribute("open"),
    "",
    "PX-E technical-evidence action did not open preserved audit evidence",
  );
  assert.match(
    await page.locator("#history").innerText(),
    /#/,
    "PX-E technical evidence did not retain the replay history",
  );

  await page.locator("#endingRestart").click();
  await page.waitForFunction(() =>
    document.querySelector("#endingPanel")?.hidden === true &&
    document.querySelector("#historyCount")?.textContent?.trim() === "0 steps" &&
    document.querySelector("#encounterTitle")?.textContent?.trim() === "Roadside Tracks",
  );
  assert.equal(
    await page.locator("#advancedEvidence").getAttribute("open"),
    null,
    "PX-E restart should restore the closed advanced-evidence state",
  );
  assert.equal(
    (await page.locator(".dirps-action").first().innerText()).trim(),
    "Examine the tracks",
    "PX-E restart did not return to the accepted initial action",
  );
  assert.equal(
    await page.evaluate(() => document.activeElement?.classList.contains("dirps-action")),
    true,
    "PX-F restart did not return keyboard focus to the current action",
  );

  await page.setViewportSize({ width: 390, height: 844 });

  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    "PX-F phone layout has horizontal overflow",
  );

  const mobileActionBox = await page.locator(".dirps-action").first().boundingBox();
  assert.ok(mobileActionBox, "PX-F current action is not laid out on phone viewport");
  assert.ok(
    mobileActionBox.height >= 48,
    `PX-F current action touch target is too short: ${mobileActionBox.height}px`,
  );
  assert.ok(
    mobileActionBox.width >= 340,
    `PX-F current action is not easy to locate/use on phone: ${mobileActionBox.width}px`,
  );

  assert.equal(
    await page.evaluate(() => {
      const grid = document.querySelector(".dirps-condition-grid");
      return grid ? getComputedStyle(grid).gridTemplateColumns.split(" ").length : 0;
    }),
    2,
    "PX-F phone condition summary should remain a compact two-column grid",
  );

  assert.equal(
    await page.evaluate(() => {
      const resolution = document.querySelector("#lastResolutionPanel");
      const advanced = document.querySelector(".dirps-advanced");
      if (!resolution || !advanced) return false;
      return resolution.getBoundingClientRect().top < advanced.getBoundingClientRect().top;
    }),
    true,
    "PX-F technical evidence moved ahead of the primary phone play loop",
  );

  await page.evaluate(() => {
    document.querySelector("#seedInput").value = "phase-f-mobile-focus";
  });
  await page.locator(".dirps-action").first().click();
  await page.waitForFunction(() =>
    document.querySelector("#historyCount")?.textContent?.trim() === "1 step",
  );
  assert.equal(
    await page.evaluate(() => document.activeElement?.id),
    "lastResolutionPanel",
    "PX-F resolved action did not move focus to the new player-facing result",
  );
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    "PX-F resolved result introduced horizontal overflow on phone",
  );

  assert.equal(
    browserErrors.length,
    0,
    `browser transport/runtime errors:\n${browserErrors.join("\n")}`,
  );

  console.log(
    "PASS dirps/scenario-01: Phase I browser/Pyodide smoke executes shared runtime",
  );
} finally {
  if (browser) await browser.close();
  server.kill("SIGTERM");
}
