---
name: cloudflare
description: "Use when developing or operating Cloudflare Workers, Pages, storage, AI, networking,
  security, deployment, or infrastructure-as-code resources."
metadata:
  type: guideline
---

# Retrieval and routing

- Ground product selection, API signatures, numeric limits, pricing, and configuration in current
  official documentation at <https://developers.cloudflare.com/>.
- Treat bundled product references as navigation and historical context, not a current command
  runbook. Verify version-sensitive fields, limits, and operations against current official docs
  and the installed toolchain before use; their examples do not override host installation,
  deletion, secret-handling, or authorization restrictions.
- Read `references/products.md` for the product-to-reference index. Load only the material needed
  by the task, starting with the selected product's local reference directory.
- Route edge execution to Workers; stateful coordination to Durable Objects; multi-step jobs to
  Workflows; asynchronous delivery to Queues; relational storage to D1 or Hyperdrive; object
  storage to R2; and vector retrieval to Vectorize after validating current product capabilities.
- Select the smallest product set satisfying the actual workload, consistency, latency, operational,
  privacy, and cost requirements. Distinguish a prototype from an authorized production deployment.

# Project and account context

- Inspect existing project instructions, package scripts, lockfiles, Wrangler configuration, binding
  declarations, deployment environments, and generated types before changing the implementation.
- Resolve the intended account, environment, resource names, and deployment effect from trusted
  project context and the user's request. Preserve existing remote resources and secrets.
- Use the project's installed Wrangler version and configuration schema for CLI and binding work.
  Read the upstream-managed `../wrangler/SKILL.md` for CLI work. `.chezmoiexternal.toml` owns that file;
  update it from the official Cloudflare skills repository, never maintain a patched local copy.
- Keep local development, preview, staging, and production effects explicit in commands and reports.
- Keep credentials in the platform's supported secret stores or existing local secret files.
  Track portable configuration separately from credentials and machine runtime state.

# Implementation and verification

- Confirm compatibility dates, flags, runtime APIs, binding shapes, and product availability against
  current documentation and the installed toolchain.
- Validate with existing project checks and a local execution path. Exercise a deployed endpoint
  when the requested outcome depends on remote bindings, routing, permissions, or execution.
- Check migrations, namespace identities, data effects, and rollback implications before applying
  authorized remote changes. Use explicit environment and local/remote selectors where supported.
- Verify the returned deployment or resource identity, URL, bindings, and observed application
  behavior. Report local success and remote success as distinct outcomes.
