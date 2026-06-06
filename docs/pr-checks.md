# PR Checks and Merge Gate

This repository uses a typed PR gate: each pull request is classified, checked
with the matching test set, reviewed in parallel, and merged only when the
blocking signals are clear.

## PR Classes

| PR class | Required checks |
| --- | --- |
| `bugfix` | Regression test, related module tests, full pytest matrix, ruff, mypy |
| `feature` | New unit tests, related CLI/parser/LSP integration tests, coverage gate |
| `test-only` | Target tests, at least one full pytest run, no assertion-removal or unexplained skip/xfail |
| `dependency/CI` | Full Python matrix, extras smoke tests, `poetry check`, `poetry build` |
| `large LSP enhancement` | LSP open/change/close, diagnostics severity/code/range, multi-document behavior, CLI subprocess smoke, stable async waits |

## Required CI Jobs

Every merge-ready PR must pass:

- `quality`: `poetry check`, `ruff check .`, and `mypy cp2k_input_tools`
- `pytest`: Python 3.10, 3.11, and 3.12 with coverage reporting and the current baseline threshold
- `extras-smoke`: no extras, `yaml`, `lsp`, and `yaml+lsp` install smoke checks
- `package-smoke`: build the wheel, install it in a clean venv, and smoke-check import plus console scripts

The coverage threshold is intentionally set to the current project baseline
first. Raise it only after the baseline has improved on `develop`.

## Parallel Review Lanes

Use subagents for independent review lanes when Codex multi-agent support is
available:

- `test-engineer`: coverage, CI gate, flaky-test risk
- `reviewer`: correctness, security, missing tests, request-changes decision
- `architect`: interfaces, parser/LSP contracts, long-term maintenance risk
- `verifier`: CI status, diff check, local verification evidence
- `git-master`: merge strategy, history hygiene, rebase/squash recommendation

The lanes should review the same PR independently and then synthesize one
deterministic merge decision.

## Merge Rules

Do not merge when any of these are true:

- A required CI job failed or did not run.
- A reviewer recommends `REQUEST CHANGES`.
- The architect lane reports `BLOCK`.
- The PR has conflicts.
- CI is stale and there is no verified merge result.
- The PR added behavior without corresponding tests.
- The PR introduces unexplained `skip` or `xfail` markers.

Small, low-risk PRs with green checks and no blockers should use
`rebase and merge` by default. Larger multi-commit feature PRs may use squash
when the commit history does not carry useful review context.

## Current PR Decisions

- PR #12, `fix/lsp-cli-import-safe`: merge-ready after checks; prefer
  `rebase and merge`. The CLI behavior tests cover import, help, and the missing
  `lsp` extra failure path.
- PR #4, `feat/issue-3-semantic-validation`: do not merge while conflicting.
  Resolve `cp2k_input_tools/ls.py` and `tests/test_basic.py`, clarify the LSP
  parser-to-validator contract, add LSP semantic diagnostic tests, and rerun the
  full gate before review.
