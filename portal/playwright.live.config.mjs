import { defineConfig } from '@playwright/test';
// Same journeys, run against the deployed site. Usage: npx playwright test -c playwright.live.config.mjs
export default defineConfig({ testDir: 'tests/e2e', use: { baseURL: 'https://senior-ai-dev-kit.web.app' } });
