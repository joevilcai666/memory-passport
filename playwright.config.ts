import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config — the browser→API→database release gate (#37).
 *
 * Runs against the production Next.js server (port 3000) talking to the seeded
 * credential-free local Compose stack. Each browser success is paired with an
 * independent API assertion via MP_API_URL. Run with `pnpm test:e2e` after the
 * stack + production server are up (see `make check-e2e` / the CI e2e job).
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
