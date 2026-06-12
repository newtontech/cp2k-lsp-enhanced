# FORCE_EVAL 力计算节 (FORCE_EVAL Section)

## 概述 (Overview)

FORCE_EVAL 节定义如何计算力和能量。一个输入文件可以包含多个 FORCE_EVAL 节用于混合计算。

## 结构 (Structure)

```
&FORCE_EVAL
   METHOD <method>
   &SUBSECTIONS...
&END FORCE_EVAL
```

## 关键字 (Keywords)

### METHOD (方法)

```fortran
METHOD Quickstep
METHOD MT
METHOD FIST
```

可用方法：
- `Quickstep`: DFT 方法
- `MT`: 分子力学/蒙特卡洛
- `FIST`: 快速离子色势

### STRESS_TENSOR (应力张量)

```fortran
STRESS_TENSOR ANALYTICAL
STRESS_TENSOR NUMERICAL
STRESS_TENSOR NONE
```

## 子节 (Subsections)

### DFT 节

密度泛函理论计算参数。

### SUBSYS 节

分子系统定义（原子、坐标、晶胞等）。

## 示例 (Example)

```fortran
&FORCE_EVAL
   METHOD Quickstep
   STRESS_TENSOR ANALYTICAL

   &DFT
      BASIS_SET_FILE_NAME BASIS_SETS
      POTENTIAL_FILE_NAME POTENTIALS
      &XC
         &XC_FUNCTIONAL PBE
         &END XC_FUNCTIONAL
      &END XC
   &END DFT

   &SUBSYS
      &KIND H
         ELEMENT H
         BASIS_SET DZVP-MOLOPT-SR-GTH
         POTENTIAL GTH-PBE
      &END KIND
      &COORD
         H 0.0 0.0 0.0
      &END COORD
   &END SUBSYS
&END FORCE_EVAL
```

## 参考来源 (Sources)

- `raw/assets/NaCl.inp`: 完整示例
- `cp2k_input_tools/parser.py`: 解析器实现
