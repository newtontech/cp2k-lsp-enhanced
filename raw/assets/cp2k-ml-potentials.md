> Source: https://manual.cp2k.org/trunk/methods/machine_learning/nequip.html
> Additional: https://manual.cp2k.org/trunk/methods/machine_learning/deepmd.html, https://manual.cp2k.org/trunk/methods/machine_learning/ace.html, https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/NNP.html, https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/LS_SCF/PAO/MACHINE_LEARNING.html

# CP2K Machine Learning Potentials -- GAP, NEP, NequIP, DeePMD, ACE, NNP

## Overview

CP2K supports multiple machine learning (ML) interatomic potential interfaces, enabling
large-scale molecular dynamics simulations with near-DFT accuracy at classical force field cost.
This document covers all supported ML potential methods, their input syntax, compilation
requirements, and typical workflows.

## Supported ML Potential Methods

| Method | Interface Type | CP2K Section | Required Library |
|--------|---------------|--------------|------------------|
| Neural Network Potentials (n2p2) | `FORCE_EVAL/METHOD=NNP` | `&NNP` | libnnp |
| NequIP / Allegro | `FORCE_EVAL/METHOD=Fist` | `&NEQUIP` (under NONBONDED) | LibTorch |
| DeePMD-kit | `FORCE_EVAL/METHOD=Fist` | `&DEEPMD` | libdeepmd_c |
| Atomic Cluster Expansion (ACE) | `FORCE_EVAL/METHOD=Fist` | `&ACE` | ACE/PACE |
| PAO-ML (GAP-like) | `FORCE_EVAL/METHOD=Quickstep` | `&MACHINE_LEARNING` | Built-in |
| i-PI interface | External coupling | Socket | i-PI server |

Note: NEP (Neuroevolution Potential) does not have a native CP2K interface. NEP is used
through the GPUMD package. A common workflow is CP2K for DFT reference data -> NEP training
in GPUMD -> large-scale MD in GPUMD.

## 1. Neural Network Potentials (NNP) -- n2p2/RuNNer Format

### Section Path

```
CP2K_INPUT / FORCE_EVAL / NNP
```

References: Behler2007, Behler2011, Schran2020, Schran2020b

### Input Syntax

```cp2k
&FORCE_EVAL
  METHOD NNP
  &NNP
    NNP_INPUT_FILE_NAME input.nn       # n2p2/RuNNer format input file
    SCALE_FILE_NAME scaling.data        # Scaling information
    &BIAS
      # Optional bias potential
    &END BIAS
    &MODEL
      # Model configuration
    &END MODEL
    &PRINT
      # Output control
    &END PRINT
  &END NNP
  &SUBSYS
    &CELL
      ABC 10.0 10.0 10.0
      PERIODIC XYZ
    &END CELL
    &COORD
      # ... atomic coordinates ...
    &END COORD
    &KIND Si
      # Element definition
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
```

### NNP Keywords

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `NNP_INPUT_FILE_NAME` | string | input.nn | File with n2p2/RuNNer format input |
| `SCALE_FILE_NAME` | string | scaling.data | Scaling information for symmetry functions |

## 2. NequIP and Allegro

Equivariant neural network interatomic potentials using E(3)-equivariant architectures.

### Section Path

```
CP2K_INPUT / FORCE_EVAL / MM / FORCEFIELD / NONBONDED / NEQUIP
```

### Input Syntax

```cp2k
&FORCE_EVAL
  METHOD Fist
  &MM
    &FORCEFIELD
      &NONBONDED
        &NEQUIP
          MODEL_TYPE  NEQUIP           # NEQUIP or ALLEGRO
          ATOMS H O                    # List of elements
          POT_FILE_NAME NequIP/model.nequip.pth
          UNIT_ENERGY eV              # Model's energy unit
          UNIT_FORCES eV*angstrom^-1  # Model's force unit
          UNIT_LENGTH angstrom        # Model's length unit
        &END NEQUIP
      &END NONBONDED
    &END FORCEFIELD
  &END MM
  &SUBSYS
    # ... system definition ...
  &END SUBSYS
&END FORCE_EVAL
```

### NequIP Keywords

