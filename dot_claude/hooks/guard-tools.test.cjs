'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const { policyReason } = require('./guard-tools.cjs');

for (const command of ['rm x', 'sudo rm -rf x', 'cd x && rm y', 'printf x | xargs rm', '/bin/rm x', 'env A=1 /usr/bin/rm x', 'find . -name x', 'cat x | grep y', '/usr/bin/grep x y', 'python3 -c "print(1)"', 'python3 -uc "print(1)"', "python3 - <<'PY'\nprint(1)\nPY", 'pypy3 -u << "PY"\npass\nPY']) {
  test(`blocks ${JSON.stringify(command)}`, () => assert.ok(policyReason({tool_name:'Bash',tool_input:{command}})));
}
for (const command of ['trash x', 'rg pattern file', 'rg --files -g "*.md"', 'git grep text', 'git log --grep=fix', 'git rm --cached file', 'rmdir empty', 'python3 script.py', 'python3 -m nbconvert notebook.ipynb', 'printf "affirm"']) {
  test(`allows ${JSON.stringify(command)}`, () => assert.equal(policyReason({tool_name:'Bash',tool_input:{command}}), null));
}
for (const tool_name of ['Write','Edit','NotebookEdit']) {
  test(`protects .env through ${tool_name}`, () => assert.ok(policyReason({tool_name,tool_input:{file_path:'/tmp/.env.local',notebook_path:'/tmp/.env.ipynb'}})));
}
test('inline Python guidance uses saved scripts without retired notebook services', () => {
  const reason = policyReason({tool_name:'Bash',tool_input:{command:'python3 -c "print(1)"'}});
  assert.match(reason, /\.py file/);
  assert.doesNotMatch(reason, /notebook|kernel|MCP/i);
});
test('does not prohibit reading env files', () => assert.equal(policyReason({tool_name:'Read',tool_input:{file_path:'/tmp/.env'}}), null));
test('unrelated tool is untouched', () => assert.equal(policyReason({tool_name:'Agent',tool_input:{}}), null));
test('normal edits work', () => assert.equal(policyReason({tool_name:'Edit',tool_input:{file_path:'/tmp/config.json'}}), null));
test('real hook exits 2 and explains a block', () => {
  const result=spawnSync(process.execPath,[path.join(__dirname,'guard-tools.cjs')],{input:JSON.stringify({tool_name:'Bash',tool_input:{command:'rm /tmp/example'}}),encoding:'utf8'});
  assert.equal(result.status,2);assert.match(result.stderr,/trash/);assert.equal(result.stdout,'');
});
test('real hook allows ordinary commands', () => {
  const result=spawnSync(process.execPath,[path.join(__dirname,'guard-tools.cjs')],{input:JSON.stringify({tool_name:'Bash',tool_input:{command:'rg --files'}}),encoding:'utf8'});
  assert.equal(result.status,0);assert.equal(result.stderr,'');
});
test('invalid hook payload fails closed', () => {
  const result=spawnSync(process.execPath,[path.join(__dirname,'guard-tools.cjs')],{input:'not json',encoding:'utf8'});
  assert.equal(result.status,2);assert.match(result.stderr,/payload/);
});
