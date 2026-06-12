# SCF 自洽场收敛 (SCF Convergence)

## 概述 (Overview)

自洽场（SCF）迭代是 DFT 计算的核心步骤，需要正确配置以确保收敛。

## SCF 节结构

```fortran
&SCF
   EPS_SCF <threshold>
   MAX_SCF <max_iterations>
   SCF_GUESS <guess_method>
   &DIAGONALIZATION
      ...
   &END DIAGONALIZATION
   &MIXING
      ...
   &END MIXING
   &SMEAR
      ...
   &END SMEAR
&END SCF
```

## 关键参数

### EPS_SCF

SCF 收敛阈值：

```fortran
EPS_SCF 1.0E-7
```

| 精度级别 | EPS_SCF | 用途 |
|---------|---------|------|
| 粗略 | 1.0E-5 | 初步测试 |
| 标准 | 1.0E-6 - 1.0E-7 | 常规计算 |
| 高精度 | 1.0E-8 | 能量差计算 |
| 极高精度 | 1.0E-9 | 振动频率 |

### MAX_SCF

最大 SCF 迭代次数：

```fortran
MAX_SCF 100
```

### SCF_GUESS

初始猜测方法：

```fortran
SCF_GUESS ATOMIC     ! 原子密度叠加
SCF_GUESS RESTART    ! 从波函数文件读取
SCF_GUESS CORE       ! 核心哈密顿量猜测
SCF_GUESS HISTORICAL ! 使用历史信息
```

## 收敛策略

### 对角化 (Diagonalization)

```fortran
&DIAGONALIZATION
   ALGORITHM STANDARD
&END DIAGONALIZATION
```

算法选项：
- `STANDARD`: 标准对角化
- `DAVIDSON`: Davidson 方法
- `RI`: 分辨率恒等近似

### OT (Orbital Transformation)

适用于大系统：

```fortran
&SCF
   &OT
      MINIMIZER CG
      PRECONDITIONER FULL_SINGLE_INVERSE
   &END OT
&END SCF
```

### 混合 (Mixing)

```fortran
&MIXING
   METHOD BROYDEN_MIXING
   ALPHA 0.4
   BETA 1.5
   NBUFF 8
&END MIXING
```

混合方法：
- `BROYDEN_MIXING`: Broyden 混合
- `BROYDEN_MIXING_NEW`: 新版 Broyden
- `PULAY`: Pulay 混合
- `DIRECT_PULAY`: 直接 Pulay
- `LINEAR`: 线性混合

### 涂抹 (Smearing)

适用于金属或半导体系：

```fortran
&SMEAR
   METHOD FERMI_DIRAC
   ELECTRONIC_TEMPERATURE 300.0
&END SMEAR
```

涂抹方法：
- `FERMI_DIRAC`: 费米-狄拉克涂抹
- `GAUSSIAN`: 高斯涂抹
- `METHFESSEL_PAXTON`: Methfessel-Paxton

## 收敛问题排查

### 不收敛的原因

1. **初始猜测不好**
   - 尝试 `SCF_GUESS RESTART`
   - 或使用核心哈密顿量

2. **混合参数不当**
   - 调整 `ALPHA` (降低到 0.1-0.3)
   - 增加 `NBUFF`

3. **涂抹太小**
   - 增加 `ELECTRONIC_TEMPERATURE`
   - 或启用涂抹

4. **基组问题**
   - 检查基组匹配
   - 尝试更小的基组

5. **系统几何**
   - 优化几何结构
   - 检查原子间距

### 诊断技巧

```fortran
&PRINT
   &SCF
      ADD_LAST NUMERIC
   &END SCF
&END PRINT
```

输出每步 SCF 信息用于诊断。

## 示例 (Example)

### 标准配置

```fortran
&SCF
   EPS_SCF 1.0E-7
   MAX_SCF 100
   SCF_GUESS ATOMIC
   &DIAGONALIZATION
      ALGORITHM STANDARD
   &END DIAGONALIZATION
&END SCF
```

### 大系统 OT 方法

```fortran
&SCF
   EPS_SCF 1.0E-6
   MAX_SCF 50
   &OT
      MINIMIZER CG
      PRECONDITIONER FULL_SINGLE_INVERSE
   &END OT
&END SCF
```

### 金属系统

```fortran
&SCF
   EPS_SCF 1.0E-6
   MAX_SCF 200
   &SMEAR
      METHOD FERMI_DIRAC
      ELECTRONIC_TEMPERATURE 300.0
   &END SMEAR
   &MIXING
      METHOD BROYDEN_MIXING
      ALPHA 0.2
   &END MIXING
&END SCF
```

## 参考来源 (Sources)

- CP2K 手册: SCF 收敛策略
- `raw/assets/NaCl.inp`: SCF 配置示例
