# CLI 命令参考 (CLI Reference)

## 概述 (Overview)

CP2K 输入工具提供多个命令行工具，用于处理和验证 CP2K 输入文件。

## 命令列表 (Command List)

### cp2klint - 输入文件检查

```bash
cp2klint input.inp
```

**功能：** 语法检查输入文件

**选项：**
- `-E KEY=value`: 设置预处理器变量
- `-b PATH`: 设置基目录（用于 @INCLUDE）

**示例：**
```bash
cp2klint tests/inputs/unterminated_var.inp
# Syntax error: unterminated variable, in tests/inputs/unterminated_var.inp:
# line   36: @IF ${HP
#                ~~~~^
```

### fromcp2k - 转换为 JSON/YAML

```bash
fromcp2k input.inp [options]
```

**功能：** 将 CP2K 输入文件转换为 JSON 或 YAML

**选项：**
- `-y, --yaml`: 输出 YAML 而非 JSON
- `-c, --canonical`: 使用规范格式
- `-b PATH, --base-dir PATH`: @INCLUDE 搜索路径
- `-t TRAFO, --trafo TRAFO`: 键名转换 (auto/upper/lower)

**示例：**
```bash
fromcp2k NaCl.inp > NaCl.json
fromcp2k -y NaCl.inp > NaCl.yaml
fromcp2k --canonical NaCl.inp > NaCl_canonical.json
```

### tocp2k - 从 JSON/YAML 转换

```bash
tocp2k input.json
tocp2k -y input.yaml
```

**功能：** 将 JSON/YAML 转换回 CP2K 输入文件

**示例：**
```bash
tocp2k NaCl.json > Nacl_new.inp
```

### cp2kgen - 输入文件生成

```bash
cp2kgen template.inp "expression1" "expression2" ...
```

**功能：** 基于模板生成参数变化的输入文件

**表达式语法：**
```
path/to/keyword=value1,value2,value3
path/to/section/keyword=value1,value2,value3
```

**示例：**
```bash
# 截断能收敛测试
cp2kgen NaCl.inp "force_eval/dft/mgrid/cutoff=[800,900,1000]"
# 输出: NaCl-cutoff_800.inp, NaCl-cutoff_900.inp, NaCl-cutoff_1000.inp

# 多参数组合
cp2kgen NaCl.inp \
  "force_eval/dft/mgrid/cutoff=[800,1000]" \
  "force_eval/dft/xc/xc_functional/=[PBE,BLYP]"
# 输出 4 个文件: 2x2 组合
```

### cp2kget - 提取值

```bash
cp2kget input.inp "path/to/keyword"
```

**功能：** 从输入文件提取特定值

**路径语法：**
```
section_name/subsection_name/keyword_name
section_name/repeatable_section[index]/keyword
```

**示例：**
```bash
cp2kget restart.inp "force_eval/subsys/cell/a/0"
# 输出: 5.64123539364476

cp2kget restart.inp "global/project_name"
# 输出: my_calculation
```

### cp2k-language-server - LSP 服务器

```bash
cp2k-language-server
```

**功能：** 启动 Language Server Protocol 服务器

**编辑器配置见:** `wiki/concepts/lspfeatures.md`

### cp2k-datafile-lint - 数据文件检查

```bash
cp2k-datafile-lint --basis-set BASIS_SETS
cp2k-datafile-lint --pseudopotential POTENTIALS
```

**功能：** 验证基组和赝势文件格式

### cp2k-lsp - LSP 验证工具

```bash
cp2k-lsp validate input.inp
cp2k-lsp inspect diagnostics input.inp
cp2k-lsp inspect hover input.inp --line 10 --character 4
cp2k-lsp inspect format-preview input.inp --apply
```

**功能：** 使用 LSP 功能进行验证和检查

**子命令：**
- `validate`: 完整验证
- `inspect diagnostics`: 检查诊断
- `inspect hover`: 悬停检查
- `inspect references`: 引用查找
- `inspect format-preview`: 格式预览
- `inspect code-actions`: 代码操作

## 工作流示例 (Workflow Examples)

### 典型编辑验证循环

```bash
# 1. 编辑文件
vim NaCl.inp

# 2. 语法检查
cp2klint NaCl.inp

# 3. 完整验证
cp2k-lsp validate NaCl.inp

# 4. 检查诊断
cp2k-lsp inspect diagnostics NaCl.inp --json
```

### 参数扫描工作流

```bash
# 1. 生成输入文件
cp2kgen template.inp "force_eval/dft/mgrid/cutoff=[600,700,800,900,1000]"

# 2. 验证所有生成的文件
for f in template-cutoff_*.inp; do
    cp2k-lsp validate $f || echo "Error in $f"
done

# 3. 转换为 JSON 处理
for f in template-cutoff_*.inp; do
    fromcp2k $c > ${f%.inp}.json
done
```

### 格式转换工作流

```bash
# CP2K → JSON
fromcp2k input.inp > input.json

# 编辑 JSON
vim input.json

# JSON → CP2K
tocp2k input.json > input_formatted.inp

# 验证结果
cp2k-lsp validate input_formatted.inp
```

## 参考来源 (Sources)

- `raw/assets/README.md`: 完整 CLI 文档
- `cp2k_input_tools/cli/`: CLI 实现源码
- `tests/test_cli.py`: CLI 测试
