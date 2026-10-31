# Design basis

- Claude Code best practices ground completion in observable checks and browser screenshots:
  <https://code.claude.com/docs/en/best-practices>.
- Playwright page evaluation runs in the page environment and passes serializable values between
  environments: <https://playwright.dev/docs/evaluating>.
- Playwright actionability and locator checks support condition-based synchronization:
  <https://playwright.dev/docs/actionability>.
- The local adaptation uses the browser tools already available to Pi and capability discovery.
  It batches stable page-local work while retaining observations at state-dependent boundaries.
- The user's trajectory-review requests favor fewer screenshot round trips and grounded speed
  estimates. Visual evidence remains the source for spatial and canvas judgments.
