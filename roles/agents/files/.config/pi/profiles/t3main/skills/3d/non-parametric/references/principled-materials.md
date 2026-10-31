# Principled BSDF material reference

Read during the lighting/material phase, after the parent procedure's cheap geometry reviews.
Use this reference for Blender renders of both organic scenes and imported parametric parts.

## Contents

- Physical controls and color handling
- Metals
- Wood and common opaque surfaces
- Glass, liquids and gemstones
- Layering, texture and lighting checks
- Sources and scope

## Physical controls and color handling

Checked against the Blender 5.2 LTS manual and Blender 5.2.2 sockets on 2026-10-28; the principal
controls also exist in Blender 4.x. Inspect the installed node's `inputs` before scripting:
UI labels and socket identifiers can differ (for example, the Specular panel's IOR Level is the
`Specular IOR Level` socket). Use `ShaderNodeBsdfPrincipled`, not obsolete pre-4.x socket recipes.

The optical IOR anchors below are approximately visible-light values, not universal constants:
composition, wavelength, temperature and crystal orientation matter. Roughness and anisotropy
ranges are practical **finish-dependent starting points**, not measured constants of a substance.
Opaque composite materials such as wood, cloth, concrete and paint use effective dielectric IOR
approximations. Match reference images and surface finish rather than asserting laboratory accuracy.

- **Metallic:** use `1` for exposed metal and `0` for wood, stone, glass, plastic, paint, rust and
  gemstones. Intermediate values belong to mixtures, coverage masks or transitions, not a generic
  "shininess" control. Painted metal is a dielectric painted surface over metal; exposed chips can
  reveal a separate metal shader.
- **Roughness:** sets the width/blur of microfacet reflection and transmission. Low values give
  sharp highlights; high values give broad ones. A rough dielectric still reflects light. Avoid
  using IOR or Metallic to compensate for a wrong roughness, light size or missing environment.
- **IOR and reflectiveness:** for a dielectric in air at normal incidence,
  `F0 = ((IOR - 1) / (IOR + 1))**2`. IOR 1.33 gives about 2%, 1.5 gives 4%, 1.77 gives 7.7%,
  and diamond's 2.417 gives 17.2%. Reflectance increases at grazing angles. Leave
  `Specular IOR Level = 0.5` for the physical IOR response; it is a neutral multiplier, **not 50%
  reflectivity**. At 0 it removes reflection and at 1 it doubles normal-incidence reflection.
  Legacy specular formulas are not the Blender 4+/5.x IOR Level socket.
- **Metal reflection:** at Metallic 1, Base Color specifies colored conductor reflection rather
  than diffuse pigment. Do not enter a metal's real refractive-index component as a glass-like
  dielectric IOR; real conductors have complex, wavelength-dependent `n + ik`. The metal Base
  Color approximation below is adequate for ordinary Principled work; use measured complex-IOR
  data or a specialized conductor model when the brief requires optical precision.
- **Specular tint:** keep dielectric reflections neutral/white. Tint the pigment with Base Color,
  or colored transparent media with absorption. Metallic edge tint is a separate refinement when
  reference data supports it, not a saturation boost for every surface.
- **Anisotropic:** specular highlight directionality, not general roughness. Start at 0 unless the
  surface has directional brushing, machining or fibers. Set a Tangent/UV direction and use
  `Anisotropic Rotation` to align it; a value of 1 makes a full rotation. This is distinct from
  subsurface scattering anisotropy. Validate directional highlights in Cycles, not just EEVEE.
- **Transmission Weight:** use near 1 for clear glass/liquid/gem interiors; opacity is not the same
  phenomenon. Keep Alpha 1 for solid glass. Closed thickness, outward normals, correct nesting and
  sufficient transmission bounces matter more than adding a fake transparent mix.
- **Coat:** use `Coat Weight = 1` for an actual continuous varnish/clearcoat layer, with its own
  roughness and IOR (normally about 1.45–1.55; match a known resin when specified). A patchy coat
  can use a coverage mask. Keep Coat 0 for a bare surface.
- **Sheen / subsurface:** use Sheen for cloth fuzz, not a substitute for specular. Use Subsurface
  Weight and RGB Radius/Scale for skin, wax or translucent stone when needed; radii are physical
  distances in the scene's scale, so calibrate with thickness and units rather than copying an
  arbitrary number. Prefer a fully scattering material with calibrated distance over lowering the
  weight to hide an incorrect scale. Keep unrelated layers disabled.
