---
name: non-parametric
description: "Use when creating, modeling, rendering, editing, inspecting, or exporting
  3D objects, physical models, game assets, scenes, materials, or animation in Blender —
  non-parametric design, where form is judged by silhouette, appearance, or motion rather than
  measured dimensions: organic shapes, sculpting, procedural mesh and modifier construction,
  lighting, rendering, and existing scenes and Blender files. Exact-dimension parts defined by
  stated requirements select the parametric branch (`../parametric/SKILL.md`)."
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

- Requested scene, inspection, preview, or export artifacts. Changed scenes include a saved
  working `.blend` and reproducible build or edit script; previews are actual rendered images.
- Requested exports, plus verification of scale, orientation, material coverage, and required data.
- Findings or `scene-report.md` appropriate to the deliverable, covering relevant capabilities,
  source assets, version, commands, settings, artifact paths, and verification limits.
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
   lighting, camera, and export requirements. State a small checkable acceptance set for the
   requested asset and outputs, judged in silhouette, appearance, and motion. Stated dimensions
   act as proportions unless the brief makes them verified requirements; exact-dimension work
   belongs to the parametric branch. Build the simplest scene that satisfies it, with the
   principal subject readable in a preview.
3. Choose a modest first render and bounded thread count that preserve desktop responsiveness.
   Resolve engine and device from installed capabilities and project requirements.
4. For inspection-only or export-only work, proceed to Stage 5: Verify and export with the existing
   scene. For creation or editing, proceed to Stage 3: Build. For rendering an existing scene,
   proceed to Stage 4: Render.

## Stage 3: Build

1. Write `build-scene.py` in the output directory using Blender's bundled `bpy` API. For procedural
   mesh or modifier work, read `references/procedural-geometry.md` as the construction baseline.
   Set seeds, units, resolution, engine, lighting, camera, color management, and paths explicitly.
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
2. Select a compatible device within the resource envelope and record engine-side evidence.
   Cycles' CPU setting establishes CPU fallback. For EEVEE, record the graphics backend/device
   separately from the CPU thread cap; preserve unobserved device identity as unresolved.
3. Set all render options before rendering; Blender processes command-line arguments in order.
   Place `--render-frame` or `--render-anim` after file loading and render-setting arguments when
   rendering by CLI. Use `bpy.ops.render.render(write_still=True)` for script-controlled previews.
4. Fit each requested whole-asset view to the evaluated subject bounds with a modest margin;
   verify camera-projection bounds at each preview state using the geometry reference. Capture
   actual renders and inspect composition, silhouette, materials, shading, textures, and lighting.
5. Compare the actual preview and geometry with the Stage 2 acceptance set. Correct unmet
   requirements through Stage 3. Once those requirements hold, proceed to Stage 5: Verify and
   export; record optional polish separately and retain previews of any disclosed limitation.

## Stage 5: Verify and export

1. Inspect the requested existing scene, or reopen a changed `.blend` in a separate background
   process to verify the saved result. Inspect required objects,
   materials, transforms, camera, render settings, external paths, and animation data.
2. Check evaluated geometry with modifiers and render settings accounted for. Apply manifoldness,
   normal, topology, or polygon-budget checks only where the deliverable requires them.
3. When export is requested, use the installed Blender version's operators. Reimport
   into a separate scene or inspect with an available reader; verify units, axes, bounds, and data.
4. Proceed to Stage 6: Report.

## Stage 6: Report

1. For created artifacts, write `scene-report.md` with relevant previews, scene, scripts, exports,
   checks, device evidence, asset provenance, and reproduction commands. Inspection-only work
   returns the requested findings directly, with evidence from the inspected scene.
2. Report available and missing paths separately, with failures and unexecuted stages made explicit.
   Preserve working copies and logs; release only processes owned by this task.
