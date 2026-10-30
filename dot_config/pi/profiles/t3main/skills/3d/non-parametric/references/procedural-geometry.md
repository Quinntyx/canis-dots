# Procedural geometry

## Construction

1. Translate the requested asset into identifiable forms before adding surface detail. Use Blender
   primitives as a closed-solid baseline. Set units and dimensions, apply dimensional scale on owned
   objects, then build the modifier stack. Give boolean operands closed boundaries, consistent
   outward normals and intentional geometric overlap. Build terrain and other deformed broad
   surfaces from distributed grid/triangle faces before displacement, including caps and boolean
   cuts. A displaced large n-gon is implicitly triangulated into long facets that can produce
   spikes and diagonal bands; choose surface topology that follows the intended shape, then review
   its evaluated surface from side and overhead cameras during the geometry passes.
2. For custom closed solids, normalize the owned mesh in Object mode before solid operations.
   Create a BMesh with `bmesh.new()`, load `obj.data` through `bm.from_mesh(obj.data)`, recalculate
   all faces with `bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))`, write back through
   `bm.to_mesh(obj.data)`, free the BMesh with `bm.free()`, and call `obj.data.update()`.
3. Keep construction parameters in the build script so corrections regenerate the same scene.
   Choose modifier operators and properties from the installed Blender version. Establish a boolean
   result through evaluated geometry, actual previews and the task's required solid checks. Use the
   parent procedure's cheap random-per-object, multi-camera geometry passes before lighting work.
   Inspect carved features by their intended empty space from opening-facing and overhead cameras.
   For an open coastal inlet, show both a water-connected shoreline recess and sky clearance above
   the bay. Size the cutter to clear that intended space across the evaluated terrain surface.

## Evaluated geometry

1. Call `bpy.context.view_layer.update()`, then obtain the dependency graph through
   `bpy.context.evaluated_depsgraph_get()`. Match viewport and render modifier settings to the
   intended deliverable before inspecting it. In the separate reopen verification, read the saved
   camera transforms, lens/orthographic scale and image settings as loaded, then project the subject
   through every planned review/delivery camera. Any framing correction belongs in the build phase,
   followed by saving and reopening the corrected scene for another observation.
2. Obtain the evaluated object with `obj.evaluated_get(depsgraph)` and its temporary mesh through
   `evaluated.to_mesh()`. Read vertices, polygons and required topology properties from that mesh.
   Release the temporary mesh with `evaluated.to_mesh_clear()` in a `finally` block.
3. Check required forms and assembly relationships first, then silhouette and material separation
   in actual images from the complementary camera set. Include hidden/backside surfaces, not only
   the hero view. The brief's acceptance set determines completion. Report additional cosmetic
   ideas as optional follow-up after saving the verified asset.

## Whole-asset camera framing

1. Fit every whole-asset review/delivery camera to evaluated subject bounds at every relevant
   preview state. Set that frame and update the view layer. Select the requested renderable objects
   as the subject set, excluding backdrops, light rigs and the landscape emitter plane. Center
   individual-object views with square image dimensions and square pixels unless overridden;
   preserve the default aspect ratio and intended composition for landscape/scene views.
2. Enumerate all eight corners in each evaluated object's `bound_box`. Transform each to world
   coordinates with
   `evaluated.matrix_world @ mathutils.Vector(corner)`, then project through
   `bpy_extras.object_utils.world_to_camera_view(scene, scene.camera, world_corner)`.
3. Blender's projection uses `[0, 1]` across the image. Use a normalized image margin of `0.02`.
   Require a nonempty projected set, positive `z`, and
   both `x` and `y` between `0.02` and `0.98` for every corner. Record the per-state bounds.
   Recenter and expand camera framing until every requested state passes, then inspect renders.
   Camera placement updates must reach the dependency graph before projection: call
   `bpy.context.view_layer.update()` after each change to `camera.location` or its rotation.

For a centered whole-object perspective view, this bounded pattern fits the actual evaluated
corners. Call it after setting the image aspect and placing the named camera on its chosen side;
retain its returned bounds as framing evidence. Landscape composition can offset the aim afterward
and repeat the same projection check; orthographic views expand `camera.data.ortho_scale` instead
of perspective distance.

```python
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


def fit_perspective_camera(scene, camera, subjects, margin=0.02):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    corners = []
    for subject in subjects:
        evaluated = subject.evaluated_get(depsgraph)
        corners.extend(evaluated.matrix_world @ Vector(p) for p in evaluated.bound_box)
    assert corners and camera.data.type == 'PERSP'
    center = sum(corners, Vector()) / len(corners)
    direction = (camera.location - center).normalized()
    radius = max((p - center).length for p in corners)
    camera.location = center + direction * max((camera.location - center).length, 2 * radius)
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    for _ in range(32):
        bpy.context.view_layer.update()
        projected = [world_to_camera_view(scene, camera, p) for p in corners]
        if all(p.z > 0 and margin <= p.x <= 1 - margin
               and margin <= p.y <= 1 - margin for p in projected):
            return {axis: [min(getattr(p, axis) for p in projected),
                           max(getattr(p, axis) for p in projected)] for axis in ('x', 'y', 'z')}
        camera.location = center + (camera.location - center) * 1.15
    raise RuntimeError(f'Camera fit did not converge: {camera.name}')
```

For the separate reopen process, run this observational check on each named camera as loaded.
It uses Blender's projection and the complete evaluated corner set, just like the fit above;
retain the returned bounds in the verification report.

```python
def verify_camera_framing(scene, camera, subjects, margin=0.02):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    projected = []
    for subject in subjects:
        evaluated = subject.evaluated_get(depsgraph)
        projected.extend(world_to_camera_view(scene, camera, evaluated.matrix_world @ Vector(p))
                         for p in evaluated.bound_box)
    assert projected, 'Expected evaluated subject corners'
    bounds = {axis: [min(getattr(p, axis) for p in projected),
                     max(getattr(p, axis) for p in projected)] for axis in ('x', 'y', 'z')}
    assert all(p.z > 0 and margin <= p.x <= 1 - margin and margin <= p.y <= 1 - margin
               for p in projected), (camera.name, bounds)
    return bounds
```

4. Record graphics-device observations separately from thread count. For EEVEE, inspect backend
   and device through the installed `gpu.platform` API where available. Preserve unavailable
   observations as unresolved; Cycles CPU selection establishes its distinct CPU fallback path.

## Primary references

- [BMesh face normals](https://docs.blender.org/api/current/bmesh.ops.html)
- [Evaluated geometry](https://docs.blender.org/api/current/bpy.types.Depsgraph.html)
- [Mesh conversion](https://docs.blender.org/api/current/bpy.types.Object.html)
- [Camera projection](https://docs.blender.org/api/current/bpy_extras.object_utils.html)
- [Graphics platform](https://docs.blender.org/api/current/gpu.platform.html)
