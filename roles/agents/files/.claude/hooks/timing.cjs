'use strict';
// UserPromptSubmit adapter; runtime state intentionally stays outside chezmoi.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
function localIso(date) {
  const pad=(value,width=2)=>String(value).padStart(width,'0');
  const offset=-date.getTimezoneOffset();
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}${offset<0?'-':'+'}${pad(Math.floor(Math.abs(offset)/60))}:${pad(Math.abs(offset)%60)}`;
}
function timingBlock(now,previous) {
  const lines=['[timing]',`${previous===null?'local_time=':''}${localIso(now)}`];
  if (previous!==null && now.getTime()>=previous) lines.push(`since_last_prompt=${((now.getTime()-previous)/1000).toFixed(1)}s`);
  lines.push('[/timing]');
  return lines.join('\n');
}
module.exports={timingBlock};
if (require.main===module) {
  try {
    const input=JSON.parse(fs.readFileSync(0,'utf8'));
    if (typeof input.session_id!=='string' || !input.session_id) process.exit(0);
    const dir=process.env.CLAUDE_TIMING_STATE_DIR ?? path.join(process.env.XDG_STATE_HOME??path.join(os.homedir(),'.local/state'),'claude-code','timing');
    fs.mkdirSync(dir,{recursive:true,mode:0o700});
    const file=path.join(dir,crypto.createHash('sha256').update(input.session_id).digest('hex')+'.json');
    let previous=null;
    try {const saved=JSON.parse(fs.readFileSync(file,'utf8')).lastUserPromptAt;if(Number.isFinite(saved))previous=saved;} catch {}
    const now=new Date();
    fs.writeFileSync(file,JSON.stringify({lastUserPromptAt:now.getTime()}),{mode:0o600});
    console.log(JSON.stringify({hookSpecificOutput:{hookEventName:'UserPromptSubmit',additionalContext:timingBlock(now,previous)}}));
  } catch (error) {
    // Timing is informational; a broken cache must never reject a real prompt.
    process.stderr.write(`Timing hook skipped: ${error.message}\n`);
  }
}
