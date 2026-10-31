<div align="center">

<img src="web/assets/favicon.svg" width="72" height="72" alt="Estagent logo" />

# Estagent

### See the space. Understand the place.

Property tours built with spatial context, guided narration and conversational AI.

<p><strong><a href="https://estagent.duckdns.org">Explore the demo</a> · <a href="docs/PRODUCT-OVERVIEW.md">Giới thiệu sản phẩm</a> · <a href="#quick-start">Quick start</a> · <a href="#architecture">Architecture</a> · <a href="docs/DEPLOYMENT.md">Deployment</a></strong></p>

<p><code>OpenAI</code> &nbsp; <code>LangGraph</code> &nbsp; <code>Blender</code> &nbsp; <code>Three.js</code> &nbsp; <code>FastAPI</code> &nbsp; <code>MinIO</code></p>

</div>

---

Estagent helps people understand a property before deciding to visit. Creators turn photos,
panoramas and property information into a reviewed tour. Visitors explore the space, listen
to its story and ask questions about the room they are viewing.

| Create with context | Explore with confidence |
| :--- | :--- |
| Upload captures and an optional floorplan. Clarify the AI layout, review the model and refine the narration. | Move between a 3D dollhouse and panorama checkpoints, follow guided audio and ask about approved property information. |
| **Creator / Business Studio** | **Viewer / Rental seeker** |

## From captures to a conversation

1. **Bring the evidence.** Add property photos or panoramas, a description and an optional floorplan.
2. **Shape the space.** OpenAI helps organize the captures into a structured scene plan. The Creator clarifies and approves the layout before Blender builds the model.
3. **Tell the story.** Review narration and navigation, generate speech, then publish a shareable tour.
4. **Explore and ask.** Visitors inspect the dollhouse, enter panorama checkpoints and ask questions grounded in the published tour.

### What makes Estagent different

- **A tour you can discuss.** Questions use the active checkpoint and approved tour context; supported navigation targets are checked by the backend.
- **A Creator who stays in control.** Layout and content reviews are explicit. Natural-language edit proposals create a new generation after confirmation.
- **A workflow that can resume.** LangGraph checkpoints, a SQLite outbox, request deduplication and version history preserve progress across interruptions.
- **One OpenAI foundation.** Planning, vision, text, speech and visitor assistance use backend OpenAI integrations with configurable model roles.
- **A published version that stays stable.** Later draft edits do not rewrite an already published snapshot.
- **Private media, deliberate publication.** Local storage or private MinIO holds assets; public access is limited to assets referenced by a published tour.

## Architecture

The two diagrams below describe the **product architecture direction**. The implementation
status table separates the current runtime from the integrations shown as future capabilities.

### 01 · Tour generation

[![OpenAI and LangGraph architecture for property tour generation](docs/Langgraph%20Tour%20Generation%20OpenAI%20Architecture.png)](docs/Langgraph%20Tour%20Generation%20OpenAI%20Architecture.png)

**Creator input → scene understanding → spatial review → model building → narration and navigation → publication.**

Today's Studio runs a checkpointed graph with human reviews and a validated scene plan.
The local Blender worker authors a textured, single-floor model; Three.js renders the
dollhouse and its capture markers. This is approximate authored geometry, not metric
photogrammetry. Blender MCP and external enrichment in the diagram are extension points.

[Runtime flow and Mermaid](docs/Business%20Workflow%20Langgraph/Estagent_Business_LangGraph_Flow.md) ·
[House-modeling implementation](docs/HOUSE-MODELING-AGENT.md)

### 02 · Spatial context assistant

[![Customer assistant architecture with spatial context and retrieval](docs/Langgraph%20Rag%20Spatial%20Context%20Assistant.png)](docs/Langgraph%20Rag%20Spatial%20Context%20Assistant.png)

**Question + viewing context → relevant evidence → grounded response → supported viewer action.**

The current assistant uses approved tour data, the selected scene or checkpoint and bounded
conversation context. The diagram extends that foundation toward hybrid retrieval, a spatial
knowledge hub and external tools. PostgreSQL, BM25/vector retrieval, Maps and market-data
connectors shown here are architecture goals, not claims that these services are connected today.

[Creator and Viewer chat](docs/CHAT-FLOW-HANDOFF.md) ·
[Product writeup and roadmap](docs/PRODUCT-OVERVIEW.md)

### Implementation at a glance

| Capability | Current implementation |
| :--- | :--- |
| AI tour generation | OpenAI scene planning, clarification, spatial/content approval and a local Blender builder |
| Immersive exploration | Three.js dollhouse, selectable capture markers and panorama checkpoints |
| Narration and audio | Reviewed OpenAI TTS in Studio; uploaded narration/music and guided playback in photo tours |
| Conversational editing | Confirmed Studio proposals, selective regeneration and immutable published versions |
| Customer assistance | Published-tour Q&A, active scene/checkpoint context and validated navigation |
| Media and exports | Private MinIO or local media; metadata/audio/video export paths depend on the tour flow and enabled renderer |
| Broader spatial RAG | PostgreSQL knowledge hub, hybrid search and external intelligence remain planned |

