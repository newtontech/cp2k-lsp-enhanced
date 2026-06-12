# 诊断错误目录 (Diagnostics Catalog)

## 概述 (Overview)

完整的 CP2K 输入文件诊断错误代码和消息参考。

## 错误分类 (Error Categories)

### 语法错误 (Syntax Errors)

#### E001: 未终止的节 (Unterminated Section)

```
Line 10: &GLOBAL
Line 15: ^ file ends without &END GLOBAL
```

**原因：** 节开始后没有对应的 `&END`

**修复：** 添加匹配的 `&END SECTION_NAME`

---

#### E002: 节名称不匹配 (Section Name Mismatch)

```
Line 5: &END FORCE_EVAL
Expected: &END GLOBAL
```

**原因：** `&END` 后的名称与最近的 `&SECTION` 不匹配

**修复：** 检查节名称拼写或嵌套顺序

---

#### E003: 未终止的变量 (Unterminated Variable)

```
Line 36: @IF ${HP
                 ~~~~^
```

**原因：** 预处理器变量未正确闭合

**修复：** 使用 `${VAR}` 或 `$VAR` 格式

---

#### E004: 未定义的变量引用 (Undefined Variable Reference)

```
Line 20: ${UNDEFINED_VAR}
             ^^^^^^^^^^^^^
Variable 'UNDEFINED_VAR' is not defined
```

**原因：** 引用了未通过 `@SET` 定义的变量

**修复：** 添加 `@SET UNDEFINED_VAR value`

---

#### E005: 无效的条件表达式 (Invalid Conditional Expression)

```
Line 10: @IF ${VAR} == value
                    ^^
Expected: ==, !=, <, >, <=, >=
```

**原因：** 条件运算符无效

**修复：** 使用有效的比较运算符

---

### Schema 错误 (Schema Errors)

#### E101: 未知的节 (Unknown Section)

```
Line 15: &UNKNOW_SECTION
            ^^^^^^^^^^^^^^
Unknown section 'UNKNOW_SECTION'
Did you mean: 'FORCE_EVAL'?
```

**原因：** 节名称不在 XML Schema 中

**修复：** 检查拼写或查阅 CP2K 手册

---

#### E102: 未知的节参数 (Invalid Section Parameter)

```
Line 10: &KIND UNKNOW_KIND
            ^^^^^^^^^^^^
Section parameter 'UNKNOW_KIND' not found in ELEMENT values
```

**原因：** 节参数值无效

**修复：** 使用有效的元素符号或参数

---

#### E103: 未知的关键字 (Unknown Keyword)

```
Line 12:   PROJET test
           ^^^^^^
Unknown keyword 'PROJET' in section GLOBAL
Did you mean 'PROJECT'?
```

**原因：** 关键字名称拼写错误

**修复：** 修正关键字名称

---

#### E104: 无效的关键字值 (Invalid Keyword Value)

```
Line 15:   RUN_TYPE UNKNOWN
                  ^^^^^^^^
Invalid value 'UNKNOWN' for keyword RUN_TYPE
Valid values: ENERGY, ENERGY_FORCE, GEO_OPT, ...
```

**原因：** 关键字值不在允许的枚举中

**修复：** 使用有效的值

---

#### E105: 无效的数据类型 (Invalid Data Type)

```
Line 20:   CUTOFF abc
               ^^^
Expected float value for keyword CUTOFF
```

**原因：** 值类型与关键字类型不匹配

**修复：** 使用正确的数据类型

---

### 语义错误 (Semantic Errors)

#### E201: RUN_TYPE 与 MOTION 不匹配 (RUN_TYPE Motion Mismatch)

```
Line 5: RUN_TYPE ENERGY
...
Line 50: &MOTION
           &GEO_OPT
...
Error: RUN_TYPE 'ENERGY' is a static type and should not have MOTION section
```

**原因：** RUN_TYPE 与 MOTION 节类型不兼容

**修复：** 更改 RUN_TYPE 或移除 MOTION 节

---

#### E202: 缺少必需的 MOTION 节 (Missing Required MOTION)

```
Line 5: RUN_TYPE GEO_OPT
...
Error: RUN_TYPE 'GEO_OPT' requires &GEO_OPT subsection in &MOTION
```

**原因：** RUN_TYPE 需要对应的 MOTION 子节

**修复：** 添加相应的 MOTION 子节

---

#### E203: 无效的元素符号 (Invalid Element Symbol)

```
Line 30: ELEMENT Xx
             ^^
Invalid element symbol 'Xx'
Valid symbols: H, He, Li, ...
```

**原因：** 元素符号不在周期表中

**修复：** 使用正确的元素符号（首字母大写）

---

#### E204: 基组文件未找到 (Basis Set File Not Found)

```
Line 25: BASIS_SET_FILE_NAME ./BASIS_SETS
                          ^^^^^^^^^^^^^^^
File not found: ./BASIS_SETS
```

**原因：** 基组文件不存在

**修复：** 检查文件路径或设置正确的基组文件

---

#### E205: 赝势文件未找到 (Potential File Not Found)

```
Line 26: POTENTIAL_FILE_NAME ./POTENTIALS
                          ^^^^^^^^^^^^^^^
File not found: ./POTENTIALS
```

**原因：** 赝势文件不存在

**修复：** 检查文件路径

---

#### E206: KPoints 与周期性冲突 (KPoints Periodicity Conflict)

```
Line 40: PERIODIC NONE
...
Line 50: &KPOINTS
Error: KPOINTS section specified but PERIODIC is NONE
```

**原因：** 非周期系统不应有 KPOINTS 节

**修复：** 移除 KPOINTS 或更改 PERIODIC 设置

---

### 警告 (Warnings)

#### W001: 已弃用的关键字 (Deprecated Keyword)

```
Line 45: QUIP ...
        ^^^^
Keyword 'QUIP' is deprecated. Use other machine-learning potentials instead.
```

**建议：** 更新到推荐的方法

---

#### W002: 重复的节定义 (Duplicate Section Definition)

```
Line 10: &KIND Na
Line 30: &KIND Na
Warning: Section 'KIND' with parameter 'Na' is defined multiple times
```

**建议：** 检查是否需要重复定义

---

#### W003: 缺少推荐关键字 (Missing Recommended Keyword)

```
Line 20: &SCF
           EPS_SCF 1.0E-6
Warning: Keyword 'MAX_SCF' is recommended but not set
```

**建议：** 添加推荐的设置

---

#### W004: 已移除的关键字 (Removed Keyword)

```
Line 50: SINGLE_PRECISION_MATRICES .TRUE.
        ^^^^^^^^^^^^^^^^^^^^^^^^
Keyword 'SINGLE_PRECISION_MATRICES' was removed in CP2K 2024.1
```

**建议：** 移除此关键字或使用替代方案

---

## 参考来源 (Sources)

- `cp2k_input_tools/validator.py`: 验证规则实现
- `cp2k_input_tools/parser_errors.py`: 错误定义
- `tests/test_validation.py`: 验证测试用例
