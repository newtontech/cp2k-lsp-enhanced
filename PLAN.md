# Development Plan for cp2k-lsp-enhanced

## Current Focus

The active maintenance focus is PR quality control: classify every PR, run the
matching checks, gather parallel review evidence, and merge only when the gate is
green.

## PR Gate

See `docs/pr-checks.md` for the canonical PR matrix and merge rules.

Required checks:

- `quality`: package metadata, ruff, and mypy
- `pytest`: Python 3.10, 3.11, and 3.12 with coverage gate
- `extras-smoke`: no extras, `yaml`, `lsp`, and `yaml+lsp`
- `package-smoke`: wheel build and install smoke

## Current PR Decisions

- PR #12, `fix/lsp-cli-import-safe`: merge-ready after checks; prefer
  `rebase and merge`.
- PR #4, `feat/issue-3-semantic-validation`: blocked until conflicts are
  resolved, the LSP parser-to-validator contract is clarified, semantic LSP
  diagnostics are tested, and the full gate is rerun.

## Next Testing Work

- Replace fragile LSP sleeps with deterministic waiting.
- Restore or rewrite the `cp2k-language-server` subprocess smoke test.
- Add LSP semantic diagnostic tests for severity, code, range, and line number.
- Raise the coverage gate after `develop` improves beyond the current baseline.
