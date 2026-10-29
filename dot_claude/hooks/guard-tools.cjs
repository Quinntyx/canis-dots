'use strict';
// Claude PreToolUse adapter for the Pi profile's accidental-command guardrails.
// These regexes intentionally preserve upstream trade-offs; this is not a shell
// parser or a security sandbox. Scripts, obfuscation and other MCP tools can bypass it.
const fs = require('node:fs');
const RM = /(^|[;&|\n/])\s*(?:(?:sudo|time|nice|env|xargs|nohup|command)\s+)*rm(?=\s|$)/;
const SEARCH = /(^|[;&|\n/])\s*(?:(?:sudo|time|nice|env|xargs|nohup|command)\s+)*(find|grep)(?=\s|$)/;
const PYTHON = String.raw`(?:\S*\/)?(?:python|pypy)(?:\d+(?:\.\d+)*)?`;
const FLAGS = String.raw`(?:(?:-[WXQ]\s+\S+|-|-[A-Za-z]+)\s+)*`;
const HEREDOC = new RegExp(String.raw`(?:^|[\s;&|(){}[\]])${PYTHON}\s*${FLAGS}<<-?\s*["']?[A-Za-z_][A-Za-z0-9_]*["']?`);
const INLINE = new RegExp(String.raw`(?:^|[\s;&|(){}[\]])${PYTHON}\s+${FLAGS}-[A-Za-z]*c[A-Za-z]*(?=\s|$|[^A-Za-z0-9_-])`);

function policyReason(event) {
  const input = event.tool_input ?? {};
  if (['Write','Edit','NotebookEdit'].includes(event.tool_name)) {
    const file = input.file_path ?? input.notebook_path ?? '';
    if (file.includes('.env')) return 'Editing .env files is blocked by the migrated permissions policy. Ask the user to make the secret/configuration change outside the agent.';
  }
  if (!['Bash','PowerShell'].includes(event.tool_name)) return null;
  const command = input.command ?? '';
  if (RM.test(command)) return '`rm` is blocked. Use `trash <path>` for recoverable deletion; if trash is unavailable, stop and ask. Git removals should use `git rm --cached` or trash followed by staging.';
  const search = command.match(SEARCH);
  if (search) return `${search[2]} is blocked. Use rg for text searches and rg --files -g '<glob>' for file discovery. git grep and git log --grep= remain allowed.`;
  if (HEREDOC.test(command) || INLINE.test(command)) return 'Inline Python (-c or a stdin heredoc) is blocked. Write a .py file and run it with Bash using an existing project runtime. Do not retry to bypass this rule.';
  return null;
}
module.exports = { policyReason };

if (require.main === module) {
  try {
    const event = JSON.parse(fs.readFileSync(0,'utf8'));
    if (!event || typeof event !== 'object' || typeof event.tool_name !== 'string') throw new Error('missing tool_name');
    const reason = policyReason(event);
    if (reason) { process.stderr.write(reason+'\n'); process.exitCode=2; }
  } catch (error) {
    process.stderr.write(`Policy hook could not validate its payload: ${error.message}\n`);
    process.exitCode=2;
  }
}
