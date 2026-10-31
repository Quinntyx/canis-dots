---
name: wrangler
description: "Use when running Wrangler commands or managing Cloudflare deployments, bindings,
  secrets, Workers, Pages, KV, R2, D1, queues, or other Cloudflare resources through the CLI."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A Cloudflare CLI task, project directory, intended environment, and authorized effects.
- An existing Wrangler installation or project dependency and the relevant account context.
- Existing configuration and resource identifiers when operating on an established project.

## Output Contract

- The requested local or remote operation with verified environment and resource identity.
- Portable configuration changes separated from secrets and runtime artifacts.
- A concise result with observed behavior, deployment URL or resource identity, and any blocker.

# Entrypoint

## Stage 1: Resolve the installed tool and project

1. Inspect project instructions, package scripts, lockfiles, and Wrangler configuration. Prefer the
   project's existing package script or installed local binary.
2. Read the installed CLI version and its help for the required command. Read current official
   documentation at <https://developers.cloudflare.com/workers/wrangler/commands/> for command
   syntax and <https://developers.cloudflare.com/workers/wrangler/configuration/> for config.
3. When a compatible Wrangler installation is available, continue to Stage 2: Resolve effects.
   Otherwise, report the missing prerequisite and a copy-pastable project installation command;
   finish with a blocked result for executable operations.

## Stage 2: Resolve effects and identities

1. Identify account, project, deployment environment, binding names, resource identities, and
   whether the operation is local, preview, or remote. Use the supported account inspection command
   and project configuration for authenticated operations.
2. Read the actual command's installed help for environment selectors and local/remote switches.
   Resolve defaults explicitly for operations affecting data, secrets, routes, or deployments.
3. Match the intended effects to the user's authorization. A request to inspect or plan ends with
   observations or a plan; an authorized deployment or resource operation continues to Stage 3:
   Prepare. Otherwise, ask the specific missing effects or destination decision and finish blocked.

## Stage 3: Prepare the operation

1. Resolve required bindings, migrations, build inputs, secrets, and existing resource identifiers.
2. Edit portable configuration through its owning configuration workflow. Keep secrets in existing
   secret files or supported platform secret operations and use generated types where applicable.
3. Run project validation and the closest local execution path. Read the installed command help
   for supported planning, dry-run, migration-preview, and resource-inspection operations.
4. When prerequisites and checks support the authorized operation, continue to Stage 4: Execute.
   Otherwise, report the failed prerequisite and finish with the retained state and blocker.

## Stage 4: Execute and verify

1. Run the resolved command from the project directory with explicit supported environment and
   local/remote selectors. Use a retained background job for long-running development servers.
2. Capture the resulting deployment or resource identity, command result, and relevant diagnostics.
3. Re-query the resulting resource or exercise the deployed endpoint and verify the requested
   behavior in the intended environment.
4. When verification succeeds, continue to Stage 5: Report. Otherwise, retain diagnostics and
   continue to Stage 5: Report with the observed failure and any verified partial effects.

## Stage 5: Report

1. State the observed result, environment, resource identity or URL, and checks performed.
2. Distinguish successful local validation, submitted deployment, and verified remote behavior.
3. Report remaining prerequisites or failed checks and preserve the information needed to resume.

# Sources

- CLI reference: <https://developers.cloudflare.com/workers/wrangler/commands/>.
- Configuration: <https://developers.cloudflare.com/workers/wrangler/configuration/>.
- Environments: <https://developers.cloudflare.com/workers/wrangler/environments/>.
