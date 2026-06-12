# 验证规则 (Validation Rules)

## 概述 (Overview)

CP2K 输入工具提供多层次验证，包括语法检查、Schema 验证和语义验证。

## 验证层次 (Validation Layers)

### 1. 语法验证 (Syntax Validation)

**检查内容：**
- 节开始/结束匹配
- 关键字格式
- 预处理指令语法
- 变量引用格式

**错误示例：**
```fortran
! 错误：节结束不匹配
&GLOBAL
   PROJECT test
&END FORCE_EVAL  ! 应该是 &END GLOBAL
```

### 2. Schema 验证 (Schema Validation)

**检查内容：**
- 已知节名称
- 已知关键字名称
- 数据类型匹配
- 值范围检查

**错误示例：**
```fortran
! 错误：未知关键字
&GLOBAL
   PROJECT test
   UNKNOW_KEY value  ! 拼写错误
&END GLOBAL
```

### 3. 语义验证 (Semantic Validation)

**检查内容：**
- RUN_TYPE 与 MOTION 一致性
- DFT 参数冲突
- 元素符号有效性
- 物理约束检查

**错误示例：**
```fortran
! 错误：RUN_TYPE 与 MOTION 不匹配
&GLOBAL
   RUN_TYPE ENERGY
&END GLOBAL

&MOTION
   &GEO_OPT
      ...
   &END GEO_OPT
&END MOTION
! ENERGY 类型不需要 MOTION 节
```

## 具体验证规则 (Specific Validation Rules)

### RUN_TYPE/MOTION 规则

```python
RUN_TYPE_MOTION_MAP = {
    "GEO_OPT": {"GEO_OPT"},
    "MD": {"MD"},
    "CELL_OPT": {"CELL_OPT"},
    "BAND": {"BAND"},
    "MC": {"MC"},
    "VIBRATIONAL_ANALYSIS": {"VIBRATIONAL_ANALYSIS"},
}

STATIC_RUN_TYPES = {
    "ENERGY", "ENERGY_FORCE", "WAVEFUNCTION",
    "ELECTRONIC_SPECTRA", "ELASTIC_CONSTANT"
}
```

**验证逻辑：**
1. 如果 RUN_TYPE 为 STATIC，不应有 MOTION 节
2. 如果 RUN_TYPE 需要 MOTION，必须存在对应的子节
3. MOTION 节类型必须与 RUN_TYPE 匹配

### 元素符号规则

```python
ELEMENTS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    # ... 周期表所有元素
}
```

**验证：**
- KIND 节的 ELEMENT 必须在 ELEMENTS 集合中
- 大小写敏感（需首字母大写）

### 已移除关键字

```python
REMOVED_KEYWORDS = {
    "SINGLE_PRECISION_MATRICES",
    "BROYDEN_MIXING_NEW",
    "KP_RI_EXTENSION_FACTOR",
}
```

### 已弃用关键字

```python
DEPRECATED_KEYWORDS = {
    "QUIP": "Use other machine-learning potentials instead.",
    "PEXSI": "PEXSI support is deprecated in CP2K 2024.1.",
}
```

### DFT 参数冲突

检查：
- GAPW 与 GPW 的互斥参数
- 基组与赝势的兼容性
- KPoints 与周期性的一致性

## 诊断格式 (Diagnostic Format)

```python
@dataclass
class Diagnostic:
    severity: str  # "error", "warning", "info"
    source: str  # "cp2k-parser", "cp2k-schema", "cp2k-lint"
    code: str  # 错误代码
    message: str  # 错误描述
    line: Optional[int]
    column: Optional[int]
    suggested_fix: Optional[str]
```

## 常见错误代码 (Common Error Codes)

| 代码 | 说明 | 严重性 |
|------|------|--------|
| `syntax-error` | 语法错误 | ERROR |
| `unknown-section` | 未知节 | ERROR |
| `unknown-keyword` | 未知关键字 | ERROR |
| `invalid-value` | 无效值 | ERROR |
| `runtype-motion-mismatch` | RUN_TYPE/MOTION 不匹配 | ERROR |
| `deprecated-keyword` | 已弃用关键字 | WARNING |
| `missing-required` | 缺少必需关键字 | ERROR |
| `duplicate-section` | 重复节 | WARNING |

## 验证工具使用 (Validation Tools)

### cp2klint

```bash
cp2klint input.inp
```

快速语法检查。

### cp2k-lsp validate

```bash
cp2k-lsp validate input.inp
cp2k-lsp validate input.inp --json
cp2k-lsp validate input.inp --fail-on-error
```

完整语法和语义验证。

### cp2k-lsp validate --dry-run

```bash
cp2k-lsp validate input.inp --dry-run --cp2k-exe cp2k.psmp
```

使用 CP2K 二进制进行完整验证。

## 示例诊断输出 (Example Diagnostic Output)

```json
{
  "diagnostics": [
    {
      "severity": "error",
      "source": "cp2k-schema",
      "code": "unknown-keyword",
      "message": "Unknown keyword 'PROJET' in section GLOBAL",
      "line": 12,
      "column": 3,
      "suggested_fix": "Did you mean 'PROJECT'?"
    },
    {
      "severity": "warning",
      "source": "cp2k-lint",
      "code": "deprecated-keyword",
      "message": "Keyword 'QUIP' is deprecated. Use other machine-learning potentials instead.",
      "line": 45,
      "column": 8
    }
  ],
  "error_count": 1,
  "warning_count": 1
}
```

## 参考来源 (Sources)

- `cp2k_input_tools/validator.py`: 验证器实现
- `cp2k_input_tools/linter.py`: Linter 实现
- `cp2k_input_tools/typecheck.py`: 类型检查器
- `tests/test_validation.py`: 验证测试
