import assert from "node:assert/strict";
import test from "node:test";
import extension from "./index.ts";

let handler;
extension({ on(event, callback) { assert.equal(event, "message_end"); handler = callback; } });

const assistantError = (errorMessage) => ({
  role: "assistant",
  stopReason: "error",
  errorMessage,
  content: [{ type: "text", text: "Partial response" }],
  provider: "openai-codex",
  usage: { totalTokens: 123 },
});

for (const text of [
  "Codex error: stream disconnected before completed",
  "stream disconnected before completed",
  "Codex error: stream disconnected before completed: Transport error: error decoding response body",
  "  CODEX ERROR: STREAM DISCONNECTED BEFORE COMPLETED  ",
]) {
  test(`classifies disconnect: ${text}`, () => {
    const message = assistantError(text);
    const result = handler({ message });
    assert.deepEqual(result, { message: { ...message, errorMessage: `Connection error: ${text}` } });
    assert.equal(message.errorMessage, text);
    assert.equal(result.message.content, message.content);
    assert.equal(result.message.usage, message.usage);
    assert.equal(handler({ message: result.message }), undefined);
  });
}

for (const text of [undefined, "", "Codex error: authentication failed", "quota exceeded", "context length exceeded", "stream disconnected before completedness", "Other error: stream disconnected before completed"]) {
  test(`leaves unrelated error unchanged: ${text}`, () => {
    assert.equal(handler({ message: assistantError(text) }), undefined);
  });
}

for (const stopReason of ["stop", "toolUse", "aborted"]) {
  test(`does not retry ${stopReason} messages`, () => {
    assert.equal(handler({ message: { ...assistantError("Codex error: stream disconnected before completed"), stopReason } }), undefined);
  });
}

for (const role of ["user", "toolResult", "custom"]) {
  test(`ignores ${role} messages`, () => {
    assert.equal(handler({ message: { ...assistantError("Codex error: stream disconnected before completed"), role } }), undefined);
  });
}
