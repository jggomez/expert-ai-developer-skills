import { test, expect } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const EVIDENCE = resolve(import.meta.dirname, '..', '..', '..', 'docs', 'dev-kit-portal', 'evidence');
mkdirSync(EVIDENCE, { recursive: true });

function trackErrors(page) {
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('response', (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
  return errors;
}

test('root sends a Spanish browser to /es/', async ({ browser }) => {
  const context = await browser.newContext({ locale: 'es-MX' });
  const page = await context.newPage();
  await page.goto('/');
  await expect(page).toHaveURL(/\/es\/$/);
  await expect(page.locator('html')).toHaveAttribute('lang', 'es');
  await context.close();
});

test('root sends an English browser to /en/', async ({ browser }) => {
  const context = await browser.newContext({ locale: 'en-US' });
  const page = await context.newPage();
  await page.goto('/');
  await expect(page).toHaveURL(/\/en\/$/);
  await context.close();
});

test('search and kind filter narrow the catalog', async ({ page }) => {
  const errors = trackErrors(page);
  await page.goto('/es/');
  const rows = page.locator('#list .row:visible');
  await expect(rows).toHaveCount(120);
  await page.getByRole('button', { name: /^hooks/ }).click();
  await expect(rows).toHaveCount(19);
  await page.getByRole('button', { name: /^Todo/ }).click();
  await page.locator('#q').fill('flutter');
  const flutterCount = await rows.count();
  expect(flutterCount).toBeGreaterThan(5);
  // Search covers the visible text and the technical English description kept in data-search.
  for (const haystack of await rows.evaluateAll((els) => els.map((e) => e.dataset.search))) expect(haystack).toContain('flutter');
  const flutterTitles = await page.locator('#list .row:visible .row__title').allInnerTexts();
  expect(flutterTitles.filter((t) => /flutter/i.test(t)).length).toBeGreaterThan(5);
  await expect(page).toHaveURL(/q=flutter/);
  await page.locator('#q').fill('zzzz-no-match');
  await expect(page.locator('#empty')).toBeVisible();
  await page.getByRole('button', { name: 'Quitar filtros' }).click();
  await expect(rows).toHaveCount(120);
  expect(errors).toEqual([]);
});

test('host filter keeps only Antigravity items', async ({ page }) => {
  await page.goto('/en/');
  await page.locator('#host').selectOption('antigravity');
  const hosts = await page.locator('#list .row:visible').evaluateAll((els) => els.map((e) => e.dataset.hosts));
  expect(hosts.length).toBeGreaterThan(0);
  for (const h of hosts) expect(h.split(' ')).toContain('antigravity');
});

test('pipeline phases switch with click and keyboard', async ({ page }) => {
  await page.goto('/en/');
  await page.getByRole('tab', { name: /Verify/ }).click();
  await expect(page.locator('#panel-verify')).toBeVisible();
  await expect(page.locator('#panel-triage')).toBeHidden();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: /Ship/ })).toHaveAttribute('aria-selected', 'true');
  await page.locator('#panel-ship a').first().click();
  await expect(page).toHaveURL(/\/en\/(skill|agent|hook|workflow)\//);
});

test('detail page shows install command, copies it and switches language on the same item', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const errors = trackErrors(page);
  await page.goto('/es/plugin/senior-dev/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Senior dev');
  await expect(page.getByText('claude plugin install senior-dev@expert-ai-developer-skills')).toBeVisible();
  const copy = page.locator('button[data-copy="claude plugin install senior-dev@expert-ai-developer-skills"]');
  await copy.click();
  await expect(copy).toHaveText('Copiado');
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('claude plugin install senior-dev@expert-ai-developer-skills');
  await page.getByRole('link', { name: 'English' }).click();
  await expect(page).toHaveURL(/\/en\/plugin\/senior-dev\/$/);
  await expect(page.getByText('When to use it')).toBeVisible();
  expect(errors).toEqual([]);
});

test('unknown pages render the bilingual 404', async ({ page }) => {
  const res = await page.goto('/es/skill/no-existe/');
  expect(res.status()).toBe(404);
  await expect(page.getByRole('heading', { name: 'Esta página no existe' })).toBeVisible();
});

for (const width of [375, 768, 1280, 1920]) {
  test(`evidence screenshots at ${width}px without horizontal scroll`, async ({ page }) => {
    const errors = trackErrors(page);
    await page.setViewportSize({ width, height: 900 });
    for (const [name, path] of [['home-es', '/es/'], ['detail-en', '/en/skill/qa-tester/']]) {
      await page.goto(path, { waitUntil: 'networkidle' });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `${name} @${width}`).toBeLessThanOrEqual(0);
      await page.screenshot({ path: `${EVIDENCE}/${name}-${width}.png`, fullPage: false });
    }
    expect(errors).toEqual([]);
  });
}
