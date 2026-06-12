> Source: https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/MD.html
> Additional: https://manual.cp2k.org/trunk/methods/sampling/molecular_dynamics.html, https://www.cp2k.org/exercises:common:ensemble, https://www.cp2k.org/exercises:2016_summer_school:aimd

# CP2K Molecular Dynamics Tutorials -- NVT, NPT, and Beyond

## Overview

This document covers the complete MD input reference for CP2K, including ensemble selection,
thermostat/barostat configuration, and practical input examples for NVT, NPT, and other
common MD simulations.

## MD Section Path

```
CP2K_INPUT / MOTION / MD
```

## MD Section Keywords -- Complete Reference

### ENSEMBLE (enum, default: NVE)

| Value | Description |
|-------|-------------|
| `NVE` | Constant energy (microcanonical) |
| `NVT` | Constant temperature and volume (canonical) |
| `NPT_I` | Constant T and P using an isotropic cell |
| `NPT_F` | Constant T and P using a flexible cell |
| `MSST` | Simulate steady shock (uniaxial) |
| `MSST_DAMPED` | Steady shock with extra viscosity |
| `HYDROSTATICSHOCK` | Steady shock with hydrostatic pressure |
| `ISOKIN` | Constant kinetic energy |
| `REFTRAJ` | Reading frames from reftraj.xyz |
| `LANGEVIN` | Langevin dynamics (constant T) |
| `NPE_F` | Constant pressure, no thermostat, flexible cell |
| `NPE_I` | Constant pressure, no thermostat, isotropic cell |
| `NVT_ADIABATIC` | Adiabatic dynamics in NVT (CAFES) |
| `NPT_IA` | NPT_I with frozen atoms in absolute coordinates |

References: Evans1983, VandeVondele2002, Minary2003

### Core MD Parameters

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `STEPS` | integer | 3 | Number of MD steps to perform |
| `MAX_STEPS` | integer | 1E9 | Maximum number of steps |
| `TIMESTEP` | real | 0.5 fs | Length of integration step |
| `TEMPERATURE` | real | 300 K | Target temperature for NVT/NPT |
| `TEMP_TOL` | real | 0 K | Max temperature deviation before velocity rescaling (obsolescent) |
| `STEP_START_VAL` | integer | 0 | Starting step value |
| `TIME_START_VAL` | real | 0 fs | Starting time value |
| `ECONS_START_VAL` | real | 0 hartree | Starting conserved quantity value |

### Velocity Initialization

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `INITIALIZATION_METHOD` | enum | DEFAULT | DEFAULT: random + scale; VIBRATIONAL: canonical from modes |
| `ANGVEL_ZERO` | logical | F | Set initial angular velocity to zero |
| `COMVEL_TOL` | real | - | Max accepted center-of-mass velocity |
| `DISPLACEMENT_TOL` | real | 1 Bohr | Max atomic displacement per step; rescales timestep if exceeded |

### Annealing

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `ANNEALING` | real | 1.0 | Rescaling factor for velocity annealing |
| `ANNEALING_CELL` | real | 1.0 | Rescaling factor for cell velocity annealing |
| `TEMPERATURE_ANNEALING` | real | 1.0 | Rescaling factor for external temperature (Langevin only) |

### Per-Kind Temperature

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `TEMP_KIND` | logical | F | Compute temperature per kind separately |
| `SCALE_TEMP_KIND` | logical | F | Rescale temperature per kind separately |

## MD Subsections

| Subsection | Purpose |
|------------|---------|
| `THERMOSTAT` | Temperature control (NVT, NPT) |
| `BAROSTAT` | Pressure control (NPT) |
| `LANGEVIN` | Langevin dynamics parameters |
| `PRINT` | Output control for trajectory, energies, etc. |
| `AVERAGES` | Running averages |
| `RESPA` | Multiple timestep integration |
| `SHELL` | Shell model (polarizable) MD |
| `THERMAL_REGION` | Regional thermostats |
| `CASCADE` | Cascade dynamics |
| `MSST` | Multi-scale shock technique |
| `ADIABATIC_DYNAMICS` | Adiabatic dynamics |
| `INITIAL_VIBRATION` | Vibrational mode initialization |
| `VELOCITY_SOFTENING` | Velocity softening |
| `REFTRAJ` | Reference trajectory reading |

## Thermostat Configuration

Configured under `&MOTION / &MD / &THERMOSTAT`:

### Thermostat Types (TYPE keyword)

| Type | Description | Use Case |
|------|-------------|----------|
| `NOSE` | Nose-Hoover chain | Standard NVT, default for most production |
| `CSVR` | Canonical Sampling through Velocity Rescaling | Good equilibration, smooth thermostat |
| `BERENDSEN` | Berendsen thermostat | Fast equilibration (does not sample true canonical) |
| `GLB` | Global Langevin | Stochastic global thermostat |
| `ADIABATIC` | Adiabatic dynamics | CAFES method |

### Nose-Hoover Chain Example

```cp2k
&THERMOSTAT
  TYPE NOSE
  &NOSE
    TIMECON 1000          # Time constant [fs]
    MASSES 500            # Number of degrees of freedom
    MULTIPLE 0            # Chain length override
  &END NOSE
&END THERMOSTAT
```

### CSVR Thermostat Example

