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

## Next Testing Work

- Replace fragile LSP sleeps with deterministic waiting.
- Keep `cp2k-language-server` covered by wheel and subprocess smoke tests.
- Add LSP semantic diagnostic tests for severity, code, range, and line number.
- Raise the coverage gate after `develop` improves beyond the current baseline.
