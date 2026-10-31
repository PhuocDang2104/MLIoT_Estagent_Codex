# Seoul furnished sample

User-supplied `seoul-floorplan-and-model.zip`, SHA-256
`254d6bc4a53ac452e07247b05b1418066f7ad4546a072e0ed1325a099e5b8d58`.
This is a premade furnished scene recovered from a matching companion model,
not evidence of a new panorama-only reconstruction. Scale remains approximate.
Furniture/materials are preserved; no added furniture or panorama projection.

Source dollhouse GLB: 115,265,812 bytes. Web derivative uses glTF Transform
4.5.0 `meshopt` with position 16 / normal 12 / texcoord 14 bit quantization.
No simplification. All 27 embedded images retained. Tiled UVs outside [0,1]
remain unquantized. Meshoptimizer decoder 1.2.0 is vendored with MIT license.
The original ZIP/Blender/GLB files remain unchanged outside Git.

The source GLB has five invalid texture references across four materials with
UV index -1. `deploy/repair_seoul_uv.mjs` assigns planar UVs to the five affected
primitives before compression. This is an approximate texture-coordinate repair,
not geometry reconstruction. Khronos validation reports zero errors after repair
(nine tangent-generation warnings remain). Original and derivative both retain
111 meshes and 1,686,672 triangles. Actual Three.js decoding is also checked,
since the validator does not decode EXT_meshopt_compression.

`deploy/prepare_seoul.py` verifies the pinned ZIP, member hashes and eight original
panorama hashes, ignores source absolute paths, and emits a sanitized manifest,
12 public assets and a content-addressed MinIO catalog. Pass an explicit local
panorama directory; source paths and authoring scripts are never served.
Keep this output outside the repository. Upload only catalog-listed files into
the existing private bucket under `demos/seoul-apartment/{sha256}/{name}`, with
`sha256` object metadata. Verify remote bytes before enabling the catalog.

Set `SEOUL_CATALOG_DIR` to the directory containing catalog.json and
`SEOUL_CATALOG_PATH=/seoul-catalog/catalog.json`. No Studio generation/upload cap
is relaxed. The old ZInD catalog remains separately pinned and unchanged.
The sample appears at `/demos/seoul-apartment` and in `/viewer.html`.

Blender positions convert exactly `(x,y,z) -> (x,z,-y)` for glTF. Five selected
central capture positions appear on the dollhouse; all eight originals are
accessible through the panorama selector and previous/next buttons. Sequence
navigation makes no claim of a traversable straight path between captures.
Room labels are six functional zones, not six enclosed rooms. Floorplan retains
source camera labels. Source-camera Euler orientation is preserved in the public
manifest; panoramas initially show their image center. The premade sample has no
generated narration or music.
