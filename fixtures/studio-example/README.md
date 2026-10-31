# Synthetic Creator contract example

`studio-tour.json` is exported from real HTTP → LangGraph → SQLite execution using the
finite test provider and triangle worker in `tests/ai/creator_fixtures.py`.
It is a schema fixture, not a reconstructed property or a deployable cached tour.
Images are generated color PNGs, audio is generated silence, and geometry is one
synthetic triangle. Media stays in the test's temporary database and is not
distributed here; asset IDs in this JSON are references only.

Regenerate explicitly: `python -m tests.ai.export_creator_fixture`.
No external data/assets or paid OpenAI calls; no real property measurements.