- **Color management:** Base Color/albedo textures are sRGB; roughness, metallic, normal,
  displacement and masks are Non-Color data. `bpy` node color defaults expect scene-linear RGB.
  Convert sRGB swatches before assigning them; do not paste display RGB as linear shader values.
  Keep exposure and the chosen view transform fixed while comparing materials. Normal maps need
  a Normal Map node; height maps need a Bump/displacement route and realistic physical scale.

For an sRGB 8-bit swatch, convert each channel before assigning Base Color:

```python
def srgb8_to_linear(rgb):
    values = [c / 255.0 for c in rgb]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                 for c in values) + (1.0,)
```

## Metals

All rows: Metallic 1, Transmission 0, Coat 0 unless actually coated; leave Specular IOR Level at
0.5. A single dielectric IOR is not the metal parameter to tune. The displayed RGB swatches are
approximate **sRGB 8-bit reflection colors**, adapted from Filament's PBR reference, not diffuse
paint colors. Finishing changes roughness and anisotropy, not the metal's identity.

| Surface | Base Color starting point | Roughness | Anisotropic | Finish cues |
| --- | --- | --- | --- | --- |
| Polished aluminum | (244, 245, 245) | 0.05–0.15 | 0–0.15 | Neutral bright reflection; fine imperfection map |
| Brushed aluminum | (244, 245, 245) | 0.20–0.40 | 0.5–0.85 | Align brushing/tangent with fabrication |
| Polished steel / stainless | Neutral gray; use measured alloy reflectance when known | 0.08–0.20 | 0–0.2 | Not chrome-white; small edge bevels reveal form |
| Brushed stainless steel | Same alloy reflection color | 0.25–0.45 | 0.5–0.85 | Directional grain and roughness variation |
| Iron / cast iron | (192, 189, 186) for clean iron | 0.35–0.65 | 0–0.2 | Casting microtexture; oxide/rust is a separate dielectric layer |
| Silver | (250, 249, 245) | 0.03–0.15 | 0–0.15 | Tarnish changes surface chemistry; mask a separate layer |
| Gold | (255, 220, 157) | 0.05–0.20 | 0–0.2 | Warm reflection, no yellow diffuse paint |
| Copper | (251, 216, 184) | 0.08–0.25 | 0–0.3 | Patina is a separate, nonmetallic surface |
| Brass | (244, 228, 173) | 0.10–0.30 | 0–0.4 | Alloy-dependent warm reflection; brushing optional |
| Titanium | (206, 200, 194) | 0.20–0.45 | 0–0.5 | Machining direction; anodized oxide needs its own optical treatment |
| Chrome plating | Near-neutral high reflection; source measured chromium data | 0.03–0.12 | 0–0.1 | A reflective coating, not gray plastic |

Polished metals need large reflected light shapes and some dark surroundings to show form.
A uniformly bright world can make correct metal look flat. For a brushed finish, establish UVs or
an explicit mesh tangent along the machining/brushing direction, connect a Tangent node to the
Principled `Tangent` input, and align `Anisotropic Rotation` with that direction. Add fine,
low-amplitude directional roughness/bump at a plausible physical grain scale while retaining the
metal's reflection color. Under the off-axis key, inspect the elongated highlight from multiple
angles and compare with a smooth patch: the grain should read within the reflection rather than
as broad painted stripes or cloudy color patches. Tune light/dark reflected shapes and texture
scale in Cycles until both the metal and its brushing direction read clearly. Add wear only where
the object's use supports it.

## Wood and common opaque surfaces

All rows: Metallic 0, Transmission 0, Specular IOR Level 0.5 and Anisotropic 0 unless noted.
Use reference-derived diffuse Base Color: not pure black/white and not a photograph with baked
lighting. Roughness refers to the substrate; a coat's roughness is independent.

