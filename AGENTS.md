# AGENTS.md

This is the repository-level source of truth for AI coding agents working on `newtontech/cp2k-lsp-enhanced`.

- Codex and GitHub coding agents should read this file directly.
- `CLAUDE.md` is intentionally a symlink to this file so Claude Code uses the same rules.
- GitHub Copilot also receives a compact copy in `.github/copilot-instructions.md` plus path-specific guidance in `.github/instructions/`.

## Repository map

- `cp2k_input_tools/`: canonical CP2K input parsing, conversion, linting, and CLI tools.
- `packages/language-server/cp2k_lsp/`: enhanced CP2K Language Server Protocol implementation, parser, diagnostics, hover, completion, formatting, code actions, and agent-facing APIs.
- `tests/`: pytest suite. Add or update tests here before changing behavior.
- `.github/workflows/test.yml`: CI gates for package metadata, ruff, mypy, pytest matrix, package smoke checks, extras smoke checks, and enhanced LSP smoke tests.
- `README.md`: user-facing commands and OpenQC alignment notes. Update or open an OpenQC alignment issue when changes affect language-server behavior, parser validation, command names, file detection, or fixtures.

## Setup and local commands

Prefer Poetry because CI uses Poetry.

```bash
poetry install --with dev -E yaml -E lsp
```

Targeted checks:

```bash
poetry run pytest tests/<target_test_file>.py -q
poetry run ruff check .
poetry run mypy cp2k_input_tools packages/language-server/cp2k_lsp --ignore-missing-imports
poetry check
```

Full PR-class checks:

```bash
poetry run pytest --cov-report=term-missing --cov-fail-under=40 --cov=cp2k_input_tools tests/
poetry run ruff check .
poetry run mypy cp2k_input_tools packages/language-server/cp2k_lsp --ignore-missing-imports
poetry check
```

Use the smallest targeted test first, then escalate to the full PR-class checks before marking work ready for review.

## TDD contract

All behavior-changing work must follow red-green-refactor.

1. **Red**: add or update a failing test that captures the issue or requested behavior before changing production code.
2. Run the smallest relevant test command and record the failure in the PR.
3. **Green**: implement the minimal production change needed to pass the test.
4. Run the targeted test again and record the passing command.
5. **Refactor**: clean up naming, duplication, and docs without changing behavior.
6. Run the relevant PR-class checks and paste the command summary into the PR.

Allowed exceptions:

- Documentation-only, template-only, or metadata-only PRs may state `TDD exception: docs/templates only` in the PR body.
- CI-only changes must include an explanation of the expected CI behavior and, when possible, a `workflow_dispatch` or pull request CI result.
- Do not add unexplained `skip`, `xfail`, or coverage exclusions. Explain every skip/xfail with the upstream issue or missing optional dependency.

## CP2K and LSP-specific rules

- Do not invent CP2K scientific semantics when schema/manual data is absent. Return structured not-found errors, diagnostics, or conservative fallbacks instead.
- Keep parser, diagnostics, completion, hover, code action, formatting, and agent-facing APIs deterministic.
- For completion/hover/diagnostic changes, add tests that assert labels/messages/ranges or JSON shapes directly.
- For parser changes, include representative valid and invalid CP2K input snippets.
- Do not require the external CP2K solver for default tests. Solver-backed checks must be optional and clearly marked.
- Preserve the separation between the canonical `cp2k_input_tools` parser and the enhanced `cp2k_lsp` parser unless the issue explicitly asks to bridge them.
- When adding agent-facing JSON APIs, keep output stable, serializable, and covered by schema-shape tests.

## GitHub AI-native workflow

Use GitHub issues as executable task specs.

Every implementation issue should include:

- problem statement and affected files;
- acceptance criteria;
- expected failing test or test fixture;
- targeted commands to run;
- non-goals and safety constraints;
- expected PR size or split points.

Every PR should include:

- linked issue, ideally `Fixes #...` only when fully closed;
- failing test evidence from the red step, or an explicit TDD exception;
- passing targeted test command;
- broader validation commands or CI evidence;
- notes about dependencies, generated files, external data, and OpenQC alignment impact.

Keep PRs small and reviewable. Prefer one coherent behavior change per PR. Split large LSP enhancements into schema/data, parser/context, feature behavior, tests, and documentation PRs.

## Agent operating rules

- Start by reading the issue, this file, the relevant source files, and the closest tests.
- Make a short plan before editing.
- Avoid broad rewrites unless the issue explicitly asks for a refactor.
- Do not add production dependencies without explaining why an existing dependency cannot satisfy the requirement.
- Do not commit secrets, tokens, large generated artifacts, solver outputs, cache directories, or local environment files.
- Keep `CLAUDE.md` as a symlink to `AGENTS.md`; do not replace it with a divergent copy unless maintainers explicitly request Claude-specific instructions.
- Use `CLAUDE.local.md` only for private local preferences and keep it out of commits.

## External references used for this convention

- OpenAI Codex AGENTS.md guide: https://developers.openai.com/codex/guides/agents-md
- OpenAI Codex best practices: https://developers.openai.com/codex/learn/best-practices
- Anthropic Claude Code memory / CLAUDE.md guide: https://code.claude.com/docs/en/memory
- GitHub Copilot repository custom instructions: https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions
- pytest assertion guidance: https://docs.pytest.org/en/stable/how-to/assert.html
- GitHub Actions Python build/test guide: https://docs.github.com/en/actions/tutorials/build-and-test-code/python
