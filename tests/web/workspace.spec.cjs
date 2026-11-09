const { chromium } = require("@playwright/test");
const fs = require("node:fs/promises");
const assert = require("node:assert/strict");
const base = process.env.SAFETYOPS_TEST_URL || "http://127.0.0.1:8010";
(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
    recordVideo: {
      dir: ".impeccable/review/video",
      size: { width: 1440, height: 1000 },
    },
  });
  const page = await context.newPage();
  const failures = [];
  page.on("pageerror", (e) => failures.push(e.message));
  await fs.mkdir(".impeccable/review", { recursive: true });
  await page.goto(base);
  await page.evaluate(() => document.fonts.ready);
  assert.equal(await page.locator("h1").count(), 1);
  await page.getByRole("button", { name: "Electrical", exact: true }).click();
  assert.match(await page.locator("#example-text").inputValue(), /electrical/);
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({
    path: ".impeccable/review/home-desktop.png",
    fullPage: true,
  });
  await page.goto(base + "/app#demo");
  await page.waitForFunction(
    () => !document.querySelector("#assess-button").disabled,
  );
  await page.locator("[data-observation]").nth(1).focus();
  await page.keyboard.press("Enter");
  assert.equal(
    await page.evaluate(() => document.activeElement?.dataset.observation),
    "s2",
  );
  await page.keyboard.press("Tab");
  assert.equal(
    await page.evaluate(() => document.activeElement?.dataset.observation),
    "s3",
  );
  await page.locator("[data-observation]").first().click();
  await page.screenshot({
    path: ".impeccable/review/desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Create my workspace" }).click();
  await page.getByText("Personal workspace / saved to database").waitFor();
  await page
    .locator("#observation-text")
    .fill("A worker slipped on a wet access platform and suffered a fracture.");
  await page.locator("#observation-location").fill("North platform");
  await page.locator("#assess-button").click();
  await page.locator(".observation-row").waitFor();
  await page.locator("#action-owner").fill("Shift coordinator");
  await page.locator("#action-form button[type=submit]").click();
  await page.locator("#next-actions .action-row").waitFor();
  await page.reload();
  await page.getByText("Personal workspace / saved to database").waitFor();
  assert.equal(await page.locator(".observation-row").count(), 1);
  assert.equal(await page.locator("#next-actions .action-row").count(), 1);
  await page.locator("#next-actions [data-progress]").click();
  await page
    .locator("#next-actions .pill")
    .filter({ hasText: "In progress" })
    .waitFor();
  await page.locator("#next-actions [data-show-close]").click();
  await page
    .locator("#next-actions textarea[name=evidence]")
    .fill(
      "Platform inspected and housekeeping controls verified in the site log.",
    );
  await page.locator("#next-actions .closure-form button[type=submit]").click();
  await page.waitForFunction(() =>
    document.querySelector("#stats").textContent.includes("1Actions closed"),
  );
  await page
    .getByRole("button", { name: "Shift handover", exact: true })
    .click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download handover (.md)" }).click();
  const download = await downloadPromise;
  const content = await fs.readFile(await download.path(), "utf8");
  assert.match(content, /housekeeping controls verified/);
  assert.match(content, /North platform/);
  assert.ok(
    content.includes(String.fromCharCode(10)),
    "Markdown needs actual line breaks",
  );
  assert.ok(content.split(String.fromCharCode(10)).length > 10);
  const csvPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export actions (.csv)" }).click();
  const csvDownload = await csvPromise;
  const csv = await fs.readFile(await csvDownload.path(), "utf8");
  assert.equal(csv.charCodeAt(0), 0xfeff);
  assert.equal(csv.split(String.fromCharCode(13, 10)).length, 2);
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.locator("#search").fill("no matching text");
  assert.match(
    await page.locator("#observation-list").textContent(),
    /No matching/,
  );
  await page.locator("#search").fill("");
  await page
    .locator("#observation-text")
    .fill(
      "<img src=x onerror=alert(1)> A test observation near access equipment.",
    );
  await page.locator("#assess-button").click();
  await page.waitForFunction(
    () => document.querySelectorAll(".observation-row").length === 2,
  );
  assert.equal(await page.locator(".observation-row img").count(), 0);
  const cookie = (await context.cookies()).find(
    (c) => c.name === "safetyops_workspace",
  );
  assert.equal(cookie.httpOnly, true);
  assert.equal(cookie.secure, base.startsWith("https://"));
  const outsider = await browser.newContext();
  assert.equal(
    (await outsider.request.get(base + "/api/workspace")).status(),
    401,
  );
  await outsider.close();
  assert.equal(cookie.sameSite, "Strict");
  await page.getByRole("button", { name: "Workspace", exact: true }).click();
  await page.locator("#delete-workspace").click();
  await page.locator("#confirm-delete").click();
  await page.getByText("Sample workspace / synthetic records").waitFor();
  await context.close();
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    reducedMotion: "reduce",
  });
  const mp = await mobile.newPage();
  mp.on("pageerror", (e) => failures.push(e.message));
  for (const [path, name] of [
    ["/", "home-mobile"],
    ["/app#demo", "mobile"],
    ["/guides/incident-triage", "guide-mobile"],
  ]) {
    await mp.goto(base + path);
    await mp.evaluate(() => document.fonts.ready);
    if (path.includes("/app"))
      await mp.waitForFunction(
        () => !document.querySelector("#assess-button").disabled,
      );
    assert.equal(
      await mp.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
      "Horizontal overflow at " + path,
    );
    await mp.screenshot({
      path: ".impeccable/review/" + name + ".png",
      fullPage: true,
    });
  }
  await mobile.close();
  await browser.close();
  assert.deepEqual(failures, []);
  console.log(
    "PASS: desktop/mobile, sample switch, persistence, action closure, exports, XSS text, deletion, no overflow or JS errors.",
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
