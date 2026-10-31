---
name: house-modeling
description: Build or refine editable 3D house models and architectural dollhouse views from panoramas, floorplans, photos, or layout annotations. Recover a provisional layout when no plan is supplied, model source-visible fixtures and materials, and validate exported geometry and optional panorama-tour viewers. Use for reconstructing an existing home or designing a requested variation; not for generic website styling or standalone image generation.
---

# House Modeling

Create a coherent, editable house model whose geometry, materials and furnishings can be traced to the supplied evidence. Use reference renders as a quality target; distinguish their styling from facts about the actual house.

## Establish the evidence and deliverable

When invoked inside Estagent Creator Studio, read [studio-agent.md](references/studio-agent.md).
It defines the bounded HousePlan output, review/clarification flow and fixed Blender
builder interface. The application loads this skill and that template as trusted
planner instructions; it does not grant the planner arbitrary code execution.

- Inspect the available panoramas, plan, annotations, camera poses, dimensions and existing project before choosing a reconstruction route. Build a small capture inventory or contact sheet; inspect details in the original images rather than relying only on thumbnails.
- Identify house, floor, room and capture IDs. Do not combine unrelated homes or treat a multi-view subset as a complete house. Preserve source resolution separately from render resolution.
- Infer the requested output from context: editable model, portable GLB, architectural stills, interactive dollhouse, panorama navigation, or a combination. Building geometry does not automatically require a website, neural rendering, a cloud GPU, or publication.
- For an existing project, preserve its coordinate system and working viewer. Before a substantial model redesign, save a recoverable scene/source snapshot and work in a separate revision. A normal source revision is sufficient for a small viewer fix.

## Choose the layout route

**A plan or metric annotations are available:** recover room outlines, heights, openings and floor levels; reconcile them with the photographs. Verify plan scale and orientation using known dimensions and identifiable doors/windows. Resolve material contradictions before committing to detailed geometry.

**Panoramas are available but no plan:** attempt a provisional reconstruction before asking for a complete plan. Read [layout-recovery.md](references/layout-recovery.md) for room-local inference, cross-room registration, scale ambiguity and targeted questions. Continue independently supported rooms while uncertain connections remain unresolved. Never present an invented connection or assumed dimension as measured.

**Only a plan or design brief is available:** build the supported shell. Ask about or explicitly label proposed furnishings and finishes if they matter to the requested design. A staged design is a different evidentiary claim from a reconstruction.

Record a compact scene manifest alongside the model: units/axes, room polygons and heights, opening locations, capture IDs and poses if known, material regions, fixture evidence, and unresolved assumptions. Adapt an existing schema rather than forcing a new one. Use separate fields for evidence status (`observed`, `inferred`, `proposed`) and geometric accuracy (measured or approximate).

## Build from structure to detail

Read [blender-modeling.md](references/blender-modeling.md) when creating geometry, authoring materials, exporting or refining renders.

1. Establish the shell, floor levels, doors and windows. Compare a top-down blockout to the plan and source views before adding detail.
2. Inventory visible fixtures by room. In reconstruction mode, model supported cabinets, counters, appliances, sanitary fixtures, shelving and furniture; leave confirmed empty areas empty. Unseen does not mean absent: record uncertainty and request another view if that distinction changes the result. Do not add attractive staging unless the user asks for a design variation.
3. Author recognizable materials and physically plausible object shapes. Prefer reusable material textures to stretching entire panorama photographs across the shell. Use panorama projection only when it is an intentional, requested reconstruction technique, and identify its limitations.
4. Refine with matched overview and close-up renders. Look for geometric intersections, floating fixtures, wrong orientation, texture scale and lighting problems. Fix the largest demonstrated defect, render again and compare. Do not prescribe a fixed number of passes or claim reference-level fidelity from a successful export alone.

Keep source-supported reconstruction and proposed design changes separable in collections or scene metadata. Distinguish approximate authored furniture from measured or photogrammetric geometry.

## Add an interactive tour when requested

Read [interactive-viewer.md](references/interactive-viewer.md) for depth precision, cutaways, panorama orientation and checkpoint navigation. Preserve the user's existing stack and hosted site when applicable. Use an available hosting workflow for publication; this skill does not grant access to accounts, spending, or broader sharing.

For a concise dollhouse tour, start with one or two central, unobstructed checkpoints per room, keeping all captures reachable within the panorama view. Adapt that density to room geometry and the user's preference. A synthesized novel-view video, photographic panorama and authored mesh are different components; label and validate them separately.

## Completion evidence

- Check geometry coverage, units, finite bounds, fixture evidence, opening alignment and export materials. Inspect both the editable scene and the exported model; modifier application and shader export can change appearance.
- Review the whole house and the most detailed rooms, including kitchens and bathrooms when present. Inspect from more than one angle; a single flattering render can conceal missing support or collisions.
- For a viewer, orbit and zoom through affected views, switch model versions and enter/return from panoramas. A still image cannot establish that moving-camera artifacts are fixed.
- Verify the actual deliverable: successful build and deployed state for a site, decoded output and dimensions for a video, accessible files for a model. Report which checks were performed and any remaining reconstruction uncertainty.
- Deliver the editable scene and requested portable/rendered assets with the manifest and a clear preview. Preserve the prior version when promised. Clean up task-owned temporary processes when no longer needed; keep requested previews/services running and leave unrelated work alone.

If inputs cannot resolve the requested fidelity, deliver the supported provisional result and state the specific missing evidence. Further iterations should address observed issues or new evidence, not merely increase samples or decorate unsupported areas.
