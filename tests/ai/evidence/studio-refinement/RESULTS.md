# Flow documentation and Studio refinement — 2026-10-31

Branch: `web/creator-studio-integrated`, baseline `150a4ea`.

- Web strict gate PASS: lint, 6 tests, static build, both existing schemas.
- AI strict gate PASS: compile, 30 tests, both existing schemas. Added real graph
  final-reject coverage: no TTS or publish after Business rejection.
- Mermaid 11.12.1 parsed/rendered Business, native and original reference diagrams
  on localhost. No remote image renderer. SVG/PNG and validation JSON are here.
- Actual StateGraph declarations: 12 processing nodes + START/END, 17 edges;
  both reject-to-END edges and image/audio loops retained. Source hash and the
  pinned compiled visualizer's differing edges are captured in graph-export.json.
- Downloads Markdown/Mermaid/native files match repository exports by SHA-256;
  original supplied diagram is preserved in `.reference.mmd`.
- Three browser runs PASS: absent worker/spatial review/reload, full fixture
  publish/Viewer/audio/Q&A, actual no-key application. No page errors.
- Desktop and mobile 390/320px: no horizontal overflow in creation/workspace;
  completed cards default collapsed, manual expansion persists across updates.
- Main site palette/brand reused: ink #292c2e, paper #ededed, accent #ed321e,
  Manrope and existing apartment photo. Inspiration image is explicitly labeled.

Backend route semantics/provider configuration and tour schemas are unchanged.
Explicit conditional path maps improve graph introspection; export reads declared
edges/branch maps to avoid the pinned get_graph() END visualization discrepancy.
No live OpenAI/Blender calls, new application dependencies or production rollout.
Core is still an independent known global strict-gate gap; this request only
pushes the feature branch.
