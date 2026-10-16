# mdBook execution reference

## Resolve tools and paths

1. Bind `book_root` to the project directory containing `book.toml`. Keep source downloads,
   extraction notes, and private ledgers elsewhere in the same task workspace.
2. Check `command -v mdbook`. When available, inspect `mdbook --version`, `mdbook build --help`,
   `mdbook test --help`, and `mdbook serve --help`. Record installed versions and compare
   configuration and math syntax with the official docs for those versions.
3. When mdBook is unavailable, provide `cargo install mdbook` as the documented user-install
   command. Its prerequisites are Rust and Cargo with the release's supported Rust version, and
   Cargo's bin directory on `PATH`. This procedure records the dependency and preserves authored
   source for handoff; installation remains a separate user action. Record build, rendered links,
   and browser inspection as blocked until the dependency is available.
4. Inspect project configuration and installed preprocessor versions. Use current upstream
   documentation to resolve release compatibility and renderer requirements before configuration.

## Author configuration and contents

1. Set `[book]` metadata from the task and `src` to the chapter directory. Write that directory's
   `SUMMARY.md` as the ordered, nested chapter-link structure. Write every linked chapter file.
   Use real chapter links for the finished curriculum and verify nesting matches prerequisite
   order.
2. Set `create-missing = false` under `[build]` so a missing chapter produces an actionable error.
   Bind the desired output through `build-dir` and retain any existing project build conventions.
3. Configure the selected math path below. Include `[output.html]` explicitly when using
   additional renderers; defining other output tables changes the default HTML behavior.
4. Resolve relative configuration paths from `book_root`. With one renderer, output goes directly
   into the configured build directory; multiple renderers get renderer-specific subdirectories.
   Record the actual HTML path after building rather than assuming `book/index.html` exists.
5. Review everything below `book.src`: mdBook copies its non-Markdown files into the output. Place
   distributable figures and licensed assets there deliberately and retain private PDFs elsewhere.

## Select one math renderer

### Built-in MathJax

1. Set `mathjax-support = true` under `[output.html]`. This is mdBook's built-in MathJax
   integration.
2. Use literal Markdown delimiters `\\(` and `\\)` for inline math, and `\\[` and `\\]` for
   display math. These have two backslashes in the Markdown source. Current mdBook documentation
   specifies these escaped delimiters, rather than dollar delimiters, for its built-in path.
3. Preserve TeX escaping through Markdown: a TeX two-backslash line break needs four backslashes
   in this source path. Check the actual rendered result of alignment and matrix environments.
4. Inspect the generated script URL and installed theme to identify the loaded MathJax version.
   Select its documented completion signal for browser checks. Account for script and font network
   dependencies; verify local asset provisioning when offline delivery is required.
5. Validate each needed command, macro, equation label, and reference against that MathJax
   version. Check the built page and browser diagnostics before accepting the rendering
   configuration.

### KaTeX preprocessor

1. Treat KaTeX as a separate preprocessor dependency. Verify the installed `mdbook-katex`
   release's mdBook compatibility, build requirements, and supported math functions against
   upstream docs. When absent, record it as a blocked dependency. Provide the documented
   user-install command `cargo install mdbook-katex`, with its platform requirements and Cargo
   bin path requirement.
2. Configure `[preprocessor.katex]` with `after = ["links"]` as documented by the preprocessor.
   Use its default pre-render mode for build-time HTML math when suitable for the requested
   output. Set built-in `mathjax-support = false` under `[output.html]` for this renderer path.
3. Use the preprocessor's documented dollar delimiters: one dollar on each side for inline math,
   two on each side for display math. Escape literal dollar characters according to its syntax.
   Record custom delimiters and macro files explicitly when the project requires them.
4. Keep `throw-on-error = true` under `[preprocessor.katex]` so unsupported expressions fail
   visibly. Verify every required macro and environment against KaTeX's supported-function
   documentation.
5. Inspect stylesheet and font URLs. The preprocessor injects CDN CSS by default; self-hosted
   assets require deliberate project configuration and retained license notices. Test actual asset
   loading and glyph rendering in the intended delivery environment.

## Build and verify

1. Run `mdbook build "$book_root"` with native output and exit status saved in verification notes.
   Run jobs likely to exceed 10–15 seconds in retained background terminal jobs with logs and
   status.
2. Determine the generated HTML root from configuration, enabled outputs, and actual build
   results. Check all chapter destinations, local links, fragment anchors, images, styles,
   scripts, and fonts. Use emitted HTML IDs as anchor truth; Markdown headings alone are
   insufficient for link checks.
3. Run `mdbook test "$book_root"` when Rust code testing applies. This command runs Rust snippet
   tests through rustdoc; it does not validate citations, mathematics, browser layout, or links.
   Bare code fences are interpreted as Rust by this test path. Tag non-Rust fences accurately.
4. Check other executable material with its own verified runtime and check symbolic derivations
   independently. Record inapplicable tests explicitly and preserve unresolved dependency
   failures.
5. Bind `preview_port` to an available loopback port and start a retained background preview using
   `mdbook serve "$book_root" --hostname 127.0.0.1 --port "$preview_port"`. Record the actual URL,
   process handle, and logs. This is a local inspection server; production publishing uses the
   authorized project's deployment path.
6. Open the built pages in an available browser. Wait for actual typesetting and font readiness.
   Record rendered math, citation navigation, narrow-width layout, screenshots, and browser
   errors. A successful build supports file-generation claims; browser evidence supports rendering
   claims.
7. When publication uses a path prefix, verify `site-url` under `[output.html]` and inspect the
   deployed path itself. The local preview changes the effective site URL for serving, so preview
   success alone does not validate deployment-prefix behavior.

## Authoritative sources

- Installation and user-install prerequisites:
  https://rust-lang.github.io/mdBook/guide/installation.html
- Chapter structure: https://rust-lang.github.io/mdBook/format/summary.html
- General metadata, source directory, and build options:
  https://rust-lang.github.io/mdBook/format/configuration/general.html
- HTML renderer, output directories, and site URL:
  https://rust-lang.github.io/mdBook/format/configuration/renderers.html
- Build command and source-asset copying: https://rust-lang.github.io/mdBook/cli/build.html
- Rust-only test scope: https://rust-lang.github.io/mdBook/cli/test.html
- Preview server: https://rust-lang.github.io/mdBook/cli/serve.html
- Built-in math configuration and escaping: https://rust-lang.github.io/mdBook/format/mathjax.html
- KaTeX preprocessor installation, ordering, delimiters, and assets:
  https://github.com/lzanini/mdbook-katex/blob/master/README.md
- KaTeX function support: https://katex.org/docs/supported.html
- Browser capture capabilities, when Playwright is the available project runtime:
  https://playwright.dev/docs/screenshots