| Keyword | Description |
|---------|-------------|
| `MODEL_TYPE` | Architecture: `NEQUIP` or `ALLEGRO` |
| `ATOMS` | List of elements/kinds handled by the model |
| `POT_FILE_NAME` | Path to compiled NequIP/Allegro model (.pth) |
| `UNIT_ENERGY` | Energy unit of the model |
| `UNIT_FORCES` | Force unit of the model |
| `UNIT_LENGTH` | Length unit of the model |

### Compilation

Requires LibTorch (versions 2.4 through 2.7):

```bash
# CPU only
./install_cp2k_toolchain.sh --with-libtorch

# With GPU acceleration (CUDA)
./install_cp2k_toolchain.sh --with-libtorch=<path-to-libtorch-cuda>
```

### Validation

The CP2K NequIP interface has been verified to numerically reproduce results from the
LAMMPS `pair_nequip_allegro` plugin. Validation data available on Zenodo: doi:10.5281/zenodo.18848354.

Example regression tests:
- `tests/Fist/regtest-nequip/water-bulk.inp`
- `tests/Fist/regtest-allegro/water-bulk.inp`

References: Batzner2022, Musaelian2023, Tan2025

## 3. DeePMD-kit

Deep learning-based interatomic potential models.

### Section Path

```
CP2K_INPUT / FORCE_EVAL / MM / FORCEFIELD / NONBONDED / DEEPMD
```

### Input Syntax

```cp2k
&FORCE_EVAL
  METHOD Fist
  &MM
    &FORCEFIELD
      &NONBONDED
        &DEEPMD
          ATOMS W                      # Elements handled by DeePMD
          ATOMS_DEEPMD_TYPE 0          # Index consistent with type_map
          POT_FILE_NAME DeePMD/W.pb    # Deployed DeePMD model
        &END DEEPMD
      &END NONBONDED
    &END FORCEFIELD
  &END MM
  &SUBSYS
    # ... system definition ...
  &END SUBSYS
&END FORCE_EVAL
```

### DeePMD Keywords

| Keyword | Description |
|---------|-------------|
| `ATOMS` | List of elements/kinds |
| `ATOMS_DEEPMD_TYPE` | Index consistent with type_map in DeePMD parameters (CRITICAL: must match) |
| `POT_FILE_NAME` | Path to deployed DeePMD model (.pb file) |

**Important**: `ATOMS_DEEPMD_TYPE` must match the `type_map` in DeePMD-kit parameters. Mismatches
produce unphysical results with significantly wrong energies.

### Compilation

```bash
./install_cp2k_toolchain.sh --with-deepmd
```

GPU support is enabled when CUDA environment exists.

References: Wang2018, Zeng2023

## 4. Atomic Cluster Expansion (ACE)

Complete descriptor-based ML potential with nonlinear functions.

### Section Path

```
CP2K_INPUT / FORCE_EVAL / MM / FORCEFIELD / NONBONDED / ACE
```

### Input Syntax

```cp2k
&FORCE_EVAL
  METHOD Fist
  &MM
    &FORCEFIELD
      &NONBONDED
        &ACE
          ATOMS O H                    # Elements
          POT_FILE_NAME ./sample.yaml  # ACE model file
        &END ACE
      &END NONBONDED
    &END FORCEFIELD
  &END MM
  &SUBSYS
    # ... system definition ...
  &END SUBSYS
&END FORCE_EVAL
```

### ACE Keywords

| Keyword | Description |
|---------|-------------|
| `ATOMS` | List of elements/kinds treated with ACE |
| `POT_FILE_NAME` | Path to ACE model file (.yaml) |

### Compilation

```bash
./install_cp2k_toolchain.sh --with-ace
```

GPU support available with CUDA.

References: Drautz2019, Lysogorskiy2021, Bochkarev2024

Example regression test: `H2O-64_ACE_MD.inp`

## 5. PAO-ML (GAP-like Gaussian Process)

Built-in ML interface using Gaussian processes with polarized atomic orbitals.

### Section Path

```
CP2K_INPUT / FORCE_EVAL / DFT / LS_SCF / PAO / MACHINE_LEARNING
```

### Keywords

| Keyword | Description |
|---------|-------------|
| `DESCRIPTOR` | Descriptor type for atomic environment |
| `GP_NOISE_VAR` | Gaussian process noise variance |
| `GP_SCALE` | GP length scale parameter |
| `METHOD` | ML method selection |
| `PRIOR` | Prior function for GP |
| `TRAINING_SET` | Training data configuration |

