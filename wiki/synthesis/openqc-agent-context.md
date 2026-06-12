# OpenQC Agent Context

OpenQC consumes `cp2k-lsp-tool` and `lsp-capabilities.json` to assemble diagnostics, hover, completion, symbols, examples, next-token guidance, and repair-plan hints for `cp2k` documents.

## LSP Capability Surface

| Capability | Operation | Source Evidence |
|------------|-----------|-----------------|
| Completion | `complete` | Schema-backed keywords from [completion.py](../../raw/assets/cp2k_input_tools/completion.py); see [LSP Features](./lsp-features.md) |
| Hover | `hover` | Schema hover from `cp2k_input_tools/schema_hover.py`; keyword docs in [cp2k-dft-qs-reference.md](../../raw/assets/cp2k-dft-qs-reference.md) |
| Diagnostics | `check` | Parser + linter from [parser.py](../../raw/assets/cp2k_input_tools/parser.py), [lint.py](../../raw/assets/cp2k_input_tools/cli/lint.py); [Diagnostic Engine](../concepts/diagnostic-engine-v1.md) |
| Symbols | `symbols` | Section/keyword outline from LSP document symbols |
| Fix Preview | `fix` | Repair suggestions from validation rules in [validationrules.md](../concepts/validationrules.md) |
| Blocking Gate | `check` | Error diagnostics block submission (`blockingPolicy.mode: blocking` in `lsp-capabilities.json`) |

## Source Provenance

The LSP draws domain knowledge from these upstream sources (recorded in `lsp-capabilities.json` → `sourceProvenance`):

- **CP2K input reference**: https://manual.cp2k.org/trunk/CP2K_INPUT.html
- **MOTION/MD reference**: https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/MD.html
- **CP2K exercises**: https://www.cp2k.org/exercises
- **ML potential methods**: https://manual.cp2k.org/trunk/methods/machine_learning/index.html
- **Upstream manifest**: [raw/assets/upstream-cp2k-reference.md](../../raw/assets/upstream-cp2k-reference.md)

## Diagnostic Engine

Diagnostics follow `DiagnosticEnvelope/v1` (see `diagnostics/diagnostic-engine-v1.schema.json`). Blocking policy is `blocking` — error diagnostics block agent submission until resolved.

## Example Inputs

- **NVT MD (H2)**: [raw/assets/example-nvt-md.inp](../../raw/assets/example-nvt-md.inp) — canonical NVT ensemble with CSVR thermostat
- **NaCl energy/force**: [raw/assets/NaCl.inp](../../raw/assets/NaCl.inp) — periodic DFT with k-points
- **MD tutorial reference**: [raw/assets/cp2k-md-tutorials.md](../../raw/assets/cp2k-md-tutorials.md) — annotated NVT/NPT examples

## 参考来源 (Sources)

- `cp2k_input_tools/openqc_lsp_factory.py`: agent context factory
- `raw/assets/agent-workflow.md`: agent workflow guidance
- [OpenQC Agent Context](./openqc-agent-context.md): this page
