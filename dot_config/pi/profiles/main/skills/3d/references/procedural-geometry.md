# Procedural geometry baseline

## Form and construction

Translate the asset into a small set of identifiable forms before adding surface detail. Blender
primitives are a useful closed-solid baseline. Set units and dimensions, apply dimensional scale
on owned objects, then build the modifier stack. Give boolean operands closed boundaries,
consistent outward normals and intentional geometric overlap.

For custom closed solids, use consistent face winding. In Object mode, normalize the owned mesh
before solid operations:

```python
import bmesh

mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(mesh)
bm.free()
mesh.update()
```

Keep construction parameters in the build script so corrections regenerate the same scene.
Choose modifier operators and properties from the installed Blender version. A boolean's result
is established by the evaluated geometry and preview, together with any task-required solid checks.

## Inspect the geometry Blender actually uses

After updating the view layer, obtain evaluated geometry through the dependency graph. Match
viewport and render modifier settings to the intended deliverable before inspecting it.

```python
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = obj.evaluated_get(depsgraph)
evaluated_mesh = evaluated.to_mesh()
try:
    print(obj.name, len(evaluated_mesh.vertices), len(evaluated_mesh.polygons))
finally:
    evaluated.to_mesh_clear()
```

Check the requested forms and assembly relationships first, then silhouette and material separation
in the actual camera image. The brief's acceptance set determines completion. Additional cosmetic
ideas can be reported as optional follow-up after the verified asset is saved.

## Primary references

- [BMesh face-normal recalculation](https://docs.blender.org/api/current/bmesh.ops.html#bmesh.ops.recalc_face_normals)
- [Evaluated dependency graph](https://docs.blender.org/api/current/bpy.types.Depsgraph.html)
- [Object mesh conversion](https://docs.blender.org/api/current/bpy.types.Object.html#bpy.types.Object.to_mesh)
