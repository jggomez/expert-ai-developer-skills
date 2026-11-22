#!/usr/bin/env node
/**
 * Builds portal/src/data/catalog.json from the repository sources so the portal never
 * drifts from what the kit actually ships: plugins, subagents, skills, rules, workflows,
 * hooks, sidecars and standalone tools, plus the relations between them.
 *
 * Usage: node scripts/build-catalog.mjs [--repo <path>] [--out <path>]
 */
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync, mkdirSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseYaml } from 'yaml';

const HERE = dirname(fileURLToPath(import.meta.url));
export const REPO_SLUG = 'jggomez/expert-ai-developer-skills';
export const MARKETPLACE = 'expert-ai-developer-skills';
const GITHUB_TREE = `https://github.com/${REPO_SLUG}/tree/main`;
const GITHUB_BLOB = `https://github.com/${REPO_SLUG}/blob/main`;
const HOSTS = ['claude', 'antigravity'];

/** Lists sub-directories of `dir` (sorted); empty when `dir` is missing. */
function listDirs(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((name) => !name.startsWith('.') && !name.startsWith('__') && statSync(join(dir, name)).isDirectory())
    .sort();
}

/** Lists files in `dir` with extension `ext` (sorted); empty when `dir` is missing. */
function listFiles(dir, ext) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((name) => name.endsWith(ext) && statSync(join(dir, name)).isFile())
    .sort();
}

/** Splits a Markdown file into YAML frontmatter (object) and body (string). */
export function readFrontmatter(file) {
  const text = readFileSync(file, 'utf8');
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!match) return { data: {}, body: text };
  try {
    return { data: parseYaml(match[1]) ?? {}, body: match[2] };
  } catch (err) {
    throw new Error(`Invalid frontmatter in ${file}: ${err.message}`);
  }
}

