# Release Diff: cp2k 2025.2 to 2026.1

## Structured Changes

- renamed: RENAMED_KEY -> NEW_NAME
- removed: OLD_KEY
- deprecated: DEPRECATED_KEY -> NEW_NAME
- changed: EPS_SCF `default` from `1e-6` to `1e-7`
- changed: EPS_SCF `enum` from `['1e-6']` to `['1e-7', '1e-8']`
- changed: EPS_SCF `unit` from `` to `hartree`
- changed: EPS_SCF `description` from `SCF threshold.` to `Tighter SCF threshold.`

## Human Review Checklist

- Review low-confidence changes before promoting generated diagnostics.

## Sources

- `sources/cp2k/2025.2.json`
- `sources/cp2k/2026.1.json`
- `generated/openqc_lsp_factory/cp2k/release-diff-2025.2-to-2026.1/release_diff.json`
- `generated/openqc_lsp_factory/cp2k/release-diff-2025.2-to-2026.1/version_policy.json`