## 6. NEP (Neuroevolution Potential) -- External Workflow

NEP does not have a native CP2K interface. Typical workflow:

1. **Generate DFT training data with CP2K**:
   - Run AIMD simulations (PBE + DZVP + D3)
   - Sample configurations at regular intervals
   - Extract energies, forces, and stresses

2. **Train NEP model in GPUMD**:
   - Prepare train.xyz in NEP format
   - Run NEP training with GPUMD
   - Validate accuracy

3. **Run large-scale MD in GPUMD**:
   - NEP achieves GPU-optimized performance for millions of atoms
   - Far greater efficiency than CPU-based potentials (GAP, MTP)

Reference: Fan Zheyong, GPUMD/NEP development

## Typical ML Training Data Generation Workflow

### Step 1: AIMD with CP2K

```cp2k
&GLOBAL
  PROJECT_NAME training_data
  RUN_TYPE MD
&END GLOBAL

&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME BASIS_SET
    POTENTIAL_FILE_NAME POTENTIAL
    &MGRID
      CUTOFF 400
      REL_CUTOFF 60
    &END MGRID
    &QS
      METHOD GPW
      EPS_DEFAULT 1.0E-8
    &END QS
    &SCF
      EPS_SCF 1.0E-5
      MAX_SCF 50
      &OT
        PRECONDITIONER FULL_ALL
      &END OT
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
      &VDW_POTENTIAL
        POTENTIAL_TYPE PAIR_POTENTIAL
        &PAIR_POTENTIAL
          TYPE DFTD3(BJ)
          PARAMETER_FILE_NAME dftd3.dat
        &END PAIR_POTENTIAL
      &END VDW_POTENTIAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      ABC 12.42 12.42 12.42
      PERIODIC XYZ
    &END CELL
    &TOPOLOGY
      COORD_FILE_NAME water.xyz
      COORD_FILE_FORMAT XYZ
    &END TOPOLOGY
    &KIND O
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q6
    &END KIND
    &KIND H
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q1
    &END KIND
  &END SUBSYS
  &PRINT
    &FORCES ON
    &END FORCES
  &END PRINT
&END FORCE_EVAL

&MOTION
  &MD
    ENSEMBLE NVT
    STEPS 10000
    TIMESTEP 0.5
    TEMPERATURE 300.0
    &THERMOSTAT
      TYPE CSVR
      &CSVR
        TIMECON 100
      &END CSVR
    &END THERMOSTAT
  &END MD
&END MOTION
```

### Step 2: Convert to Training Format

Use tools like:
- `cp2k_2_deepmdkit` for DeePMD format
- Custom scripts for n2p2 format
- ORNL converter for DeePMD raw files

## Performance Comparison

| Method | Accuracy | Speed | GPU Support | Scale |
|--------|----------|-------|-------------|-------|
| NNP (n2p2) | Good | Moderate | No | ~10K atoms |
| NequIP | Very High | Moderate | Yes (LibTorch) | ~10K atoms |
| Allegro | Very High | Fast | Yes (LibTorch) | ~100K atoms |
| DeePMD | High | Fast | Yes | ~100K atoms |
| ACE | High | Fast | Yes | ~100K atoms |
| NEP (GPUMD) | High | Very Fast | Yes (native) | ~10M atoms |
| PAO-ML | Moderate | Slow | No | ~1K atoms |

## References

1. NequIP/Allegro: https://manual.cp2k.org/trunk/methods/machine_learning/nequip.html
2. DeePMD-kit: https://manual.cp2k.org/trunk/methods/machine_learning/deepmd.html
3. ACE: https://manual.cp2k.org/trunk/methods/machine_learning/ace.html
4. NNP: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/NNP.html
5. PAO-ML: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/LS_SCF/PAO/MACHINE_LEARNING.html
6. ML Methods Index: https://manual.cp2k.org/trunk/methods/machine_learning/
7. Batzner et al., Nature Communications 13, 2453 (2022)
8. Musaelian et al., Nature Communications 14, 686 (2023)
9. Behler, J. Chem. Phys. 134, 074106 (2011)