```cp2k
&THERMOSTAT
  TYPE CSVR
  &CSVR
    TIMECON 100           # Time constant [fs]
  &END CSVR
&END THERMOSTAT
```

## Barostat Configuration

Configured under `&MOTION / &MD / &BAROSTAT` for NPT ensembles:

### Barostat Types

| Type | Description |
|------|-------------|
| `MANOSTAT` | Standard barostat |
| `BERENDSEN` | Berendsen barostat |

### NPT Barostat Example

```cp2k
&BAROSTAT
  PRESSURE 1.0           # Target pressure [bar]
  TIMECON 1000           # Time constant [fs]
  TEMP_TOL 10            # Temperature tolerance [K]
&END BAROSTAT
```

## Complete Input Examples

### NVT MD -- Canonical Ensemble (Equilibration)

```cp2k
&GLOBAL
  PROJECT_NAME water_nvt
  RUN_TYPE MD
  PRINT_LEVEL MEDIUM
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
  &SUBSYS
    &CELL
      ABC 12.0 12.0 12.0
      PERIODIC XYZ
    &END CELL
    &COORD
      # ... water molecule coordinates ...
    &END COORD
    &KIND O
      BASIS_SET TZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q6
    &END KIND
    &KIND H
      BASIS_SET TZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q1
    &END KIND
  &END SUBSYS
&END FORCE_EVAL

&MOTION
  &MD
    ENSEMBLE NVT
    STEPS 5000
    TIMESTEP 0.5
    TEMPERATURE 300.0
    &THERMOSTAT
      TYPE CSVR
      &CSVR
        TIMECON 100
      &END CSVR
    &END THERMOSTAT
    &PRINT
      &TRAJECTORY
        FORMAT XYZ
        STRIDE 10
      &END TRAJECTORY
      &VELOCITIES
        FORMAT XYZ
        STRIDE 100
      &END VELOCITIES
      &ENERGY
        STRIDE 1
      &END ENERGY
    &END PRINT
  &END MD
&END MOTION
```

### NPT_I MD -- Isotropic Pressure Control

```cp2k
&MOTION
  &MD
    ENSEMBLE NPT_I
    STEPS 10000
    TIMESTEP 0.5
    TEMPERATURE 300.0
    &THERMOSTAT
      TYPE NOSE
      &NOSE
        TIMECON 1000
      &END NOSE
    &END THERMOSTAT
    &BAROSTAT
      PRESSURE 1.0         # 1 bar
      TIMECON 1000
    &END BAROSTAT
    &PRINT
      &TRAJECTORY
        FORMAT XYZ
        STRIDE 10
      &END TRAJECTORY
      &CELL
        STRIDE 1
      &END CELL
    &END PRINT
  &END MD
&END MOTION
```

### NPT_F MD -- Flexible Cell (Full Stress Tensor)

```cp2k
&MOTION
  &MD
    ENSEMBLE NPT_F
    STEPS 10000
    TIMESTEP 0.5
    TEMPERATURE 300.0
    &THERMOSTAT
      TYPE NOSE
      &NOSE
        TIMECON 1000
      &END NOSE
    &END THERMOSTAT
    &BAROSTAT
      PRESSURE 1.0
      TIMECON 1000
    &END BAROSTAT
  &END MD
&END MOTION
```

### NVE MD -- Microcanonical (Energy Conservation Test)

```cp2k
&MOTION
  &MD
    ENSEMBLE NVE
    STEPS 1000
    TIMESTEP 0.5
    TEMPERATURE 300.0      # Only used for initial velocity assignment
  &END MD
&END MOTION
```

### Langevin Dynamics

```cp2k
&MOTION
  &MD
    ENSEMBLE LANGEVIN
    STEPS 5000
    TIMESTEP 0.5
    TEMPERATURE 300.0
    &LANGEVIN
      GAMMA 0.001          # Friction coefficient [fs^-1]
    &END LANGEVIN
  &END MD
&END MOTION
```

## Practical Recommendations

### Equilibration Protocol

1. **Initial equilibration**: NVT with CSVR thermostat, short time constant (100 fs)
2. **Density equilibration** (liquids): NPT_I with Nose-Hoover thermostat + barostat
3. **Production**: NVT with Nose-Hoover chain, long time constant (1000 fs)

### Timestep Selection

| System | Recommended Timestep |
|--------|---------------------|
| Water (DFT) | 0.5 fs |
| Water (classical FF) | 1.0 fs |
| Heavy atoms only | 1.0-2.0 fs |
| High-temperature | 0.25-0.5 fs |

### NPT_I vs NPT_F

- Use **NPT_I** for isotropic systems (liquids, amorphous solids) -- only volume changes
- Use **NPT_F** for anisotropic systems (crystals, interfaces) -- full cell tensor changes

## References

1. MD Section Reference: https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/MD.html
2. MD Methods Overview: https://manual.cp2k.org/trunk/methods/sampling/molecular_dynamics.html
3. CP2K Ensemble Exercise: https://www.cp2k.org/exercises:common:ensemble
4. CECAM MD Ensembles Tutorial: https://www.cp2k.org/_media/events:2015_cecam_tutorial:hahn_mdensembles.pdf
5. Evans & Morriss, "Statistical Mechanics of Nonequilibrium Liquids" (1983)
6. Marx & Hutter, "Ab Initio Molecular Dynamics" (2009)
