# Authoritative API and source map

## Installed version first

1. Resolve the Pi executable and its installed `@earendil-works/pi-coding-agent` package root.
   Read `package.json` for version and repository metadata, then the complete `README.md` and
   capability documents selected by the requested implementation.
2. Read `docs/extensions.md`, `docs/packages.md`, and `docs/skills.md` for the basic lifecycle.
   Read `docs/cli.md`, `docs/configuration.md`, `docs/settings.md`, and
   `docs/environment-variables.md` for profile scope, commands, and runtime selection.
3. For terminal components, read `docs/tui.md`; for embedded sessions read `docs/sdk.md`.
   Follow linked resource documents when delivering prompts, themes, providers, or other resources.
4. Verify exact signatures against `dist/core/extensions/types.d.ts`,
   `dist/core/resource-loader.d.ts`, `dist/core/settings-manager.d.ts`, and `dist/core/sdk.d.ts`.
   Check corresponding installed JavaScript for behavior not guaranteed by those declarations.
5. Inspect `dist/utils/git.js`, `dist/core/package-manager.js`, and `dist/package-manager-cli.js`
   for Git ref parsing, branch reconciliation, dependency installation, update scope, and paths.
   The inspected Pi 1.1.0 marks configured Git refs as pinned identities but reconciles branch refs
   to their current remote commit on update; distinguish ref identity from immutable code.
6. Inspect `dist/core/agent-session.js` and the selected mode implementation when designing
   lifecycle assertions. Factory loading and session-start dispatch are separate operations.

## Upstream documentation

These URLs locate upstream documents. Installed-version files govern executable commands and APIs.

- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli.md
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/configuration.md
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/environment-variables.md
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/tui.md
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/sdk.md
- https://github.com/earendil-works/pi/tree/main/packages/coding-agent/src/core

## Personal host authority

- Installed `fj` and `gh` help, authenticated repository state, and the Forgejo OpenAPI schema
  govern host operations. Confirm runner eligibility and action runtimes from actual server state.
- https://git.quinntyx.dev/swagger.v1.json
- https://forgejo.org/docs/latest/user/repo-mirror/
- https://cli.github.com/manual/gh_repo_create
- https://cli.github.com/manual/gh_repo_clone
- https://cli.github.com/manual/gh_repo_edit
- Read the active Git setup policy for optional deeper repository or mirror reconciliation detail.
  The essential personal hosting, ordinary-clone layout, bootstrap branches, mirror options,
  and source-before-apply sequence are specified within this package.
