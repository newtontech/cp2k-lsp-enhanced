# MD Setup Guide / MD 设置指南

## Purpose / 目的

A practical guide for setting up molecular dynamics simulations in CP2K, covering the complete workflow from system preparation through production runs. This synthesis page combines knowledge from multiple entity and concept pages.

从系统准备到生产运行的 CP2K 分子动力学模拟完整设置实用指南。此综合页面结合了多个实体和概念页面的知识。

## Step 1: System Preparation / 系统准备

### Build the System

1. Define the simulation cell in `&SUBSYS / &CELL`
2. Provide atomic coordinates via `&COORD` or `&TOPOLOGY`
3. Assign basis sets and pseudopotentials in `&KIND`

```cp2k
&SUBSYS
  &CELL
    ABC 12.42 12.42 12.42
    PERIODIC XYZ
  &END CELL
  &TOPOLOGY
    COORD_FILE_NAME system.xyz
    COORD_FILE_FORMAT XYZ
  &END TOPOLOGY
  &KIND O
    BASIS_SET TZVP-MOLOPT-GTH
    POTENTIAL GTH-PBE-q6
  &END KIND
  &KIND H
    BASIS_SET TZVP-MOLOPT-GTH
    POTENTIAL GTH-PBE-q1
  &END KIND
&END SUBSYS
```

### Choose Calculation Method

- **AIMD (DFT-based)**: `METHOD Quickstep` in `&FORCE_EVAL` -- accurate but expensive
- **Classical MD**: `METHOD Fist` in `&FORCE_EVAL` -- fast with force fields
- **ML-based MD**: `METHOD NNP` or `METHOD Fist` with ML potentials -- balanced

## Step 2: DFT Settings / DFT 设置

For AIMD, configure the DFT engine:

```cp2k
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
    EXTRAPOLATION ASPC
    EXTRAPOLATION_ORDER 3
  &END QS
  &SCF
    EPS_SCF 1.0E-5
    MAX_SCF 50
    SCF_GUESS restart
    &OT
      PRECONDITIONER FULL_ALL
    &END OT
  &END SCF
  &XC
    &XC_FUNCTIONAL PBE
    &END XC_FUNCTIONAL
  &END XC
&END DFT
```

Key decisions:
- **CUTOFF**: 300-600 Ry depending on system and basis set
- **EPS_SCF**: 1.0E-5 for MD (relaxed), 1.0E-6 for static calculations
- **EXTRAPOLATION**: ASPC for MD stability, PS for general use
- **SCF solver**: OT (Orbital Transformation) for large systems, DIIS for small

## Step 3: MD Configuration / MD 配置

### Equilibration Phase

```cp2k
&MOTION
  &MD
    ENSEMBLE NVT
    STEPS 500
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

### NPT Equilibration (for liquids)

```cp2k
&MD
  ENSEMBLE NPT_I
  STEPS 5000
  TIMESTEP 0.5
  TEMPERATURE 300.0
  &THERMOSTAT
    TYPE NOSE
    &NOSE
      TIMECON 500
    &END NOSE
  &END THERMOSTAT
  &BAROSTAT
    PRESSURE 1.0
    TIMECON 500
  &END BAROSTAT
&END MD
```

### Production Run

```cp2k
&MD
  ENSEMBLE NVT
  STEPS 20000
  TIMESTEP 0.5
  TEMPERATURE 300.0
  &THERMOSTAT
    TYPE NOSE
    &NOSE
      TIMECON 1000
    &END NOSE
  &END THERMOSTAT
  &PRINT
    &TRAJECTORY
      FORMAT XYZ
      STRIDE 10
      ENSURE_TRAJECTORY_CONTINUITY
    &END TRAJECTORY
    &VELOCITIES
      FORMAT XYZ
      STRIDE 100
    &END VELOCITIES
    &ENERGY
      STRIDE 1
    &END ENERGY
    &RESTART
      STRIDE 500
      BACKUP_COPIES 5
    &END RESTART
  &END PRINT
&END MD
```

## Step 4: Restart Protocol / 重启协议

To continue a calculation from a restart file:

```cp2k
&EXT_RESTART
  RESTART_FILE_NAME previous-1.restart
&END EXT_RESTART
```

And set:
- `SCF_GUESS restart` in `&SCF`
- `STEP_START_VAL` to continue step numbering
- Use the same `&MD` settings

## Timestep Selection Guide / 时间步长选择指南

| System / 系统 | Timestep | Notes |
|---------------|----------|-------|
| Water (DFT-AIMD) | 0.5 fs | Standard for O-H dynamics |
| Water (classical FF) | 1.0 fs | With SHAKE/constraint on bonds |
| Heavy atoms | 1.0-2.0 fs | No light atoms |
| High temperature (>500K) | 0.25 fs | Faster vibrations |
| Path integral MD | 0.25-0.5 fs | Smaller for bead resolution |

## Common Issues / 常见问题

### SCF Not Converging in MD

1. Reduce EPS_SCF to 1.0E-4 (less strict but faster)
2. Increase MAX_SCF to 100
3. Use `SCF_GUESS restart` after first step
4. Add `&SMEAR` section for metallic systems

### Energy Drift in NVE

1. Check timestep (reduce if too large)
2. Increase EPS_DEFAULT in QS section
3. Verify no Pulay forces (converge CUTOFF)

### Temperature Not Stable

1. Increase thermostat TIMECON
2. Switch from BERENDSEN to CSVR or NOSE
3. Check system size (too small = large fluctuations)

## Referenced Pages / 引用页面

- Entities: md-section.md, qs-section.md, dft-section.md, subsys-section.md
- Concepts: molecular-dynamics.md, thermostats-barostats.md, scf-convergence.md
- Synthesis: typical-workflow.md

## 参考来源 (Sources)

1. MD Reference: https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/MD.html
2. CP2K AIMD Exercise: https://www.cp2k.org/exercises:2016_summer_school:aimd
3. Marx & Hutter, "Ab Initio Molecular Dynamics" (2009)
