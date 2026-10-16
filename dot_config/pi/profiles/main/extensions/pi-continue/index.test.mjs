import assert from "node:assert/strict";
import test from "node:test";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const sdk = await import(process.env.PI_CONTINUE_HOST || "@earendil-works/pi-coding-agent");
const cwd = await mkdtemp(join(tmpdir(), "pi-continue-unit-"));
const loader = new sdk.DefaultResourceLoader({
  cwd, agentDir: cwd, settingsManager: sdk.SettingsManager.inMemory({}),
  additionalExtensionPaths: [new URL("./index.ts", import.meta.url).pathname],
  noSkills: true, noPromptTemplates: true, noThemes: true, noContextFiles: true,
});
await loader.reload();
const loaded = loader.getExtensions();
assert.deepEqual(loaded.errors, []);
const extension = loaded.extensions.find((entry) => entry.commands.has("continue"));
assert.ok(extension, "pi-continue must load through Pi's real extension loader");

function setup(overrides = {}) {
  const sent = [];
  const notices = [];
  loaded.runtime.sendMessage = (...args) => sent.push(args);
  loaded.runtime.sendUserMessage = () => assert.fail("must not add a user turn");
  const ctx = {
    isIdle: () => true,
    hasPendingMessages: () => false,
    model: { id: "test" },
    sessionManager: {
      buildSessionContext: () => ({ messages: [{ role: "user", content: "Original request" }] }),
    },
    ui: { notify: (...args) => notices.push(args) },
    ...overrides,
  };
  return {
    command: extension.commands.get("continue"),
    context: extension.handlers.get("context")[0],
    renderer: extension.messageRenderers.get("pi-continue:request"),
    sent, notices, ctx,
  };
}

test("starts exactly one request without a user message", async () => {
  const { command, sent, notices, ctx } = setup();
  await command.handler("", ctx);
  assert.deepEqual(sent, [[
    { customType: "pi-continue:request", content: "Continued from existing session", display: true },
    { triggerTurn: true },
  ]]);
  assert.deepEqual(notices, []);
});

test("renders a compact dim status line, including restored legacy markers", () => {
  const { renderer } = setup();
  const theme = { fg: (color, text) => {
    assert.equal(color, "dim");
    return `\x1b[2m${text}\x1b[22m`;
  } };
  for (const message of [
    { customType: "pi-continue:request", content: "Continued from existing session", display: true },
    { customType: "pi-continue:request", content: [], display: false },
  ]) {
    for (const width of [12, 40, 80]) {
      const component = renderer(message, { expanded: false, outputPad: 2 }, theme);
      const lines = component.render(width);
      const plain = lines.map((line) => line.replace(/\x1b\[[0-9;]*m/g, ""));
      assert.ok(plain.every((line) => line.length <= width));
      assert.equal(plain.join("").replace(/\s/g, ""), "Continuedfromexistingsession");
      if (width >= 40) {
        assert.equal(plain.length, 1);
        assert.equal(plain[0].trim(), "Continued from existing session");
      }
      component.invalidate();
      assert.deepEqual(component.render(width), lines);
    }
  }
});

test("removes current and restored markers, preserving all real context", () => {
  const { context } = setup();
  const original = [
    { role: "system", content: "System" },
    { role: "user", content: "Original", timestamp: 1 },
    { role: "custom", customType: "pi-continue:request", content: [], display: false },
    { role: "assistant", content: [{ type: "text", text: "Answer" }] },
    { role: "custom", customType: "other-extension", content: "Keep me" },
    { role: "custom", customType: "pi-continue:request", content: "Continued from existing session", display: true },
  ];
  const result = context({ messages: original }).messages;
  assert.deepEqual(result, [original[0], original[1], original[3], original[4]]);
  assert.equal(result[1], original[1]);
  assert.equal(original.length, 6);
});

for (const [label, args, overrides] of [
  ["arguments", "extra prompt", {}],
  ["active request", "", { isIdle: () => false }],
  ["pending messages", "", { hasPendingMessages: () => true }],
  ["no model", "", { model: undefined }],
  ["empty session", "", { sessionManager: { buildSessionContext: () => ({ messages: [] }) } }],
  ["system-only session", "", { sessionManager: { buildSessionContext: () => ({ messages: [{ role: "system" }] }) } }],
]) {
  test(`rejects ${label} without modifying the conversation`, async () => {
    const { command, sent, notices, ctx } = setup(overrides);
    await command.handler(args, ctx);
    assert.deepEqual(sent, []);
    assert.equal(notices.length, 1);
    assert.equal(notices[0][1], "warning");
  });
}
