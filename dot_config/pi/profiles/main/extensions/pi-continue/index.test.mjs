import assert from "node:assert/strict";
import test from "node:test";
import extension from "./index.ts";

function setup(overrides = {}) {
  const commands = new Map();
  const events = new Map();
  const sent = [];
  const notices = [];
  extension({
    registerCommand: (name, command) => commands.set(name, command),
    on: (name, handler) => events.set(name, handler),
    sendMessage: (...args) => sent.push(args),
    sendUserMessage: () => assert.fail("must not add a user turn"),
  });
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
  return { command: commands.get("continue"), context: events.get("context"), sent, notices, ctx };
}

test("starts exactly one request without a user message", async () => {
  const { command, sent, notices, ctx } = setup();
  await command.handler("", ctx);
  assert.deepEqual(sent, [[
    { customType: "pi-continue:request", content: [], display: false },
    { triggerTurn: true },
  ]]);
  assert.deepEqual(notices, []);
});

test("removes current and restored markers, preserving all real context", () => {
  const { context } = setup();
  const original = [
    { role: "system", content: "System" },
    { role: "user", content: "Original", timestamp: 1 },
    { role: "custom", customType: "pi-continue:request", content: [], display: false },
    { role: "assistant", content: [{ type: "text", text: "Answer" }] },
    { role: "custom", customType: "other-extension", content: "Keep me" },
    { role: "custom", customType: "pi-continue:request", content: [], display: false },
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
