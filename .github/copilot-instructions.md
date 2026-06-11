# GitHub Copilot instructions

Read `AGENTS.md` first; it is the source of truth for TDD, validation, and agent workflow in this repository.

## Codebase map

- `cp2k_input_tools/`: canonical CP2K input parsing, linting, conversion, and CLI implementation.
- `packages/language-server/cp2k_lsp/`: enhanced CP2K LSP implementation, including parser, diagnostics, completion, hover, formatting, code actions, and agent-facing APIs.
- `tests/`: pytest tests. Add or update tests before behavior changes.
- `.github/workflows/test.yml`: CI uses Poetry, ruff, mypy, pytest, package smoke checks, extras smoke checks, and enhanced LSP smoke tests.

## TDD workflow

For behavior-changing work, follow red-green-refactor:

1. Add or update the failing test first.
2. Run the smallest targeted pytest command and record the failure.
3. Implement the minimal production change.
4. Re-run the targeted test and then the relevant PR-class checks.
5. Include test evidence in the PR body.

Docs/templates-only changes may state `TDD exception: docs/templates only`.

## Preferred commands

```bash
poetry install --with dev -E yaml -E lsp
poetry run pytest tests/<target_test_file>.py -q
poetry run ruff check .
poetry run mypy cp2k_input_tools packages/language-server/cp2k_lsp --ignore-missing-imports
poetry check
```

Full pytest command used by CI:

```bash
poetry run pytest --cov-report=term-missing --cov-fail-under=40 --cov=cp2k_input_tools tests/
```

## CP2K/LSP guardrails

- Do not invent CP2K semantics when schema/manual data is absent.
- Keep parser, diagnostics, completion, hover, formatting, code actions, and agent APIs deterministic.
- Do not require an external CP2K solver in default tests.
- Preserve separation between `cp2k_input_tools` and `cp2k_lsp` unless the issue explicitly asks otherwise.
- If language-server behavior, parser validation, command names, file detection, or fixtures change, update README/OpenQC notes or open an alignment issue.

## Pull request expectations

Open small PRs linked to a GitHub issue. Include failing-test evidence, passing-test evidence, broader validation commands or CI evidence, dependency notes, and OpenQC alignment impact.
