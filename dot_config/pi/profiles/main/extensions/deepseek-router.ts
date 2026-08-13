/**
 * deepseek-router.ts
 *
 * A "fake" provider that presents three router models to Pi:
 *   - deepseek-v4-flash    : opencode (free) -> opencode-go -> openrouter (200k ctx cap)
 *   - deepseek-v4-flash-1m : opencode-go              -> openrouter (1M ctx, no free tier)
 *   - deepseek-v4-pro      : opencode-go              -> openrouter
 *
 * The provider's streamSimple() re-issues the *same* normalized request
 * against each upstream provider in order, failing over silently (without the
 * agent re-sending the user's prompt) when an upstream fails before emitting
 * any content due to quota exhaustion. The first upstream that
 * starts streaming "wins"; its events are forwarded verbatim so Pi attributes
 * usage and cost to the real serving provider.
 * After a quota failure, the failed provider is put on a wall-clock
 * backoff (1-2 min, x2 per failure, capped at 1h) so we don't re-hit it on
 * every agent message; the first healthy upstream serves silently.
 *
 * A compound footer status shows, for the active tier:
 *   Free · Go NN% · OpenRouter $X.XX
 *   Go NN% · OpenRouter $X.XX
 * where "Go NN%" is OpenCode Go's dashboard usage percentage and
 * "OpenRouter $X.XX" is OpenRouter's *billed* credit usage (GET /api/v1/key).
 *
 * Config (optional, auto-discovered at <agent-dir>/deepseek-router.json):
 *   {
 *     "flash": [ {provider, model, label}, ... ],
 *     "pro":   [ {provider, model, label}, ... ],
 *     "go":    { "workspaceId": "", "authCookie": "" }
 *   }
 * The `go` block is only needed for the OpenCode Go quota percentage; it is
 * read from OpenCode's web dashboard (the completion API key does not expose
 * quota). Leave it empty to show "Go —" instead.
 */

import { createAssistantMessageEventStream } from "@earendil-works/pi-ai";
import type {
  AssistantMessage,
  AssistantMessageEvent,
  AssistantMessageEventStream,
} from "@earendil-works/pi-ai";
import type {
  ExtensionAPI,
  ExtensionContext,
  ExtensionUIContext,
  ModelRegistry,
} from "@earendil-works/pi-coding-agent";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RouteStep {
  provider: string;
  model: string;
  label: string;
}

interface GoQuotaConfig {
  workspaceId?: string;
  authCookie?: string;
}

interface RouterConfig {
  flash: RouteStep[];
  flash1m: RouteStep[];
  pro: RouteStep[];
  go?: GoQuotaConfig;
}

type Tier = "flash" | "flash1m" | "pro";

