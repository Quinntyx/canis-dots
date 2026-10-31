# Procedural geometry

## Construction

1. Translate the requested asset into identifiable forms before adding surface detail. Use Blender
   primitives as a closed-solid baseline. Set units and dimensions, apply dimensional scale on owned
   objects, then build the modifier stack. Give boolean operands closed boundaries, consistent
   outward normals and intentional geometric overlap.
2. For custom closed solids, normalize the owned mesh in Object mode before solid operations.
   Create a BMesh with `bmesh.new()`, load `obj.data` through `bm.from_mesh(obj.data)`, recalculate
   all faces with `bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))`, write back through
   `bm.to_mesh(obj.data)`, free the BMesh with `bm.free()`, and call `obj.data.update()`.
3. Keep construction parameters in the build script so corrections regenerate the same scene.
   Choose modifier operators and properties from the installed Blender version. Establish a boolean
   result through evaluated geometry, actual previews and the task's required solid checks. Use the
   parent procedure's cheap random-per-object, multi-camera geometry passes before lighting work.

## Evaluated geometry

1. Call `bpy.context.view_layer.update()`, then obtain the dependency graph through
   `bpy.context.evaluated_depsgraph_get()`. Match viewport and render modifier settings to the
   intended deliverable before inspecting it.
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
2. Obtain each evaluated object's `bound_box`. Transform every corner to world coordinates with
   `evaluated.matrix_world @ mathutils.Vector(corner)`, then project through
   `bpy_extras.object_utils.world_to_camera_view(scene, scene.camera, world_corner)`.
3. Use a normalized image margin of `0.02`. Require a nonempty projected set, positive `z`, and
   both `x` and `y` between `0.02` and `0.98` for every corner. Record the per-state bounds.
   Recenter and expand camera framing until every requested state passes, then inspect renders.
4. Record graphics-device observations separately from thread count. For EEVEE, inspect backend
   and device through the installed `gpu.platform` API where available. Preserve unavailable
   observations as unresolved; Cycles CPU selection establishes its distinct CPU fallback path.

## Primary references

- [BMesh face normals](https://docs.blender.org/api/current/bmesh.ops.html)
- [Evaluated geometry](https://docs.blender.org/api/current/bpy.types.Depsgraph.html)
- [Mesh conversion](https://docs.blender.org/api/current/bpy.types.Object.html)
- [Camera projection](https://docs.blender.org/api/current/bpy_extras.object_utils.html)
- [Graphics platform](https://docs.blender.org/api/current/gpu.platform.html)
