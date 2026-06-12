# 解析器架构 (Parser Architecture)

## 概述 (Overview)

CP2K 输入工具采用分层解析架构，包括预处理、词法分析、语法分析和语义验证。

## 解析流程 (Parsing Pipeline)

```
输入文件 → 预处理器 → 词法分析器 → 语法分析器 → 语义验证器 → 输出
```

## 1. 预处理器 (Preprocessor)

### 功能

- 变量展开 (`@SET`, `${VAR}`)
- 条件编译 (`@IF`, `@ENDIF`)
- 文件包含 (`@INCLUDE`)
- 行拼接

### 实现

```python
# cp2k_input_tools/preprocessor.py
class CP2KPreprocessor:
    def process(self, text: str, variables: dict = None) -> str:
        # 处理 @SET 变量
        # 处理 @IF/@ENDIF 条件
        # 处理 @INCLUDE 文件
        ...
```

### 示例

输入：
```fortran
@SET GRID 8
&KPOINTS
   SCHEME MONKHORST-PACK ${GRID} ${GRID} ${GRID}
&END KPOINTS
```

预处理后：
```fortran
&KPOINTS
   SCHEME MONKHORST-PACK 8 8 8
&END KPOINTS
```

## 2. 词法分析器 (Tokenizer)

### 功能

- 分词（关键字、值、注释）
- 识别节开始/结束
- 追踪上下文（行号、列号）

### 实现

```python
# cp2k_input_tools/tokenizer.py
class Tokenizer:
    def tokenize(self, text: str) -> Iterator[Token]:
        for line in text.split('\n'):
            # 跳过注释
            # 识别节标记 (&SECTION)
            # 识别关键字 (KEYWORD value)
            ...
```

### Token 类型

- `SECTION_START`: `&SECTION_NAME`
- `SECTION_END`: `&END SECTION_NAME`
- `KEYWORD`: `KEYWORD value`
- `COMMENT`: `! comment`
- `EMPTY`: 空行

## 3. 语法分析器 (Parser)

### 功能

- 构建 XML 树
- 验证语法正确性
- 提取节参数

### 实现

```python
# cp2k_input_tools/parser.py
class CP2KInputParser:
    def __init__(self, xmlspec=DEFAULT_CP2K_INPUT_XML):
        self._spec = ET.parse(xmlspec)  # 加载 CP2K 输入规范

    def parse(self, fhandle) -> dict:
        # 预处理
        # 词法分析
        # 语法分析
        # 构建输出树
        ...
```

### XML Schema

CP2K 输入规范存储在 `cp2k_input.xml`：

```xml
<SECTION NAME="GLOBAL">
    <KEYWORD NAME="PROJECT">
        <DATA_TYPE>STRING</DATA_TYPE>
    </KEYWORD>
    <KEYWORD NAME="RUN_TYPE">
        <DATA_TYPE>ENUMERATION</DATA_TYPE>
    </KEYWORD>
</SECTION>
```

## 4. 语义验证器 (Validator)

### 功能

- 类型检查
- 值范围验证
- 逻辑一致性检查
- 物理约束验证

### 实现

```python
# cp2k_input_tools/validator.py
class Validator:
    def validate(self, tree: dict) -> ValidationResult:
        # 检查 RUN_TYPE/MOTION 一致性
        # 检查 DFT 参数冲突
        # 检查元素符号有效性
        ...
```

### 验证规则

- `RUN_TYPE_MOTION_MAP`: RUN_TYPE 与 MOTION 节的对应关系
- `ELEMENTS`: 有效元素符号列表
- `REMOVED_KEYWORDS`: 已移除的关键字
- `DEPRECATED_KEYWORDS`: 已弃用的关键字

## 5. 类型检查器 (Typechecker)

### 功能

- 单位转换
- 数据类型验证
- 关键字参数验证

### 实现

```python
# cp2k_input_tools/typecheck.py
class TypeChecker:
    def check_keyword(self, keyword: Keyword, value: Any):
        # 验证数据类型
        # 转换单位
        # 检查枚举值
        ...
```

## 输出格式 (Output Formats)

### Canonical Format

严格遵循 CP2K 结构：

```json
{
  "+global": {
    "print_level": "medium"
  },
  "+force_eval": [{
    "method": "quickstep",
    "+DFT": {...}
  }]
}
```

### Simplified Format

更易读的格式：

```json
{
  "global": {
    "print_level": "medium"
  },
  "force_eval": {
    "method": "quickstep",
    "DFT": {...}
  }
}
```

## 错误处理 (Error Handling)

### 错误类型

```python
# cp2k_input_tools/parser_errors.py
class ParserError(Exception):
    """基础解析错误"""
class InvalidNameError(ParserError):
    """无效的节或关键字名称"""
class SectionMismatchError(ParserError):
    """节开始/结束不匹配"""
class InvalidParameterError(ParserError):
    """无效的节参数"""
```

### 错误报告

```python
try:
    tree = parser.parse(fhandle)
except ParserError as e:
    print(f"Syntax error: {e}")
    print(f"Line {e.line}: {e.context}")
```

## 参考来源 (Sources)

- `cp2k_input_tools/preprocessor.py`: 预处理器实现
- `cp2k_input_tools/tokenizer.py`: 词法分析器实现
- `cp2k_input_tools/parser.py`: 语法分析器实现
- `cp2k_input_tools/validator.py`: 验证器实现
- `cp2k_input_tools/typecheck.py`: 类型检查器实现
