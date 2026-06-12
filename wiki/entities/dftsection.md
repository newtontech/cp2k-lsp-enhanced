# DFT 密度泛函理论节 (DFT Section)

## 概述 (Overview)

DFT 节包含密度泛函理论计算的所有参数设置，是 CP2K Quickstep 方法的核心。

## 关键子节 (Key Subsections)

### XC 交换相关节

```fortran
&XC
   &XC_FUNCTIONAL PBE
   &END XC_FUNCTIONAL
&END XC
```

#### XC_FUNCTIONAL 类型

- `LDA`: 局域密度近似
- `PBE`: Perdew-Burke-Ernzerhof GGA
- `BLYP`: Becke-Lee-Yang-Parr
- `TPSS`: Tao-Perdew-Staroverov-Scuseria meta-GGA
- `HYBRID`: 杂化泛函 (如 PBE0, HSE06)

### MGRID 多重网格节

```fortran
&MGRID
   CUTOFF 800
   REL_CUTOFF 80
   NGRIDS 6
&END MGRID
```

#### 关键字

- `CUTOFF`: 主网格截断能 (Ry)
- `REL_CUTOFF`: 相对截断能 (Ry)
- `NGRIDS`: 网格层数

### SCF 自洽场节

```fortran
&SCF
   EPS_SCF 1.0E-7
   MAX_SCF 100
   SCF_GUESS ATOMIC
&END SCF
```

#### 关键字

- `EPS_SCF`: SCF 收敛阈值
- `MAX_SCF`: 最大 SCF 迭代次数
- `SCF_GUESS`: 初始猜测方法 (ATOMIC, RESTART, CORE)
- `SMEAR`: 费米-狄拉克涂抹

### KPOINTS K点节

```fortran
&KPOINTS
   SCHEME MONKHORST-PACK 8 8 8
   FULL_GRID FALSE
   SYMMETRY FALSE
&END KPOINTS
```

### POISSON 泊松求解器节

```fortran
&POISSON
   PERIODIC XYZ
   PSOLVER MT
&END POISSON
```

### QS 快速节

```fortran
&QS
   EPS_DEFAULT 1.0E-12
   METHOD GAPW
&END QS
```

QS 方法选项：
- `GPW`: 高斯平面波
- `GAPW`: 广义高斯平面波

## 示例 (Example)

```fortran
&DFT
   BASIS_SET_FILE_NAME BASIS_SETS
   POTENTIAL_FILE_NAME POTENTIALS

   &QS
      METHOD GAPW
   &END QS

   &MGRID
      CUTOFF 800
      REL_CUTOFF 80
      NGRIDS 6
   &END MGRID

   &SCF
      EPS_SCF 1.0E-7
      MAX_SCF 80
   &END SCF

   &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
   &END XC
&END DFT
```

## 参考来源 (Sources)

- `raw/assets/NaCl.inp`: 完整 DFT 配置示例
- CP2K 手册: DFT 参数详解
