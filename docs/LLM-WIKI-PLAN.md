# LLM Wiki 结构计划 (LLM Wiki Structure Plan)

## 项目: CP2K LSP Enhanced

## 目标 (Goal)

为 CP2K 量子化学输入文件和 LSP 工具创建 Karpathy 风格的 LLM Wiki 知识库，支持 AI 辅助的 CP2K 输入文件编写和调试。

## 知识库结构 (Knowledge Base Structure)

```
cp2k-lsp-enhanced/
├── raw/assets/              # 源证据文件
│   ├── README.md           # 项目 README
│   ├── CHANGELOG.md        # 变更日志
│   ├── AGENTS.md           # Agent 工作流
│   ├── agent-workflow.md   # LSP 验证循环文档
│   ├── *.inp               # 示例输入文件
│   └── cp2k_input.xml      # CP2K 输入规范
│
├── wiki/
│   ├── entities/           # CP2K 特定概念 (13 页)
│   │   ├── cp2k-input-format.md
│   │   ├── globalsection.md
│   │   ├── forceevalsection.md
│   │   ├── dftsection.md
│   │   ├── subsyssection.md
│   │   ├── motionsection.md
│   │   ├── basissets.md
│   │   ├── pseudopotentials.md
│   │   ├── xcfunctionals.md
│   │   ├── kpoints.md
│   │   ├── scfconvergence.md
│   │   ├── units.md
│   │   └── molecularmechanics.md
│   │
│   ├── concepts/           # 跨领域概念 (4 页)
│   │   ├── parserarchitecture.md
│   │   ├── lspfeatures.md
│   │   ├── validationrules.md
│   │   └── jsonyamlformats.md
│   │
│   └── synthesis/          # 综合参考 (3 页)
│       ├── clireference.md
│       ├── diagnosticscatalog.md
│       └── workflows.md
│
├── index.md                # 导航中心
├── log.md                  # 变更日志
└── docs/LLM-WIKI-PLAN.md   # 本计划文件
```

## 实体页面主题 (Entity Page Topics)

### 输入格式与结构
1. **cp2k-input-format.md** - CP2K 输入文件格式基础语法
2. **globalsection.md** - GLOBAL 全局节详解
3. **forceevalsection.md** - FORCE_EVAL 力计算节
4. **dftsection.md** - DFT 密度泛函理论节
5. **subsyssection.md** - SUBSYS 子系统节
6. **motionsection.md** - MOTION 运动节

### 物理化学参数
7. **basissets.md** - 基组类型与选择
8. **pseudopotentials.md** - 赝势类型与应用
9. **xcfunctionals.md** - 交换相关泛函
10. **kpoints.md** - K 点设置与采样
11. **scfconvergence.md** - SCF 自洽场收敛
12. **units.md** - 单位系统与转换
13. **molecularmechanics.md** - 分子力学与 QM/MM

## 概念页面主题 (Concept Page Topics)

1. **parserarchitecture.md** - 解析器架构与流程
   - 预处理 → 词法分析 → 语法分析 → 语义验证
   - XML Schema 使用
   - 错误处理

2. **lspfeatures.md** - LSP 功能特性
   - 诊断、补全、悬停、定义跳转
   - 文档符号、代码操作
   - 格式化、重命名

3. **validationrules.md** - 验证规则与层次
   - 语法验证
   - Schema 验证
   - 语义验证
   - RUN_TYPE/MOTION 一致性

4. **jsonyamlformats.md** - JSON/YAML 格式规范
   - Canonical vs Simplified 格式
   - 映射规则
   - API 使用

## 综合页面主题 (Synthesis Page Topics)

1. **clireference.md** - CLI 命令完整参考
   - cp2klint, fromcp2k, tocp2k
   - cp2kgen, cp2kget
   - cp2k-language-server, cp2k-lsp

2. **diagnosticscatalog.md** - 诊断错误目录
   - 语法错误代码
   - Schema 错误代码
   - 语义错误代码
   - 警告代码

3. **workflows.md** - 工作流程与最佳实践
   - 编辑验证循环
   - 参数扫描
   - 格式转换
   - 调试工作流

## 内容格式 (Content Format)

### 双语结构
- 中文标题和描述
- 英文术语和代码示例
- 中英文对照表格

### 每页包含
- 概述 (Overview)
- 语法/参数说明
- 代码示例
- 表格总结
- 参考来源 (Sources)

## 源文件引用 (Source References)

每个知识页面引用相关源文件：

| 页面类型 | 主要引用 |
|---------|---------|
| 实体页面 | README.md, *.inp, CP2K 手册 |
| 概念页面 | 源代码实现, docs/ |
| 综合页面 | 所有源材料 |

## 验证清单 (Validation Checklist)

- [x] 创建目录结构
- [x] 复制源文件到 raw/assets/
- [x] 创建 13 个实体页面
- [x] 创建 4 个概念页面
- [x] 创建 3 个综合页面
- [x] 创建 index.md 导航
- [x] 创建 log.md 变更日志
- [x] Git 提交和 PR

## 统计 (Statistics)

- **总页面数**: 20+
- **实体页面**: 13
- **概念页面**: 4
- **综合页面**: 3
- **导航文件**: 2
- **覆盖主题**: CP2K 输入格式、DFT 参数、LSP 功能、CLI 工具

---

**创建日期**: 2024-06-12
**状态**: 已完成
