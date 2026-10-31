# Layout recovery and coordinate contracts

Read this when the plan is missing, camera poses are unknown, or the plan and photographs disagree.

## Inventory before solving

For each capture, retain its source path, original size, panorama projection type, known room/floor labels, known pose and any measurement. Do not assume that every wide photograph is a full, level, 2:1 equirectangular panorama. Cropping, stitching seams, pitch/roll and mirrored images can invalidate a naive layout estimate.

Separate the questions:

| Quantity | Useful evidence | If unresolved |
| --- | --- | --- |
| Room-local footprint | Wall-floor/ceiling boundaries, corners, layout annotations, calibrated depth | Produce a labeled approximate local outline |
| Metric scale | A reliable wall length, plan dimension, measured camera height, or calibrated depth | Keep scale relative or explicitly assumed; ask for a measurement if metric output matters |
| Camera heading | Known pose, window/door bearings, repeated landmarks | Preserve an unknown yaw rather than silently aligning unrelated views |
| Room adjacency | A shared doorway seen from both sides, walk sequence, plan or user confirmation | Keep an unresolved connection in the manifest |
| Global room placement | Multiple shared constraints and consistent scale | Keep room models separate until registration is supported |
| Floor elevation | Floor labels, stairs and measured level changes | Do not flatten multiple floors into one plane |

## With a floorplan

- Extract the scale or ask for one dimension. A screen image's pixel size does not establish meters.
- Identify whether lines represent wall centerlines, inner faces or outer faces. Wall thickness must not shrink usable rooms or double shared partitions accidentally.
- Align using identifiable openings and corners. Use more than a single match when available so orientation, reflection and scale errors become visible.
- Check the plan against panoramas. A marketing plan can be outdated or schematic. Keep disputed geometry provisional rather than silently distorting the photos or plan to force agreement.
- Preserve nonrectangular rooms. Manhattan/right-angle assumptions are conveniences only when supported by the house.

## Without a floorplan

1. **Infer local rooms.** Inspect each panorama's wall boundaries, openings and visible structural corners. Ceiling/floor boundaries, available depth estimates and calibrated multi-view reconstruction can support a local shell. Treat occluded walls and automatic predictions as hypotheses requiring review.
2. **Establish scale.** A single panorama does not determine absolute room scale by itself. Use supplied measurements or measured camera height when its ground-plane assumptions hold. A standard-looking door or cabinet is only a weak size prior, not a measurement. If the user accepts an illustrative model, record the assumed scale explicitly.
3. **Register overlapping captures within a room.** Use repeatable structural features and known poses where available. Check that camera locations lie within the room and that projected doorway/window bearings match the photographs. A convincing local room does not prove the entire house is registered correctly.
4. **Build the connectivity graph.** Link rooms through confirmed shared openings or documented capture sequence. Use multiple constraints where possible; featureless walls, mirrors and repeated doors make isolated visual matches ambiguous. Maintain unresolved edges instead of guessing hallways or room order.
5. **Assemble a provisional top-down plan.** Show room outlines, confirmed connections, uncertain boundaries and scale status. Ask a focused question when the answer changes topology or dimensional accuracy. Continue valid local modeling while waiting.

Useful clarification examples:

- "Does the doorway beside the kitchen counter lead to the hall or the bedroom?"
- "What is the length of this wall, or the camera's measured height? One reliable dimension will establish scale."
- "Are these captures on the same floor, and do you know their walking order?"

Ask for another panorama, a rough sketch or a floorplan only when the current evidence cannot resolve the needed fact. If such a file is needed, request it through the normal user-facing channel; a text-only question tool cannot receive an upload.

Do not manufacture unseen rooms to make a complete-looking footprint. If there is no visual overlap or adjacency evidence, separate room models with unresolved placement are a valid intermediate deliverable. Pause only the dependent assembly step, not all useful work.

## Keep coordinate transforms explicit

Choose one documented world convention, such as meters with Y up, and record each input-to-world transform. Preserve supplied calibrated poses unless a justified conversion is required. Do not change camera calibration to hide a scale mismatch.

For an X-right/Y-up application with an XZ floor plane, one explicit Blender mapping is `(x, y, z) -> (x, -z, y)`. Treat this as an example convention, not a universal dataset transform. Account for Blender/glTF export axis conversion exactly once.

Record whether a pose is camera-to-world or world-to-camera, the camera forward axis and panorama longitude/latitude origin. Test transforms with one room corner and one visible doorway before converting the whole dataset. Verify determinant/handedness, units and floor elevation, and compare export bounds to input bounds.

When changing between panoramas, preserve the world heading by transforming the current local viewing ray through the source pose and into the destination pose. With unknown relative yaw, retain an explicit limitation or a user-calibrated heading instead of claiming heading preservation.

## Minimal evidence record

Reuse the project's manifest when it already stores these concepts. A useful fixture entry is:

```json
{
  "id": "kitchen_sink",
  "roomId": "kitchen",
  "evidenceStatus": "observed",
  "sourceCaptureIds": ["capture_07", "capture_08"],
  "geometryAccuracy": "approximate",
  "notes": "Two bowls and one shared faucet visible; dimensions estimated"
}
```

For an inferred wall or proposed furnishing, use the corresponding evidence status and record the assumption. Source IDs establish traceability; they do not by themselves establish accurate geometry.