| Surface | IOR starting point | Roughness | Additional setup |
| --- | --- | --- | --- |
| Raw oak / ash | 1.45–1.55 effective | 0.55–0.80 | Grain-aligned color/roughness/pores; Anisotropic 0–0.3 only if directional highlights are visible |
| Raw walnut / mahogany | 1.45–1.55 effective | 0.45–0.70 | Warmer/darker grain, not a uniformly brown plastic shader |
| Sanded pine / maple | 1.45–1.55 effective | 0.45–0.70 | Finer light grain; distinguish end grain from long grain |
| Varnished wood | Base about 1.5 | Base 0.40–0.70 | Coat 1, Coat IOR 1.5, Coat Roughness 0.08–0.25; retain grain below |
| Painted wood / powder coat | 1.45–1.60 effective | 0.30–0.65 | Surface is dielectric paint; mild orange peel only when appropriate |
| Gloss automotive paint | About 1.5 base | Base 0.20–0.40 | Coat 1, Coat Roughness 0.03–0.12; model metallic flakes as a separate effect if needed |
| ABS / opaque molded plastic | About 1.5 effective | Gloss 0.15–0.30; matte 0.40–0.65 | Tiny mold texture, no automatic coat or subsurface |
| Polypropylene plastic | About 1.49 | 0.25–0.55 | Subsurface only for visibly thin/translucent variants |
| Rubber / tire | About 1.5 effective | 0.55–0.85 | Dark gray rather than black zero; worn/wet patches differ |
| Leather | About 1.5 effective | 0.35–0.65 | Fine pores and folds; coat only for a sealed glossy finish |
| Cotton / linen | About 1.5 effective | 0.65–0.90 | Sheen Weight 0.2–0.6; weave at physical scale |
| Wool / velvet | About 1.5 effective | 0.70–0.95 | Sheen Weight 0.5–1; silhouette fibers may need geometry |
| Silk / satin | About 1.5 effective | 0.25–0.45 | Anisotropic 0.3–0.7 with weave tangent; modest sheen |
| Paper / cardboard | 1.45–1.55 effective | 0.65–0.90 | Fiber-scale bump; thin-sheet transmission needs an appropriate setup |
| Concrete | About 1.5 effective | 0.65–0.90 | Aggregate and pores; polished concrete can be 0.20–0.40 |
| Brick / terracotta | About 1.5 effective | 0.70–0.95 | Porous texture; keep mortar a separate surface |
| Granite / rough stone | About 1.5 effective | 0.60–0.90 | Mineral-scale variation; polished stone about 0.10–0.25 |
| Marble | About 1.5 effective | Polished 0.10–0.25; honed 0.35–0.55 | Veins below surface; small-scale subsurface if thickness warrants |
| Unglazed ceramic | About 1.5 effective | 0.55–0.85 | Fine porous bump, no blanket gloss |
| Glazed porcelain | About 1.5 effective | Base 0.35–0.60 | Coat 1, Coat IOR about 1.5, Coat Roughness 0.04–0.18 |
| Skin | About 1.4 | 0.35–0.60 | Calibrated Random Walk skin scattering; vary oil/pores, not Metallic |
| Candle wax | About 1.44 | 0.25–0.45 | Subsurface with scattering distance matched to wax thickness |
| Soil / sand | About 1.5 effective | 0.75–0.95 | Granular detail and particle-scale variation; wetness changes layering |
| Leaves | About 1.45 effective | 0.35–0.65 | Waxy top surface, veins and suitable thin-leaf transmission/backlighting |

Wood is anatomical, not just stretched noise. Orient long grain along the board, give cut ends
a distinct end-grain pattern, and vary pores/rings at plausible scales. A varnish layer changes
surface reflection without erasing the wood underneath. Similar care applies to cloth weave,
stone aggregate and molded-plastic texture.

## Glass, liquids and gemstones

All rows: Metallic 0, Alpha 1, Specular IOR Level 0.5, Anisotropic 0, Coat 0 by default.
Use Transmission Weight 1 for a clear bulk medium; use roughness for a frosted surface, not Alpha.
Values shown assume the surface borders air. Nested media need correct boundaries and relative
optical behavior, not overlapping shells with arbitrary IORs.

| Material | IOR | Roughness | Transmission / bulk treatment |
| --- | --- | --- | --- |
| Clear soda-lime glass | 1.50–1.52 | 0.00–0.06 | Weight 1; model wall thickness; slight volume absorption for thick glass |
| Frosted glass | 1.50–1.52 | 0.20–0.50 | Weight 1; rough transmission, not opaque gray paint |
| Borosilicate glass | About 1.47 | 0.00–0.06 | Weight 1; actual hollow geometry where needed |
| Acrylic / PMMA | About 1.49 | 0.02–0.10 | Weight 1; less reflective than high-IOR gems |
| Polycarbonate | About 1.585 | 0.03–0.12 | Weight 1 for clear PC; match molded finish |
| Water | About 1.333 | 0.00–0.05 calm | Weight 1; waves are geometry/normal variation; depth-dependent absorption |
| Ice | About 1.31 | Clear 0.03–0.15; frosted 0.20–0.45 | Weight 1 for clear ice; bubbles/cracks/scattering for cloudy ice |
| Quartz / amethyst | 1.54–1.55 | 0.00–0.08 polished | Weight 1; amethyst uses volume color/absorption, not Metallic |
| Emerald | 1.57–1.60 | 0.01–0.08 polished | Weight 1; green absorption and reference-driven inclusions |
| Ruby / sapphire | 1.76–1.77 | 0.00–0.06 polished | Weight 1; red/blue absorption; preserve crisp facet normals |
| Diamond | About 2.417 | 0.00–0.04 polished | Weight 1; precise facets, adequate transmission bounces and visible reflected light shapes |
| Amber | About 1.50–1.55 | 0.04–0.20 | Weight 1 for clear amber; honey-colored absorption and optional inclusions |

