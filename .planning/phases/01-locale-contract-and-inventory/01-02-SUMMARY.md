# Phase 1 Plan 02 Summary

**Mirrored dependency-free locale runtime supplies complete English and Simplified Chinese catalogs, finite fallback, plain-text interpolation, and missing-key diagnostics.**

## Accomplishments

- Added byte-identical classic-browser `window.EaglerXI18n` assets to both web roots.
- Exposed `en` / `English` and `zh-CN` / `简体中文` catalogs with the shared preference key.
- Implemented active-locale to English to visible-marker lookup, one warning per missing key, and text-only named interpolation.
- Added Node VM-backed standard-library tests for metadata, coverage, fallback, diagnostics, interpolation, and byte parity.

## Files Created/Modified

- `web-1.8/admin-i18n.js` - Canonical browser-local locale runtime.
- `web-1.12/admin-i18n.js` - Byte-identical runtime mirror.
- `tests/test_regressions.py` - Runtime contract regression tests.

## Verification

- `node --check web-1.8/admin-i18n.js && node --check web-1.12/admin-i18n.js`
- `python3 -m unittest tests.test_regressions.I18nInventoryTests tests.test_regressions.I18nRuntimeTests -v` — 6 tests passed.
- `python3 -m unittest discover -s tests -p 'test_*.py'` — 21 tests passed.
- `cmp -s web-1.8/admin-i18n.js web-1.12/admin-i18n.js && cmp -s web-1.8/admin-i18n-inventory.json web-1.12/admin-i18n-inventory.json`
- Protected administration assets retain their original paired SHA-256 values.

## Commits

- `02165a4` - `feat: add browser i18n runtime`
- `121b5cd` - `test: cover browser i18n runtime`

## Deviations

None.

## Next Phase Readiness

Phase 1 execution is complete and awaits its separate verify-work stage.
