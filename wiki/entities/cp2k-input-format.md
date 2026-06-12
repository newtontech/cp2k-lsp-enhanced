# CP2K 输入文件格式 (CP2K Input File Format)

## 概述 (Overview)

CP2K 输入文件使用基于 Fortran NAMELIST 风格的格式，具有以下特点：

- 基于节（Section）的结构
- 关键字-值对
- 支持变量和预处理指令
- 大小写不敏感

## 基本语法 (Basic Syntax)

### 节定义 (Section Definition)

```fortran
&SECTION_NAME
   # 关键字和内容
&END SECTION_NAME
```

### 关键字语法 (Keyword Syntax)

```fortran
KEYWORD value
KEYWORD value1 value2 value3
```

## 预处理指令 (Preprocessor Directives)

### 变量设置 (@SET)

```fortran
@SET VAR_NAME value
```

### 变量引用 (Variable Reference)

```fortran
${VAR_NAME}
$VAR_NAME
```

### 条件编译 (@IF/@ENDIF)

```fortran
@IF ${VAR_NAME} == value
   # 内容
@ENDIF
```

### 文件包含 (@INCLUDE)

```fortran
@INCLUDE path/to/file.inp
```

## 注释 (Comments)

```fortran
! 这是注释
# 这也是注释
```

## 数据类型 (Data Types)

| 类型 | 示例 | 说明 |
|------|------|------|
| INTEGER | 42 | 整数 |
| FLOAT | 3.14 | 浮点数 |
| BOOLEAN | TRUE, FALSE | 布尔值 |
| STRING | "filename" | 字符串 |
| KEYWORD | PBE, LDA | 枚举关键字 |

## 单位 (Units)

CP2K 支持显式单位指定：

```fortran
CUTOFF [angstrom] 4.0
TEMPERATURE [kelvin] 300.0
```

## 示例 (Example)

```fortran
&GLOBAL
   PROJECT test
   RUN_TYPE ENERGY
   PRINT_LEVEL MEDIUM
&END GLOBAL

&FORCE_EVAL
   METHOD Quickstep
   &DFT
      &XC
         &XC_FUNCTIONAL PBE
         &END XC_FUNCTIONAL
      &END XC
   &END DFT
&END FORCE_EVAL
```

## 参考来源 (Sources)

- `raw/assets/docs/`: CP2K 输入工具文档
- `raw/assets/README.md`: 项目 README
- CP2K 官方手册: https://manual.cp2k.org/
