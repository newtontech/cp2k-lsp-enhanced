# LSP 功能特性 (LSP Features)

## 概述 (Overview)

CP2K Language Server 提供完整的 LSP 功能，支持 VS Code、vim、Emacs 等编辑器。

## 核心功能 (Core Features)

### 1. 诊断 (Diagnostics)

实时语法和语义检查：

```python
# LSP 服务器端
async def validate(document):
    diagnostics = []

    # 语法检查
    syntax_errors = parser.validate(document.text)
    diagnostics.extend(syntax_errors)

    # 语义检查
    semantic_errors = validator.validate(tree)
    diagnostics.extend(semantic_errors)

    return diagnostics
```

**诊断来源：**

| 来源 | 说明 |
|------|------|
| `cp2k-parser` | 词法/语法错误 |
| `cp2k-schema` | Schema 验证（未知关键字） |
| `cp2k-lint` | 语义验证（RUN_TYPE/MOTION 一致性） |
| `cp2k-semantics` | 物理约束验证 |

### 2. 自动补全 (Completion)

基于 XML Schema 的智能补全：

```python
async def completion(params):
    # 获取当前位置的上下文
    context = get_context(params.position)

    # 从 Schema 获取可用关键字
    if context.in_section:
        keywords = schema.get_section_keywords(context.section_name)
        return [CompletionItem(name=kw) for kw in keywords]
```

**补全类型：**

- 节名称 (`&GLOBAL`, `&FORCE_EVAL`)
- 关键字名称 (`PROJECT`, `RUN_TYPE`)
- 枚举值 (`ENERGY`, `PBE`)
- 变量名 (`${VAR_NAME}`)

### 3. 悬停提示 (Hover)

显示关键字的详细信息：

```python
async def hover(params):
    keyword = get_keyword_at_position(params.position)

    # 从 Schema 获取描述
    info = schema.get_keyword_info(keyword)

    return Hover(contents=MarkupContent(
        language="markdown",
        value=f"**{keyword}**\n\n{info.description}\n\nType: {info.type}"
    ))
```

### 4. 定义跳转 (Go to Definition)

跳转到变量定义位置：

```python
async def definition(params):
    # 获取变量引用
    var_name = get_variable_ref_at_position(params.position)

    # 查找定义位置
    definitions = find_variable_definitions(document.text, var_name)

    return [Location(uri=document.uri, range=defn.position)]
```

### 5. 引用查找 (Find References)

查找变量的所有引用：

```python
async def references(params):
    var_name = get_variable_at_position(params.position)

    refs = []
    for line in document.text.split('\n'):
        if f"${{{var_name}}}" in line or f"${var_name}" in line:
            refs.append(Location(...))

    return refs
```

### 6. 文档符号 (Document Symbols)

显示输入文件的符号树：

```python
async def document_symbols(params):
    tree = parser.parse(document.text)

    symbols = []
    for section in tree.sections:
        symbols.append(DocumentSymbol(
            name=section.name,
            kind=SymbolKind.Struct,
            range=section.range,
            children=section.children
        ))

    return symbols
```

### 7. 代码操作 (Code Actions)

快速修复和重构：

```python
async def code_actions(params):
    actions = []

    # 修复建议
    for diagnostic in params.context.diagnostics:
        if diagnostic.code == "deprecated_keyword":
            actions.append(CodeAction(
                title=f"Replace {keyword} with {replacement}",
                kind=CodeActionKind.QuickFix,
                edit=TextEdit(replace=replacement)
            ))

    return actions
```

**支持的操作：**

- 修复已弃用的关键字
- 修复拼写错误
- 移除重复节
- 格式化代码

### 8. 格式化 (Formatting)

美化输入文件：

```python
async def formatting(params):
    # 使用 CP2K formatter
    formatted = formatter.format(document.text)
    return [TextEdit(new_text=formatted)]
```

**格式化规则：**

- 节缩进
- 关键字对齐
- 注释位置
- 空行规范

### 9. 重命名 (Rename)

重命名变量：

```python
async def rename(params):
    old_name = get_variable_at_position(params.position)
    new_name = params.new_name

    # 创建工作区编辑
    edits = {}
    for doc in workspace.documents:
        refs = find_variable_refs(doc.text, old_name)
        edits[doc.uri] = create_edits(refs, new_name)

    return WorkspaceEdit(edits)
```

## LSP 服务器启动

```bash
cp2k-language-server
```

## 编辑器配置 (Editor Configuration)

### VS Code

```json
{
  "languageserver": {
    "cp2k": {
      "command": "cp2k-language-server",
      "filetypes": ["cp2k"]
    }
  }
}
```

### vim (ALE)

```vim
call ale#Set('cp2k_lsp_executable', 'cp2k-language-server')
call ale#linter#Define('cp2k', {
\   'name': 'language_server',
\   'lsp': 'stdio',
\   'executable': {b -> ale#Var(b, 'cp2k_lsp_executable')},
\})
```

### Emacs (eglot)

```elisp
(add-to-list 'eglot-server-programs
             '(cp2k-mode . ("cp2k-language-server")))
```

## CLI 检查工具 (CLI Inspection Tools)

### 诊断检查

```bash
cp2k-lsp inspect diagnostics input.inp
cp2k-lsp inspect diagnostics input.inp --fail-on-error
```

### 悬停检查

```bash
cp2k-lsp inspect hover input.inp --line 10 --character 4
```

### 引用检查

```bash
cp2k-lsp inspect references input.inp --line 5 --character 2
```

### 格式预览

```bash
cp2k-lsp inspect format-preview input.inp
cp2k-lsp inspect format-preview input.inp --apply
```

## 参考来源 (Sources)

- `cp2k_input_tools/ls.py`: LSP 实现源码
- `docs/agent-workflow.md`: LSP + CLI 验证工作流
- `tests/test_lsp.py`: LSP 功能测试
