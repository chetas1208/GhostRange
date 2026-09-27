// Records a real ~60s walkthrough of the live GhostRange deployment.
// Real captures against the real live URL — no staged/fake state, no
// invented data. Shows whatever the live deployment actually renders.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import path from "node:path";

const BASE_URL = process.env.RECORD_BASE_URL ?? "https://45.76.248.45.sslip.io";
const OUT_DIR = process.env.RECORD_OUT_DIR ?? "artifacts/video";

mkdirSync(OUT_DIR, { recursive: true });

async function wait(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

async function main() {
  const browser = await chromium.launch({
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--mute-audio"],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: OUT_DIR, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();

  console.log(`[record] navigating to ${BASE_URL}/?tab=multiverse`);
  await page.goto(`${BASE_URL}/?tab=multiverse`, { waitUntil: "networkidle", timeout: 30_000 });
  await wait(8_000);

  console.log("[record] Execution tab");
  const execTab = page.getByText("EXECUTION", { exact: false }).first();
  if (await execTab.count()) {
    await execTab.click();
  } else {
    await page.goto(`${BASE_URL}/?tab=execution`, { waitUntil: "networkidle" });
  }
  await wait(15_000);

  console.log("[record] Evidence tab");
  const evTab = page.getByText("EVIDENCE", { exact: false }).first();
  if (await evTab.count()) {
    await evTab.click();
  } else {
    await page.goto(`${BASE_URL}/?tab=evidence`, { waitUntil: "networkidle" });
  }
  await wait(15_000);

  console.log("[record] back to Multiverse");
  const multTab = page.getByText("MULTIVERSE", { exact: false }).first();
  if (await multTab.count()) {
    await multTab.click();
  } else {
    await page.goto(`${BASE_URL}/?tab=multiverse`, { waitUntil: "networkidle" });
  }
  await wait(15_000);

  await context.close();
  await browser.close();
  console.log(`[record] done, video saved under ${OUT_DIR}/`);
}

main().catch((err) => {
  console.error("[record] FAILED:", err);
  process.exit(1);
});
