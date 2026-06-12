# QS Section (Quickstep) / QS 部分

## Overview / 概述

The `&QS` section under `&FORCE_EVAL / &DFT / &QS` controls the Quickstep electronic structure framework in CP2K. It specifies the calculation method (GPW, GAPW, semi-empirical, etc.), precision parameters, wavefunction extrapolation strategy, and advanced options for all-electron and linear-scaling calculations.

`&FORCE_EVAL / &DFT / &QS` 下的 `&QS` 部分控制 CP2K 中的 Quickstep 电子结构框架。它指定计算方法（GPW、GAPW、半经验等）、精度参数、波函数外推策略以及全电子和线性标度计算的高级选项。

## Section Path / 部分路径

```
CP2K_INPUT / FORCE_EVAL / DFT / QS
```

## Subsections / 子部分

| Subsection | Purpose / 用途 |
|------------|----------------|
| CDFT | Constrained DFT / 约束 DFT |
| DDAPC_RESTRAINT | Density-derived charge restraint / 密度导出电荷约束 |
| DFTB | Density Functional Tight Binding / 密度泛函紧束缚 |
| DISTRIBUTION | Parallel distribution / 并行分布 |
| LRIGPW | Local Resolution of Identity GPW / 局部分辨率恒等 GPW |
| MULLIKEN_RESTRAINT | Mulliken population restraint / Mulliken 布居约束 |
| OPTIMIZE_LRI_BASIS | Optimize LRI basis / 优化 LRI 基组 |
| SE | Semi-empirical methods / 半经验方法 |
| XTB | Extended Tight Binding (GFN-xTB) / 扩展紧束缚 |

## METHOD Keyword / METHOD 关键字

| Value | Description / 描述 |
|-------|---------------------|
| GPW | Gaussian and Plane Waves (most common) / 高斯和平面波（最常用） |
| GAPW | Gaussian Augmented Plane Waves / 高斯增广平面波 |
| GAPW_XC | GAPW only for XC / GAPW 仅用于交换关联 |
| LRIGPW | Local RI GPW / 局部 RI GPW |
| RIGPW | Resolution of Identity GPW / 分辨率恒等 GPW |
| OFGPW | Orbital-free GPW / 无轨道 GPW |
| DFTB | Density Functional Tight Binding / 密度泛函紧束缚 |
| XTB | GFN-xTB Extended Tight Binding / 扩展紧束缚 |
| MNDO / AM1 / PM3 / PM6 | Semi-empirical / 半经验 |

## Precision Control / 精度控制

| Keyword | Default | Description / 描述 |
|---------|---------|---------------------|
| EPS_DEFAULT | 1.0E-10 | Master precision threshold / 主精度阈值 |
| EPS_PGF_ORB | sqrt(EPS_DEFAULT) | Overlap matrix precision / 重叠矩阵精度 |
| EPS_FILTER_MATRIX | 0.0 | Matrix element filter threshold / 矩阵元过滤阈值 |
| EPS_GVG_RSPACE | sqrt(EPS_DEFAULT) | Real-space KS matrix precision / 实空间 KS 矩阵精度 |
| EPS_RHO | EPS_DEFAULT | Density mapping precision / 密度映射精度 |
| EPS_PPL | 1.0E-2 | Local pseudopotential precision / 局域赝势精度 |
| EPS_PPNL | sqrt(EPS_DEFAULT) | Non-local pseudopotential precision / 非局域赝势精度 |

## EXTRAPOLATION / 外推策略

| Value | Description / 描述 | Use Case / 用途 |
|-------|---------------------|-----------------|
| PS | Higher order P*S extrapolation / 高阶 P*S 外推 | General production / 通用生产 |
| ASPC | Always stable predictor-corrector / 始终稳定预测校正 | MD stability / MD 稳定性 |
| LINEAR_PS | Linear P*S extrapolation / 线性 P*S 外推 | Simple MD / 简单 MD |
| USE_GUESS | No extrapolation / 无外推 | Single point / 单点计算 |

EXTRAPOLATION_ORDER: typically 2-4 for PS/ASPC, 4-10 for GEXT.

## Example / 示例

```cp2k
&QS
  METHOD GPW
  EPS_DEFAULT 1.0E-10
  EXTRAPOLATION ASPC
  EXTRAPOLATION_ORDER 3
&END QS
```

## Related / 相关

- Entity: dft-section.md (parent DFT section / 父 DFT 部分)
- Concept: scf-convergence.md (SCF convergence / SCF 收敛)
- Concept: density-functional-theory.md (DFT concepts / DFT 概念)

## References / 参考资料

1. QS Reference: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS.html
2. Lippert et al. (1997), VandeVondele et al. (2005)

## Sources

- CP2K official documentation and repository assets (synthesized wiki entry).
