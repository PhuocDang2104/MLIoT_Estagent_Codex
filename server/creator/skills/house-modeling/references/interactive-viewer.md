# Interactive dollhouse and panorama viewer

Read this only when implementing or diagnosing an interactive viewer.

## One source of geometry

Load the model's floors and walls as the architectural source of truth. Inspect the GLB before adding generated room slabs or fallback floors. If a fallback is needed, enable it only when the model lacks the corresponding geometry. Do not overlay a second almost-coplanar floor on an existing model floor.

Keep a presentation ground/backdrop below the lowest architectural surface with deliberate clearance. A backdrop is not another room floor. Preserve version-specific models; a viewer fix should not require rewriting the saved baseline GLB.

## Diagnose moving-camera flicker

White stripes or crawling patterns that change with camera motion often indicate competing depth surfaces. Distinguish these from a deliberately striped texture or shadow-map artifacts.

1. Inspect both loaded geometry and viewer-created meshes. Check duplicate floor faces/slabs, a ground plane intersecting the model, and overlapping room boundaries. Temporarily isolating a suspected surface can identify the cause.
2. Remove redundant geometry or correct the intersection. Do not use polygon offset, transparency or a large lift as the first substitute for a structurally correct scene.
3. Fit camera near/far planes to the scene. An unnecessarily tiny near plane and very large far plane waste depth precision. For one meter-scale house, `near = 0.1` and `far = 200` can be a starting point, not universal constants. Account for the model bounds, allowed orbit distance, close-ups and panorama sphere radius. Restrict excessive orbit distance or adapt the range if necessary.
4. Update depth-based postprocessing when camera projection changes. Some SSAO passes cache projection/inverse-projection matrices and near/far uniforms. Synchronize those when changing FOV, clipping range, projection type or mode; do not assume an installed library updates them every frame.
5. Verify normal, low-angle and zoomed-out orbits in the target viewer. Check both saved and new model versions where applicable, then enter and return from a panorama. Save a representative result, but do not claim motion stability from one still alone.

For shadow acne, inspect light shadow bounds, map resolution, bias and normal bias separately. Depth precision fixes and shadow bias solve different problems; excessive bias can detach contact shadows.

## Cutaways and lighting

- Group trim and attached parts coherently so camera-dependent hiding does not leave isolated headers. Do not toggle each submesh solely by its own center if it belongs to one opening.
- Keep visual cutaways separate from the actual structural model and export. Provide full-wall inspection when useful.
- Environment reflections, shadows and restrained ambient occlusion improve material readability. Verify antialiasing after adding a postprocessing composer; renderer antialiasing alone may not cover intermediate targets.
- Render on demand when idle where feasible. Invalidate for asset loads, resize, camera changes, UI changes, model switches, panorama loads and video seek/playback. Continue frames through damping and transitions. A stale frame after a mode change is a functional bug, not an optimization.

## Checkpoint placement and transitions

Prefer one or two central, unobstructed captures per room for the dollhouse when the user wants a concise overview. Choose from actual capture locations. For concave or long rooms, a simple vertex-average centroid can lie outside the usable interior; use an interior point, distance-to-wall criterion or representative capture medoid and visually inspect the choice. Do not move a photographic checkpoint to an invented camera position just to center the marker.

Keep the full capture sequence accessible via thumbnails or Previous/Next controls. Directional arrows should refer to valid same-room paths or verified doorway connections. Do not connect nearby points through walls, stair voids or unverified room adjacency. Mesh distance alone is not a navigation graph.

Project arrows with the correct source-camera orientation. Confirm that a visible doorway and its destination arrow agree. Preserve world heading across captures only when relative camera orientation is known. Avoid excessive overlapping arrows; screen-space filtering can simplify the display without deleting captures.

Transition from an orbit view toward the selected capture, then switch to the corresponding panorama. Preserve the prior orbit for return, respect reduced-motion preferences, and keep the currently selected capture correct through asynchronous texture loads. Explicitly handle failed loads and rapid repeated navigation.

Keep these modes distinct:

| Component | What the user is seeing |
| --- | --- |
| Dollhouse | Authored/reconstructed geometry with its stated accuracy |
| Captured panorama | An original photographic viewpoint |
| Novel-view video/splat scene | Synthesized views with possible blur, ghosting or disocclusion artifacts |

A fade or camera animation between photographs is not continuous reconstructed motion. Avoid UI claims that imply otherwise.

## Verify and hand off

Check loading, orbit/zoom, cutaways, version switching, marker selection, panorama stepping, return-to-model and any video controls affected by the change. Inspect console errors and the actual rendered result. Verify resolution/frame decoding for newly produced videos; do not rerun unchanged expensive inference just to fix a viewer.

If publication is in scope, use the existing site's supported workflow and preserve its audience. Confirm successful deployment before claiming the live site is fixed; if a publish request times out, reconcile saved versions/deployments before retrying. Do not change sharing or use a different account to work around a failure. Local-only modeling tasks need no hosting workflow.
