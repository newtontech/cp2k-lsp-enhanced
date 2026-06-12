# MOTION 运动节 (MOTION Section)

## 概述 (Overview)

MOTION 节定义与原子运动相关的计算类型，如几何优化、分子动力学等。

## 运动类型 (Motion Types)

### GEO_OPT 几何优化

```fortran
&MOTION
   &GEO_OPT
      MAX_FORCE 1.0E-4
      RMS_FORCE 1.0E-5
      MAX_ITER 200
      OPTIMIZER BFGS
   &END GEO_OPT
&END MOTION
```

#### 关键字

- `MAX_FORCE`: 最大力收敛准则
- `RMS_FORCE`: 均方根力收敛准则
- `MAX_ITER`: 最大迭代次数
- `OPTIMIZER`: 优化算法 (BFGS, LBFGS, CG)

### CELL_OPT 晶胞优化

```fortran
&MOTION
   &CELL_OPT
      KEEP_ANGLES TRUE
      MAX_FORCE 1.0E-10
      PRESSURE 0.0
   &END CELL_OPT
&END MOTION
```

#### 关键字

- `KEEP_ANGLES`: 保持晶胞角度
- `PRESSURE`: 外部压力
- `CELL_OPTIMIZER`: 优化方法

### MD 分子动力学

```fortran
&MOTION
   &MD
      ENSEMBLE NVT
      STEPS 10000
      TIMESTEP 0.5
      TEMPERATURE 300.0
      &THERMOSTAT
         TYPE NOSE
      &END THERMOSTAT
   &END MD
&END MOTION
```

#### 系综 (Ensembles)

- `NVE`: 微正则系综
- `NVT`: 正则系综（恒温）
- `NPT`: 等温等压系综
- `NVT_GLE`: 广义朗温

#### 恒温器 (Thermostats)

- `NOSE`: Nose-Hoover 恒温器
- `CSVR`: Canonical Sampling Velocity Rescaling
- `LANGEVIN`: 朗之万恒温器

### VIBRATIONAL_ANALYSIS 振动分析

```fortran
&MOTION
   &VIBRATIONAL_ANALYSIS
      DO_NORMAL_MODES TRUE
   &END VIBRATIONAL_ANALYSIS
&END MOTION
```

### MC 蒙特卡洛

```fortran
&MOTION
   &MC
      MOVES_PER_ATOM 100
      TEMPERATURE 300.0
   &END MC
&END MOTION
```

### BAND 能带计算

```fortran
&MOTION
   &BAND
      BAND_SUBSPACE ROTATION
      ADDED_BANDS 50
   &END BAND
&END MOTION
```

## RUN_TYPE 与 MOTION 的对应关系

| RUN_TYPE | 所需 MOTION 节 |
|---------|----------------|
| GEO_OPT | &GEO_OPT |
| CELL_OPT | &CELL_OPT |
| MD | &MD |
| VIBRATIONAL_ANALYSIS | &VIBRATIONAL_ANALYSIS |
| BAND | &BAND |
| MC | &MC |
| ENERGY | 无 |
| ENERGY_FORCE | 无 |

## 示例 (Example)

```fortran
! 几何优化示例
&GLOBAL
   RUN_TYPE GEO_OPT
&END GLOBAL

&MOTION
   &GEO_OPT
      MAX_FORCE 1.0E-4
      OPTIMIZER BFGS
   &END GEO_OPT
&END MOTION
```

## 参考来源 (Sources)

- `cp2k_input_tools/validator.py`: RUN_TYPE/MOTION 验证逻辑
- `raw/assets/NaCl.inp`: 条件编译示例
