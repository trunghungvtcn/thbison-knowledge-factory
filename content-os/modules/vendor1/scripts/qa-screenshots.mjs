#!/usr/bin/env node
/** Delivery QA screenshots. Wait until client console is mounted; capture after hydrate. */
import { mkdirSync, writeFileSync } from "node:fs";
import { chromium } from "playwright";

const url = process.argv[2] || "http://127.0.0.1:8080/";
const outDir = process.argv[3] || "/workspace/delivery/qa";
mkdirSync(outDir, { recursive: true });

const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 800 },
  { name: "mobile", width: 390, height: 844 },
];

const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});

const viewports = {};
try {
  for (const vp of VIEWPORTS) {
    const consoleErrors = [];
    const pageErrors = [];
    const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => pageErrors.push(String(err?.message || err)));
    const resp = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.locator("[data-qa=planning-console]").waitFor({ timeout: 15000 });
    await page.waitForTimeout(800);
    const png = `${outDir}/planning-${vp.name}.png`;
    await page.screenshot({ path: png, fullPage: false });
    const title = await page.title();
    await page.close();
    const hydration = consoleErrors.filter((t) => /hydrat/i.test(t));
    viewports[vp.name] = {
      width: vp.width,
      height: vp.height,
      status: resp?.status() ?? 0,
      title,
      screenshot: png,
      consoleErrors,
      pageErrors,
      hydrationErrors: hydration,
    };
  }
} finally {
  await browser.close();
}

const hydrationFail = Object.values(viewports).some((v) => v.hydrationErrors.length > 0);
const out = {
  url,
  viewports,
  hydration_mismatch: hydrationFail,
  verdict: hydrationFail ? "FAIL_HYDRATION" : "PASS_NO_HYDRATION_ERROR",
};
writeFileSync(`${outDir}/qa-verdict.json`, JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
process.exit(hydrationFail ? 1 : 0);
