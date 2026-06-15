# Valid CP2K input fixtures

Canonical **valid** fixtures referenced by `lsp-capabilities.json` → `fixturePaths.valid`.

Each file must stay clean under `cp2k-lsp-tool check` (no blocking diagnostics).

| Fixture | Role |
|---------|------|
| `valid_minimal.inp` | Minimal ENERGY calculation |
| `valid_geo_opt.inp` | Geometry optimization workflow |

Golden expectations live under `tests/fixtures/golden/`; these copies are the OpenQC gate paths.
