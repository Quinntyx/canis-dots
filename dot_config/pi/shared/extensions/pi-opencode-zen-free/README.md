# OpenCode GLM-5.3-Flash Free for Pi

Local, dependency-free Pi extension shared by the main and subagents profiles.
Select `opencode-zen-free/glm-5.3-flash-free` in `/model` after `/reload`.
Both profiles include it in `enabledModels`; their existing defaults are unchanged.

## Why this implementation

`pi-opencode-free@0.2.0` intersects advertised free IDs with Pi's bundled models.
A new `*-free` ID therefore disappears when Pi only knows the paid counterpart.
It also targets the older Zen endpoint and patches process-wide fetch.
The live OpenCode client uses `https://opencode.ai/inference/v1` instead.

This implementation adapts the current Pi provider/auth/streaming approach of
[Aymendje/pi-opencode-direct](https://github.com/Aymendje/pi-opencode-direct/tree/f6aa87411e5bf3dcc0340292a78396cf2ad2571c),
under its MIT license. It explicitly registers only `glm-5.3-flash-free`, inheriting
limits, reasoning and image metadata from Pi's `opencode/glm-5.3-flash` entry
(with an explicit fallback). Discovery is not a startup/network dependency.

It uses request-local OpenCode headers, fresh time-based OpenCode session IDs,
stable per-Pi-session affinity, and Pi's native OpenAI-compatible streaming/tools.
It uses anonymous `Bearer public` only: never OPENCODE_API_KEY or stored paid keys,
and never a paid model fallback. No OpenCode binary, daemon, proxy, login or npm
installation is required. The old pi-opencode-free package is disabled in main.

OpenCode separately gates compaction prompts; only short tool-less summarization
system prompts are normalized to its summarizer instruction. User messages and
normal coding system prompts are preserved.

## Verification and limitations (2026-10-16)

- Real Pi streaming request passed.
- Real Pi tool-use round trip read a file and returned its exact nonce.
- A real tool-less summary passed; a prior attempt received transient upstream 429.
- Unit checks cover explicit registration, zero pricing, session ID shape/uniqueness,
  compaction normalization, user-message preservation and anonymous-only auth.
- Free endpoint availability and quotas remain controlled by OpenCode. Errors are
  propagated without silently switching to a paid provider. Do not assume privacy
  or data-retention guarantees from a free public endpoint.

Managed in chezmoi; edit source state rather than live profile files.

Run the offline regression checks without enabling other extensions:

```sh
PI_OFFLINE=1 pi --no-extensions \
  -e ~/.config/pi/shared/extensions/pi-opencode-zen-free/tests/regression.ts \
  --list-models __regression_only__
```
