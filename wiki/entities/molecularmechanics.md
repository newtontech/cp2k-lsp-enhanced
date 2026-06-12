# 分子力学 (Molecular Mechanics)

## 概述 (Overview)

CP2K 支持混合量子力学/分子力学 (QM/MM) 计算，允许将 DFT 与力场结合。

## MM 方法 (MM Methods)

### FIST (Fast Ionic Subspace Technique)

```fortran
&FORCE_EVAL
   METHOD FIST
&END FORCE_EVAL
```

特点：
- 快速离子色势方法
- 适用于大系统
- 可以与 QM 耦合

### MT (Molecular Mechanics / Monte Carlo)

```fortran
&FORCE_EVAL
   METHOD MT
&END FORCE_EVAL
```

## QT/MM 耦合 (QM/MM Coupling)

### 设置示例

```fortran
&FORCE_EVAL
   METHOD Quickstep
   &SUBSYS
      &KIND C
         BASIS_SET DZVP-MOLOPT-SR-GTH
         POTENTIAL GTH-PBE
         MM_TYPE CHARMM
      &END KIND
      &KIND H
         BASIS_SET DZVP-MOLOPT-SR-GTH
         POTENTIAL GTH-PBE
         MM_TYPE CHARMM
      &END KIND
   &END SUBSYS

   &QMMM
      E_COUPL GAUSS
      &CELL
         &MM
            ! MM 区域定义
         &END MM
      &END CELL
   &END QMMM
&END FORCE_EVAL

&FORCE_EVAL
   METHOD FIST
   &SUBSYS
      ! MM 原子定义
   &END SUBSYS
   &MM
      FORCEFIELD charmm
   &END MM
&END FORCE_EVAL
```

## 力场 (Force Fields)

### CHARMM 力场

```fortran
&MM
   FORCEFIELD CHARMM
   PAR_FILE_NAME charmm.par
   PSF_FILE_NAME structure.psf
&END MM
```

### GROMOS 力场

```fortran
&MM
   FORCEFIELD GROMOS
&END MM
```

### 自定义力场

```fortran
&MM
   FORCEFIELD GENERIC
   &BOND
      ...
   &END BOND
   &ANGLE
      ...
   &END ANGLE
   &DIHEDRAL
      ...
   &END DIHEDRAL
   &IMPROPER
      ...
   &END IMPROPER
&END MM
```

## QMMM 节参数 (QMMM Section Parameters)

### E_COUPL (静电耦合)

```fortran
E_COUPL GAUSS
```

选项：
- `NONE`: 无静电耦合
- `ELSTAT`: 仅静电
- `GAUSS`: 高斯展开
- `COULOMB`: 库仑相互作用

### LINK_METHOD (连接方法)

```fortran
&QMMM
   LINK_METHOD LOCAL_RULE
&END QMMM
```

选项：
- `LOCAL_RULE`: 局部规则
- `FORCE`: 力方法

## MM_TYPE 关键字

在 KIND 节中指定 MM 类型：

```fortran
&KIND C
   ELEMENT C
   MM_TYPE CHARMM
   ! 如果不做 QM 计算，不需要基组
&END KIND
```

## 示例 (Examples)

### 纯 MM 计算

```fortran
&FORCE_EVAL
   METHOD FIST
   &SUBSYS
      &COORD
         C 0.0 0.0 0.0
         O 1.0 0.0 0.0
      &END COORD
      &KIND C
         ELEMENT C
         MM_TYPE CHARMM
      &END KIND
      &KIND O
         ELEMENT O
         MM_TYPE CHARMM
      &END KIND
   &END SUBSYS
   &MM
      FORCEFIELD CHARMM
   &END MM
&END FORCE_EVAL
```

### QM/MM 计算

```fortran
&FORCE_EVAL
   METHOD Quickstep
   &SUBSYS
      &KIND C
         ELEMENT C
         BASIS_SET DZVP-MOLOPT-SR-GTH
         POTENTIAL GTH-PBE
      &END KIND
   &END SUBSYS
   &QMMM
      E_COUPL GAUSS
      &CELL
         ABC 0.0 0.0 10.0
         &MM
            ATOMS 1-100
         &END MM
      &END CELL
   &END QMMM
&END FORCE_EVAL

&FORCE_EVAL
   METHOD FIST
   &SUBSYS
      &COORD
         ! MM 原子坐标
      &END COORD
   &END SUBSYS
   &MM
      FORCEFIELD CHARMM
   &END MM
&END FORCE_EVAL
```

## 参考来源 (Sources)

- CP2K 手册: QM/MM 方法
- CP2K 示例: QMMM 输入文件
