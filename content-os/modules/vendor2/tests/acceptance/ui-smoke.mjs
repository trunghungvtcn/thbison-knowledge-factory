#!/usr/bin/env node
import { chromium } from "playwright";

const BASE = process.env.ACCEPTANCE_BASE_URL ?? "http://127.0.0.1:8080";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const failures = [];

async function check(name, fn) {
  try {
    await fn();
    console.log(`PASS ${name}`);
  } catch (err) {
    failures.push(`${name}: ${err.message}`);
    console.log(`FAIL ${name}: ${err.message}`);
  }
}

await page.goto(BASE, { waitUntil: "networkidle" });
await check("home-vi", async () => {
  const t = await page.locator("h1").innerText();
  if (!t.includes("THBISON")) throw new Error(t);
});
await page.screenshot({ path: "/workspace/screenshots/01-home.png", fullPage: true });

await page.goto(`${BASE}/ke-hoach`, { waitUntil: "networkidle" });
await check("planning", async () => {
  const t = await page.locator("h1").innerText();
  if (!t.includes("Kế hoạch")) throw new Error(t);
});
await page.screenshot({ path: "/workspace/screenshots/02-ke-hoach.png", fullPage: true });

await page.goto(`${BASE}/ke-hoach/test-brief-1`, { waitUntil: "networkidle" });
await check("brief-detail", async () => {
  await page.getByRole("button", { name: "Tạo bản nháp từ fixture" }).click();
  await page.waitForTimeout(800);
});
await page.screenshot({ path: "/workspace/screenshots/03-brief.png", fullPage: true });

await page.goto(`${BASE}/bai-viet`, { waitUntil: "networkidle" });
await check("articles", async () => {
  const t = await page.locator("h1").innerText();
  if (!t.includes("Bài viết")) throw new Error(t);
});
await page.screenshot({ path: "/workspace/screenshots/04-bai-viet.png", fullPage: true });

const first = page.locator("a").filter({ hasText: /Cấu tạo|pa lăng|Bài/ }).first();
if (await first.count()) {
  await first.click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: "/workspace/screenshots/05-editor.png", fullPage: true });
}

await page.goto(`${BASE}/nghiem-thu`, { waitUntil: "networkidle" });
await check("acceptance-labels", async () => {
  const body = await page.locator("body").innerText();
  if (body.includes("ADAPTER_VERIFIED") && !body.includes("Không gộp nhãn")) throw new Error("merged labels");
});
await page.screenshot({ path: "/workspace/screenshots/06-nghiem-thu.png", fullPage: true });

await browser.close();
if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
