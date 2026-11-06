import { defineConfig, devices } from "@playwright/test";

// Ponta a ponta contra o portal e a API reais (docker compose, perfil web).
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  reporter: [["list"]],
  outputDir: "test-results",
  use: {
    baseURL: process.env.PORTAL_URL ?? "http://localhost:3000",
    viewport: { width: 1440, height: 900 },
    locale: "pt-BR",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
});
