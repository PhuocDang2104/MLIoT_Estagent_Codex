# Landing extension acceptance

Base: `4cec440`. Scope: additive landing content only; no production rollout.

The existing hero, Seoul media links, three-step section and footer are identical
to the base. The original JavaScript and CSS remain unchanged prefixes. The two
architecture PNGs are byte-for-byte copies of the user-supplied files in `docs/`.
Hashes and browser results are recorded in `browser.json`.

- `scripts/gate.sh web --strict`: PASS lint, test, build and contract validation.
- Chromium: PASS at 1440, 1024, 768, 390 and 320 CSS pixels; no horizontal overflow.
- Creator/Visitor tabs: click, arrow keys and Home; selected state and panel visibility.
- Both original diagrams: load on demand, native dialog, close button, Escape,
  focus restoration and scroll unlock.
- Mobile menu, reduced motion and JavaScript-disabled reading: PASS.
- Browser page errors: 0. Provider calls and production writes: 0.

Screenshots show the desktop and mobile Creator/Visitor layouts and diagram dialog.
The full diagrams are described as architecture direction; PostgreSQL, Maps and
market data remain labelled as planned connections.

The repeatable browser check uses local file routes and disables WebGL to isolate
the new UI. Real Seoul rendering/rotation is outside this check; preservation is
verified from source. An earlier read-only public sample check encountered HTTP 502.
No backend, configuration or production service was changed for this task.

To repeat, install Playwright/Chromium in an external QA environment and run:

```sh
python docs/evidence/landing-architecture/verify_browser.py
```

`ESTAGENT_CHROMIUM` may point to an existing Chromium executable. The harness
intercepts all browser requests locally and rejects non-GET/HEAD methods.
