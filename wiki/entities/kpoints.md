# K点设置 (K-Point Settings)

## 概述 (Overview)

K点用于在周期性系统中采样布里渊区，是固体计算的重要参数。

## KPOINTS 节结构

```fortran
&KPOINTS
   SCHEME <scheme> <parameters>
   FULL_GRID <boolean>
   SYMMETRY <boolean>
&END KPOINTS
```

## K点方案 (K-Point Schemes)

### MONKHORST-PACK

最常用的等间距网格：

```fortran
&KPOINTS
   SCHEME MONKHORST-PACK 8 8 8
&END KPOINTS
```

参数：`nx ny nz` - 三个方向的网格点数

### WRLF-CPL

Wentzcovitch-Rao-Liu-Cappelletti 方案：

```fortran
&KPOINTS
   SCHEME WRLF-CPL 8 8 8
&END KPOINTS
```

### OMPI-MP

适用于金属系统：

```fortran
&KPOINTS
   SCHEME OMPI-MP 8 8 8 0.1
&END KPOINTS
```

### GENERIC

指定任意K点：

```fortran
&KPOINTS
   SCHEME GENERIC
   FULL_GRID FALSE
   POINTS 3
   0.0 0.0 0.0 1.0
   0.5 0.5 0.5 1.0
   0.25 0.25 0.25 1.0
&END KPOINTS
```

### PATH

能带结构计算路径：

```fortran
&KPOINTS
   SCHEME PATH
   NPOINTS 50
   POINTS 2
   GAMMA 0.0 0.0 0.0
   X 0.5 0.0 0.0
&END KPOINTS
```

## 参数说明

### FULL_GRID

```fortran
FULL_GRID TRUE   ! 使用完整的 Monkhorst-Pack 网格
FULL_GRID FALSE  ! 使用缩减网格
```

### SYMMETRY

```fortran
SYMMETRY TRUE   ! 考虑对称性减少K点
SYMMETRY FALSE  ! 不考虑对称性
```

### PARALLEL_GROUP_SIZE

```fortran
&KPOINTS
   PARALLEL_GROUP_SIZE -1
&END KPOINTS
```

控制并行计算的K点分组。

## K点网格选择指南

| 系统类型 | 推荐网格 | 说明 |
|---------|---------|------|
| 分子 | 无K点 | 使用 Gamma 点 |
| 小晶胞 | 8 8 8 或更高 | 充分采样 |
| 大晶胞 | 2 2 2 或 4 4 4 | 计算效率 |
| 金属 | 更密集网格 | 费米面需要 |
| 表面/板 | 8 8 1 | 二维周期 |
| 链 | 1 1 8 | 一维周期 |

## 测试收敛性

```fortran
@SET KP_GRID 4
! 其他设置...
&KPOINTS
   SCHEME MONKHORST-PACK ${KP_GRID} ${KP_GRID} ${KP_GRID}
&END KPOINTS
```

使用 `cp2kgen` 测试不同网格：

```bash
cp2kgen input.inp "force_eval/dft/kpoints/scheme=[4,6,8,10]"
```

## 示例 (Example)

```fortran
&KPOINTS
   SCHEME MONKHORST-PACK 8 8 8
   FULL_GRID .FALSE.
   SYMMETRY .FALSE.
&END KPOINTS
```

## 无K点计算

对于分子或大晶胞（孤立边界条件）：

```fortran
&SUBSYS
   &CELL
      PERIODIC NONE
   &END CELL
&END SUBSYS

! 不设置 KPOINTS 节
```

## 参考来源 (Sources)

- `raw/assets/NaCl.inp`: KPOINTS 使用示例
- CP2K 手册: K点采样详解
