# ML Potentials in CP2K / CP2K 中的机器学习势

## Overview / 概述

CP2K supports multiple machine learning interatomic potential (MLIP) interfaces, enabling near-DFT accuracy at classical force field cost. This entity page catalogs the supported methods, their input sections, and compilation requirements.

CP2K 支持多种机器学习原子间势（MLIP）接口，能够以经典力场的成本实现接近 DFT 的精度。此实体页面记录了支持的方法、其输入部分和编译要求。

## Supported Methods / 支持的方法

### Neural Network Potentials (NNP) -- n2p2/RuNNer

Section: `&FORCE_EVAL / &NNP` with `METHOD NNP`

```cp2k
&FORCE_EVAL
  METHOD NNP
  &NNP
    NNP_INPUT_FILE_NAME input.nn
    SCALE_FILE_NAME scaling.data
  &END NNP
&END FORCE_EVAL
```

References: Behler2007, Behler2011, Schran2020

### NequIP and Allegro

Section: `&FORCE_EVAL / &MM / &FORCEFIELD / &NONBONDED / &NEQUIP` with `METHOD Fist`

```cp2k
&NONBONDED
  &NEQUIP
    MODEL_TYPE  NEQUIP
    ATOMS H O
    POT_FILE_NAME model.nequip.pth
    UNIT_ENERGY eV
    UNIT_FORCES eV*angstrom^-1
    UNIT_LENGTH angstrom
  &END NEQUIP
&END NONBONDED
```

Requires: LibTorch (2.4-2.7). Compatible with NequIP >= 0.7.0.

### DeePMD-kit

Section: `&FORCE_EVAL / &MM / &FORCEFIELD / &NONBONDED / &DEEPMD` with `METHOD Fist`

```cp2k
&NONBONDED
  &DEEPMD
    ATOMS W
    ATOMS_DEEPMD_TYPE 0
    POT_FILE_NAME model.pb
  &END DEEPMD
&END NONBONDED
```

Requires: libdeepmd_c. Critical: ATOMS_DEEPMD_TYPE must match DeePMD type_map.

### Atomic Cluster Expansion (ACE)

Section: `&FORCE_EVAL / &MM / &FORCEFIELD / &NONBONDED / &ACE` with `METHOD Fist`

```cp2k
&NONBONDED
  &ACE
    ATOMS O H
    POT_FILE_NAME ./sample.yaml
  &END ACE
&END NONBONDED
```

Requires: ACE library. GPU support with CUDA.

### PAO-ML (GAP-like)

Section: `&FORCE_EVAL / &DFT / &LS_SCF / &PAO / &MACHINE_LEARNING`

Built-in Gaussian process-based ML. Keywords: DESCRIPTOR, GP_NOISE_VAR, GP_SCALE, METHOD, PRIOR.

### NEP (External)

No native CP2K interface. Used via GPUMD. Typical workflow: CP2K DFT data -> NEP training in GPUMD -> large-scale MD in GPUMD.

## Compilation Flags / 编译标志

| Method | Toolchain Flag |
|--------|---------------|
| NNP | `--with-libnnp` |
| NequIP/Allegro | `--with-libtorch=<path>` |
| DeePMD | `--with-deepmd` |
| ACE | `--with-ace` |

## Related / 相关

- Concept: machine-learning-potentials.md
- Entity: force-field.md (Fist method / Fist 方法)

## 参考来源 (Sources)

1. NequIP: https://manual.cp2k.org/trunk/methods/machine_learning/nequip.html
2. DeePMD: https://manual.cp2k.org/trunk/methods/machine_learning/deepmd.html
3. ACE: https://manual.cp2k.org/trunk/methods/machine_learning/ace.html
4. NNP: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/NNP.html
5. ML Methods Index: https://manual.cp2k.org/trunk/methods/machine_learning/
