# CP2K LSP Enhanced 知识库索引 (Knowledge Base Index)

## 概述 (Overview)

本知识库采用 Karpathy 风格 LLM Wiki 模式，为 CP2K 量子化学输入文件和 LSP 工具提供结构化的领域知识。

## 目录结构 (Structure)

```
cp2k-lsp-enhanced/
├── raw/assets/          # 源证据文件
├── wiki/
│   ├── entities/        # CP2K 特定概念
│   ├── concepts/        # 跨领域概念
│   └── synthesis/       # 综合参考文档
├── index.md            # 本文件
├── log.md              # 变更日志
└── docs/               # 原始项目文档
```

## 实体页面 (Entity Pages)

### 输入格式与结构

| 页面 | 描述 |
|------|------|
| `cp2k-input-format.md` | CP2K 输入文件格式基础语法 |
| `globalsection.md` | GLOBAL 全局节详解 |
| `forceevalsection.md` | FORCE_EVAL 力计算节 |
| `dftsection.md` | DFT 密度泛函理论节 |
| `subsyssection.md` | SUBSYS 子系统节 |
| `motionsection.md` | MOTION 运动节 |

### 物理化学参数

| 页面 | 描述 |
|------|------|
| `basissets.md` | 基组类型与选择 |
| `pseudopotentials.md` | 赝势类型与应用 |
| `xcfunctionals.md` | 交换相关泛函 |
| `kpoints.md` | K 点设置与采样 |
| `scfconvergence.md` | SCF 自洽场收敛 |
| `units.md` | 单位系统与转换 |
| `molecularmechanics.md` | 分子力学与 QM/MM |

## 概念页面 (Concept Pages)

| 页面 | 描述 |
|------|------|
| `parserarchitecture.md` | 解析器架构与流程 |
| `lspfeatures.md` | LSP 功能特性 |
| `validationrules.md` | 验证规则与层次 |
| `jsonyamlformats.md` | JSON/YAML 格式规范 |

## 综合页面 (Synthesis Pages)

| 页面 | 描述 |
|------|------|
| `clireference.md` | CLI 命令完整参考 |
| `diagnosticscatalog.md` | 诊断错误目录 |
| `workflows.md` | 工作流程与最佳实践 |

## 快速查找 (Quick Reference)

### 按任务查找

| 任务 | 相关页面 |
|------|----------|
| 学习输入格式 | `cp2k-input-format.md` |
| 编写 DFT 计算 | `dftsection.md`, `xcfunctionals.md` |
| 设置几何优化 | `motionsection.md` |
| 选择基组/赝势 | `basissets.md`, `pseudopotentials.md` |
| 解决 SCF 不收敛 | `scfconvergence.md` |
| 配置 LSP | `lspfeatures.md` |
| 使用 CLI 工具 | `clireference.md` |
| 调试错误 | `diagnosticscatalog.md` |
| 参数扫描 | `workflows.md` |

### 按主题查找

| 主题 | 相关页面 |
|------|----------|
| 输入结构 | 所有 `*section.md` 页面 |
| DFT 参数 | `dftsection.md`, `xcfunctionals.md`, `kpoints.md` |
| 系统设置 | `subsyssection.md`, `basissets.md`, `pseudopotentials.md` |
| 计算类型 | `motionsection.md` |
| 收敛问题 | `scfconvergence.md` |
| 工具使用 | `lspfeatures.md`, `clireference.md`, `workflows.md` |
| 格式转换 | `jsonyamlformats.md` |
| 错误排查 | `diagnosticscatalog.md`, `validationrules.md` |

## 源文件引用 (Source References)

所有知识页面均引用源证据文件：

- `raw/assets/*.rst`: 项目文档快照
- `raw/assets/README.md`: 主 README
- `raw/assets/CHANGELOG.md`: 变更日志
- `raw/assets/*.inp`: 示例输入文件
- `cp2k_input_tools/`: 源代码实现
- `sources/cp2k/0.9.1.json`: 源文件清单、校验和和版本元数据

## 维护指南 (Maintenance Guide)

### 添加新页面

1. 确定页面类型 (entity/concept/synthesis)
2. 创建双语格式 (中文标题，英文术语)
3. 添加源文件引用
4. 更新本索引

### 更新现有页面

1. 检查源文件变更
2. 验证代码示例
3. 添加变更到 `log.md`

## 版本信息 (Version Info)

- **知识库版本**: 1.0.0
- **CP2K 工具版本**: 0.9.1
- **创建日期**: 2026-06-12
- **最后更新**: 2026-06-12

---

**导航提示**: 使用编辑器的搜索功能快速定位所需信息。所有页面支持关键词搜索。
