import { describe, expect, it } from 'vitest';
import { LANGS, PIPELINE, UI, KINDS, KIND_LABELS, KIND_BLURBS, catalogItems, getItem, itemText, swapLangPath, translations } from '../../src/lib/site.mjs';

describe('bilingual content', () => {
  it.each(LANGS)('has a %s title, summary and use for every catalog item', (lang) => {
    for (const item of catalogItems) {
      const text = itemText(lang, item.id);
      expect(text.title?.trim(), `${lang} ${item.id} title`).toBeTruthy();
      expect(text.summary?.trim(), `${lang} ${item.id} summary`).toBeTruthy();
      expect(text.use?.trim(), `${lang} ${item.id} use`).toBeTruthy();
    }
  });

  it.each(LANGS)('has no %s translation for an id that left the catalog', (lang) => {
    const ids = new Set(catalogItems.map((i) => i.id));
    const stale = Object.keys(translations(lang)).filter((id) => !ids.has(id));
    expect(stale).toEqual([]);
  });

  it('keeps the same UI keys in both languages', () => {
    expect(Object.keys(UI.es).sort()).toEqual(Object.keys(UI.en).sort());
    for (const lang of LANGS) {
      for (const kind of KINDS) {
        expect(KIND_LABELS[lang][kind]).toHaveLength(2);
        expect(KIND_BLURBS[lang][kind]).toBeTruthy();
      }
    }
  });

  it('only references real catalog ids in the pipeline', () => {
    for (const phase of PIPELINE) {
      for (const id of phase.ids) expect(getItem(id), `${phase.key}: ${id}`).toBeDefined();
      for (const lang of LANGS) expect(phase.name[lang] && phase.text[lang]).toBeTruthy();
    }
  });

  it('swaps the language prefix and keeps the rest of the path', () => {
    expect(swapLangPath('/es/skill/qa-tester/', 'es')).toBe('/en/skill/qa-tester/');
    expect(swapLangPath('/en/', 'en')).toBe('/es/');
    expect(swapLangPath('/en', 'en')).toBe('/es');
  });

  it('throws on a missing translation instead of rendering blank text', () => {
    expect(() => itemText('es', 'skill/does-not-exist')).toThrow(/Missing es translation/);
  });
});

describe('tools showcase', async () => {
  const { existsSync } = await import('node:fs');
  const { resolve } = await import('node:path');
  const { TOOLS, screenMedia } = await import('../../src/lib/site.mjs');
  const SOURCE = resolve(import.meta.dirname, '..', '..', '..', 'tools');

  it.each(Object.keys(TOOLS))('%s has a screenshot and ES/EN captions for every screen', (slug) => {
    const item = getItem(`tool/${slug}`);
    expect(item, slug).toBeDefined();
    for (const screen of TOOLS[slug].screens) {
      for (const lang of LANGS) {
        const media = screenMedia(item, screen.id, lang);
        expect(media, `${slug} ${screen.id} ${lang}`).toBeDefined();
        expect(existsSync(resolve(SOURCE, slug, 'docs', 'images', media.src.split('/').pop()))).toBe(true);
        expect(screen.name[lang] && screen.caption[lang]).toBeTruthy();
      }
    }
  });

  it('shows the Spanish agent-meter screenshot on Spanish pages', () => {
    const item = getItem('tool/agent-meter');
    expect(screenMedia(item, 'app-live', 'es').src).toBe('/media/agent-meter/app-live-es.png');
    expect(screenMedia(item, 'app-live', 'en').src).toBe('/media/agent-meter/app-live.png');
  });

  it('pins Python 3.12 in the agent-meter install command', () => {
    const commands = TOOLS['agent-meter'].steps.map((s) => s.command).filter(Boolean);
    expect(commands[0]).toMatch(/^uv tool install --python 3\.12 /);
  });
});
