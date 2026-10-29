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

- By default for created or changed models, actual rendered still images from complementary
  cameras, plus a saved working `.blend` and reproducible build or edit script. Honor explicit
  deliverable overrides; inspection-only and export-only work do not gain unwanted renders.
- Final rendered images use Cycles unless the user specifies another engine. Part/individual-object
  views are square and centered by default; landscapes/scenes retain the default aspect ratio.
- Requested exports, plus verification of scale, orientation, material coverage, and required data.
- Findings or `scene-report.md` appropriate to the deliverable, covering relevant capabilities,
  source assets, version, commands, phase-by-phase previews, checks, settings, artifact paths,
  and verification limits. Parametric handoffs retain the CAD branch's sheet-first image order.
- Capability-limited output explicitly identifies which stages ran and which remain pending.
- Scene operations and artifacts stay within the authorized project and owned working copy.

# Entrypoint

## Stage 1: Preflight and choose transport

1. Resolve the skill root and execute `bin/blender-preflight` directly. Its Python 3 shebang
   selects the standard-library capability probe, which reads executable availability and invokes
   Blender's bounded `--version` query. It writes JSON to stdout, changes no files, and returns
   0 for Blender availability or 2 when unavailable.
2. Blender provides the baseline geometry, materials, rendering, and its own Python with `bpy`.
   After a successful probe, author the build script for that Blender and run it there. Host
   Python is useful for paths and process launch; Blender executes the scene operations.
3. Record executable paths, version status, and available device-inspection commands. Treat these
   as executable availability; establish GPU support with Blender's own device enumeration in
   Stage 4 before escalating render cost. Finding `nvidia-smi` is not evidence of a usable Cycles GPU.
4. If an existing MCP route is desired, discover Blender tools with `tool_search`, read their
   actual schemas, and inspect scene identity through a read-only tool. Identify the server and
   live scene explicitly; independent Blender MCP implementations expose different interfaces.
5. Prefer standalone headless Blender for reproducible creation and batch work. Select an existing
   MCP only when live-scene access is useful and authorized; its code runs with Blender's access.
6. If standalone Blender is usable, proceed to Stage 2: Plan. If only an existing authorized MCP is
   usable, proceed to Stage 2 with that transport recorded. Otherwise proceed to Stage 7: Report
   with the available paths, missing capability, and pending artifacts.

## Stage 2: Plan

1. Inspect existing scene metadata and source assets through the selected transport. Preserve the
   original file and use a distinct output path for edits. Record units, axes, scale, frame range,
   materials, node groups, cameras, lights, textures, color management, and linked dependencies.
2. Translate the brief into silhouette, proportions, composition, topology needs, material roles,
   lighting, camera, and export requirements. State a small checkable acceptance set, separating
   base geometry from lighting/material appearance. Stated dimensions act as proportions unless
   the brief makes them verified requirements; exact-dimension work belongs to the parametric branch.
3. Plan a complementary camera set for all-around inspection: normally at least three genuinely
   different angles (for example front three-quarter, rear three-quarter, and side/top), adding
   underside or close interface views when those surfaces matter. Landscapes/scenes use multiple
   useful viewpoints rather than a single flattering hero angle. Reuse named cameras across passes.
4. Unless specified otherwise, make part/individual-object images square (`resolution_x ==
   resolution_y`, square pixels) with the subject centered and fully in frame. For landscapes/scenes,
   retain Blender's default aspect ratio (normally 16:9 for a new scene; preserve an existing
   scene's configured ratio). A cheap preview can lower resolution without changing that ratio.
5. Choose modest preview resolutions, sample counts, and bounded threads that preserve desktop
   responsiveness. Budget geometry reviews before lighting, then fast lighting passes before
   final Cycles images. A request for animation is not approval for a Cycles animation render.
6. For inspection-only or export-only work, proceed to Stage 6: Verify and export with the existing
   scene. For creation or editing, proceed to Stage 3: Build. For rendering an existing scene,
   proceed to Stage 4: Geometry review and render gate, without rebuilding already-correct geometry.

