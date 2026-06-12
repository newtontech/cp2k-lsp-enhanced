> Source: https://www.cp2k.org/howto:static_calculation
> Additional: https://docs.bioexcel.eu/qmmm_bpg/en/main/running_cp2k/cp2k_output.html, https://github.com/cp2k/cp2k/discussions/3036, https://calvera.ornl.gov/docs/user_guide/tools/Chemical%20Spectroscopy/neutrons_amml_cp2k_convert/

# CP2K Output File Format -- Energy, Forces, and Parsing

## Overview

CP2K generates multiple output files during a calculation. This document describes the formats of
the main output file (.out), energy files (.ener), trajectory files, and how to parse energy,
forces, and stress data programmatically.

## Main Output File (.out)

The standard output file (named `PROJECT_NAME.out`) contains the complete calculation log:

### Structure

1. **Header**: Version, build info, date, parallel settings
2. **Input echo**: Repeated input file contents
3. **Initialization**: System setup, basis set info, grid info
4. **SCF iterations**: Per-SCF-step convergence info
5. **Results**: Energy, forces, stress tensor, coordinates
6. **MD/Optimization steps**: Per-step output for dynamics

### Energy Output Format

Energy lines follow this pattern:

```
ENERGY| Total FORCE_EVAL ( F= -2.3473674278E+02 E= -2.3473674278E+02 )
```

Where:
- `F` = Free energy (Helmholtz)
- `E` = Potential energy

For DFT calculations, energy components include:

```
Total energy:                            -2.3473674278E+02
energy corrections for chained runs:      0.0000000000E+00
Self-interaction correction (SIC):        0.0000000000E+00
Total charge density on r-space grids:    5.6000000000E+01
Total charge density g-space:             5.6000000000E+01
Overlap energy of the core charge:       -1.0823478373E+03
Self energy of the core charge:           1.0823478373E+03
Core Hamiltonian energy:                 -3.4567823478E+01
Hartree energy:                           6.7890123456E+01
Exchange-correlation energy:             -1.2345678901E+01
Total energy:                            -2.3473674278E+02
```

### Force Output Format

Atomic forces are printed as:

```
 ATOMS                                                    [Ang]
 Index Kind Element     X           Y           Z          Mass
     1    1  Si     -1.234567   -2.345678   -0.123456   28.0855
     2    1  Si      1.234567    2.345678    0.123456   28.0855

  Atom   Kind Element          X             Y             Z
     1     1  Si         0.00123456   -0.00234567    0.00012345
     2     1  Si        -0.00123456    0.00234567   -0.00012345
 SUM OF ATOMIC FORCES        0.00000000    0.00000000    0.00000000
```

### Stress Tensor Format

```
 STRESS| Analytical stress tensor [GPa]
 STRESS|                X                  Y                  Z
 STRESS| X       12.34567890123    -0.12345678901     0.00000000000
 STRESS| Y       -0.12345678901    12.34567890123     0.00000000000
 STRESS| Z        0.00000000000     0.00000000000    12.34567890123
```

## Energy File (.ener)

The `.ener` file contains per-step thermodynamic data. Generated under `&MOTION / &PRINT / &ENERGY`.

### Format

Tab-separated columns:

```
#     StepNr.          Time[fs]        Kin.[a.u.]        Temp[K]        Pot.[a.u.]        Cons Qty[a.u.]        UsedTime[s]
           0        0.000000       0.439597E-01       300.00      -0.234567E+03      -0.234527E+03        0.00
           1        0.500000       0.442312E-01       301.86      -0.234567E+03      -0.234527E+03        2.34
```

Columns:
1. Step number
2. Time in femtoseconds
3. Kinetic energy in Hartree (a.u.)
4. Instantaneous temperature in Kelvin
5. Potential energy in Hartree (a.u.)
6. Conserved quantity in Hartree (a.u.)
7. Wall time in seconds

## Trajectory Files

### XYZ Trajectory (pos-1.xyz)

Standard extended XYZ format:

```
   64
 i =       10, E =      -234.5678901234
 Si         1.2345678901        2.3456789012        3.4567890123
 Si         4.5678901234        5.6789012345        6.7890123456
 ...
```

- First line: number of atoms
- Second line: comment with step and energy
- Subsequent lines: element, x, y, z coordinates

### DCD Trajectory

Binary trajectory format (CHARMM/NAMD compatible). Configured with:

```cp2k
&PRINT
  &TRAJECTORY
    FORMAT DCD
    STRIDE 10
  &END TRAJECTORY
&END PRINT
```

### Velocity Trajectory (vel-1.xyz)

Same format as position trajectory but with velocities instead of positions.

## Restart Files (.restart)

Binary or text files containing complete simulation state:
- Wavefunction coefficients
- Density matrix
- Atomic positions and velocities
- Cell parameters
- Nose-Hoover chain state

Usage for restart:

```cp2k
&EXT_RESTART
  RESTART_FILE_NAME previous_calc.restart
  &RESTART
    WAVEFUNCTION
  &END RESTART
&END EXT_RESTART
```

