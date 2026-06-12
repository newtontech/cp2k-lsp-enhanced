# Upstream CP2K Reference Links (CP2K 上游参考链接)

**Purpose**: Concise manifest of official CP2K documentation sources for LLM wiki evidence.
**Do not duplicate content**; link to canonical upstream resources.

## CP2K Manual and Input Reference

| Resource | URL | Description |
|----------|-----|-------------|
| CP2K input reference (trunk) | https://manual.cp2k.org/trunk/CP2K_INPUT.html | Complete hierarchical input keyword reference |
| CP2K input file overview | https://www.cp2k.org/input_file | Executable/version-matched manual generation |
| CP2K release notes | https://www.cp2k.org/release_notes | Version changelog and migration notes |
| CP2K methods overview | https://manual.cp2k.org/trunk/methods/index.html | DFT, MD, ML, and sampling methods |

## Key Input Sections

| Section | URL | Scope |
|---------|-----|-------|
| GLOBAL | https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL.html | Project name, RUN_TYPE, print level |
| FORCE_EVAL | https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL.html | Force evaluation method tree |
| DFT / QS | https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS.html | Quickstep DFT engine keywords |
| MOTION / MD | https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/MD.html | Molecular dynamics ensembles and thermostats |
| SUBSYS | https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS.html | Cell, coordinates, kinds, k-points |

## Methods and Workflows

| Topic | URL | Description |
|-------|-----|-------------|
| Molecular dynamics sampling | https://manual.cp2k.org/trunk/methods/sampling/molecular_dynamics.html | AIMD workflow overview |
| Machine learning potentials | https://manual.cp2k.org/trunk/methods/machine_learning/index.html | NNP, NequIP, DeePMD, ACE interfaces |
| NequIP / Allegro | https://manual.cp2k.org/trunk/methods/machine_learning/nequip.html | Graph neural network potentials |
| DeePMD-kit | https://manual.cp2k.org/trunk/methods/machine_learning/deepmd.html | Deep potential MD |
| ACE potentials | https://manual.cp2k.org/trunk/methods/machine_learning/ace.html | Atomic cluster expansion |

## Tutorials and Exercises

| Tutorial | URL | Notes |
|----------|-----|-------|
| CP2K exercises hub | https://www.cp2k.org/exercises | Official exercise collection |
| Common MD ensembles | https://www.cp2k.org/exercises:common:ensemble | NVT/NPT ensemble examples |
| 2016 summer school AIMD | https://www.cp2k.org/exercises:2016_summer_school:aimd | Ab initio MD tutorial |

## Developer / Source

| Resource | URL | Notes |
|----------|-----|-------|
| CP2K GitHub | https://github.com/cp2k/cp2k | Official source repository |
| cp2k-input-tools | https://github.com/cp2k/cp2k-input-tools | Parser, linter, and LSP upstream |

---
*Manifest created: 2026-06-13*
*Evidence for issue #109: upstream documentation coverage gap fill*
