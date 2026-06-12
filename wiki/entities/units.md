# 单位系统 (Unit System)

## 概述 (Overview)

CP2K 支持显式单位指定，使用 Pint 库进行单位转换。

## 单位指定语法 (Unit Specification Syntax)

```fortran
KEYWORD [unit] value
KEYWORD [unit] value1 value2 value3
```

### 示例

```fortran
CUTOFF [Ry] 800.0
TEMPERATURE [K] 300.0
PRESSURE [GPa] 0.0
CELL_ANGLE [deg] 90.0
```

## 常用单位 (Common Units)

### 能量单位 (Energy Units)

| 单位 | 符号 | 说明 |
|------|------|------|
| Rydberg | `[Ry]` | CP2K 默认能量单位 |
| Hartree | `[Hartree]` | 原子单位 |
| eV | `[eV]` | 电子伏特 |
| kcal/mol | `[kcal/mol]` | 千卡每摩尔 |
| kJ/mol | `[kJ/mol]` | 千焦每摩尔 |

### 距离单位 (Distance Units)

| 单位 | 符号 | 说明 |
|------|------|------|
| Bohr | `[bohr]` | CP2K 默认长度单位 |
| Angstrom | `[angstrom]` | 埃 |
| pm | `[pm]` | 皮米 |
| nm | `[nm]` | 纳米 |

### 温度单位 (Temperature Units)

| 单位 | 符号 | 说明 |
|------|------|------|
| Kelvin | `[K]` | 开尔文 |
| Celsius | `[C]` | 摄氏度 |
| Fahrenheit | `[F]` | 华氏度 |

### 压力单位 (Pressure Units)

| 单位 | 符号 | 说明 |
|------|------|------|
| GPa | `[GPa]` | 吉帕 |
| bar | `[bar]` | 巴 |
| atm | `[atm]` | 标准大气压 |
| Pa | `[Pa]` | 帕斯卡 |

### 角度单位 (Angle Units)

| 单位 | 符号 | 说明 |
|------|------|------|
| degree | `[deg]` | 度 |
| radian | `[rad]` | 弧度 |

### 时间单位 (Time Units)

| 单位 | 符号 | 说明 |
|------|------|------|
| fs | `[fs]` | 飞秒 (10^-15 s) |
| ps | `[ps]` | 皮秒 (10^-12 s) |
| ns | `[ns]` | 纳秒 (10^-9 s) |

## 单位转换 (Unit Conversion)

### 默认单位 (Default Units)

当没有指定单位时，CP2K 使用默认单位：

```fortran
CUTOFF 800.0  ! 默认为 Ry
A 5.64 0.0 0.0  ! 默认为 bohr
TEMPERATURE 300.0  ! 默认为 K
```

### 转换示例

```fortran
! 这些是等效的
CUTOFF 800.0  ! 800 Ry
CUTOFF [Ry] 800.0
CUTOFF [Hartree] 400.0  ! 1 Hartree = 2 Ry

! 长度转换
A 10.65 0.0 0.0  ! 10.65 bohr
A [angstrom] 5.64 0.0 0.0  ! 等效
```

## 单位在输入文件中的使用 (Unit Usage in Input Files)

### 晶格向量

```fortran
&CELL
   A [angstrom] 4.07419 0.0 0.0
   B [angstrom] 2.037095 3.52835204 0.0
   C [angstrom] 2.037095 1.17611735 3.32656221
&END CELL
```

### MD 参数

```fortran
&MD
   TIMESTEP [fs] 0.5
   TEMPERATURE [K] 300.0
&END MD
```

### 压力

```fortran
&CELL_OPT
   PRESSURE [GPa] 0.0
&END CELL_OPT
```

### 截断能

```fortran
&MGRID
   CUTOFF [Ry] 800
   REL_CUTOFF [Ry] 80
&END MGRID
```

## 单位验证 (Unit Validation)

输入工具会验证单位的有效性：

```bash
# 单位拼写错误
&MGRID
   CUTOFF [Rydberg] 800  ! 错误：应为 Ry
&END MGRID
```

## 支持的单位库 (Supported Unit Library)

基于 Pint 库，支持 SI 和常用单位：

```python
# cp2k_input_tools/keyword_helpers.py
UREG = UnitRegistry(system='atomic')
```

## 单位参考 (Unit Reference)

| 量 | CP2K 默认 | 常用单位 |
|------|----------|----------|
| 能量 | Hartree/Ry | eV, kcal/mol |
| 长度 | bohr | angstrom, pm |
| 质量 | atomic mass | amu, kg |
| 时间 | atomic time | fs, ps |
| 温度 | K | K, C |
| 压力 | GPa | GPa, bar |

## 参考来源 (Sources)

- `cp2k_input_tools/keyword_helpers.py`: 单位处理实现
- `cp2k_input_tools/pint_units.txt`: Pint 单位定义
