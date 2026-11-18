import { defineConfig, devices } from "@playwright/test";

// Ponta a ponta contra o portal e a API reais (docker compose, perfil web).
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  // Uma única API (DuckDB) atende todos os testes. Em paralelo, as geometrias municipais
  // enchem a fila de consultas e a API responde 503 após 5 s (proteção da Vitrine, V5).
  // Um worker custa ~10 s a mais na suíte e a deixa determinística.
  workers: 1,
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
