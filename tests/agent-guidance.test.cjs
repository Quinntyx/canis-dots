// Static guidance contracts only; these do not prove agent behavior or deployment.
// Run from the checkout with: node --test tests/agent-guidance.test.cjs
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');

const root = path.resolve(__dirname, '..');
const files = execFileSync('git', ['ls-files', '--cached', '--others', '--exclude-standard', '-z'], { cwd: root, encoding: 'utf8' })
  .split('\0').filter(file => file && fs.existsSync(path.join(root, file)));
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
// Suffixes survive relocation from legacy dot_* sources into roles/agents/files.
const locate = suffix => {
  const matches = files.filter(file => file.endsWith(suffix));
  assert.equal(matches.length, 1, `Expected one guidance source ending in ${suffix}`);
  return matches[0];
};
const configSkills = [
  'pi/profiles/main/skills/edit-config/SKILL.md',
  'pi/profiles/t3main/skills/edit-config/SKILL.md',
  'claude/skills/edit-config/SKILL.md',
].map(locate);

for (const file of configSkills) {
  test(`${file}: manifest/controller and bounded deployment contract`, () => {
    const text = read(file);
    assert.match(text, /^---\nname: edit-config\ndescription: "[^"]+"\nmetadata:\n  type: procedure\n---\n/);
    const description = text.match(/^description: "([^"]+)"/m)[1].replace(/\s+/g, ' ');
    assert.ok(description.length > 0 && description.length <= 1024, 'Pi description size');
    for (const required of [
      'name: edit-config', 'type: procedure', '# Contract', '# Entrypoint',
      'scripts/dots-source', '~/.config/ansible/dots-source.json',
      'source_root', 'inventory_hostname', 'path on the controller',
      'roles/<component>/manifest.yml', '`source`, `dest`, `mode`',
      'ansible.cfg', 'inventory/hosts.yml', 'playbooks/site.yml',
      'inventory/group_vars', 'inventory/host_vars',
      'encrypted_files/<host>/...', 'policy/secrets.yml', 'no_log: true', 'diff: false',
      'scripts/deploy --host "$host" --components "$components" --check --diff',
      'Component scope is not exact-file scope', 'Source-only', 'no-deploy',
    ]) assert.ok(text.includes(required), `${file} is missing ${required}`);
    assert.ok(text.indexOf('## Stage 3: Publish') < text.indexOf('## Stage 4: Deploy'));
    assert.ok(!/\.\.\/\.\.\/\.\.\//.test(text), 'Do not hard-code the source layout');
  });
}

test('user-owned executing guidance no longer selects Chezmoi', () => {
  const guidance = files.filter(file => file.endsWith('.md') && (
    file.includes('/pi/profiles/') || /(?:^|\/)(?:dot_claude|\.?claude)\//.test(file)
  ) && !file.endsWith('/MIGRATION.md') && !/\/skills\/(cloudflare|freya|wrangler)\//.test(file));
  assert.ok(guidance.length > configSkills.length, 'The scan must include callers, not just owners');
  const stale = guidance.filter(file => /\bchezmoi\b|\.chezmoi/i.test(read(file)));
  assert.deepEqual(stale, [], 'Migrate callers too; upstream resources and audit history are excluded');
});

test('Claude keeps native configuration semantics behind source ownership', () => {
  const text = read(locate('claude/skills/edit-config/SKILL.md'));
  for (const required of ['/update-config', 'source-only boundary', '~/.claude.json',
    'Plugin caches', 'fresh-session discovery']) assert.ok(text.includes(required), required);
});

test('changed skill dependencies still resolve after source relocation', () => {
  const changedSkills = files.filter(file => /\/skills\/(?:edit-config|git|pi-plugin|aerc-email)\//.test(file)
    && file.endsWith('/SKILL.md'));
  for (const file of changedSkills) {
    const text = read(file);
    for (const match of text.matchAll(/`((?:\.\.\/)+[^`\n]+\/SKILL\.md)`/g)) {
      assert.ok(fs.existsSync(path.resolve(root, path.dirname(file), match[1])),
        `${file}: missing dependency ${match[1]}`);
    }
  }
});
