# Agent Instructions

This repository keeps the active CP2K LSP branch on `develop`.

## LLM Wiki

- Start with `index.md` for the knowledge map and `log.md` for recent changes.
- Keep durable knowledge under `wiki/entities`, `wiki/concepts`, and `wiki/synthesis`.
- Keep original evidence under `raw/assets` only when it is small and representative.
- Do not vendor large manuals, generated registries, or large logs into `raw/assets`; link them from `sources/` or use an existing tracked project file instead.
- Every durable claim should be traceable to a `sources/cp2k/*.json` entry, a `raw/assets/*` evidence file, or an existing project source file.

## Verification

Run this before changing wiki or source manifest content:

```bash
python scripts/wiki_lint.py
```

For runtime LSP changes, also run the repo-supported Python gate:

```bash
ruff check .
mypy cp2k_input_tools packages/language-server/cp2k_lsp
pytest
```

## Boundaries

- Preserve unrelated local changes.
- Add focused fixtures for behavior changes.
- Prefer narrow PRs that close one GitHub issue with explicit evidence.
