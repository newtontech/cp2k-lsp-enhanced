# 维护日志 - 2026-03-01

## 完成内容

### 1. 修复 pygls 废弃警告
- **文件**: `tests/test_lsp.py`
  - `workspace.documents` → `workspace.text_documents` (3处)
- **文件**: `cp2k_input_tools/ls.py`
  - `workspace.get_document()` → `workspace.get_text_document()` (1处)

### 2. 测试状态
- LSP 核心测试通过：2 passed
- 无 deprecation warnings

### 3. 提交记录
- `a4a565e` chore: Maintenance 2026-03-01 - fix test syntax and update deps
- `8ccb2b8` fix: 修复 pygls 废弃警告

## 下一步建议
- Phase 1: 继续完善 LSP 功能（diagnostics、completion、hover）
- 添加更多单元测试覆盖
- 代码质量检查（black/ruff）
