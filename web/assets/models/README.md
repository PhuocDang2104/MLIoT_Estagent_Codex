# Landing demo-house preview

Thai corrected the target: use the **actual demo home's dollhouse**, not the illustrative office tower. `building-preview.js` reads `/api/demos/zind-house-000/assets/house/manifest.json` and then its existing `dollhouse.url`. The previous `sunrise-office.glb` copy is removed.

The model remains in the existing demo asset service; no GLB, embedded textures, panoramas or screenshots are committed here. The currently served model is `house/dollhouse-studio.glb`: 876 meshes, 116784 triangles, 13 materials and 12 embedded base/normal images. Built from existing ZInD layout annotations, with approximate built-in fixture dimensions and positions. This change does not regenerate geometry or make a new rights claim; source disclosure stays on the demo tour.

The native WebGL preview preserves all scene geometry, node transforms (TRS/matrix), base colors, embedded base-color textures and double-sided materials. It uses simplified directional lighting, without the full demo renderer's normal-map/PBR postprocessing. An elevated camera exposes the floor plan. It is a narrow loader for the supplied opaque static GLB, not a generic glTF runtime. Existing exported function and canvas IDs retained for compatibility.

New Codex-assisted frontend adaptation; cached demo model predates this change; competition H0 unverified. No new dependency, provider call, paid generation or upload. The prior office-model illustration was a mistaken interpretation and is superseded.