## Stage 3: Build

1. Write `build-scene.py` in the output directory using Blender's bundled `bpy` API. For procedural
   mesh or modifier work, read `references/procedural-geometry.md` as the construction baseline.
   Set seeds, units, preview resolution, engine, camera set, color management, and paths explicitly;
   keep the initial scene cheap and focused on base geometry, not production materials or lighting.
2. Use deterministic object names and a dedicated collection. Target owned data blocks and save
   results to the new `.blend` path. Preserve identity-bearing materials, nodes, and animation;
   use reversible preview overrides rather than replacing source materials for diagnostic colors.
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
7. If construction and saving succeed, proceed to Stage 4: Geometry review and render gate.
   Otherwise preserve logs and proceed to Stage 7: Report with the failing operation and any
   completed artifacts.

## Stage 4: Geometry review and render gate

1. Establish render capability inside Blender. For Cycles, select an installed supported compute
   backend, call `bpy.context.preferences.addons['cycles'].preferences.get_devices()`, and inspect
   available device types. Enable the selected non-CPU device and set the scene's Cycles device to
   GPU; record the backend, enabled devices, and scene setting. Confirm actual use on a bounded
   test before a costly batch. Do not confuse GPU presence, EEVEE graphics support, and usable
   Cycles GPU acceleration. Record EEVEE backend/device observations separately from thread count.
2. If a usable Cycles GPU is unavailable or unverified, warn the user and stop before long CPU
   rendering, large resolutions, high sample counts, or expensive batches. Cheap geometry reviews
   and explicitly bounded timing tests may proceed within the resource envelope, but get approval
   for the proposed slow CPU budget, or for a non-Cycles final alternative, before those steps.
   Do not silently downgrade the final engine or begin slow work while waiting for permission.
3. Never launch a Cycles animation render without explicit user approval, even with a GPU.
   State frame count, resolution, samples, and a timing-based estimate first. Without approval,
   render only bounded representative stills, or use an agreed cheap animation-preview engine;
   do not evade the gate by looping Cycles over every frame as separate stills.
4. For base-geometry reviews use a cheap renderer: Workbench with flat/studio shading by default,
   or EEVEE with a simple flat diagnostic setup. In Workbench set
   `scene.display.shading.color_type = 'RANDOM'` and, for flat shading,
   `scene.display.shading.light = 'FLAT'`. In EEVEE use an Object Info `Random`-driven diagnostic
   material or deterministic distinct per-object preview colors; Workbench's color setting alone
   does not change EEVEE materials. Keep diagnostic overrides separate from production materials.
5. Spend at least three base-geometry review passes before lighting/material refinement: blockout
   and silhouette; proportions, clearances and assembly relationships; then all-around surfaces,
   backside/underside details and shading defects. Each pass renders the complementary camera
   set, inspects the actual images and evaluated geometry, and corrects unmet requirements through
   Stage 3 before the next pass. Record findings per pass; re-confirm already-correct geometry
   rather than making pointless edits. A single hero render or three copies of one view do not
   satisfy this review. Inspection/render-only work on an unchanged existing asset reviews the
   camera set without imposing unnecessary geometry edits or three reconstruction passes.
6. Fit each whole-asset camera to evaluated subject bounds using the geometry reference, checking
   every camera and relevant preview state with the `0.02` normalized margin. Exclude light rigs,
   backdrops, and emitter planes from the subject bounds. Center individual objects in frame;
   use intentional composition for landscape cameras. Render actual diagnostic images and inspect
   them; saving camera configurations alone is not evidence.
7. Repeat geometry-only reviews until the base-geometry acceptance set holds across the camera
   set. Only then proceed to Stage 5: Lighting, materials, and final renders. Missing approval
   blocks the costly step, not preservation/reporting of completed CAD, scene, or cheap previews.

## Stage 5: Lighting, materials, and final renders

