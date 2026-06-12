# SUBSYS 子系统节 (SUBSYS Section)

## 概述 (Overview)

SUBSYS 节定义分子系统的物理结构，包括晶胞、原子种类、坐标等。

## 主要子节 (Main Subsections)

### CELL 晶胞节

```fortran
&CELL
   A [angstrom] 4.07419 0.0 0.0
   B [angstrom] 2.037095 3.52835204 0.0
   C [angstrom] 2.037095 1.17611735 3.32656221
   PERIODIC XYZ
&END CELL
```

#### 关键字

- `A, B, C`: 晶格向量
- `PERIODIC`: 周期性方向 (NONE, X, Y, Z, XY, XZ, YZ, XYZ)
- `CELL_REF`: 参考晶胞（用于形变计算）

### KIND 原子种类节

```fortran
&KIND Na
   ELEMENT Na
   BASIS_SET pob-TZVP
   POTENTIAL ALL
&END KIND
```

#### 关键字

- `ELEMENT`: 元素符号
- `BASIS_SET`: 基组名称
- `POTENTIAL`: 赝势名称
- `MAGNETISM`: 磁性设置

### COORD 坐标节

```fortran
&COORD
   Na 0.0 0.0 0.0
   Cl 1.5 1.5 1.5
&END COORD
```

#### 坐标格式

```fortran
! 直角坐标
Atom x y z

! 分数坐标
&COORD
   SCALED TRUE
   Na 0.0 0.0 0.0
&END COORD
```

### TOPOLOGY 拓扑节

```fortran
&TOPOLOGY
   COORD_FILE_NAME structure.xyz
   COORD_FILE_FORMAT XYZ
&END TOPOLOGY
```

### CONSTRAINT 约束节

```fortran
&CONSTRAINT
   &COLLECTIVE
      ...
   &END COLLECTIVE
&END CONSTRAINT
```

## 示例 (Example)

```fortran
&SUBSYS
   &CELL
      A 5.64 0.0 0.0
      B 0.0 5.64 0.0
      C 0.0 0.0 5.64
      PERIODIC XYZ
   &END CELL

   &KIND Na
      ELEMENT Na
      BASIS_SET pob-TZVP
      POTENTIAL ALL
   &END KIND

   &KIND Cl
      ELEMENT Cl
      BASIS_SET pob-TZVP
      POTENTIAL ALL
   &END KIND

   &COORD
      Na 0.0 0.0 0.0
      Cl 2.82 2.82 2.82
   &END COORD
&END SUBSYS
```

## 参考来源 (Sources)

- `raw/assets/NaCl.inp`: 完整 SUBSYS 示例
- `cp2k_input_tools/parser.py`: 解析实现
