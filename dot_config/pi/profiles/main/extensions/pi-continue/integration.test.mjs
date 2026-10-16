import assert from "node:assert/strict";
import { createServer } from "node:http";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

// Set this to the installed host's dist/index.js when testing outside node_modules.
const host = process.env.PI_CONTINUE_HOST;
const sdk = await import(host || "@earendil-works/pi-coding-agent");
const { createAgentSession, DefaultResourceLoader, ModelRuntime, SessionManager, SettingsManager } = sdk;

test("/continue sends the existing transcript over HTTP with no new user turn", { timeout: 15000 }, async () => {
  const requests = [];
  const server = createServer(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    requests.push(JSON.parse(Buffer.concat(chunks).toString()));
    const index = requests.length;
    res.writeHead(200, { "content-type": "text/event-stream" });
    for (const [delta, finish_reason] of [
      [{ role: "assistant", content: `Answer ${index}` }, null],
      [{}, "stop"],
    ]) {
      res.write(`data: ${JSON.stringify({
        id: `response-${index}`, object: "chat.completion.chunk",
        created: 1, model: "continue-test",
        choices: [{ index: 0, delta, finish_reason }],
      })}\n\n`);
    }
    res.end("data: [DONE]\n\n");
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  let session;
  try {
    const cwd = await mkdtemp(join(tmpdir(), "pi-continue-test-"));
    const settingsManager = SettingsManager.inMemory({
      defaultTools: [], compaction: { enabled: false }, retry: { enabled: false },
    });
    const modelRuntime = await ModelRuntime.create({
      authPath: join(cwd, "auth.json"), modelsPath: null,
      modelsStorePath: join(cwd, "models-store.json"), refreshOnCreate: false,
    });
    modelRuntime.registerProvider("pi-continue-test", {
      api: "openai-completions", apiKey: "local-test-only",
      baseUrl: `http://127.0.0.1:${server.address().port}/v1`,
      models: [{
        id: "continue-test", name: "Continue test", reasoning: false,
        input: ["text"], contextWindow: 32000, maxTokens: 1024,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      }],
    });
    const resourceLoader = new DefaultResourceLoader({
      cwd, agentDir: cwd, settingsManager,
      additionalExtensionPaths: [new URL("./index.ts", import.meta.url).pathname],
      noSkills: true, noPromptTemplates: true, noThemes: true, noContextFiles: true,
      systemPrompt: "Continue integration test.",
    });
    await resourceLoader.reload();
    const result = await createAgentSession({
      cwd, agentDir: cwd, modelRuntime,
      model: modelRuntime.getModel("pi-continue-test", "continue-test"),
      resourceLoader, settingsManager, sessionManager: SessionManager.inMemory(cwd),
      noTools: true,
    });
    session = result.session;
    assert.deepEqual(result.extensionsResult.errors, []);
    await session.bindExtensions({});
    await session.prompt("Original request");
    assert.equal(requests.length, 1, JSON.stringify(session.messages));
    assert.equal(session.getLastAssistantText(), "Answer 1");

    for (let i = 2; i <= 3; i++) {
      const prior = structuredClone(requests.at(-1).messages);
      const before = session.sessionManager.buildSessionContext().messages;
      const previousAssistant = before.filter((m) => m.role === "assistant").at(-1);
      const usersBefore = before.filter((m) => m.role === "user").length;
      await session.prompt("/continue");
      await session.waitForIdle();
      assert.equal(requests.length, i);
      const outgoing = requests.at(-1).messages;
      assert.deepEqual(outgoing.slice(0, prior.length), prior);
      assert.equal(outgoing.length, prior.length + 1);
      assert.equal(outgoing.at(-1).role, "assistant");
      assert.equal(outgoing.at(-1).content, previousAssistant.content[0].text);
      assert.equal(outgoing.filter((m) => m.role === "user").length, usersBefore);
      assert.ok(!JSON.stringify(requests.at(-1)).includes("pi-continue:request"));
      assert.ok(!JSON.stringify(requests.at(-1)).includes("Continued from existing session"));
      const after = session.sessionManager.buildSessionContext().messages;
      const markers = after.filter((m) => m.role === "custom" && m.customType === "pi-continue:request");
      assert.equal(markers.length, i - 1);
      assert.ok(markers.every((m) => m.display === true && m.content === "Continued from existing session"));
      assert.equal(after.filter((m) => m.role === "user").length, usersBefore);
      assert.equal(session.getLastAssistantText(), `Answer ${i}`);
    }
    console.log("3 HTTP requests; /continue twice; unchanged transcript prefixes; 1 original user turn; visible status entries; no marker or status sent.");
  } finally {
    session?.dispose();
    server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
  }
});
