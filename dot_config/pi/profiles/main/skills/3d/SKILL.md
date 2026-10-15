---
name: 3d
description: "Use when creating, modeling, rendering, editing, inspecting, or exporting
  3D objects, physical models, game assets, scenes, procedural geometry, materials, or animation.
  Uses installed Blender or an existing connected scene."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A 3D deliverable, intended use, project path, editing authority, and output directory.
- Available source scenes and assets, with their licenses and identity constraints preserved.
- An existing Blender executable for the standalone baseline, or an already connected Blender MCP
  with scene access. Capability availability is established during preflight.
- An agreed resource envelope inferred conservatively from the task and current machine workload.

## Output Contract

- A saved `.blend`, reproducible Python build or edit script, and actual rendered preview artifacts.
- Requested exports, plus verification of scale, orientation, material coverage, and required data.
- `scene-report.md` containing capability results, source assets, commands, Blender version,
  engine, actual render device, settings, artifact paths, and remaining limitations.
- Capability-limited output explicitly identifies which stages ran and which remain pending.
- Scene operations and artifacts stay within the authorized project and owned working copy.

# Entrypoint

## Stage 1: Preflight and choose transport

1. Resolve the skill root and execute `bin/blender-preflight` directly. Its Python 3 shebang
   selects the standard-library capability probe, which reads executable availability and invokes
   Blender's bounded `--version` query. It writes
   JSON to stdout, changes no files, and returns 0 for Blender availability or 2 when unavailable.
2. Blender provides the baseline geometry, materials, rendering, and its own Python with `bpy`.
   After a successful probe, author the build script for that Blender and run it there. Host
   Python is useful for paths and process launch; Blender executes the scene operations.
3. Record executable paths, version status, and available device-inspection commands. Treat these
   as executable availability; establish GPU support with Blender's own device enumeration later.
4. If an existing MCP route is desired, discover Blender tools with `tool_search`, read their
   actual schemas, and inspect scene identity through a read-only tool. Identify the server and
   live scene explicitly; independent Blender MCP implementations expose different interfaces.
5. Prefer standalone headless Blender for reproducible creation and batch work. Select an existing
   MCP only when live-scene access is useful and authorized; its code runs with Blender's access.
6. If standalone Blender is usable, proceed to Stage 2: Plan. If only an existing authorized MCP is
   usable, proceed to Stage 2 with that transport recorded. Otherwise proceed to Stage 6: Report
   with the available paths, missing capability, and pending artifacts.

## Stage 2: Plan

1. Inspect existing scene metadata and source assets through the selected transport. Preserve the
   original file and use a distinct output path for edits. Record units, axes, scale, frame range,
   materials, node groups, cameras, lights, textures, color management, and linked dependencies.
2. Translate the brief into silhouette, proportions, composition, topology needs, material roles,
   lighting, camera, and export requirements. Make the principal subject readable in a preview.
3. Choose a modest first render and bounded thread count that preserve desktop responsiveness.
   Resolve engine and device from installed capabilities and project requirements.
4. Proceed to Stage 3: Build.

## Stage 3: Build

1. Write `build-scene.py` in the output directory using Blender's bundled `bpy` API. Set seeds,
   units, resolution, engine, lighting, camera, color management, and output paths explicitly.
2. Use deterministic object names and a dedicated collection. Target owned data blocks and save
   results to the new `.blend` path. Preserve identity-bearing materials, nodes, and animation.
3. Pass project-specific inputs after Blender's `--` separator and parse that trailing argument
   vector in the script. Use absolute process arguments and resolve asset paths explicitly.
4. For new standalone scenes, invoke the resolved executable with `--background`,
   `--factory-startup`, `--disable-autoexec`, `--threads` and the chosen count,
   `--python-exit-code 1`, then `--python` and the script path. For an existing scene, place its
   absolute path after startup flags and before the script so edits act on the intended file.
5. Headless loading and explicit scripts work without a desktop connector. `--disable-autoexec`
   controls automatic file scripts; execute authored Python only with authority for its file access.
6. With MCP, save a working copy before the edit, inspect the scene again, then execute the same
   bounded operations using actual discovered tools. Keep Python and asset access project-scoped.
7. If construction and saving succeed, proceed to Stage 4: Render. Otherwise preserve logs and
   proceed to Stage 6: Report with the failing operation and any completed artifacts.

## Stage 4: Render

1. Enumerate supported render devices through Blender's engine API. For Cycles, call
   `bpy.context.preferences.addons['cycles'].preferences.get_devices()` and inspect devices after
   selecting a supported compute backend. Record enabled devices and the scene's device setting.
2. Select an available device within the resource envelope. Record CPU fallback as CPU execution;
   host GPU visibility alone establishes neither Cycles support nor GPU rendering.
3. Set all render options before rendering; Blender processes command-line arguments in order.
   Place `--render-frame` or `--render-anim` after file loading and render-setting arguments when
   rendering by CLI. Use `bpy.ops.render.render(write_still=True)` for script-controlled previews.
4. Capture a camera render and views needed to judge the requested asset. Inspect actual image
   files for composition, silhouette, materials, shading, texture resolution, and lighting.
5. If visible defects need correction within scope, return to Stage 3. Otherwise proceed to
   Stage 5: Verify and export, retaining previews even when a remaining defect is disclosed.

## Stage 5: Verify and export

1. Reopen the saved `.blend` in a separate background process and inspect required objects,
   materials, transforms, camera, render settings, external paths, and animation data.
2. Check evaluated geometry with modifiers and render settings accounted for. Apply manifoldness,
   normal, topology, or polygon-budget checks only where the deliverable requires them.
3. Export only the requested formats through the installed Blender version's operators. Reimport
   into a separate scene or inspect with an available reader; verify units, axes, bounds, and data.
4. Proceed to Stage 6: Report.

## Stage 6: Report

1. Write `scene-report.md` with inline preview links, saved scene, scripts, exports, validation,
   device evidence, asset provenance, and the exact command vector needed to reproduce the run.
2. Report available and missing paths separately, with failures and unexecuted stages made explicit.
   Preserve working copies and logs; release only processes owned by this task.
