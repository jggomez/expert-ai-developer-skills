import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://senior-ai-dev-kit.web.app',
  trailingSlash: 'always',
  build: { format: 'directory' },
});