/** First H1 heading of a Markdown body, without the leading '#'. */
function firstHeading(body) {
  const line = body.split('\n').find((l) => /^#\s+/.test(l));
  return line ? line.replace(/^#\s+/, '').trim() : '';
}

/** First prose paragraph of a Markdown body (skips headings, badges, quotes, lists). */
function firstParagraph(body) {
  const blocks = body.split(/\n\s*\n/).map((b) => b.trim());
  const prose = blocks.find((b) => b && !/^(#|\[!\[|!\[|>|\||-|\*|```|<)/.test(b));
  return prose ? prose.replace(/\s+/g, ' ') : '';
}

function readJson(file) {
  try {
    return JSON.parse(readFileSync(file, 'utf8'));
  } catch (err) {
    throw new Error(`Invalid JSON in ${file}: ${err.message}`);
  }
}

function clean(text) {
  return String(text ?? '').replace(/\s+/g, ' ').trim();
}

/** Reads every plugin for both hosts and returns a map name -> plugin record. */
function collectPlugins(repo) {
  const plugins = new Map();
  for (const host of HOSTS) {
    const root = join(repo, 'plugins', host);
    for (const name of listDirs(root)) {
      const dir = join(root, name);
      const manifestPath = host === 'claude' ? join(dir, '.claude-plugin', 'plugin.json') : join(dir, 'plugin.json');
      const manifest = existsSync(manifestPath) ? readJson(manifestPath) : {};
      const record = plugins.get(name) ?? {
        name,
        hosts: [],
        description: '',
        agents: new Set(),
        skills: new Set(),
        hooks: new Set(),
        mcp: false,
      };
      record.hosts.push(host);
      if (!record.description && manifest.description) record.description = clean(manifest.description);
      for (const file of listFiles(join(dir, 'agents'), '.md')) record.agents.add(basename(file, '.md'));
      for (const skill of listDirs(join(dir, 'skills'))) record.skills.add(skill);
      for (const file of listFiles(join(dir, 'hooks'), '.js')) record.hooks.add(basename(file, '.js'));
      if (existsSync(join(dir, 'mcp')) || existsSync(join(dir, 'mcp_config.json')) || existsSync(join(dir, '.mcp.json'))) {
        record.mcp = true;
      }
      plugins.set(name, record);
    }
  }
  return plugins;
}

/** Builds the full catalog object for the repository at `repo`. */
export function buildCatalog(repo) {
  const plugins = collectPlugins(repo);
  const items = [];
  const pluginsWith = (key, value) =>
    [...plugins.values()].filter((p) => p[key].has(value)).map((p) => p.name).sort();

  for (const p of plugins.values()) {
    const readme = join(repo, 'plugins', 'claude', p.name, 'README.md');
    const lead = existsSync(readme) ? firstParagraph(readFileSync(readme, 'utf8')) : '';
    items.push({
      id: `plugin/${p.name}`,
      type: 'plugin',
      slug: p.name,
      name: p.name,
      description: p.description || lead,
      hosts: [...p.hosts].sort(),
      source: `${GITHUB_TREE}/plugins/${p.hosts.includes('claude') ? 'claude' : 'antigravity'}/${p.name}`,
      contains: {
        agent: [...p.agents].sort(),
        skill: [...p.skills].sort(),
        hook: [...p.hooks].sort(),
      },
      mcp: p.mcp,
      install: {
        claude: p.hosts.includes('claude') ? `claude plugin install ${p.name}@${MARKETPLACE}` : null,
        antigravity: p.hosts.includes('antigravity') ? `agy plugin install ./plugins/antigravity/${p.name}` : null,
      },
    });
  }

  for (const slug of listDirs(join(repo, 'skills'))) {
    const file = join(repo, 'skills', slug, 'SKILL.md');
    if (!existsSync(file)) continue;
    const { data, body } = readFrontmatter(file);
    const inPlugins = pluginsWith('skills', slug);
    items.push({
      id: `skill/${slug}`,
      type: 'skill',
      slug,
      name: clean(data.name) || slug,
      title: firstHeading(body),
      description: clean(data.description),
      hosts: [...new Set(inPlugins.flatMap((n) => plugins.get(n).hosts))].sort(),
      source: `${GITHUB_TREE}/skills/${slug}`,
      includedIn: inPlugins,
      install: { skills: `npx skills add ${REPO_SLUG} --skill ${slug}` },
    });
  }

  const agentSeen = new Map();
  for (const p of plugins.values()) {
    for (const host of p.hosts) {
      for (const file of listFiles(join(repo, 'plugins', host, p.name, 'agents'), '.md')) {
        const slug = basename(file, '.md');
        const path = `plugins/${host}/${p.name}/agents/${file}`;
        const entry = agentSeen.get(slug) ?? { slug, path, description: '', model: '', plugins: new Set(), hosts: new Set() };
        entry.plugins.add(p.name);
        entry.hosts.add(host);
        if (!entry.description || host === 'claude') {
          const { data } = readFrontmatter(join(repo, path));
          if (data.description) {
            entry.description = clean(data.description);
            entry.model = clean(data.model);
            entry.path = path;
          }
        }
        agentSeen.set(slug, entry);
      }
    }
  }
  for (const a of [...agentSeen.values()].sort((x, y) => x.slug.localeCompare(y.slug))) {
    const owners = [...a.plugins].sort();
    const isOrchestrator = a.slug.endsWith('orchestrator');
    items.push({
      id: `agent/${a.slug}`,
      type: 'agent',
      slug: a.slug,
      name: a.slug,
      description: a.description,
      model: a.model || 'inherit',
      hosts: [...a.hosts].sort(),
      source: `${GITHUB_BLOB}/${a.path}`,
      includedIn: owners,
      install: isOrchestrator ? { claude: `claude --agent ${owners[0]}:${a.slug}` } : {},
    });
  }

  const hookSeen = new Map();
  for (const p of plugins.values()) {
    for (const host of p.hosts) {
      for (const file of listFiles(join(repo, 'plugins', host, p.name, 'hooks'), '.js')) {
        const slug = basename(file, '.js');
        const entry = hookSeen.get(slug) ?? { slug, path: `plugins/${host}/${p.name}/hooks/${file}`, plugins: new Set(), hosts: new Set() };
        entry.plugins.add(p.name);
        entry.hosts.add(host);
        hookSeen.set(slug, entry);
      }
    }
  }
  for (const h of [...hookSeen.values()].sort((x, y) => x.slug.localeCompare(y.slug))) {
    items.push({
      id: `hook/${h.slug}`,
      type: 'hook',
      slug: h.slug,
      name: h.slug,
      description: '',
      hosts: [...h.hosts].sort(),
      source: `${GITHUB_BLOB}/${h.path}`,
      includedIn: [...h.plugins].sort(),
      install: {},
    });
  }

  for (const file of listFiles(join(repo, 'rules'), '.md')) {
    if (file === 'README.md') continue;
    const slug = basename(file, '.md');
    const { data, body } = readFrontmatter(join(repo, 'rules', file));
    items.push({
      id: `rule/${slug}`,
      type: 'rule',
      slug,
      name: slug,
      title: firstHeading(body).replace(/^Rule:\s*/, ''),
      description: clean(data.description),
      hosts: ['antigravity', 'claude'],
      source: `${GITHUB_BLOB}/rules/${file}`,
      includedIn: [],
      install: {},
    });
  }

  for (const file of listFiles(join(repo, 'workflows'), '.md')) {
    if (file === 'README.md') continue;
    const slug = basename(file, '.md');
    const { data, body } = readFrontmatter(join(repo, 'workflows', file));
    const heading = firstHeading(body).replace(/^Workflow:\s*/, '');
    const command = (heading.match(/\((\/[^)]+)\)/) || [])[1] || null;
    items.push({
      id: `workflow/${slug}`,
      type: 'workflow',
      slug,
      name: slug,
      title: heading.replace(/\s*\([^)]*\)\s*$/, ''),
      command,
      description: clean(data.description) || firstParagraph(body),
      hosts: ['antigravity', 'claude'],
      source: `${GITHUB_BLOB}/workflows/${file}`,
      includedIn: [],
      install: {},
    });
  }

  for (const slug of listDirs(join(repo, 'sidecars'))) {
    const file = join(repo, 'sidecars', slug, 'sidecar.json');
    if (!existsSync(file)) continue;
    const data = readJson(file);
    items.push({
      id: `sidecar/${slug}`,
      type: 'sidecar',
      slug,
      name: slug,
      title: clean(data.display_name),
      description: clean(data.description),
      schedule: data.builtin === 'schedule' ? data.args?.[0] ?? null : null,
      hosts: ['antigravity'],
      source: `${GITHUB_TREE}/sidecars/${slug}`,
      includedIn: [],
      install: {},
    });
  }

  for (const slug of listDirs(join(repo, 'tools'))) {
    const readme = join(repo, 'tools', slug, 'README.md');
    if (!existsSync(readme)) continue;
    const body = readFileSync(readme, 'utf8');
    items.push({
      id: `tool/${slug}`,
      type: 'tool',
      slug,
      name: slug,
      description: firstParagraph(body),
      hosts: ['antigravity', 'claude'],
      source: `${GITHUB_TREE}/tools/${slug}`,
      includedIn: [],
      install: {},
    });
  }

  const counts = {};
  for (const item of items) counts[item.type] = (counts[item.type] ?? 0) + 1;
  return { repo: REPO_SLUG, marketplace: MARKETPLACE, counts, items };
}

function main() {
  const args = process.argv.slice(2);
  const flag = (name, fallback) => {
    const i = args.indexOf(name);
    return i >= 0 && args[i + 1] ? resolve(args[i + 1]) : fallback;
  };
  const repo = flag('--repo', resolve(HERE, '..', '..'));
  const out = flag('--out', resolve(HERE, '..', 'src', 'data', 'catalog.json'));
  const catalog = buildCatalog(repo);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, `${JSON.stringify(catalog, null, 2)}\n`);
  console.log(`catalog: ${catalog.items.length} items ${JSON.stringify(catalog.counts)} -> ${out}`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (err) {
    console.error(`build-catalog failed: ${err.message}`);
    process.exit(1);
  }
}