For transparent bulk objects start with a near-neutral Base Color and a Volume Absorption node
for thickness-dependent color; tune density against the model's real scale. Surface tint alone
can look like colored plastic paint. Closed topology, sensible bevels and the actual cut dominate
gem appearance. A single-IOR Principled setup does not reproduce spectral dispersion, gemstone
birefringence, or every caustic effect: use an appropriate renderer/material setup if these matter,
and disclose approximation limits rather than faking "diamond" with Metallic 1.

## Layering, texture and lighting checks

1. Choose the physical surface first (bare metal, painted metal, varnished wood, porous stone,
   coated ceramic), then assign the substrate and actual layers. A dirt/rust mask may change
   Metallic as well as color and roughness; a wet layer changes reflection and absorption.
2. Build correlated but nonidentical color, roughness and normal detail at the asset's scale.
   Keep important silhouette detail in geometry. Avoid a perfect uniform gloss or identical noise
   everywhere; also avoid gratuitous scratches, dirt and bevels unsupported by the reference.
   Choose texture frequency in its actual coordinate space: Generated spans approximately 0–1
   across each mesh axis, while Object coordinates follow the chosen object's local scale. Mapping
   scale and texture scale multiply. For example, Generated × `(1, 4, 4)` into Noise Scale `40`
   gives about 40 versus 160 coordinate-scale units across those axes, not 40 cycles per meter;
   Noise is not periodic, so confirm the actual feature size visually. Judge fine brushing in a
   final-density crop and keep subpixel microtexture represented by roughness/anisotropy. Match
   bump distance to physical scene units, preserving the texture's contrast while tuning lighting.
3. Test under the parent procedure's three-point rig for objects, or broad out-of-frame emitter
   for landscapes. Inspect complementary camera angles, broad/grazing highlights and shadowed
   regions. Fix surface normals, tangent direction, texture scale or lighting before forcing a
   physically implausible shader value to compensate.
4. Confirm in bounded-sample Cycles before final rendering when a usable GPU is available; obey
   the parent's CPU-cost and animation approval gates otherwise. EEVEE preview limitations are
   especially relevant to anisotropy, refractive thickness, emission-driven lighting and indirect
   transport. Record chosen material values and any visual approximation in the scene report.

## Sources and scope

Researched 2026-10-28. Parameter semantics and optical anchors are sourced below; the finish ranges
and layering recipes above are practical starting guidance, not claims that the sources measured
all listed surfaces at those exact roughness/anisotropy settings.

- [Blender 5.2 LTS: Principled BSDF](https://docs.blender.org/manual/en/5.2/render/shader_nodes/shader/principled.html)
  — layer model, IOR/IOR Level, roughness, anisotropy, coat, sheen and subsurface semantics.
- [Blender: Workbench object color](https://docs.blender.org/manual/en/4.5/render/workbench/color.html)
  — random-per-object geometry diagnostics are not production shader settings.
- [Blender: EEVEE light-probe volumes](https://docs.blender.org/manual/en/4.5/render/eevee/light_probes/volume.html)
  — baked emission contribution and EEVEE approximation limits.
- [Filament: crafting physically based materials](https://google.github.io/filament/Material%20Properties.pdf)
  and [web reference](https://google.github.io/filament/notes/material_properties.html)
  — sRGB metal reflection swatches, metallic/dielectric separation and surface-finish concepts.
  Its engine-specific reflectance control is not Blender's Specular IOR Level.
- [Physically Based materials API](https://api.physicallybased.info/materials) and
  [schema](https://api.physicallybased.info/) — named material IORs and per-material source links;
  its linear RGB values and centimeter scattering distances require explicit conversion before use.
- [RefractiveIndex.INFO: artist material selection](https://refractiveindex.info/?shelf=3d)
  — wavelength-dependent optical data, including diamond, sapphire, quartz, glass and water.
- [OTOY: Procedural Wood — A Deep Dive](https://help.otoy.com/hc/en-us/articles/45411909964827-Procedural-Wood-A-Deep-Dive)
  — grain anatomy, finish and layered wood appearance; adapt the concepts, not another renderer's sockets.

**This material list is not exhaustive and is only a reference. If a different material, parameter
range, shader, or material setup better matches the model and its references, feel free to diverge
from it; record the choice and verify the result under the intended lighting.**
