# GLOBAL 全局节 (GLOBAL Section)

## 概述 (Overview)

GLOBAL 节是 CP2K 输入文件的必需顶层节，定义计算的全局参数和项目设置。

## 关键字 (Keywords)

### PROJECT (项目名称)

```fortran
PROJECT my_calculation
```

设置项目名称，用于输出文件命名。

### RUN_TYPE (运行类型)

```fortran
RUN_TYPE ENERGY
RUN_TYPE ENERGY_FORCE
RUN_TYPE GEO_OPT
RUN_TYPE CELL_OPT
RUN_TYPE MD
```

可用值：
- `ENERGY`: 单点能量计算
- `ENERGY_FORCE`: 能量和力计算
- `GEO_OPT`: 几何优化
- `CELL_OPT`: 晶胞优化
- `MD`: 分子动力学
- `WAVEFUNCTION`: 波函数优化
- `BAND`: 能带结构计算

### PRINT_LEVEL (打印级别)

```fortran
PRINT_LEVEL LOW
PRINT_LEVEL MEDIUM
PRINT_LEVEL HIGH
PRINT_LEVEL DEBUG
```

控制输出详细程度。

### EXTENDED_TEMPERATURE (扩展温度)

```fortran
EXTENDED_TEMPERATURE 100.0
```

设置扩展拉格朗日方法的参考温度。

## 示例 (Example)

```fortran
&GLOBAL
   PROJECT NaCl_calculation
   RUN_TYPE ENERGY_FORCE
   PRINT_LEVEL MEDIUM
&END GLOBAL
```

## 参考来源 (Sources)

- `raw/assets/NaCl.inp`: 完整示例输入文件
- `cp2k_input_tools/parser.py`: GLOBAL 节解析实现
