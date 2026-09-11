#!/usr/bin/env node
import { chromium } from "playwright";

const BASE = process.env.ACCEPTANCE_BASE_URL ?? "http://127.0.0.1:8080";
const browser = await chromium.launch({ headless: true });

async function shot(page, name) {
  await page.screenshot({ path: `/workspace/screenshots/${name}.png`, fullPage: true });
}

const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await desktop.goto(BASE, { waitUntil: "networkidle" });
await shot(desktop, "qa-1440-home");
await desktop.goto(`${BASE}/ke-hoach/test-brief-1`, { waitUntil: "networkidle" });
await desktop.getByRole("button", { name: "Tạo bản nháp từ fixture" }).click();
await desktop.waitForTimeout(1200);
await shot(desktop, "qa-1440-brief-draft");
await desktop.goto(`${BASE}/bai-viet`, { waitUntil: "networkidle" });
await shot(desktop, "qa-1440-articles");
const link = desktop.locator("a").filter({ hasText: "Cấu tạo" }).first();
if (await link.count()) {
  await link.click();
  await desktop.waitForTimeout(600);
  await desktop.getByRole("tab", { name: "Xem trước" }).click();
  await shot(desktop, "qa-1440-preview");
  const duyet = desktop.getByRole("link", { name: /duyệt/i });
  if (await duyet.count()) {
    await duyet.click();
    await desktop.waitForTimeout(500);
    await shot(desktop, "qa-1440-review");
  }
}

const phone = await browser.newPage({ viewport: { width: 375, height: 812 } });
await phone.goto(BASE, { waitUntil: "networkidle" });
await shot(phone, "qa-375-home");
await phone.goto(`${BASE}/ke-hoach`, { waitUntil: "networkidle" });
await shot(phone, "qa-375-planning");
await phone.goto(`${BASE}/nghiem-thu`, { waitUntil: "networkidle" });
await shot(phone, "qa-375-acceptance");

await browser.close();
console.log("ui-flow screenshots written");
