# Source Manifests

`sources/` records where LLM Wiki facts come from. It is the durable provenance
layer for `wiki/` pages and complements the small evidence snapshots in
`raw/assets/`.

Each software/version manifest must:

- Follow `sources/manifest.schema.json`.
- Record `source_ref`, `kind`, `version`, and `confidence` for every source.
- Include `sha256` and `size_bytes` for repo-local files.
- Link large upstream manuals, generated registries, or large logs instead of
  copying them into `raw/assets/`.

Run `python scripts/wiki_lint.py` after editing `wiki/`, `raw/assets/`, or
`sources/`.
