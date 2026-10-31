# Hero / font audit — 2026-10-31

## Observed

- `web/assets/hero.jpg`: copied from the user-supplied Aigocy `assets/images/section/hero-1.jpg`. Still active in `.hero` and `.closing`. No original author/license document supplied, so permission for production reuse remains unverified.
- `EX5MuYyeX2ow.woff2`, `vxO6gC8PjDdn.woff2`: embedded font metadata identifies Urbanist and Copyright 2021 The Urbanist Project Authors. SIL OFL 1.1 verified against the official Google Fonts repository and bundled as Urbanist-OFL.txt. FontTools cmap check shows missing Vietnamese letters (including đ, ơ, ư and many tone-marked vowels); fallback font mixing explains visual differences between EN and VI.
- Active replacement: unmodified upstream Manrope variable TTF from google/fonts, 164700 bytes, axis wght 200–800, all checked Vietnamese characters present. Included Manrope-OFL.txt; copyright matches embedded metadata. Current source `assets/fonts.css` names Manrope for both languages, preserving the layout/weight structure.
- Apartment photos: existing Pexels assets with source/photographer/license already recorded in assets/SOURCES.md. They are illustration, not listings or a single verified property.

## Proposed hero replacement (not applied)

Recommendation if no Aigocy usage license is available: replace the external template background with the already-downloaded `apartment-light.jpg` under its documented Pexels license. Keep the foreground readable with an opaque light overlay. Approximate patch for integrator design review:

```css
.hero, .closing {
  background-image:
    linear-gradient(110deg, rgba(240,242,245,.96), rgba(240,242,245,.88)),
    url('assets/apartment-light.jpg');
}
```

This changes the red/silver reference artwork the user requested, so it is proposed rather than silently applied. Existing asset can remain in source for traceability but should be excluded from a release if its rights remain unresolved. No file deletion or build exclusion performed here.

No paid services or generated assets. Font change fixes bilingual typography; no assistant/API/backend changes.
