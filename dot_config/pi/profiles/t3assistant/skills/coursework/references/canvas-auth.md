# Persistent Canvas authentication and human handoff

Read before any authorized embedded Canvas/Codio browser access or on an authentication failure.
This reference inherits the router's browser-request gate and human-only submission boundary.

1. Discover embedded T3 browser capabilities and inspect existing profiles/tabs. Reuse the user's
   persistent T3 browser profile for Canvas and Codio; use its existing authenticated context
   rather than a disposable/incognito session. A Pi profile name is not a browser profile ID.
   Select the browser profile only from observed T3 state or explicit user selection.
2. Keep one dedicated assignment tab (or the verified LTI child tab). Reuse it when it already
   belongs to this task; do not commandeer unrelated user tabs. Retain it for user handoff.
3. If login, SSO, MFA, consent, account choice, or licensing is required, leave the real sign-in
   page visible and ask the user to complete it in T3. Supply the actual tab link if available.
   Record `blocked: authentication` with the last safe URL and expected next action; stop active
   browsing until the user reports completion. Distinguish access denied from missing login.
4. After the user completes sign-in, inspect the resulting page and verify the intended course
   context before resuming. Session expiry later follows the same handoff, not an automatic
   credential workaround. Preserve already prepared local materials and progress.
5. Keep passwords, MFA codes, cookies, session tokens, Canvas API tokens, and browser storage out
   of chat, source, artifacts, reports, and progress. Use the browser's persistent authentication;
   do not export/import cookies or request copied credentials. Never transfer omn/main browser
   credentials or read another profile's secrets to populate t3assistant.
6. If embedded tools or a persistent browser profile are unavailable, deliver an explicit blocked
   handoff and stable source link; do not install a browser stack or silently switch to a personal
   browser. Preparation from already available authorized materials may continue independently.

Completion: a verified authenticated assignment page ready for the selected preparation step, or a
specific login/access/tool blocker with a preserved user-facing tab/link. Authentication success is
not assignment completion, and this workflow never starts or submits an assessment for the user.
