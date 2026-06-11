# Agent Workflow: LSP + CLI Verification Loop for CP2K Input Files

## Overview

This document describes how coding agents (Claude Code, OpenCode, Codex, and others) should use the CP2K LSP and CLI tools to create a fast, reliable edit-verify loop for CP2K input files.

## Feedback Layers

The CP2K tooling provides multiple feedback layers, each with different speed and accuracy characteristics:

| Layer | Tool | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| **LSP Diagnostics** | `cp2k-language-server` | <100ms | Syntax + Schema | Inline editing feedback |
| **CLI Lint** | `cp2klint` | <1s | Syntax | Quick pre-commit check |
| **CLI Validate** | `cp2k-lsp validate` | <1s | Syntax + Schema + Semantic | Pre-PR verification |
| **CP2K Dry-Run** | `cp2k-lsp validate --dry-run` | 10-60s | Full | Final verification |
| **CI / Tests** | `pytest`, `pre-commit` | 1-5min | Full | Gate merges |

**Key principle: LSP diagnostics are a short feedback layer, NOT final CI.** Agents should never skip CLI validation or CI just because LSP reports no errors.

## Recommended Edit Loop

```text
Plan
  → use hover/definition/references to understand symbols
  → edit one focused slice
  → read LSP diagnostics (instant feedback)
  → apply safe quick fixes
  → run cp2klint <file>          # fast syntax check
  → run cp2k-lsp validate <file>  # full semantic validation
  → run cp2k-lsp validate <file> --dry-run  # optional CP2K dry-run
  → run pre-commit                # formatting, linting
  → run tests/CI checks
  → review diff
```

## CLI Commands for Agents

### Inspect Diagnostics

```bash
cp2k-lsp inspect diagnostics input.inp
# Returns JSON with diagnostics array, error_count, warning_count

cp2k-lsp inspect diagnostics input.inp --fail-on-error
# Exits non-zero if any errors found (useful in scripts)
```

### Inspect Diagnostics Delta

```bash
# Before edit
cp2k-lsp inspect diagnostics input.inp > /tmp/before.json

# After edit
cp2k-lsp inspect diagnostics input.inp > /tmp/after.json

# Compare
cp2k-lsp inspect diagnostics-delta /tmp/before.json /tmp/after.json
# Returns: {before_count, after_count, fixed_count, new_count, unchanged_count}
```

### Inspect Hover

```bash
cp2k-lsp inspect hover input.inp --line 10 --character 4
# Returns: {name, line, position, contents}
```

### Inspect References

```bash
cp2k-lsp inspect references input.inp --line 5 --character 2
# Returns: {references: [{file, line, text}], count}
```

### Inspect Format Preview

```bash
cp2k-lsp inspect format-preview input.inp
# Returns: {formatted, file}

cp2k-lsp inspect format-preview input.inp --apply
# Returns: {status: "applied", file}
```

### Inspect Code Actions

```bash
cp2k-lsp inspect code-actions input.inp --line 10 --character 4
# Returns: {actions: [{title, kind, description}], count}
```

### Validate (Full Semantic Check)

```bash
cp2k-lsp validate input.inp
# Human-readable output

cp2k-lsp validate input.inp --json
# JSON output with structured diagnostics

cp2k-lsp validate input.inp --dry-run --cp2k-exe cp2k.psmp
# Runs CP2K dry-run validation and maps errors to diagnostics

cp2k-lsp validate input.inp --fail-on-error
# Exit non-zero if errors found
```

## Sample AGENTS.md

Add this to your project's `AGENTS.md`:

```markdown
## CP2K Input Validation

When editing CP2K input files (.inp):

1. Run `cp2k-lsp validate <file>` after each substantive edit
2. Fix all errors before committing
3. Use `cp2k-lsp inspect diagnostics <file>` for machine-readable results
4. Run `cp2k-lsp inspect format-preview <file>` to preview formatting
5. Never commit if `cp2k-lsp validate --fail-on-error <file>` returns non-zero

For semantic validation (RUN_TYPE/MOTION consistency, DFT conflicts, etc.):
- `cp2k-lsp validate <file> --json` returns structured diagnostics
- Check `error_count` field; 0 means passed

For CP2K binary validation (if available):
- `cp2k-lsp validate <file> --dry-run` runs CP2K with --dry-run flag
- Timeout: 300 seconds
```

## Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Stale diagnostics | LSP may show old errors after rapid edits | Close and reopen file, or save and wait 100ms |
| Schema version mismatch | XML schema may not match installed CP2K version | Use `cp2k-lsp validate --dry-run` for authoritative check |
| Missing CP2K binary | Dry-run requires CP2K installed | Use semantic validation only (`--no-dry-run`) |
| Partial file parse | Incomplete files may give incomplete diagnostics | Edit in focused slices; validate after each slice |
| @INCLUDE resolution | Included files may not resolve correctly | Use `--base-dir` option to set search path |
| Preprocessor variables | @IF/@SET/@INCLUDE may need variable values | Use `cp2klint -E KEY=value` to preset variables |

## Failure Modes and Timeouts

| Command | Expected Time | Timeout Recommendation |
|---------|---------------|----------------------|
| LSP diagnostics | <100ms | 5s |
| cp2klint | <1s | 10s |
| cp2k-lsp validate | <1s | 10s |
| cp2k-lsp validate --dry-run | 10-60s | 300s |
| pre-commit | 10-30s | 120s |
| pytest | 1-5min | 600s |

## Diagnostics Sources

| Source | Meaning |
|--------|---------|
| `cp2k-parser` | Syntax errors (tokenizer, parser) |
| `cp2k-schema` | Schema validation (unknown keywords, invalid values) |
| `cp2k-lint` | Semantic validation (RUN_TYPE/MOTION, DFT conflicts, etc.) |
| `cp2k-dryrun` | CP2K binary dry-run output |
