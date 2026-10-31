# English demo defaults

User authorization: preload the eight supplied Seoul panoramas when starting a new tour and make the displayed interface English. Continue the already authorized production integration and release workflow.

Paths: web/, server/ (user-facing messages and locale defaults), tests/, docs/, deploy/evidence/. No schema changes or new dependencies. Preserve source panorama identities, existing drafts and published data. Do not start AI, create a project, or upload files until the user saves. Custom uploads replace the stock selection; every stock image remains removable.

OpenAI: no provider calls needed for this task. Existing model choices and spending/admission limits remain in effect. English is the default for new content, not a destructive translation of stored user content.

Validation: strict web gate, affected backend tests, real browser checks for prefill, custom replacement, cancellation, existing drafts, English UI with a stale Vietnamese preference, and public release verification. Use source sample files already supplied by the user; no fabricated room imagery. Codex assisted this implementation; no claim about competition timing.
