# Source-grounded modeling and visual refinement

Read this when building or refining an editable scene, GLB or architectural render.

## Tool choice and scene preservation

Use the connected Blender tools when available and suitable. Inspect the scene before editing: preserve unrelated objects and save the current house revision before a major change. If the connection is unavailable, an installed Blender command-line build can generate reproducible scenes and previews. Discover its actual path/version; do not assume a particular OS, version or GPU.

Prefer parameterized geometry and reusable materials when dimensions or layout will change. Keep a readable build script where useful, with paths/configuration supplied by the current project. Do not copy another house's coordinates, source IDs, account URLs or appliance inventory into a new job.

## Model in layers

Keep architecture, observed fixtures, proposed staging, lights/cameras and interaction helpers distinguishable. Include source IDs and accuracy notes on meaningful objects or in a sidecar manifest; hundreds of repeated decorative meshes are not hundreds of independently observed furnishings.

**Shell and floors**

- Model continuous floor surfaces by room or actual material region. A connected kitchen/dining/living space may contain both wood and carpet; do not assign its entire area from a single room label.
- Triangulate concave outlines correctly. Avoid beveling every internal triangle, separately thickening fragments from different photographs, or exporting coincident floor faces.
- Give walls deliberate thickness and shared-boundary ownership. Preserve doors, windows and open passages; frame the openings without filling their aperture with an accidental wall face.
- For dollhouse cutaways, split display layers deliberately. Lower and upper wall sections should meet without a visible horizontal bevel or gap when both are shown.
- Validate a top view and a few oblique views before detailed fixture work. Resolve mirrored layouts, wrong scale, overlapping floors and missing openings first.

**Fixtures and furnishings**

- Inspect each source room for built-ins as well as movable furniture. Empty bedrooms do not imply an empty kitchen or bathroom. Check cabinets, counters, sinks, cooktops, microwave/hood, appliances, vanity, toilet, tub/shower, medicine storage, shelving and visible fittings where applicable.
- Use silhouettes and surfaces appropriate to the object. Rounded ceramic bodies, recessed basins, framed cabinet doors, hardware and continuous counters often improve a close-up more than adding decorative clutter.
- Make sink and tub cavities genuinely hollow. Cut the countertop opening and ensure the cabinet body or old primitive underneath does not intersect the bowl. Check the depth and rim from above and obliquely.
- Place and orient fixtures against the walls shown in the source. Check the toilet/vanity relationship, appliance fronts, clearance and cabinet support in more than one view.
- Preserve confirmed empty appliance bays. Do not fill an empty refrigerator or laundry space merely because that appliance is common.
- Reusable or generated assets can represent observed object categories when their dimensions and appearance fit. Treat them as approximations and retain applicable asset attribution. Do not introduce unrelated assets just to approach a furnished reference image.

**Materials**

- Create recognizable wood, laminate, painted plaster, carpet, concrete, tile, porcelain and metal as supported by the room. Reference imagery can guide roughness, edge treatment and lighting without overriding the home's evidence.
- Set UVs in physical scale. Distinguish floorboard seams from continuous cabinet wood grain; using the floor map on cabinet fronts often introduces implausible seams.
- Use subtle roughness and normal variation; correct object scale and edge geometry matter more than exaggerated bump strength.
- Bake or author exportable texture maps for procedural Blender shaders. Arbitrary node graphs do not automatically survive glTF export. Preserve color-space intent: color maps versus linear data such as normal/roughness maps.
- Avoid projecting the full panorama onto walls or objects in an authored-material deliverable. If a photograph-textured reconstruction is specifically requested, keep it distinguishable from authored materials and assess baked lighting, furniture ghosts and seams.

## Render, inspect, revise

Use comparable camera framing for successive passes. Include an overview, a top-down alignment check and close-ups of detailed rooms. Use broad lighting and plausible material response to expose form; do not hide mistakes under dramatic lighting or heavy denoising.

Prioritize defects demonstrated by the images:

| Symptom | Inspect before adding detail |
| --- | --- |
| Jagged floor boundaries or moire | Duplicate faces, fragmented slabs, UV scale and render depth precision |
| Solid-looking sink | Countertop aperture, cabinet top intersection, bowl normals and interior geometry |
| Floating cabinet or mirror | Actual support geometry versus cutaway visibility |
| Texture looks like stripes or stickers | Physical scale, mapping direction, material-specific grain and roughness |
| Fixtures crowd or intersect | Orientation, wall alignment, dimensions and source interpretation |
| Interior disappears in detail render | Camera-specific cutaway state, crop, clipping and occlusion |

Cutaway render visibility must be recomputed for each camera, not inherited from the overview. Keep a door/window assembly on one cutaway anchor so a header does not float after its jambs disappear. For wall-mounted fixtures, make the presentation coherent: retain support, show a light support outline, or hide an occluding assembly together as appropriate. Keep a full-wall inspection mode; do not delete real fixtures to solve a presentation problem.

Iterate until the requested quality is met or the remaining limit is identifiable evidence, geometry or runtime budget. More samples improve noise, not topology or fixture placement. Do not promise an unlimited background loop. Record the remaining differences from a reference without claiming photorealism from pixel dimensions alone.

## Export and reproducibility

- Save the editable scene with its material resources and useful cameras. Preserve the baseline when comparison or rollback is requested.
- Export the requested portable format with units and axes checked, necessary modifiers/curves converted, and intended material textures included. Exclude staging, debug geometry and render-only backdrops unless requested.
- Inspect the exported asset in the actual target renderer. Check bounds, normal orientation, opening visibility, material texture availability and fixture evidence. A good Cycles render is not proof of correct browser appearance.
- Keep expensive inference separate from ordinary model edits. A floor, cabinet or viewer fix usually does not require rerunning panorama synthesis.

If a neural renderer such as PanSplat is requested, use its actual supported inputs and verify current official setup requirements. Its rendered novel views do not automatically supply an accurate, globally registered house mesh. Validate source captures, poses, inference/output resolution and decoded output separately; upsampling a 2K source to a 4K output does not create native 4K source detail.
