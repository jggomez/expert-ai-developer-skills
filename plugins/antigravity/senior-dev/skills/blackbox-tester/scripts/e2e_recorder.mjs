// Records what a Playwright test really did, for check_evidence.py. Copy to tests/e2e/.
//
//   const run = recordRun(page, 'docs/<feature-name>/evidence');
//   ...drive the app, then compare the screen with the source...
//   run.dataCheck('source-on-screen', 'order 42 from GET /api/orders is listed');
//   run.dataCheck('persisted-after-reload', 'the new order is still listed');
//   await run.save();
import { randomUUID } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export function recordRun(page, evidenceDir, details = {}) {
  const manifest = { version: 1, pages: [], requests: [], dataChecks: [], ...details };
  const pending = [];

  page.on('framenavigated', (frame) => {
    if (frame === page.mainFrame()) manifest.pages.push(frame.url());
  });
  page.on('response', (response) => {
    const request = response.request();
    const entry = {
      method: request.method(),
      url: response.url(),
      status: response.status(),
      resourceType: request.resourceType(),
      remote: false,
    };
    manifest.requests.push(entry);
    // Stubbed and service-worker responses have no server address.
    pending.push(response.serverAddr().then((address) => {
      entry.remote = Boolean(address) && !response.fromServiceWorker();
    }, () => {}));
  });

  return {
    dataCheck(kind, detail) {
      manifest.dataChecks.push({ kind, detail });
    },
    async save() {
      await Promise.all(pending);
      mkdirSync(evidenceDir, { recursive: true });
      writeFileSync(join(evidenceDir, `run-${randomUUID()}.json`), JSON.stringify(manifest, null, 2));
    },
  };
}
