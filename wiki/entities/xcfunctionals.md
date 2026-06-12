# 交换相关泛函 (Exchange-Correlation Functionals)

## 概述 (Overview)

交换相关泛函是 DFT 计算的核心，近似描述电子间的交换和相关作用。

## LDA 局域密度近似 (Local Density Approximation)

### 特点

- 基于均匀电子气
- 计算成本低
- 适用于高密度电子系统

### 常用 LDA 泛函

```fortran
&XC_FUNCTIONAL LDA
&END XC_FUNCTIONAL
```

- `LDA`: Slater-Vosko-Wilk-Nusair (SVWN)
- `LDA_X`: 只含交换
- `LDA_C_PZ`: Perdew-Zunger 相关

## GGA 广义梯度近似 (Generalized Gradient Approximation)

### 特点

- 考虑电子密度梯度
- 比 LDA 更准确
- 略高的计算成本

### 常用 GGA 泛函

#### PBE (Perdew-Burke-Ernzerhof)

```fortran
&XC_FUNCTIONAL PBE
&END XC_FUNCTIONAL
```

最常用的 GGA 泛函，平衡精度和效率。

#### BLYP

```fortran
&XC_FUNCTIONAL BLYP
&END XC_FUNCTIONAL
```

Becke 交换 + Lee-Yang-Parr 相关。

#### 其他 GGA 泛函

- `PBE_SOL`: 固体优化的 PBE
- `B97-D`: 带色散校正
- `REVSSB`: 修订的 SSb 泛函

## Meta-GGA

### 特点

- 包含动能密度
- 更高的精度
- 更高的计算成本

### 常用 Meta-GGA 泛函

```fortran
&XC_FUNCTIONAL TPSS
&END XC_FUNCTIONAL
```

- `TPSS`: Tao-Perdew-Staroverov-Scuseria
- `M06-L`: Minnesota 泛函

## 杂化泛函 (Hybrid Functionals)

### 特点

- 混合部分精确交换
- 高精度
- 计算成本高

### 常用杂化泛函

#### PBE0

```fortran
&XC
   &XC_FUNCTIONAL PBE0
   &END XC_FUNCTIONAL
&END XC
```

#### HSE06

```fortran
&XC_FUNCTIONAL HSE06
&END XC_FUNCTIONAL
```

适用于固体计算。

#### B3LYP

```fortran
&XC_FUNCTIONAL B3LYP
&END XC_FUNCTIONAL
```

#### 全程屏蔽交换 (RS-Range Separated)

```fortran
&XC
   &HF
      FRACTION 0.25
      SCREENING 0.11
   &END HF
   &XC_FUNCTIONAL PBE
   &END XC_FUNCTIONAL
&END XC
```

## 色散校正 (Dispersion Corrections)

### DFT-D3

```fortran
&XC
   &XC_FUNCTIONAL PBE
   &END XC_FUNCTIONAL
   &VDW
      POTENTIAL TYPE_UFF
      DISPERSION_FUNCTIONAL PAIR_POTENTIAL
      PARAMETRIZATION ORTHOGONAL
      R_CUTOFF 12.0
   &END VDW
&END XC
```

### DFT-D4

```fortran
&XC
   &XC_FUNCTIONAL PBE
   &END XC_FUNCTIONAL
   &DFTD4
      D4_CUTOFF 50.0
   &END DFTD4
&END XC
```

## 泛函选择指南 (Selection Guide)

| 系统 | 推荐泛函 | 原因 |
|------|---------|------|
| 分子/簇 | BLYP/PBE | 良好的平衡 |
| 固体 | PBE-SOL | 对晶格常数优化 |
| 高精度 | PBE0/HSE06 | 杂化泛函 |
| 弱相互作用 | B97-D3/PBE-D3 | 带色散校正 |
| 金属 | PBE+U | Hubbard U 校正 |

## Hubbard U 校正

```fortran
&XC
   &XC_FUNCTIONAL PBE
   &END XC_FUNCTIONAL
   &LDADFT
      U 5.0 3.0
      U_PROJECTORS AO_SHAPE
   &END LDADFT
&END XC
```

## 参考来源 (Sources)

- CP2K 手册: XC 泛函完整列表
- `raw/assets/NaCl.inp`: PBE 泛函使用示例
