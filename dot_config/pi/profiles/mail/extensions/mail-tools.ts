import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileP = promisify(execFile);

// The ONLY tools this profile may call. Everything else (read, bash, write,
// edit, ...) is disabled at session start.
const MAIL_ROUTING_TOOLS = ["mail_notify"] as const;

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "mail_notify",
    label: "Mail Notify",
    description:
      "Surface a routed email as a desktop notification. Call this when an " +
      "email demands the user's attention: something requires an action, it " +
      "comes from an important person, or it is explicitly urgent. Provide a " +
      "short header (sender + topic) and a 1-2 sentence summary of why it " +
      "matters. urgency=critical for time-sensitive items, low for " +
      "informational ones, normal otherwise. Do nothing for ignored mail.",
    promptSnippet:
      "mail_notify(header, summary, urgency) - Surface a routed email as a desktop notification",
    promptGuidelines:
      "You are an email triage agent. You may only call mail_notify. Follow @mail_rules.md.",
    parameters: Type.Object({
      header: Type.String({
        description: "Short notification title, e.g. \"Prof. Chen: thesis draft due Friday\"",
      }),
      summary: Type.String({
        description: "1-2 sentence summary of why this email needs the user's attention",
      }),
      urgency: Type.Union(
        [
          Type.Literal("low"),
          Type.Literal("normal"),
          Type.Literal("critical"),
        ],
        { description: "low | normal | critical (default normal)" }
      ),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      try {
        const urgency = params.urgency ?? "normal";
        const args = [
          "-a", "aerc-mail",
          "-u", urgency,
          "-h", "int:transient:1",
          params.header,
          params.summary,
        ];
        await execFileP("notify-send", args, { timeout: 10_000 });
        return {
          content: [{
            type: "text",
            text: `Sent desktop notification (${urgency}): ${params.header}`,
          }],
          details: { urgency, header: params.header },
        };
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return {
          content: [{ type: "text", text: `Failed to send notification: ${message}` }],
          details: { error: message },
          isError: true,
        };
      }
    },
  });

  pi.on("session_start", () => {
    // Restrict this profile to the mail routing tools only.
    pi.setActiveTools([...MAIL_ROUTING_TOOLS]);
  });
}
