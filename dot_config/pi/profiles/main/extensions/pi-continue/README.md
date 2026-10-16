# pi-continue

Adds `/continue` to Pi. It requests another assistant response using the current
session, without adding a user turn or sending a synthetic continuation prompt.

Installed in the main profile's auto-discovered `extensions/pi-continue/`
directory. Run `/reload` in existing Pi sessions to load it.

## Usage

```text
/continue
```

No arguments are accepted. The session must contain a conversation, have a
selected model, and be idle with no queued messages. Busy sessions are not
interrupted or silently queued.

## How it works

Pi's public extension API does not expose a bare continuation method. This
extension uses `sendMessage(..., { triggerTurn: true })` to start Pi's standard
run pipeline with a hidden, empty custom control marker. Its `context` handler
removes all such markers before conversion to provider messages, including
markers restored from earlier session history.

The marker is stored as a hidden custom session entry, **not a user turn**.
It is never sent to the model. Existing messages remain unchanged, and Pi owns
streaming, tools, cancellation, and run settlement. Provider-specific handling
of consecutive assistant responses remains the provider adapter's responsibility.

## Tests

From this directory:

```sh
node --test index.test.mjs
PI_CONTINUE_HOST=/path/to/pi-coding-agent/dist/index.js node --test integration.test.mjs
```

The integration test loads the extension through Pi's real resource loader and
calls `/continue` twice through `session.prompt()`. A loopback HTTP provider
captures the actual serialized requests, checking unchanged transcript prefixes,
no new user turns, and no leaked control markers. It makes no external requests.
