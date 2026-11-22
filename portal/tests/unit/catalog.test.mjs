import { describe, expect, it } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { buildCatalog, readFrontmatter } from '../../scripts/build-catalog.mjs';

const REPO = resolve(import.meta.dirname, '..', '..', '..');

describe('buildCatalog on the real repository', () => {
  const catalog = buildCatalog(REPO);

  it('finds every kind the kit ships', () => {
    // Arrange / Act done above. Assert:
    expect(catalog.counts).toMatchObject({ plugin: 10, skill: 40, agent: 19, rule: 11, workflow: 16, sidecar: 3, tool: 2 });
    expect(catalog.counts.hook).toBeGreaterThan(0);
  });

  it('gives every item a unique id, a source link and at least one host', () => {
    const ids = catalog.items.map((i) => i.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const item of catalog.items) {
      expect(item.source, item.id).toMatch(/^https:\/\/github\.com\/jggomez\/expert-ai-developer-skills\//);
      expect(item.hosts.length, item.id).toBeGreaterThan(0);
    }
  });

  it('links senior-dev to its agents, skills and hooks', () => {
    const plugin = catalog.items.find((i) => i.id === 'plugin/senior-dev');
    expect(plugin.contains.agent).toContain('senior-dev-orchestrator');
    expect(plugin.contains.skill).toContain('qa-tester');
    expect(plugin.contains.hook).toContain('orchestrator-role-gate');
    expect(plugin.install.claude).toBe('claude plugin install senior-dev@expert-ai-developer-skills');
    expect(plugin.install.antigravity).toBe('agy plugin install ./plugins/antigravity/senior-dev');
  });

  it('records which plugins bundle a skill and how to install it alone', () => {
    const skill = catalog.items.find((i) => i.id === 'skill/context-capture');
    expect(skill.includedIn).toEqual(expect.arrayContaining(['senior-dev', 'shared-context']));
    expect(skill.install.skills).toBe('npx skills add jggomez/expert-ai-developer-skills --skill context-capture');
  });

  it('extracts slash commands from workflow headings', () => {
    const wf = catalog.items.find((i) => i.id === 'workflow/ship-workflow');
    expect(wf.command).toBe('/ship');
  });
});

describe('buildCatalog on a minimal fixture', () => {
  it('reads a skill and a plugin from an arbitrary repo root', () => {
    // Arrange
    const root = mkdtempSync(join(tmpdir(), 'catalog-'));
    mkdirSync(join(root, 'skills', 'demo'), { recursive: true });
    writeFileSync(join(root, 'skills', 'demo', 'SKILL.md'), '---\nname: demo\ndescription: Demo skill.\n---\n# Demo\n');
    mkdirSync(join(root, 'plugins', 'claude', 'p1', '.claude-plugin'), { recursive: true });
    mkdirSync(join(root, 'plugins', 'claude', 'p1', 'skills', 'demo'), { recursive: true });
    writeFileSync(join(root, 'plugins', 'claude', 'p1', '.claude-plugin', 'plugin.json'), '{"name":"p1","description":"Plugin one."}');
    // Act
    const catalog = buildCatalog(root);
    // Assert
    expect(catalog.counts).toEqual({ plugin: 1, skill: 1 });
    expect(catalog.items.find((i) => i.id === 'skill/demo').includedIn).toEqual(['p1']);
  });

  it('fails loudly on broken frontmatter', () => {
    const root = mkdtempSync(join(tmpdir(), 'catalog-'));
    const file = join(root, 'bad.md');
    writeFileSync(file, '---\nname: [unclosed\n---\nbody');
    expect(() => readFrontmatter(file)).toThrow(/Invalid frontmatter/);
  });
});
