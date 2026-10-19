import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const ROOT = fileURLToPath(new URL("../", import.meta.url));
const PORT = 8766;
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

async function nonEmptyText(locator, message) {
  const value = (await locator.innerText()).trim();
  assert.ok(value.length > 0, message);
  return value;
}

async function assertDefaultEvidenceClosed(page, stage) {
  assert.equal(
    await page.locator("#advancedEvidence").getAttribute("open"),
    null,
    `PX-G advanced evidence opened during default play at ${stage}`,
  );
  assert.equal(
    await page.locator("#seedInput").isVisible(),
    false,
    `PX-G deterministic seed control became visible during default play at ${stage}`,
  );
  assert.equal(
    await page.locator("#debugView").isVisible(),
    false,
    `PX-G runtime debug view became visible during default play at ${stage}`,
  );

  const resolutionEvidence = page.locator(".dirps-resolution-evidence");
  if (await resolutionEvidence.count()) {
    assert.equal(
      await resolutionEvidence.getAttribute("open"),
      null,
      `PX-G technical resolution evidence opened during default play at ${stage}`,
    );
  }
}

async function assertPlayerContext(page, expectedSteps) {
  assert.equal(
    (await page.locator("#playerIdentity").innerText()).trim(),
    "Rook",
    "PX-G player cannot answer: Who am I?",
  );
  await nonEmptyText(
    page.locator("#playerRole"),
    "PX-G player role is missing",
  );
  assert.match(
    await nonEmptyText(
      page.locator("#scenarioObjective"),
      "PX-G player cannot answer: What am I trying to accomplish?",
    ),
    /courier|discover|answer/i,
    "PX-G objective is not player-readable",
  );
  await nonEmptyText(
    page.locator("#encounterTitle"),
    "PX-G player cannot answer: What is happening right now?",
  );
  await nonEmptyText(
    page.locator("#encounterPurpose"),
    "PX-G current encounter has no player-facing fiction",
  );

  const actions = page.locator(".dirps-action");
  assert.equal(
    await actions.count(),
    1,
    "PX-G bounded tutorial should expose exactly one honest current action",
  );
  await nonEmptyText(
    actions.first(),
    "PX-G player cannot answer: What can I do?",
  );

  assert.match(
    await page.locator("#playerProgress").innerText(),
    new RegExp(`Actions resolved\\s*${expectedSteps}`, "i"),
    "PX-G visible progress does not match the accepted session",
  );
  await assertDefaultEvidenceClosed(page, `step-${expectedSteps}-ready`);
}

const server = startServer();
let browser;
const browserErrors = [];

try {
  await waitForServer();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
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

  assert.equal(await page.locator("#fatal").isHidden(), true, "PX-G fatal panel is visible");
  assert.equal(await page.locator("#endingPanel").isHidden(), true, "PX-G starts terminal");

  let steps = 0;
  await assertPlayerContext(page, steps);

  while (await page.locator("#endingPanel").isHidden()) {
    if (steps >= 6) {
      throw new Error("PX-G bounded Scenario 01 did not reach a terminal state within six actions");
    }

    const currentEncounter = (await page.locator("#encounterTitle").innerText()).trim();
    const currentAction = (await page.locator(".dirps-action").first().innerText()).trim();

    await page.evaluate((seed) => {
      document.querySelector("#seedInput").value = seed;
    }, `px-g-player-${steps + 1}`);

    await page.locator(".dirps-action").first().click();
    steps += 1;

    await page.waitForFunction((expectedSteps) => {
      const text = document.querySelector("#historyCount")?.textContent?.trim();
      return text === `${expectedSteps} step` || text === `${expectedSteps} steps`;
    }, steps);

    await assertDefaultEvidenceClosed(page, `step-${steps}-resolved`);

    if (!(await page.locator("#endingPanel").isHidden())) {
      break;
    }

    const resolutionTitle = await nonEmptyText(
      page.locator("#lastResolution .dirps-resolution-title"),
      `PX-G player cannot explain the result of "${currentAction}"`,
    );
    assert.notEqual(
      resolutionTitle.toLowerCase(),
      "resolution",
      "PX-G result explanation fell back to an implementation-generic title",
    );

    await nonEmptyText(
      page.locator("#lastResolution .dirps-consequence"),
      `PX-G player cannot answer what changed after "${currentAction}"`,
    );
    await nonEmptyText(
      page.locator("#transitionOutcome"),
      `PX-G transition did not retain the outcome from "${currentEncounter}"`,
    );
    await nonEmptyText(
      page.locator("#transitionBridge"),
      `PX-G player cannot answer why the next encounter follows "${currentEncounter}"`,
    );

    await assertPlayerContext(page, steps);
  }

  assert.ok(
    steps === 4 || steps === 5,
    `PX-G bounded Scenario 01 ended after unexpected action count: ${steps}`,
  );

  await assertDefaultEvidenceClosed(page, "terminal");

  const outcome = (await page.locator("#endingTitle").innerText()).trim();
  assert.match(
    outcome,
    /^(Success|Failure)$/,
    "PX-G player cannot answer: Did I win or lose?",
  );

  const conclusion = await nonEmptyText(
    page.locator("#endingConclusion"),
    "PX-G terminal state does not explain why the run ended",
  );
  assert.match(
    conclusion,
    /courier/i,
    "PX-G ending no longer explains the courier mystery",
  );

  assert.match(
    await page.locator("#endingSummary").innerText(),
    /Result[\s\S]*(success|failure)/i,
    "PX-G ending summary omits the accepted outcome",
  );
  assert.match(
    await page.locator("#endingSummary").innerText(),
    new RegExp(`Actions resolved[\\s\\S]*${steps}`, "i"),
    "PX-G ending summary omits the accepted action count",
  );

  assert.equal(
    await page.locator("#endingEvidence").isVisible(),
    true,
    "PX-G implementor evidence is no longer deliberately available after play",
  );
  assert.equal(
    browserErrors.length,
    0,
    `PX-G browser transport/runtime errors:\n${browserErrors.join("\n")}`,
  );

  console.log(
    `PASS dirps/scenario-01: PX-G default-player acceptance reached ${outcome.toLowerCase()} in ${steps} actions without opening technical evidence`,
  );
} finally {
  if (browser) await browser.close();
  server.kill("SIGTERM");
}