## Cube Files

Volumetric data output:

- `PROJECT_NAME-ELECTRON_DENSITY-1.cube` -- Electron density
- `PROJECT_NAME-SPIN_DENSITY-1.cube` -- Spin density (if LSD)
- `PROJECT_NAME-V POTENTIAL-1.cube` -- Electrostatic potential

Cube file format is standard Gaussian cube format with grid dimensions and voxel data.

## Parsing Energy and Forces Programmatically

### Regex Patterns for Energy

```python
import re

# Total energy from main output
energy_pattern = re.compile(
    r'ENERGY\| Total FORCE_EVAL\s+\( F=\s+([-\d.E+]+)\s+E=\s+([-\d.E+]+)\s+\)'
)

# SCF energy
scf_pattern = re.compile(
    r'Total energy:\s+([-\d.E+]+)'
)
```

### Regex Patterns for Forces

```python
# Force block parsing
force_pattern = re.compile(
    r'Atom\s+Kind\s+Element\s+X\s+Y\s+Z\n'
    r'(?:\s+\d+\s+\d+\s+\w+\s+([-\d.E+]+)\s+([-\d.E+]+)\s+([-\d.E+]+)\n)+'
)
```

### Parsing .ener Files

```python
def parse_ener_file(filepath):
    """Parse CP2K .ener file into structured data."""
    data = []
    with open(filepath) as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 7:
                data.append({
                    'step': int(parts[0]),
                    'time_fs': float(parts[1]),
                    'kinetic_au': float(parts[2]),
                    'temperature_K': float(parts[3]),
                    'potential_au': float(parts[4]),
                    'conserved_au': float(parts[5]),
                    'wall_time_s': float(parts[6]),
                })
    return data
```

### Converting CP2K Output to DeePMD Format

The ORNL Neutrons platform provides a tool for parsing CP2K MD trajectory output
into `*.raw` files compatible with DeePMD-kit training:

- Extract atomic coordinates from XYZ trajectories
- Extract forces from output files
- Convert to DeePMD binary format

Reference: https://calvera.ornl.gov/docs/user_guide/tools/Chemical%20Spectroscopy/neutrons_amml_cp2k_convert/

## Force and Energy in Biased Simulations

In metadynamics and free energy calculations:

- The output energy includes the bias potential: `E_system + V_bias`
- Forces include the bias force: `F_system + F_bias`
- For multiple FORCE_EVAL sections, separate energy (E1, E2) and force outputs are generated

Reference: https://github.com/cp2k/cp2k/discussions/3036

## Output Control Keywords

### Controlling Trajectory Output

```cp2k
&MOTION
  &MD
    &PRINT
      &TRAJECTORY
        FORMAT XYZ
        STRIDE 10               # Output every 10 steps
        ENSURE_TRAJECTURE_CONTINUITY
      &END TRAJECTORY
      &VELOCITIES
        FORMAT XYZ
        STRIDE 100
      &END VELOCITIES
      &FORCES
        FORMAT XYZ
        STRIDE 10
      &END FORCES
      &ENERGY
        STRIDE 1                # Every step
      &END ENERGY
      &STRESS
        STRIDE 10
      &END STRESS
      &RESTART
        STRIDE 100
        BACKUP_COPIES 3
      &END RESTART
    &END PRINT
  &END MD
&END MOTION
```

### Controlling Main Output Verbosity

```cp2k
&GLOBAL
  PRINT_LEVEL MEDIUM           # SILENT, LOW, MEDIUM, HIGH, DEBUG
&END GLOBAL
```

## File Naming Convention

CP2K uses the pattern `PROJECT_NAME-type-number.ext`:

| File | Description |
|------|-------------|
| `proj.out` | Main output |
| `proj-1.restart` | Restart file |
| `proj-pos-1.xyz` | Position trajectory |
| `proj-vel-1.xyz` | Velocity trajectory |
| `proj-frc-1.xyz` | Force trajectory |
| `proj-1.ener` | Energy data |
| `proj-1.cell` | Cell trajectory |
| `proj-ELECTRON_DENSITY-1.cube` | Electron density |
| `proj.wfn` | Wavefunction |
| `proj.mo` | Molecular orbitals |
| `proj-vib_modes-1.molden` | Vibrational modes |

## References

1. CP2K Static Calculation HOWTO: https://www.cp2k.org/howto:static_calculation
2. BioExcel CP2K Output Guide: https://docs.bioexcel.eu/qmmm_bpg/en/main/running_cp2k/cp2k_output.html
3. CP2K GitHub Discussion #3036: https://github.com/cp2k/cp2k/discussions/3036
4. ORNL CP2K-to-DeePMD Converter: https://calvera.ornl.gov/docs/user_guide/tools/Chemical%20Spectroscopy/neutrons_amml_cp2k_convert/
5. Iannuzzi et al., "The CP2K Program Package Made Simple" (2025)
