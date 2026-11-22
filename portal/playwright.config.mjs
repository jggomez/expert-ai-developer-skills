import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: 'tests/e2e',
  use: { baseURL: 'http://localhost:4321' },
  webServer: { command: 'node tests/e2e/serve.mjs', url: 'http://localhost:4321/es/', reuseExistingServer: true, timeout: 60000 },
});
