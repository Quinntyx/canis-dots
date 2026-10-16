# Pi TUI inspection

1. Resolve the installed Pi package and read its `docs/tui.md` fully. Read the linked extension,
   theme and terminal-setup documentation relevant to the affected boundary, then inspect the
   installed `@earendil-works/pi-tui` source/declarations before choosing exact APIs or commands.
2. Identify the active renderer and mode, component mount path, theme source, input focus owner and
   render invalidation path. Use the host's injected terminal renderer and framework width helpers.
   Check cached theme-dependent strings, focus propagation and hardware cursor placement.
3. When supported by the installed version, set `PI_TUI_WRITE_LOG` to a unique path in the private
   run directory for the launched process. Inspect the file for the affected renderer writes.
   Keep the PTY recording too: the renderer log may omit direct stdout writes and has no complete
   event/timing trace by itself. Verify its existence and content before citing it.
4. Exercise the relevant normal/fullscreen path through an actual interactive Pi instance loading
   the changed source. Bind the selected profile, extension/module paths and effective settings in
   the manifest. Use isolated state and authorized fixture/provider traffic for reproducibility.
   Record explicit theme selection separately from default terminal palette negotiation.
5. Verify width handling, resize invalidation, cursor/focus handoffs and scroll/stream state through
   that installed renderer. Inspect the actual terminal output alongside component-level checks.
   Return to the current stage in `SKILL.md` with observations and exact installed API identities.

## Sources

- Installed Pi documentation and source are authoritative for the tested version.
  <https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/tui.md>
- Public TUI implementation and declarations:
  <https://github.com/earendil-works/pi/tree/main/packages/tui/src>
- Public extension types and integration source:
  <https://github.com/earendil-works/pi/tree/main/packages/coding-agent/src/core/extensions>
