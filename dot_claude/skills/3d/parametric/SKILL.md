---
name: parametric
description: "Use when a part or assembly must conform to stated requirements — parametric
  design with build123d in Python: dimension-driven solids built from specified dimensions,
  tolerances, fits, and interface geometry, exported as STEP/STL, verified by measurement, and
  documented with a first-angle multiview technical drawing sheet and rendered still images by
  default. Organic, appearance-driven modeling, sculpting, rendering, and animation select the
  non-parametric branch (`../non-parametric/SKILL.md`)."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A part brief whose controlling requirements are stated: exact dimensions and their sources
  (specification, standard fastener, measured mating part), tolerances or fit classes, and the
  intended process (FDM print, CNC, existing hardware).
- Existing CAD or mesh references that constrain interfaces, with their units and versions.
- Project or output directory, editing authority, and requested export formats.
- An available Python 3 environment; build123d availability is established in preflight.

## Output Contract

- `build-part.py` with named driving parameters at the top, so editing one parameter regenerates
  the corrected part.
- Requested exports (STEP for interchange and machining, STL for slicing) with units and
  orientation stated.
- Measured verification against the brief's acceptance set: each requirement reported as
  target, measured value, margin, and pass/fail, including solid validity and round-trip
  agreement.
- By default, rendered still images through the non-parametric pipeline, plus a first-angle
  multiview technical drawing sheet with the acceptance set's dimensions. Present the sheet before
  other images unless the user overrides the order; honor explicit deliverable overrides.
- `cad-report.md` covering the parameter table, requirement checks, versions, commands,
  artifact paths, and verification limits.
- Capability-limited output explicitly identifies which stages ran and which remain pending.
- Artifacts stay within the authorized project and owned working copy.

# Entrypoint

## Stage 1: Preflight and choose the interpreter

1. Resolve the skill root and execute `bin/cad-preflight` directly. Its Python 3 shebang runs a
   standard-library capability probe that reads executable availability and invokes Python's
   bounded `build123d` import. It writes JSON to stdout, changes no files, and returns 0 for a
   usable build123d environment or 2 when none was found.
2. Use the probed interpreter for every script in this task. If the probed interpreter cannot
   import build123d and `uv` is present, `uv run --no-project --with build123d python3 <script>`
   is an ephemeral route that fetches only into uv's cache; use it when fetching is acceptable
   for the task, otherwise report the missing capability and leave installation to the user
   (for example `uv pip install --user build123d`).
3. A probed environment proceeds to Stage 2: Plan. A missing capability ends at Stage 7: Report
   with the pending artifacts.

## Stage 2: Plan the parameter set

1. Turn the brief into a parameter table: named variable, value, unit, and source. A source is a
   stated requirement, a standard value, a measurement of a reference part, or a manufacturing
   rule; a number without a source is a recorded decision, not a requirement.
2. State the acceptance set as measurable targets: a requirement, its nominal target, and its
   tolerance (for example, "Ø4.30 mm hole +0.10/−0.00 to fit the M4 shelf bolt"). Model at
   nominal geometry and verify inside tolerance.
3. When interfaces reference existing parts, inspect the actual reference first — import a STEP
   or mesh and probe bounding boxes and sections — instead of trusting stated numbers.
4. State units and axis conventions explicitly (build123d models millimeters by default).
   Inspection-only work proceeds to Stage 4: Verify by measurement, and then returns findings
   from Stage 7: Report without exporting. Part creation proceeds to Stage 3: Build.

## Stage 3: Build the parametric solid

1. Write `build-part.py` in the output directory using build123d's algebra API as one
   consistent style (verified against build123d 0.13.0, 2026-10-28): named constants mirroring
   the Stage 2 table, primitives placed with explicit `Align` or `Plane` placement, explicit
   booleans and `fillet` operations, and no randomness.
2. Select edges for `fillet` and `chamfer` against the solid's current state: after a fillet,
   previously straight selected edges are arcs and cannot be re-selected by the same filter.
