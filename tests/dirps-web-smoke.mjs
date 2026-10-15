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
    document.querySelector("#runtimeStatus")?.textContent?.includes(
      "Shared Python resolver/runtime active in this browser.",
    ),
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

  await page.locator("#seedInput").fill("phase-i-browser-smoke");
  await page.locator(".dirps-action").first().click();

  await page.waitForFunction(() =>
    document.querySelector("#historyCount")?.textContent?.trim() === "1 step",
  );

  assert.equal(await page.locator("#fatal").isHidden(), true, "fatal panel appeared after action");
  assert.match(
    await page.locator("#lastResolution").innerText(),
    /Recorded random evidence/i,
    "runtime result/random-evidence surface did not render",
  );
  assert.match(
    await page.locator("#lastResolution").innerText(),
    /phase-i-browser-smoke/,
    "browser-selected deterministic seed was not preserved in runtime evidence",
  );
  assert.match(
    await page.locator("#history").innerText(),
    /#1/,
    "Phase H history did not advance after browser action",
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
