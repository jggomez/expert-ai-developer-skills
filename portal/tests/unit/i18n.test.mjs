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
