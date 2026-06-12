# MD Section / MD 部分

## Overview / 概述

The `&MD` section under `&MOTION` defines all parameters for molecular dynamics propagation in CP2K. It supports a wide range of ensembles (NVE, NVT, NPT_I, NPT_F, Langevin, MSST), thermostat/barostat configurations, and output control.

`&MOTION` 下的 `&MD` 部分定义了 CP2K 中分子动力学传播的所有参数。它支持多种系综（NVE、NVT、NPT_I、NPT_F、Langevin、MSST）、温控器/恒压器配置和输出控制。

## Section Path / 部分路径

```
CP2K_INPUT / MOTION / MD
```

## Subsections / 子部分

| Subsection | Purpose / 用途 |
|------------|----------------|
| THERMOSTAT | Temperature control / 温度控制 |
| BAROSTAT | Pressure control / 压力控制 |
| LANGEVIN | Langevin dynamics parameters / Langevin 动力学参数 |
| PRINT | Output control / 输出控制 |
| AVERAGES | Running averages / 运行平均 |
| RESPA | Multiple timestep / 多时间步 |
| SHELL | Shell model MD / 壳模型 MD |
| THERMAL_REGION | Regional thermostats / 区域温控 |
| CASCADE | Cascade dynamics / 级联动力学 |
| MSST | Multi-scale shock technique / 多尺度冲击技术 |
| ADIABATIC_DYNAMICS | Adiabatic dynamics / 绝热动力学 |
| INITIAL_VIBRATION | Vibrational mode initialization / 振动模式初始化 |
| VELOCITY_SOFTENING | Velocity softening / 速度软化 |
| REFTRAJ | Reference trajectory / 参考轨迹 |

## Key Keywords / 关键关键字

### ENSEMBLE (enum, default: NVE)

| Value | Description / 描述 |
|-------|---------------------|
| NVE | Constant energy (microcanonical) / 恒能量（微正则） |
| NVT | Constant T, V (canonical) / 恒温恒容（正则） |
| NPT_I | Constant T, P, isotropic cell / 恒温恒压，各向同性晶胞 |
| NPT_F | Constant T, P, flexible cell / 恒温恒压，柔性晶胞 |
| LANGEVIN | Langevin dynamics / Langevin 动力学 |
| ISOKIN | Constant kinetic energy / 恒动能 |
| REFTRAJ | Read from trajectory file / 从轨迹文件读取 |
| NPE_F / NPE_I | Constant pressure, no thermostat / 恒压无温控 |
| NVT_ADIABATIC | Adiabatic NVT (CAFES) / 绝热 NVT |
| MSST / MSST_DAMPED | Shock simulation / 冲击模拟 |

### Core Parameters / 核心参数

| Keyword | Default | Description / 描述 |
|---------|---------|---------------------|
| STEPS | 3 | Number of MD steps / MD 步数 |
| TIMESTEP | 0.5 fs | Integration step length / 积分步长 |
| TEMPERATURE | 300 K | Target temperature / 目标温度 |
| TEMP_TOL | 0 K | Temperature tolerance for rescaling / 温度容差 |
| MAX_STEPS | 1E9 | Maximum steps / 最大步数 |

### Velocity Initialization / 速度初始化

| Keyword | Description / 描述 |
|---------|---------------------|
| INITIALIZATION_METHOD | DEFAULT (random) or VIBRATIONAL (canonical modes) |
| ANGVEL_ZERO | Zero initial angular velocity / 零初始角速度 |
| COMVEL_TOL | Max center-of-mass velocity / 最大质心速度 |

## Thermostat Types / 温控器类型

Configured under `&MD / &THERMOSTAT`:

| Type | Description / 描述 | Recommended Use / 推荐用途 |
|------|---------------------|---------------------------|
| NOSE | Nose-Hoover chain | Production runs / 生产运行 |
| CSVR | Canonical velocity rescaling | Equilibration / 平衡 |
| BERENDSEN | Berendsen thermostat | Fast equilibration (not canonical) / 快速平衡（非正则） |
| GLB | Global Langevin | Stochastic / 随机 |
| ADIABATIC | Adiabatic | CAFES method / CAFES 方法 |

## NVT Example / NVT 示例

```cp2k
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
  &END MD
&END MOTION
```

## NPT_I Example / NPT_I 示例

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
      PRESSURE 1.0
      TIMECON 1000
    &END BAROSTAT
  &END MD
&END MOTION
```

## 参考来源 (Sources)

1. MD Section Reference: https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/MD.html
2. MD Methods: https://manual.cp2k.org/trunk/methods/sampling/molecular_dynamics.html
3. Evans & Morriss (1983), VandeVondele (2002), Minary (2003)
