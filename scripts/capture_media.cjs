const { chromium } = require("@playwright/test");
const fs = require("node:fs/promises");
(async () => {
  await fs.mkdir("docs/media", { recursive: true });
  const browser = await chromium.launch();
  const c = await browser.newContext({
    viewport: { width: 1200, height: 630 },
    reducedMotion: "reduce",
  });
  const p = await c.newPage();
  await p.goto("http://127.0.0.1:8010/");
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: "apps/web/social.png" });
  await c.close();
  const demo = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    recordVideo: {
      dir: ".impeccable/review/tour",
      size: { width: 1440, height: 1000 },
    },
  });
  const page = await demo.newPage();
  await page.goto("http://127.0.0.1:8010/app#demo");
  await page.waitForFunction(
    () => !document.querySelector("#assess-button").disabled,
  );
  await page.waitForTimeout(1300);
  await page
    .getByRole("button", { name: "Action tracker", exact: true })
    .click();
  await page.waitForTimeout(1600);
  await page
    .getByRole("button", { name: "Shift handover", exact: true })
    .click();
  await page.waitForTimeout(1600);
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.waitForTimeout(1600);
  const video = page.video();
  await demo.close();
  await fs.copyFile(await video.path(), "docs/media/workspace-tour.webm");
  await browser.close();
  for (const [a, b] of [
    ["home-desktop.png", "homepage.png"],
    ["desktop.png", "workspace.png"],
    ["mobile.png", "workspace-mobile.png"],
  ])
    await fs.copyFile(".impeccable/review/" + a, "docs/media/" + b);
  console.log("Saved product media");
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
