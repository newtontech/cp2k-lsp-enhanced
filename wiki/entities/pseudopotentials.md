# 赝势 (Pseudopotentials)

## 概述 (Overview)

赝势用于替代内核电子，仅显式处理价电子，减少计算成本。

## 赝势类型 (Pseudopotential Types)

### GTH 赝势 (Goedecker-Teter-Hutter)

CP2K 的默认赝势：

```fortran
&KIND Si
   POTENTIAL GTH-PBE
&END KIND
```

### PAW 赝势 (Projector Augmented Wave)

更高精度的方法：

```fortran
&KIND Fe
   POTENTIAL PAW_PBE
&END KIND
```

### 全电子计算 (All-Electron)

不使用赝势：

```fortran
&KIND C
   POTENTIAL ALL
&END KIND
```

## 赝势文件格式 (Pseudopotential File Format)

```
# Potential for: H
#    Z   Zc   ppol  nlcc
      1    0     2     0
# rloc   cloc   nloc
  0.351  0.351     2
# ...
```

## 常用赝势库 (Common Pseudopotential Libraries)

### GTH-PBE

PBE 泛函配套赝势：

```fortran
POTENTIAL GTH-PBE
POTENTIAL GTH-PBE-QM
```

### GTH-BLYP

BLYP 泛函配套赝势：

```fortran
POTENTIAL GTH-BLYP
```

### 全电子势 (All-Electron Potentials)

```fortran
POTENTIAL ALL
POTENTIAL ALL-q32
```

## 赝势选择指南 (Selection Guide)

| 元素类型 | 推荐赝势 | 说明 |
|---------|---------|------|
| 轻元素 (H-Ne) | GTH-PBE | 标准精度 |
| 过渡金属 | PAW | 需考虑d电子 |
| 稀土元素 | PAW/ALL | f电子需要特殊处理 |
| 高精度要求 | ALL | 全电子计算 |

## 示例 (Example)

```fortran
&KIND Na
   ELEMENT Na
   BASIS_SET pob-TZVP
   POTENTIAL ALL
&END KIND

&KIND Cl
   ELEMENT Cl
   BASIS_SET pob-TZVP
   POTENTIAL GTH-PBE-q32
&END KIND
```

## 赝势验证 (Validation)

```bash
cp2k-datafile-lint --pseudopotential POTENTIALS
```

## 参考来源 (Sources)

- `cp2k_input_tools/pseudopotentials/`: 赝势验证实现
- `tests/inputs/GTH_POTENTIALS.*`: 赝势文件示例
