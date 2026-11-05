import { defineConfig, devices } from "@playwright/test";

/**
 * E2E tests run against a running stack (backend :8000 with demo seed data, frontend on BASE_URL).
 *   backend:  uv run python -m app.seed --demo && uv run uvicorn app.main:app
 *   frontend: pnpm build && pnpm start -p 3001
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  fullyParallel: false,
  use: { baseURL: process.env.BASE_URL ?? "http://localhost:3001", trace: "retain-on-failure" },
  projects: [{ name: "mobile", use: { ...devices["Pixel 7"] } }],
});