interface WindowUsage {
  pct: number;
  resetInSec: number;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_CONFIG: RouterConfig = {
  flash: [
    { provider: "opencode", model: "deepseek-v4-flash-free", label: "Free" },
    { provider: "opencode-go", model: "deepseek-v4-flash", label: "Go" },
    { provider: "openrouter", model: "deepseek/deepseek-v4-flash-0731", label: "OpenRouter" },
  ],
  flash1m: [
    { provider: "opencode-go", model: "deepseek-v4-flash", label: "Go" },
    { provider: "openrouter", model: "deepseek/deepseek-v4-flash-0731", label: "OpenRouter" },
  ],
  pro: [
    { provider: "opencode-go", model: "deepseek-v4-pro", label: "Go" },
    { provider: "openrouter", model: "deepseek/deepseek-v4-pro", label: "OpenRouter" },
  ],
};

const ROUTER_PROVIDER = "deepseek-router";
const FLASH_MODEL = "deepseek-v4-flash";
const FLASH_1M_MODEL = "deepseek-v4-flash-1m";
const PRO_MODEL = "deepseek-v4-pro";

const AGENT_DIR = process.env.PI_CODING_AGENT_DIR || join(homedir(), ".pi", "agent");
const CONFIG_PATH = join(AGENT_DIR, "deepseek-router.json");

// Only genuine quota exhaustion triggers silent failover to the next
// upstream. Everything else (rate-limit, 5xx, network hiccups) surfaces
// normally so Pi's own auto-retry handles it without rotating prematurely.
const OVERFLOW_RE = /context.?length|too long|maximum context|input.*(?:token|length)|prompt.*too/i;
const QUOTA_RE = /free.?usage.?limit|go.?usage.?limit|insufficient_quota|quota|usage limit|out of budget|billing|available balance|out of credit|insufficient credit|credit balance/i;
const ABORT_RE = /abort|cancel/i;

// ---------------------------------------------------------------------------
// Module state (captured from ctx; streamSimple has no ctx)
// ---------------------------------------------------------------------------

let registry: ModelRegistry | null = null;
let ui: ExtensionUIContext | null = null;
let config: RouterConfig = cloneConfig(DEFAULT_CONFIG);

let activeTier: Tier | null = null;
let servedBy: string | null = null;
let piRef: ExtensionAPI | null = null;
let lastStatus: string | undefined;

// Per-provider failure backoff: after a retryable (pre-content) failure we
// avoid re-hitting the same upstream for a wall-clock window that grows
// exponentially — 1-2 min initially, x2 per failure, capped at 1 hour.
const BACKOFF_INITIAL_MIN = 60_000;
const BACKOFF_INITIAL_MAX = 120_000;
const BACKOFF_MULTIPLIER = 2;
const BACKOFF_MAX = 3_600_000;

interface BackoffState {
  nextRetryAt: number;
  delayMs: number;
}
const backoff = new Map<string, BackoffState>();

// Quota / spend state.
let goRolling: WindowUsage | null = null;
let goWeekly: WindowUsage | null = null;
let goMonthly: WindowUsage | null = null;
let orTotal: number | null = null;
let orLimitRemaining: number | null = null;

let lastGoRefresh = 0;
let lastOrRefresh = 0;
const REFRESH_TTL_MS = 30_000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function cloneConfig(c: RouterConfig): RouterConfig {
  return {
    flash: c.flash.map((s) => ({ ...s })),
    flash1m: c.flash1m.map((s) => ({ ...s })),
    pro: c.pro.map((s) => ({ ...s })),
    go: c.go ? { ...c.go } : undefined,
  };
}

function loadConfig(): void {
  try {
    const raw = JSON.parse(readFileSync(CONFIG_PATH, "utf8")) as Partial<RouterConfig>;
    config = {
      flash: Array.isArray(raw.flash) && raw.flash.length ? raw.flash : cloneConfig(DEFAULT_CONFIG).flash,
      flash1m: Array.isArray(raw.flash1m) && raw.flash1m.length ? raw.flash1m : cloneConfig(DEFAULT_CONFIG).flash1m,
      pro: Array.isArray(raw.pro) && raw.pro.length ? raw.pro : cloneConfig(DEFAULT_CONFIG).pro,
      go: { ...(raw.go ?? {}) },
    };
  } catch {
    config = cloneConfig(DEFAULT_CONFIG);
  }
}

function buildError(model: any, message: string): AssistantMessage {
  return {
    role: "assistant",
    content: [],
    api: model.api,
    provider: model.provider,
    model: model.id,
    usage: {
      input: 0,
      output: 0,
      cacheRead: 0,
      cacheWrite: 0,
      totalTokens: 0,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
    },
    stopReason: "error",
    errorMessage: message,
    timestamp: Date.now(),
  } as unknown as AssistantMessage;
}

function classifyError(message: AssistantMessage): "retryable" | "hard" {
  const text = String((message as any).errorMessage ?? "");
  if (ABORT_RE.test(text)) return "hard";
  if (OVERFLOW_RE.test(text)) return "hard";
  if (QUOTA_RE.test(text)) return "retryable";
  return "hard";
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

const SCRAPED_NUMBER = "(-?\\d+(?:\\.\\d+)?)";
function parseWindow(html: string, key: string): WindowUsage | null {
  const pctFirst = new RegExp(`${key}:\\$R\\[\\d+\\]=\\{[^}]*usagePercent:${SCRAPED_NUMBER}[^}]*resetInSec:${SCRAPED_NUMBER}[^}]*\\}`);
  const resetFirst = new RegExp(`${key}:\\$R\\[\\d+\\]=\\{[^}]*resetInSec:${SCRAPED_NUMBER}[^}]*usagePercent:${SCRAPED_NUMBER}[^}]*\\}`);

  const m = pctFirst.exec(html);
  if (m) {
    const pct = Number(m[1]);
    const resetInSec = Number(m[2]);
    if (Number.isFinite(pct) && Number.isFinite(resetInSec)) return { pct, resetInSec };
  }
  const m2 = resetFirst.exec(html);
  if (m2) {
    const resetInSec = Number(m2[1]);
    const pct = Number(m2[2]);
    if (Number.isFinite(pct) && Number.isFinite(resetInSec)) return { pct, resetInSec };
  }
  return null;
}

function fmtMoney(v: number): string {
  if (v === 0) return "$0.00";
  if (v < 0.01) return `$${v.toFixed(4)}`;
  return `$${v.toFixed(2)}`;
}

function fmtDuration(sec: number): string {
  if (!Number.isFinite(sec) || sec <= 0) return "soon";
  const m = Math.round(sec / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  const d = Math.floor(h / 24);
  if (d > 0) return `${d}d ${h % 24}h`;
  if (rem === 0) return `${h}h`;
  return `${h}h ${rem}m`;
}

// ---------------------------------------------------------------------------
// Upstream quota / spend refresh
// ---------------------------------------------------------------------------

async function refreshOpenRouterSpend(force = false): Promise<void> {
  const now = Date.now();
  if (!force && now - lastOrRefresh < REFRESH_TTL_MS) return;
  lastOrRefresh = now;

  if (!registry) return;
  try {
    const key = await registry.getApiKeyForProvider("openrouter");
    if (!key) {
      orTotal = null;
      orLimitRemaining = null;
      return;
    }
    const res = await fetchWithTimeout(
      "https://openrouter.ai/api/v1/key",
      { headers: { Authorization: `Bearer ${key}`, Accept: "application/json" } },
      10_000,
    );
    if (!res.ok) return; // keep last-known value
    const body: any = await res.json();
    const data = body?.data ?? body ?? {};
    if (typeof data.usage === "number") orTotal = data.usage;
    if (typeof data.limit_remaining === "number") orLimitRemaining = data.limit_remaining;
  } catch {
    // keep last-known value
  }
}

async function refreshGoQuota(force = false): Promise<void> {
  const now = Date.now();
  if (!force && now - lastGoRefresh < REFRESH_TTL_MS) return;
  lastGoRefresh = now;

  const go = config.go;
  if (!go?.workspaceId || !go?.authCookie) {
    goRolling = null;
    goWeekly = null;
    goMonthly = null;
    return;
  }

  try {
    const res = await fetchWithTimeout(
      `https://opencode.ai/workspace/${encodeURIComponent(go.workspaceId)}/go`,
      {
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Gecko/20100101 Firefox/148.0",
          Accept: "text/html",
          Cookie: `auth=${go.authCookie}`,
        },
      },
      10_000,
    );
    if (!res.ok) return;
    const html = await res.text();
    const rolling = parseWindow(html, "rollingUsage");
    const weekly = parseWindow(html, "weeklyUsage");
    const monthly = parseWindow(html, "monthlyUsage");
    if (!rolling && !weekly && !monthly) {
      goRolling = null;
      return;
    }
    goRolling = rolling;
    goWeekly = weekly;
    goMonthly = monthly;
  } catch {
    // keep last-known value
  }
}

async function refreshQuota(force = false): Promise<void> {
  await Promise.all([refreshOpenRouterSpend(force), refreshGoQuota(force)]);
}

// ---------------------------------------------------------------------------
// Footer status
// ---------------------------------------------------------------------------

function emitStatus(text: string | undefined): void {
  lastStatus = text;
  piRef?.events.emit("deepseek-router:status", text ?? null);
}

function renderStatus(): void {
  if (!ui) return;
  if (!activeTier) {
    ui.setStatus("deepseek-router", undefined);
    emitStatus(undefined);
    return;
  }

  const parts: string[] = [];
  // Real backend that served the last agent turn (Free / Go / OpenRouter)
  parts.push(servedBy ?? "—");
  parts.push(goRolling ? `${Math.round(goRolling.pct)}%` : "—");
  parts.push(orTotal != null ? fmtMoney(orTotal) : "—");
  const text = parts.join(" · ");
  ui.setStatus("deepseek-router", text);
  emitStatus(text);
}

function notify(message: string, type: "info" | "warning" | "error" = "info"): void {
  ui?.notify?.(message, type);
}

// ---------------------------------------------------------------------------
// Router streamSimple
// ---------------------------------------------------------------------------

type ForwardResult =
  | { kind: "success" }
  | { kind: "retryable"; message: AssistantMessage }
  | { kind: "hard"; message: AssistantMessage };

/**
 * Forwards an upstream stream into `out`. Emits nothing until the upstream is
 * committed to a concrete result, so a pre-content failure can be failed over
 * invisibly. Returns:
 *  - success   -> start/content/done already forwarded to `out`.
 *  - retryable -> NOTHING forwarded; caller may try the next upstream.
 *  - hard      -> start(+content)+error already forwarded to `out`.
 */
async function forward(sub: AssistantMessageEventStream, out: AssistantMessageEventStream): Promise<ForwardResult> {
  let stashedStart: AssistantMessageEvent | null = null;
  let emitted = false;

  for await (const ev of sub) {
    if (ev.type === "start") {
      stashedStart = ev;
      continue;
    }
    if (ev.type === "done") {
      if (stashedStart && !emitted) {
        out.push(stashedStart);
        emitted = true;
      }
      out.push(ev);
      return { kind: "success" };
    }
    if (ev.type === "error") {
      if (!emitted) {
        const cls = classifyError(ev.error);
        if (cls === "retryable") {
          return { kind: "retryable", message: ev.error };
        }
        // Hard pre-content error: surface it.
        if (stashedStart) out.push(stashedStart);
        out.push(ev);
        return { kind: "hard", message: ev.error };
      }
      // Already streaming content; can't retry, must surface.
      out.push(ev);
      return { kind: "hard", message: ev.error };
    }
    // Content / thinking / toolcall event.
    if (stashedStart && !emitted) {
      out.push(stashedStart);
      emitted = true;
    }
    out.push(ev);
  }

  // Stream ended without a terminal event.
  const msg = buildError({ api: "deepseek-router", provider: ROUTER_PROVIDER, id: "router" }, "Router: upstream ended without a terminal event");
  if (stashedStart && !emitted) out.push(stashedStart);
  out.push({ type: "error", reason: "error", error: msg });
  return { kind: "hard", message: msg };
}

function tierFor(modelId: string): Tier {
  return modelId === FLASH_MODEL ? "flash" : modelId === FLASH_1M_MODEL ? "flash1m" : "pro";
}

function isRouterModel(id: unknown): boolean {
  return id === FLASH_MODEL || id === FLASH_1M_MODEL || id === PRO_MODEL;
}

function backoffRemaining(provider: string): number {
  const b = backoff.get(provider);
  if (!b) return 0;
  const remaining = b.nextRetryAt - Date.now();
  return remaining > 0 ? remaining : 0;
}

function markFailure(provider: string): number {
  const b = backoff.get(provider);
  const delayMs = b
    ? Math.min(b.delayMs * BACKOFF_MULTIPLIER, BACKOFF_MAX)
    : BACKOFF_INITIAL_MIN + Math.random() * (BACKOFF_INITIAL_MAX - BACKOFF_INITIAL_MIN);
  backoff.set(provider, { nextRetryAt: Date.now() + delayMs, delayMs });
  return delayMs;
}

function markSuccess(provider: string): void {
  backoff.delete(provider);
}

function routerStreamSimple(model: any, context: any, options?: any): AssistantMessageEventStream {
  const out = createAssistantMessageEventStream();
  const tier = tierFor(model.id);
  const chain: RouteStep[] = config[tier] ?? [];

  (async () => {
    let lastMessage: AssistantMessage | null = null;
    let terminalEmitted = false;
    let skippedBackoff = false;

    for (const step of chain) {
      if (options?.signal?.aborted) break;
      if (backoffRemaining(step.provider) > 0) {
        skippedBackoff = true;
        continue;
      }

      const target = registry?.find(step.provider, step.model);
      if (!target) {
        lastMessage = buildError(model, `Router: upstream ${step.provider}/${step.model} not found`);
        continue;
      }
      const upstream = registry?.getProvider(step.provider);
      if (!upstream) {
        lastMessage = buildError(model, `Router: provider "${step.provider}" is not registered`);
        continue;
      }

      const auth = await registry?.getApiKeyAndHeaders(target as any);
      if (!auth || !auth.ok) {
        lastMessage = buildError(model, `Router: no auth for "${step.provider}" (${auth?.error ?? "unconfigured"})`);
        continue;
      }

      const requestModel = auth.baseUrl ? { ...target, baseUrl: auth.baseUrl } : target;
      const sub = upstream.streamSimple(requestModel as any, context, {
        ...options,
        apiKey: auth.apiKey,
        headers: { ...(auth.headers ?? {}), ...(options?.headers ?? {}) },
        env: { ...(auth.env ?? {}), ...(options?.env ?? {}) },
      });

      const res = await forward(sub, out);
      if (res.kind === "success") {
        servedBy = step.label;
        markSuccess(step.provider);
        void refreshQuota(false).then(renderStatus);
        renderStatus();
        return;
      }
      if (res.kind === "retryable") {
        lastMessage = res.message;
        const delayMs = markFailure(step.provider);
        notify(
          `DeepSeek router: ${step.label} unavailable (${step.provider}) — retrying in ~${fmtDuration(Math.round(delayMs / 1000))}`,
          "warning",
        );
        continue;
      }
      // hard
      lastMessage = res.message;
      terminalEmitted = true;
      break;
    }

    if (!terminalEmitted) {
      if (options?.signal?.aborted) {
        out.push({ type: "error", reason: "aborted", error: buildError(model, "aborted") });
      } else if (lastMessage) {
        out.push({ type: "error", reason: "error", error: lastMessage });
      } else if (skippedBackoff) {
        out.push({ type: "error", reason: "error", error: buildError(model, "Router: all upstreams in backoff — retrying later") });
      } else {
        out.push({ type: "error", reason: "error", error: buildError(model, "Router: no route configured for this model") });
      }
    }
    out.end();
  })();

  return out;
}

// ---------------------------------------------------------------------------
// Extension factory
// ---------------------------------------------------------------------------

export default function deepseekRouter(pi: ExtensionAPI): void {
  loadConfig();
  piRef = pi;
  pi.events.on("deepseek-router:request", () => emitStatus(lastStatus));

  pi.registerProvider(ROUTER_PROVIDER, {
    name: "DeepSeek Router",
    baseUrl: "router://deepseek",
    // Dummy literal key so the provider counts as "configured" and its models
    // are selectable. Real auth is resolved per-upstream inside streamSimple.
    apiKey: "deepseek-router-internal",
    api: "deepseek-router",
    models: [
      {
        id: FLASH_MODEL,
        name: "DeepSeek V4 Flash",
        reasoning: true,
        input: ["text"],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 200000,
        maxTokens: 128000,
        thinkingLevelMap: { off: null, minimal: null, low: null, medium: null, high: "high", xhigh: null, max: "max" },
      },
      {
        id: PRO_MODEL,
        name: "DeepSeek V4 Pro",
        reasoning: true,
        input: ["text"],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 1000000,
        maxTokens: 384000,
        thinkingLevelMap: { off: null, minimal: null, low: null, medium: null, high: "high", xhigh: null, max: "max" },
      },
      {
        id: FLASH_1M_MODEL,
        name: "DeepSeek V4 Flash 1M",
        reasoning: true,
        input: ["text"],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 1000000,
        maxTokens: 128000,
        thinkingLevelMap: { off: null, minimal: null, low: null, medium: null, high: "high", xhigh: null, max: "max" },
      },
    ],
    streamSimple: routerStreamSimple,
  });

  pi.on("session_start", async (_event, ctx: ExtensionContext) => {
    registry = ctx.modelRegistry;
    ui = ctx.ui ?? null;
    loadConfig();

    const m = ctx.model as any;
    activeTier = m && isRouterModel(m.id) ? tierFor(m.id) : null;
    servedBy = null;

    renderStatus();
    await refreshQuota(true);
    renderStatus();
  });

  pi.on("model_select", (event, ctx: ExtensionContext) => {
    registry = ctx.modelRegistry;
    ui = ctx.ui ?? null;
    const m = event.model as any;
    activeTier = m && isRouterModel(m.id) ? tierFor(m.id) : null;
    renderStatus();
    if (activeTier) void refreshQuota(false).then(renderStatus);
  });

  pi.on("turn_end", (_event, ctx: ExtensionContext) => {
    registry = ctx.modelRegistry;
    ui = ctx.ui ?? null;
    if (activeTier) void refreshQuota(false).then(renderStatus);
  });

  pi.registerCommand("deepseek-router", {
    description: "Show DeepSeek router quota/spend and route status",
    async handler(_args, ctx) {
      registry = ctx.modelRegistry;
      ui = ctx.ui ?? null;
      loadConfig();
      await refreshQuota(true);
      renderStatus();

      const goLine =
        goRolling != null
          ? `Go ${Math.round(goRolling.pct)}% rolling (resets ${fmtDuration(goRolling.resetInSec)})` +
            (goWeekly ? ` · ${Math.round(goWeekly.pct)}% weekly` : "") +
            (goMonthly ? ` · ${Math.round(goMonthly.pct)}% monthly` : "")
          : "Go — unconfigured (set go.workspaceId + go.authCookie in deepseek-router.json)";
      const orLine =
        orTotal != null
          ? `OpenRouter ${fmtMoney(orTotal)} used` +
            (orLimitRemaining != null ? ` · ${fmtMoney(orLimitRemaining)} remaining` : "")
          : "OpenRouter — unavailable";

      ctx.ui?.notify?.(
        [
          `DeepSeek Router · tier ${activeTier ?? "none"} · serving ${servedBy ?? "—"}`,
          goLine,
          orLine,
          `Config: ${CONFIG_PATH}`,
        ].join("\n"),
        "info",
      );
    },
  });
}
