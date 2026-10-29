---
name: 3d
description: "Use when creating, modeling, rendering, editing, inspecting, or exporting
  3D objects, physical models, scenes, materials, or animation, including Blender files and
  existing connected scenes, or when a part must conform to exact dimensional requirements.
  Routes one tree between two branches: non-parametric design (Blender; organic,
  appearance-driven work) and parametric design (build123d; dimension-driven parts)."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A 3D request: deliverable, intended use, project path, editing authority, and output directory.
- Whether the controlling requirements are exact (dimensions, tolerances, fits, interfaces) or
  visual (silhouette, appearance, materials, motion).

## Output Contract

- The matching branch's procedure run from its `SKILL.md`, with that branch's input and output
  contracts satisfied.
- A request that plausibly matches both branches ends with one focused question that names what
  would decide it.

# Entrypoint

## Stage 1: Choose the branch

1. Exact-requirement deliverables are parametric: parts whose acceptance is measured — specified
   dimensions, tolerances or fit classes, interface or mating geometry, standards-driven features,
   printing or machining targets. Read `parametric/SKILL.md` and follow it.
2. Appearance-driven deliverables are non-parametric: freeform shapes, sculpting, procedural mesh
   and modifier construction, scenes, materials, lighting, animation, and inspection or export of
   existing Blender scenes, where the brief is judged in renders rather than measured dimensions.
   Read `non-parametric/SKILL.md` and follow it.
3. Mixed deliverables use both: model geometry with the parametric branch first, then continue
   with either branch's remaining stages — render measured solids for visual checks with the
   non-parametric render pipeline, or place exact interface solids inside an organic scene.
4. When both branches plausibly match, ask one focused question that names the deciding
   condition (for example, whether the finished part's dimensions will be verified by
   measurement), then route on the answer.
