/** Offline regression checks; load explicitly with Pi -e (see README). */
import assert from "node:assert/strict";
import { createSessionId, freeModel, prepareContext, SUMMARIZER_PROMPT, zenProvider } from "../index.ts";

export default async function () {
  const model = freeModel();
  assert.equal(model.id, "glm-5.3-flash-free");
  assert.equal(model.provider, "opencode-zen-free");
  assert.equal(model.baseUrl, "https://opencode.ai/inference/v1");
  assert.equal(model.contextWindow, 1_000_000);
  assert.deepEqual(Object.values(model.cost), [0, 0, 0, 0]);
  const id = createSessionId();
  assert.match(id, /^ses_[0-9a-f]{12}[0-9A-Za-z]{14}$/);
  assert.notEqual(id, createSessionId());
  const context = { messages: [
    { role: "system" as const, content: "A context summarization agent.", timestamp: 0 },
    { role: "user" as const, content: "Summary in bullets.", timestamp: 0 },
  ] };
  const normalized = prepareContext(context);
  assert.equal(normalized.messages[0].content, SUMMARIZER_PROMPT);
  assert.equal(normalized.messages[1].content, context.messages[1].content);
  assert.equal(context.messages[0].content, "A context summarization agent.");
  const normalChat = { messages: [...context.messages,
    { role: "user" as const, content: "Normal chat", timestamp: 0 }] };
  assert.deepEqual(prepareContext(normalChat), normalChat);
  const auth = await zenProvider().auth.apiKey.resolve();
  assert.equal(auth.auth.apiKey, "public");
  console.log("PASS: GLM free registration, endpoint, limits/pricing, session IDs, compaction isolation, anonymous auth");
}