3. Run the script with the Stage 1 interpreter and preserve stderr on failure. A failed run is
   repaired before rerunning; a successful run proceeds to Stage 4: Verify by measurement.

## Stage 4: Verify by measurement

1. Do not trust geometry by construction. Measure in the same script run: bounding box
   (`part.bounding_box().size`), volume (`part.volume`), validity (`part.is_valid`), solid
   count (`part.solids()`), and targeted probes for each interface — face radii, cross-sections,
   distances between named features.
2. Compare every measured value with its acceptance target from the Stage 2 table, printing one
   line per requirement with target, measured, margin, and pass/fail; have the script exit
   nonzero when any requirement fails.
3. Rerun Stage 3 with adjusted parameters until every modeled requirement passes. Requirements
   that are not geometry (finish, strength, appearance) stay unverified and are reported as such
   in Stage 7.
4. Creation work proceeds to Stage 5: Export and round-trip check.

## Stage 5: Export and round-trip check

1. Export with the installed version's API (verified on build123d 0.13.0: `export_step(part,
   path)`, `export_stl(part, path)`). STEP is the interchange format; export STL only when the
   consumer slices it. Record units and orientation in the report.
2. Re-import the exported STEP with `import_step` and re-measure volume and bounding box;
   require agreement with the built model within a stated small tolerance before the export is
   shipped.
3. For the default rendered deliverable, also export STL as a visualization intermediate and read
   `../non-parametric/SKILL.md`. Follow its preflight, scene import/build, geometry-review,
   lighting/material, final-render, and verification stages. Preserve CAD units on import; keep
   geometric corrections in `build-part.py` and repeat numeric verification and export after them.
   Numeric acceptance remains mandatory; renders add visual evidence rather than replace it.
   Explicit image opt-outs skip this handoff. Unavailable Blender or a render approval boundary
   leaves renders pending while the drawing and verified CAD artifacts can still be delivered.
4. Proceed to Stage 6: Technical drawing by default, or Stage 7: Report if the user explicitly
   omitted the sheet. Rendering execution order does not change the sheet-first presentation order.

## Stage 6: Technical drawing (default)

1. For the default engineering sheet, in addition to the rendered views, run the owned helper
   with the Stage 1 interpreter:
   `python3 bin/part-drawing.py --part <exported STEP> --out part-sheet.svg --name <part>
   --dims part-dims.json`. It projects a fixed, explicit first-angle view set — front,
   top placed below the front view, the left-hand view placed right of front, plus an
   isometric — with hidden-line removal, dimension callouts, a center mark, and a title block
   stating scale, units, and projection (verified against build123d 0.13.0, 2026-10-28).
   Keep the SVG and convert it to `part-sheet.png` with `rsvg-convert` for the default image handoff.
   If raster conversion is unavailable, deliver the SVG and name the pending PNG explicitly.
2. Dimension callouts come from the Stage 2 parameter table: one annotation per requirement,
   labeled with its target value, in model millimeters (linear between two points; diameters on
   the view whose circular face is planar to the sheet). Drawings draw no decorative dimensions;
   a callout set that differs from the acceptance set goes back to Stage 2 first.
3. The helper fixes the view set deterministically instead of letting the model pick camera
   settings: orthographic by construction, first-angle placement, with mis-specified annotations
   exiting nonzero rather than silently altering the sheet. Photorealistic
   renders remain the non-parametric branch's pipeline.
4. Proceed to Stage 7: Report.

## Stage 7: Report

1. For created parts, write `cad-report.md`: the parameter table, a requirement table with
   target, measured, margin, and pass/fail per item including unverified requirements, script
   and export paths, interpreter and build123d versions, and the reproduction command. Include
   the drawing sheet before the rendered images by default, plus the Blender report/settings and
   any pending render approval or missing image capability. Inspection-only work returns the
   requested findings directly, with evidence from the inspected reference.
2. Report available and missing paths separately, with failures and unexecuted stages explicit.
   Preserve working copies and logs; release only processes owned by this task.
