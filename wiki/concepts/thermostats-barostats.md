# Thermostats and Barostats / 温控器和恒压器

## Definition / 定义

Thermostats and barostats are algorithms that control the temperature and pressure of a molecular dynamics simulation by coupling the simulated system to a heat bath or a pressure reservoir. In CP2K, they are configured within the `&MD` section of `&MOTION`.

温控器和恒压器是通过将模拟系统耦合到热浴或压力库来控制分子动力学模拟温度和压力的算法。在 CP2K 中，它们在 `&MOTION` 的 `&MD` 部分中配置。

## Thermostats / 温控器

### Nose-Hoover Chain (NOSE)

The default thermostat in CP2K. Generates a true canonical ensemble by introducing extended Lagrangian degrees of freedom.

- **Time constant (TIMECON)**: Controls coupling strength. Shorter = tighter coupling. Typical: 100-1000 fs.
- **Chain length**: Default is sufficient for most systems.
- Generates canonical (NVT) distribution.
- Best for production runs.

```cp2k
&THERMOSTAT
  TYPE NOSE
  &NOSE
    TIMECON 1000
  &END NOSE
&END THERMOSTAT
```

### CSVR (Canonical Sampling through Velocity Rescaling)

A stochastic thermostat that rescales velocities to maintain temperature. Generates a correct canonical ensemble.

- Smoother than Nose-Hoover for equilibration.
- Good alternative to Berendsen that produces correct sampling.
- Recommended for initial equilibration phases.

```cp2k
&THERMOSTAT
  TYPE CSVR
  &CSVR
    TIMECON 100
  &END CSVR
&END THERMOSTAT
```

### Berendsen

Deterministic velocity rescaling. Does NOT produce a true canonical ensemble.

- Fast equilibration but incorrect statistical sampling.
- Not recommended for production; use CSVR instead.
- Historical significance only.

### Langevin

Stochastic thermostat with friction and random forces. Available via `ENSEMBLE LANGEVIN`.

```cp2k
&MD
  ENSEMBLE LANGEVIN
  &LANGEVIN
    GAMMA 0.001          # Friction coefficient [fs^-1]
  &END LANGEVIN
&END MD
```

## Barostats / 恒压器

Configured under `&MD / &BAROSTAT` for NPT ensembles.

### Key Parameters

| Parameter | Description / 描述 | Typical Value |
|-----------|---------------------|---------------|
| PRESSURE | Target pressure [bar] / 目标压力 | 1.0 |
| TIMECON | Coupling time constant [fs] / 耦合时间常数 | 500-2000 |

```cp2k
&BAROSTAT
  PRESSURE 1.0
  TIMECON 1000
&END BAROSTAT
```

### NPT_I vs NPT_F

- **NPT_I**: Isotropic cell -- only the cell volume changes, shape is preserved. For liquids, amorphous solids.
- **NPT_F**: Flexible cell -- full cell tensor can change. For anisotropic systems, crystals, interfaces.

## Ensemble Summary / 系综总结

| Ensemble | Thermostat | Barostat | Cell | Use Case |
|----------|-----------|----------|------|----------|
| NVE | None | None | Fixed | Energy conservation test |
| NVT | Required | None | Fixed | Production at known volume |
| NPT_I | Required | Required | Isotropic | Liquid density, isotropic systems |
| NPT_F | Required | Required | Flexible | Anisotropic crystals, interfaces |
| LANGEVIN | Built-in | None | Fixed | Stochastic dynamics |

## Recommended Protocol / 推荐协议

1. **Equilibration Phase 1** (100-500 steps): NVT, CSVR, TIMECON=100
2. **Equilibration Phase 2** (1000-5000 steps): NPT_I, NOSE+BAROSTAT, TIMECON=500
3. **Production** (10000+ steps): NVT, NOSE, TIMECON=1000

## Related / 相关

- Concept: molecular-dynamics.md
- Entity: md-section.md

## References / 参考资料

1. MD Reference: https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/MD.html
2. MD Methods: https://manual.cp2k.org/trunk/methods/sampling/molecular_dynamics.html
3. Frenkel & Smit, "Understanding Molecular Simulation" (2002)
4. Marx & Hutter, "Ab Initio Molecular Dynamics" (2009)
