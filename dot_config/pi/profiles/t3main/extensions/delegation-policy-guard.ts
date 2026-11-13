import { realpathSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { getAgentDir, type ExtensionAPI, type ExtensionContext } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  const policyFile = join(getAgentDir(), "skills/subagents/model-selection/SKILL.md");
  let hasReadPolicy = false;

  function isPolicyRead(name: string, args: Record<string, unknown> | undefined, cwd: string) {
    if (name !== "read" || typeof args?.path !== "string") return false;
    let path = args.path.replace(/^@/, "");
    if (path.startsWith("~/")) path = join(homedir(), path.slice(2));
    try {
      // Accept relative paths and symlink aliases, not unrelated same-named files.
      return realpathSync(resolve(cwd, path)) === realpathSync(policyFile);
    } catch {
      return false;
    }
  }

  function restore(_event: unknown, ctx: ExtensionContext) {
    hasReadPolicy = false;
    const reads = new Set<string>();
    // Only startup/resume/reload/tree navigation scans history, never delegation.
    for (const entry of ctx.sessionManager.getBranch()) {
      if (entry.type !== "message") continue;
      const message = entry.message;
      if (message.role === "assistant") {
        for (const part of message.content) {
          if (part.type === "toolCall" && isPolicyRead(part.name, part.arguments, ctx.cwd)) {
            reads.add(part.id);
          }
        }
      } else if (message.role === "toolResult") {
        if ((message.toolName === "read" && !message.isError && reads.has(message.toolCallId)) ||
          message.nestedCalls?.calls.some(call => call.status === "ok" &&
            isPolicyRead(call.name, call.arguments, ctx.cwd))) {
          hasReadPolicy = true;
          return;
        }
      }
    }
  }

  pi.on("session_start", restore);
  pi.on("session_tree", restore);
  pi.on("tool_result", (event, ctx) => {
    // A request alone (or an errored read) must not unlock delegation.
    if (!hasReadPolicy && !event.isError && isPolicyRead(event.toolName, event.input, ctx.cwd)) {
      hasReadPolicy = true;
    }
  });
  pi.on("tool_call", (event) => {
    if (event.toolName === "mcp__t3-code__delegate_task" && !hasReadPolicy) {
      return {
        block: true,
        reason: `Read ${policyFile} before delegating: the capabilities listing is the menu, not the policy.`,
      };
    }
  });
}
