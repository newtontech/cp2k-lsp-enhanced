# Invalid CP2K input fixtures

Canonical **invalid** fixtures referenced by `lsp-capabilities.json` → `fixturePaths.invalid`.

| Fixture | Expected |
|---------|----------|
| `blocking_misspelled_keyword.inp` | Blocking error (unknown/misspelled keyword) |
| `warning_low_cutoff.inp` | Non-blocking warning (configuration smell) |

Mutation goldens under `tests/fixtures/mutations/` remain the regression source of truth.