Video export currently renders the supported photo/panorama tour flow; it is not a cinematic
render of the generated 3D house. A complete automated live house-generation benchmark is
separate from the recorded provider-connectivity, Blender and browser checks.

## Quick start

**Requirements:** Python 3.13, [uv](https://docs.astral.sh/uv/), and Bash.
Use Git Bash or WSL on Windows. Blender is needed for local Studio model generation;
Node.js is needed for frontend checks, and FFmpeg for its supported video-export mode.

```bash
git clone https://github.com/PhuocDang2104/MLIoT_Estagent_Codex.git
cd MLIoT_Estagent_Codex
bash scripts/dev.sh
```

Open **http://127.0.0.1:5180/**. The frontend, APIs and assets share one origin.
The script resolves pinned Python dependencies; it does not load an `.env` file automatically.

| Entry | Purpose | Requirements |
| :--- | :--- | :--- |
| `/business/create` | AI / Blender Generation Studio | Uploads can be saved without a key; generation needs OpenAI and an available geometry worker |
| `/business/photos` | Photo-tour editor | Upload, edit, preview and publish visual tours without an LLM; AI chat needs OpenAI |
| `/viewer.html` | Published tour library | Explore available published tours and demos |

Start with the photo-tour editor for a local visual walkthrough. For generation, configure
the backend environment using [`.env.example`](.env.example) and follow
[Studio setup](docs/HOUSE-MODELING-AGENT.md). `STUDIO_BLENDER_EXECUTABLE` selects an explicit
Blender executable when needed. Provider keys stay on the backend; starting generation,
chatting or requesting generated narration can make paid API calls when enabled.

<details>
<summary><strong>Runtime and operating notes</strong></summary>

- Keep one API process on a dedicated local data volume. This runtime is not a distributed queue.
- Creator drafts belong to a cookie session. The MVP does not implement account login.
- Published snapshots are shared deliberately; keep the Creator cookie to retain private draft access.
- Model roles, admission limits, storage limits and optional capabilities are configured through the backend environment.
- Missing evidence stays unknown. Approximate layouts and source limitations should remain visible to reviewers.
- Production releases use an accepted source SHA, isolated secrets, preserved media and database backups.

See the [runtime contract](docs/STUDIO-RUNTIME.md), [SSH/deploy guide](docs/STUDIO-DEPLOY.md)
and [current release record](docs/STUDIO-SEOUL-RELEASE.md). The live deployment and the latest
repository commit may differ.

</details>

## Development checks

These checks use synthetic fixtures and mocked provider transports rather than paid model requests.

```bash
npm --prefix web run lint
npm --prefix web test
npm --prefix web run build

uv run --python 3.13 --with pytest --with jsonschema \
  --with-requirements server/assistant/requirements.txt \
  python -m pytest tests/ai tests/deploy -q

bash scripts/gate.sh all --strict
python3 scripts/check_commit_attribution.py --all
```

The full gate also qualifies the core pipeline. Blender-specific checks need a compatible
Blender installation; consult the [house-modeling handoff](docs/HOUSE-MODELING-AGENT.md)
and [release verification](docs/STUDIO-SEOUL-RELEASE.md) for the tested environments.

## Find your way around

| Read about… | Start here |
| :--- | :--- |
| Product, audience and user journeys | [Giới thiệu sản phẩm](docs/PRODUCT-OVERVIEW.md) · [User views](docs/USER-VIEWS.md) |
| LangGraph and model generation | [Runtime flow](docs/Business%20Workflow%20Langgraph/Estagent_Business_LangGraph_Flow.md) · [House modeling](docs/HOUSE-MODELING-AGENT.md) |
| API boundaries and conversations | [Contracts](docs/CONTRACTS.md) · [Chat context](docs/CHAT-FLOW-HANDOFF.md) |
| Audio, video and private storage | [Audio](docs/AUDIO-HANDOFF.md) · [Video export](docs/VIDEO-EXPORT-HANDOFF.md) · [MinIO](docs/MINIO-INTEGRATION-HANDOFF.md) |
| Running and releasing the product | [Deployment](docs/DEPLOYMENT.md) · [Studio SSH/deploy](docs/STUDIO-DEPLOY.md) · [Rollback](docs/ROLLBACK-SAFETY.md) |
| Contributing and source provenance | [Agent instructions](AGENTS.md) · [Source/build declaration](docs/DECLARATION.md) · [Asset sources](web/assets/SOURCES.md) |

<div align="center">

<sub>Built by the MLIoT Estagent team · Evidence before assumptions. Review before publication.</sub>

</div>
