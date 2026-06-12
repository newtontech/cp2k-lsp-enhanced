---
applyTo: "**/*.py,tests/**/*.py,packages/language-server/**/*.py,cp2k_input_tools/**/*.py"
---

# Python and pytest TDD instructions

- Add or update tests before behavior-changing Python code.
- Prefer small pytest tests with plain `assert` so pytest can show useful failure details.
- For parser and LSP behavior, assert deterministic outputs: diagnostics, labels, ranges, JSON keys, enum values, or rendered text.
- Use fixtures only when they reduce duplication or clarify state.
- Keep default tests offline and independent of external CP2K runs.
- Prefer targeted commands first, for example `poetry run pytest tests/test_enhanced_parser_grammar.py -q`, then run broader PR-class checks.
- When changing public CLI or LSP behavior, add regression tests that would fail on the previous implementation.
