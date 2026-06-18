---
name: cp2k
description: "CP2K input preflight for generated .inp files and runtime logs."
---

# CP2K LSP Skill

Use this skill when preparing, repairing, or reviewing CP2K input files before a run. It provides an installable language server and an agent-facing CLI that reports machine-readable diagnostics.

## Scope

- Input patterns: *.inp
- Server command: `cp2k-language-server`
- Agent CLI: `cp2k-lsp-tool`
- Diagnostic contract: `DiagnosticEnvelope/v1`

## Installing the checker

```bash
pip install cp2k-lsp-enhanced
```

This installs the `cp2k-language-server` language server and the `cp2k-lsp-tool` agent CLI from the `cp2k-lsp-enhanced` Python package.

## Useful inspection commands

```bash
cp2k-lsp-tool capabilities
cp2k-lsp-tool skill-spec --format json
cp2k-lsp-tool skill-export --output ./skill
cp2k-lsp-tool check <input-file-or-dir> --format json
cp2k-lsp-tool context <input-file-or-dir> --line 0 --character 0 --format json
cp2k-lsp-tool hover <input-file-or-dir> --line 0 --character 0 --format json
cp2k-lsp-tool complete <input-file-or-dir> --line 0 --character 0 --format json
cp2k-lsp-tool symbols <input-file-or-dir> --format json
cp2k-lsp-tool fix <input-file-or-dir> --line 0 --character 0 --format json
```

`fix` is advisory and must be treated as a preview. Do not blindly apply a repair without preserving the user's scientific intent.

## Validation gate

Before saying generated inputs are ready, run:

```bash
cp2k-lsp-tool check <input-file-or-dir> --format json --fail-on-blocking
```

Report `commands`, `files_checked`, `tool_available`, `diagnostics`, `blocking_findings`, `readiness`, and `reason`.

## Repair rules

1. Validate first and identify the smallest blocking issue.
2. Fix syntax or schema errors with minimal edits.
3. Preserve scientific settings unless the user explicitly asks to redesign them.
4. Re-run the checker after every edit.
5. Separate syntax, schema, semantic, and runtime-log diagnostics in the final report.
