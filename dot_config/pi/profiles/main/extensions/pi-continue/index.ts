import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const CONTINUE = "pi-continue:request";

export default function (pi: ExtensionAPI) {
  // Pi has no public continue() API. Use a hidden control message to start its
  // normal run pipeline, then remove every such marker before model conversion.
  // Filtering by type also handles markers restored from older session entries.
  pi.on("context", (event) => ({
    messages: event.messages.filter(
      (message) => message.role !== "custom" || message.customType !== CONTINUE,
    ),
  }));

  pi.registerCommand("continue", {
    description: "Request another response from the current session without a user turn",
    handler: async (args, ctx) => {
      if (args.trim()) {
        ctx.ui.notify("Usage: /continue (no arguments)", "warning");
        return;
      }
      if (!ctx.isIdle() || ctx.hasPendingMessages()) {
        ctx.ui.notify("Wait for the current request and queued messages to finish.", "warning");
        return;
      }
      if (!ctx.model) {
        ctx.ui.notify("Select a model before using /continue.", "warning");
        return;
      }
      const { messages } = ctx.sessionManager.buildSessionContext();
      if (!messages.some((message) =>
        message.role === "user" || message.role === "assistant" || message.role === "toolResult"
      )) {
        ctx.ui.notify("There is no conversation to continue yet.", "warning");
        return;
      }

      pi.sendMessage(
        { customType: CONTINUE, content: [], display: false },
        { triggerTurn: true },
      );
    },
  });
}
