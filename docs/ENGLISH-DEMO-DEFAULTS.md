# Seoul input and English interface

The main Create tour entry (`/business/create`) preselects eight source Seoul
panoramas, with an editable demo name and description. Files retain the source
capture filenames and original bytes. The user can remove individual images,
clear them, reload the sample, or choose custom images to replace the stock set.
The sample's full-sphere coverage is confirmed from the supplied source data;
custom replacements reset this confirmation. No measured floorplan is implied.

Loading the sample does not create a project, upload files, generate geometry,
or call OpenAI. Saving uses the existing retry-safe upload path and credited
placeholder music. Generation and reviews remain explicit actions. Existing
drafts and published snapshots are preserved.

All application UI copy is English: Studio stages/reviews, errors, assistant,
viewer controls, cached demo shell and exports. Old Vietnamese interface
preferences no longer switch the demo UI. Content-language options use English
labels; English is the default for new Studio and photo tours. User-authored
content and existing tour recordings are not rewritten.

Validation uses supplied Seoul bytes and real local HTTP/SQLite uploads without
provider calls. The browser regression covers source hashes, eight previews,
removal/clear/custom replacement, failed and cancelled sample loads, upload
recovery, saved drafts, and English shells with a stale Vietnamese preference.
Run `tests.ai.run_english_demo_browser` against `tests.ai.upload_browser_server`;
set `SEOUL_SAMPLE_DIR`, `UPLOAD_QA_DIR`, optional `UPLOAD_QA_ORIGIN`, and
`CREATOR_QA_BROWSER`. Source data is user-provided and kept outside Git.

No dependencies, database migration, model-default changes or new API spend.
Release evidence will be recorded under `deploy/evidence/english-demo/`.
