/**
 * GLM-5.3-Flash Free via OpenCode's anonymous inference endpoint.
 * Adapted from pi-opencode-direct, MIT; see LICENSE and README.md.
 * No process-wide fetch patches, stored credentials, or paid fallback.
 */
import { randomBytes, randomUUID } from "node:crypto";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import {
  createProvider,
  getCurrentSystemPrompt,
  getCurrentTools,
  normalizeContext,
  openAICompletionsApi,
  type Api,
  type Model,
  type StreamOptions,
  type TranscriptContext,
} from "@earendil-works/pi-ai/compat";
import { getBuiltinModels } from "@earendil-works/pi-ai/providers/all";

export const PROVIDER_ID = "opencode-zen-free";
export const MODEL_ID = "glm-5.3-flash-free";
export const BASE_URL = "https://opencode.ai/inference/v1";
const STATIC_HEADERS = {
  "User-Agent": "opencode/latest/2.0.30/cli",
  "x-opencode-client": "cli",
  "x-opencode-project": "global",
};

// OpenCode descending identifiers contain a current timestamp. Keep one per Pi
// session (not per turn), preserving affinity without sharing across subagents.
export function createSessionId(): string {
  const value = ~(BigInt(Date.now()) * 0x1000n + 1n);
  const prefix = (value & ((1n << 48n) - 1n)).toString(16).padStart(12, "0");
  const alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
  const suffix = [...randomBytes(14)].map((b) => alphabet[b % 62]).join("");
  return `ses_${prefix}${suffix}`;
}

export function freeModel(): Model<Api> {
  // Discovery in older pi-opencode-free only intersects live IDs with Pi's
  // bundled list. New IDs disappear until pi-ai updates. Register this ID
  // explicitly, inheriting capabilities/limits from its bundled counterpart.
  const template = getBuiltinModels("opencode").find((m) => m.id === "glm-5.3-flash");
  return {
    ...(template ?? {
      api: "openai-completions",
      reasoning: true,
      input: ["text", "image"],
      contextWindow: 1_000_000,
      maxTokens: 131_072,
      compat: {
        supportsStore: false,
        supportsDeveloperRole: false,
        supportsStrictMode: true,
        maxTokensField: "max_tokens",
      },
    }),
    id: MODEL_ID,
    name: "GLM-5.3-Flash Free (OpenCode)",
    provider: PROVIDER_ID,
    baseUrl: BASE_URL,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    headers: { ...STATIC_HEADERS },
  } as Model<Api>;
}

// OpenCode separately gates short, tool-less compaction requests. Use its
// summarizer instruction only for that auxiliary flow, never normal messages.
export const SUMMARIZER_PROMPT =
  "You are a context summarization agent. You are given a conversation between a user and an agent. Your goal is to produce a structured summary matching the format specified so another coding agent can continue the work.\n" +
  "Always follow the exact output structure requested by the user prompt. Keep every section, preserve exact file paths and identifiers when known, and prefer terse bullets over paragraphs.\n" +
  "Do not continue the conversation. Do not respond to any questions in the conversation. Only output the structured summary in the exact format requested by the user prompt. Respond in the same language as the conversation.\n";

export function prepareContext(context: TranscriptContext): TranscriptContext {
  const normalized = normalizeContext(context);
  const prompt = getCurrentSystemPrompt(normalized.messages);
  const other = normalized.messages.filter((m) => m.role !== "system");
  if (!prompt || prompt.length > 2000 || !prompt.toLowerCase().includes("context summarization") ||
      other.length > 1 || getCurrentTools(normalized.messages).length > 0) return normalized;
  let replaced = false;
  return {
    ...normalized,
    messages: normalized.messages.flatMap((message) => {
      if (message.role !== "system") return [message];
      if (replaced) return [];
      replaced = true;
      return [{ ...message, content: SUMMARIZER_PROMPT }];
    }),
  };
}

export function zenProvider(getSessionId: () => string | undefined = () => undefined) {
  const fallback = randomUUID();
  let currentPiSession = "";
  let currentOpenCodeSession = "";
  const provider = createProvider({
    id: PROVIDER_ID,
    name: "OpenCode Zen Free",
    baseUrl: BASE_URL,
    headers: { ...STATIC_HEADERS },
    // Anonymous free tier ONLY. Never read OPENCODE_API_KEY or paid credentials.
    auth: { apiKey: { name: "OpenCode anonymous free tier", async resolve() { return { auth: { apiKey: "public" }, source: "anonymous free tier" }; } } },
    models: [freeModel()],
    api: { "openai-completions": openAICompletionsApi() },
  });

  function requestOptions<T extends StreamOptions>(options: T = {} as T): T {
    const piSession = options.sessionId ?? getSessionId() ?? fallback;
    if (piSession !== currentPiSession) {
      currentPiSession = piSession;
      currentOpenCodeSession = createSessionId();
    }
    const headers = Object.fromEntries(Object.entries(options.headers ?? {}).filter(([name]) =>
      !["authorization", "user-agent", "x-opencode-session", "x-opencode-session-id",
        "x-session-affinity", "x-session-id", "x-opencode-client", "x-opencode-project",
        "x-opencode-request", "x-client-request-id"].includes(name.toLowerCase())));
    return {
      ...options,
      apiKey: "public",
      sessionId: currentOpenCodeSession,
      timeoutMs: options.timeoutMs ?? 180_000,
      maxRetries: options.maxRetries ?? 2,
      headers: {
        ...headers,
        ...STATIC_HEADERS,
        Authorization: "Bearer public",
        "x-opencode-session": currentOpenCodeSession,
        "x-opencode-session-id": currentOpenCodeSession,
        "x-session-affinity": currentOpenCodeSession,
        "X-Session-Id": currentOpenCodeSession,
      },
    };
  }

  return {
    ...provider,
    stream(model: Model<Api>, context: TranscriptContext, options: StreamOptions = {}) {
      return provider.stream(model, prepareContext(context), requestOptions(options));
    },
    streamSimple(model: Model<Api>, context: TranscriptContext, options: StreamOptions = {}) {
      return provider.streamSimple(model, prepareContext(context), requestOptions(options));
    },
  };
}

export default function (pi: ExtensionAPI) {
  let sessionId: string | undefined;
  pi.on("session_start", (_event, ctx) => { sessionId = ctx.sessionManager.getSessionId(); });
  pi.on("before_agent_start", (_event, ctx) => { sessionId = ctx.sessionManager.getSessionId(); });
  pi.registerProvider(zenProvider(() => sessionId));
}