1. For individual objects/parts, start with three-point lighting: an off-axis key that describes
   form, a weaker fill that preserves shadows, and a rear/rim light for separation. Use large area
   lights for controllable soft highlights; tune positions and relative powers to subject scale
   and material instead of flattening all shadows. Keep the rig useful across the review cameras.
2. For landscapes/scenes, start with a giant emissive plane outside all delivery-camera frames,
   positioned and sized as a broad soft source. Keep it contributing to lighting and reflections;
   out of frame does not mean `hide_render`. EEVEE does not automatically light the scene from
   emissive meshes as Cycles does: use an appropriately aligned area-light proxy or supported
   baked light-probe solution for early iterations and record the approximation. In Cycles restore
   the intended mesh-emitter setup without accidental double illumination from a retained proxy.
3. Iterate light placement and shadow/readability cheaply in EEVEE (or another capable cheap
   preview engine), keeping camera, exposure, and color-management settings consistent. Workbench
   flat renders assess shape, not physical illumination. Inspect all review angles after changes;
   fix geometry regressions in Stage 3/4 before spending on final rendering.
4. Before assigning or refining production materials, read `references/principled-materials.md`
   for physical parameter semantics and common-material starting ranges. Match the reference
   surface, finish, texture scale, layer structure and lighting rather than assigning arbitrary
   colors to a uniformly glossy shader. Restore source materials after diagnostic overrides.
5. With a verified GPU, switch to low-resolution, bounded-sample Cycles in later lighting/material
   iterations to confirm actual light transport, reflections, anisotropy and transmission. Correct
   mismatches that EEVEE approximations hid. Without GPU approval under Stage 4, leave expensive
   Cycles work pending; an EEVEE preview is not evidence of final Cycles lighting correctness.
6. Final rendered stills always use Cycles unless the user explicitly selects another engine.
   Restore production materials, remove diagnostic/proxy artifacts, and use the accepted lighting
   rig, centered square object framing or default scene aspect ratio. Render the complementary
   delivery-camera set, not only the hero view, within the resource/approval budget. Apply the
   Stage 4 animation gate to any final animation; a default engine is not authorization to render it.
7. Set all render options before rendering; Blender processes CLI arguments in order. Place
   `--render-frame` or `--render-anim` after file loading and render-setting arguments, or use
   `bpy.ops.render.render(write_still=True)` for script-controlled stills. Inspect the actual final
   images for geometry, composition, materials, shading, textures and lighting against the
   acceptance set. Return to the relevant phase on failure. Record optional polish separately,
   save the production `.blend` with intended final settings, and proceed to Stage 6 when verified.

## Stage 6: Verify and export

1. Inspect the requested existing scene, or reopen a changed `.blend` in a separate background
   process to verify the saved result. Inspect required objects, materials, transforms, cameras,
   final engine/render settings, external paths, and animation data. Confirm diagnostic overrides
   did not leak into the production scene; verify image aspect ratio and multi-camera coverage.
2. Check evaluated geometry with modifiers and render settings accounted for. Apply manifoldness,
   normal, topology, or polygon-budget checks only where the deliverable requires them.
3. When export is requested, use the installed Blender version's operators. Reimport into a
   separate scene or inspect with an available reader; verify units, axes, bounds, and data.
4. Proceed to Stage 7: Report.

## Stage 7: Report

1. For created artifacts, write `scene-report.md` with relevant previews, scene, scripts, exports,
   checks, device evidence, asset provenance, and reproduction commands. Include the geometry-pass
   findings, camera coverage, lighting/material iterations, final engine/aspect ratio, timings and
   any approval boundary. Distinguish cheap diagnostic previews from final renders. Inspection-only
   work returns the requested findings directly, with evidence from the inspected scene.
2. Deliver rendered images by default, not just file paths to models; parametric models retain
   their technical sheet before other images unless the user specifies otherwise. Report available
   and missing paths separately, with failures and unexecuted stages explicit. Preserve working
   copies and logs; release only processes owned by this task.
