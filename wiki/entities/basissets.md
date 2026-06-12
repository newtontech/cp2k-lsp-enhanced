# 基组 (Basis Sets)

## 概述 (Overview)

基组是描述电子波函数的数学函数集合。CP2K 支持多种基组格式和类型。

## 基组类型 (Basis Set Types)

### 高斯基组 (Gaussian Basis Sets)

CP2K 主要使用高斯基组：

- **MOLOPT**: 优化的分子基组
- **DZVP**: 双-ζ 价极化基组
- **TZVP**: 三-ζ 价极化基组
- **QZVP**: 四-ζ 价极化基组

### 基组选择标准

| 基组 | 大小 | 精度 | 适用场景 |
|------|------|------|----------|
| SZV | 小 | 低 | 初步测试 |
| DZVP | 中 | 中 | 常规计算 |
| TZVP | 大 | 高 | 精确计算 |
| QZVP | 很大 | 很高 | 高精度研究 |

## 基组文件格式 (Basis Set File Format)

### 新格式 (New Format)

```
# Basisset data for: H
#    Z    nExp   nPrim
      1     5      1
# exponent          contr. coeff.       exponent          contr. coeff.
   1.307000E+02    3.529720E-02        1.962000E+01    2.346060E-01
   4.446000E+00    8.187430E-01        1.213000E+00    1.000000E+00
```

## 基组指定 (Basis Set Specification)

```fortran
&KIND H
   ELEMENT H
   BASIS_SET DZVP-MOLOPT-SR-GTH
&END KIND
```

## 常用基组库 (Common Basis Set Libraries)

### MOLOPT 基组

专为 CP2K 优化的基组：

```fortran
BASIS_SET pob-TZVP
BASIS_SET DZVP-MOLOPT-SR-GTH
BASIS_SET TZVP-MOLOPT-GTH
```

### GTH 基组

Goedecker-Teter-Hutter 赝势配套基组：

```fortran
BASIS_SET DZVP-GTH
BASIS_SET TZVP-GTH
```

## 自定义基组 (Custom Basis Sets)

```fortran
&BASIS_SET
   ! 基组定义
&END BASIS_SET
```

## 基组验证 (Basis Set Validation)

使用 `cp2k-datafile-lint` 验证基组文件：

```bash
cp2k-datafile-lint --basis-set BASIS_SETS
```

## 参考来源 (Sources)

- `cp2k_input_tools/basissets/`: 基组验证实现
- `tests/inputs/BASIS_MOLOPT.*`: 基组文件示例
- CP2K 基组库: https://www.cp2k.org/basissets
