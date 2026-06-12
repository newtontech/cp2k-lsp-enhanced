# 变更日志 (Change Log)

## 2026-06-12 - Develop provenance update

### Changed

- Added the LLM Wiki to the active `develop` branch.
- Added `sources/manifest.schema.json` and `sources/cp2k/0.9.1.json`.
- Added `scripts/wiki_lint.py` to validate raw asset size, source manifest checksums, and wiki source sections.
- Kept the large CP2K keyword registry at `cp2k_input_tools/cp2k_input.xml` instead of duplicating it under `raw/assets/`.

## 2026-06-12 - 初始版本 (Initial Version)

### 创建 (Created)

#### 实体页面 (Entity Pages) - 8 个文件
- `wiki/entities/cp2k-input-format.md` - CP2K 输入文件格式基础
- `wiki/entities/globalsection.md` - GLOBAL 全局节
- `wiki/entities/forceevalsection.md` - FORCE_EVAL 力计算节
- `wiki/entities/dftsection.md` - DFT 密度泛函理论节
- `wiki/entities/subsyssection.md` - SUBSYS 子系统节
- `wiki/entities/basissets.md` - 基组类型与选择
- `wiki/entities/pseudopotentials.md` - 赝势类型与应用
- `wiki/entities/xcfunctionals.md` - 交换相关泛函
- `wiki/entities/motionsection.md` - MOTION 运动节
- `wiki/entities/kpoints.md` - K 点设置
- `wiki/entities/scfconvergence.md` - SCF 自洽场收敛
- `wiki/entities/units.md` - 单位系统
- `wiki/entities/molecularmechanics.md` - 分子力学与 QM/MM

#### 概念页面 (Concept Pages) - 4 个文件
- `wiki/concepts/parserarchitecture.md` - 解析器架构
- `wiki/concepts/lspfeatures.md` - LSP 功能特性
- `wiki/concepts/validationrules.md` - 验证规则
- `wiki/concepts/jsonyamlformats.md` - JSON/YAML 格式

#### 综合页面 (Synthesis Pages) - 3 个文件
- `wiki/synthesis/clireference.md` - CLI 命令参考
- `wiki/synthesis/diagnosticscatalog.md` - 诊断错误目录
- `wiki/synthesis/workflows.md` - 工作流程

#### 导航文件
- `index.md` - 知识库索引
- `log.md` - 本变更日志
- `docs/LLM-WIKI-PLAN.md` - Wiki 结构计划

### 源文件 (Source Files)
- `raw/assets/README.md` - 项目 README
- `raw/assets/CHANGELOG.md` - 变更日志
- `raw/assets/AGENTS.md` - Agent 工作流文档
- `raw/assets/agent-workflow.md` - LSP 验证循环
- `raw/assets/NaCl.inp` - 完整示例输入文件
- `raw/assets/He_PBE.inp` - 简单示例

### 统计 (Statistics)
- **总文件数**: 30+
- **实体页面**: 13
- **概念页面**: 4
- **综合页面**: 3
- **覆盖主题**: CP2K 输入格式、DFT 参数、LSP 功能、CLI 工具、工作流程

---

## 版本历史 (Version History)

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.1 | 2026-06-12 | Added source manifest and wiki lint on develop |
| 1.0.0 | 2026-06-12 | 初始版本创建 |

---

**维护说明**: 每次更新知识库时，在此文件顶部添加新的日期条目。
## 2026-06-12 - OpenQC LSP Factory

- `openqc-lsp-factory generate --software cp2k --version 0.9.1`
## 2026-06-12 - OpenQC LSP Factory

- `openqc-lsp-factory release-diff --software cp2k --from 2025.2 --to 2026.1`
