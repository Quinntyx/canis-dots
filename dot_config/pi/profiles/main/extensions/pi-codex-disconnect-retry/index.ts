import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const CODEX_DISCONNECT = /^(?:Codex error:\s*)?stream disconnected before completed\b/i;

export default function (pi: ExtensionAPI) {
  pi.on("message_end", (event) => {
    const message = event.message;
    if (message.role !== "assistant" || message.stopReason !== "error") return;
    if (!CODEX_DISCONNECT.test(message.errorMessage?.trim() ?? "")) return;

    // Preserve provider details while opting into Pi's bounded transport retries.
    return { message: { ...message, errorMessage: `Connection error: ${message.errorMessage}` } };
  });
}
