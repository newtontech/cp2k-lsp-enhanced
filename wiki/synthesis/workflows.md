# 工作流程与最佳实践 (Workflows & Best Practices)

## 概述 (Overview)

CP2K 输入工具支持多种工作流程，从简单文件检查到复杂的参数扫描。

## 核心工作流 (Core Workflows)

### 1. 编辑验证循环 (Edit-Validate Loop)

推荐用于日常开发：

```bash
# 1. 编辑文件
vim input.inp

# 2. LSP 诊断（在支持 LSP 的编辑器中）
# 实时反馈

# 3. 语法检查
cp2klint input.inp

# 4. 完整验证
cp2k-lsp validate input.inp

# 5. 如有错误，重复步骤 1
```

**时间预算：**
- LSP 诊断: <100ms
- cp2klint: <1s
- 完整验证: <1s

---

### 2. 参数扫描工作流 (Parameter Sweep)

用于收敛性测试或参数优化：

```bash
# 1. 创建模板
cp2kgen template.inp \
  "force_eval/dft/mgrid/cutoff=[600,800,1000,1200,1400]"

# 2. 验证所有生成的文件
for f in template-cutoff_*.inp; do
    cp2k-lsp validate $f || echo "Error in $f"
done

# 3. (可选) 批量提交计算
for f in template-cutoff_*.inp; do
    sbatch submit_cp2k.sh $f
done
```

**多参数组合：**
```bash
cp2kgen template.inp \
  "force_eval/dft/mgrid/cutoff=[800,1000]" \
  "force_eval/dft/xc/xc_functional/=[PBE,BLYP]" \
  "force_eval/dft/scf/eps_scf=[1.0E-6,1.0E-7]"
# 生成 8 个文件 (2×2×2)
```

---

### 3. 格式转换工作流 (Format Conversion)

用于自动化处理：

```bash
# CP2K → JSON
fromcp2k input.inp > input.json

# 处理 JSON (如使用 Python/JavaScript)
python process.py input.json > processed.json

# JSON → CP2K
tocp2k processed.json > output.inp

# 验证输出
cp2k-lsp validate output.inp
```

**用于 AiiDA 集成：**
```bash
fromcp2k --format aiida-cp2k-calc input.inp > aiida_template.py
```

---

### 4. 重启文件处理工作流 (Restart Workflow)

从重启文件提取信息：

```bash
# 提取优化后的晶胞参数
cp2kget restart.inp "force_eval/subsys/cell/a"
cp2kget restart.inp "force_eval/subsys/cell/b"
cp2kget restart.inp "force_eval/subsys/cell/c"

# 提取最终能量
cp2kget restart.inp "energy/total"
```

---

### 5. 调试工作流 (Debug Workflow)

系统诊断问题：

```bash
# 1. 详细诊断
cp2k-lsp inspect diagnostics input.inp --json > diag.json

# 2. 检查特定位置
cp2k-lsp inspect hover input.inp --line 10 --character 4

# 3. 检查变量引用
cp2k-lsp inspect references input.inp --line 5 --character 2

# 4. 格式预览（检查格式问题）
cp2k-lsp inspect format-preview input.inp
```

---

## 最佳实践 (Best Practices)

### 文件组织

```
project/
├── inputs/
│   ├── template.inp          # 主模板
│   ├── geometry.inp          # 几何设置
│   └── dft_params.inp        # DFT 参数
├── results/
├── BASIS_SETS
└── POTENTIALS
```

### 使用 @INCLUDE 组织大文件

```fortran
! main.inp
&GLOBAL
   PROJECT my_calc
   @INCLUDE settings/global.inp
&END GLOBAL

@INCLUDE geometry.inp
@INCLUDE dft_params.inp
```

### 使用预处理变量参数化

```fortran
@SET CUTOFF 800
@SET XC_FUNCTIONAL PBE
@SET TEMPERATURE 300.0

&FORCE_EVAL
   &DFT
      &MGRID
         CUTOFF ${CUTOFF}
      &END MGRID
      &XC
         &XC_FUNCTIONAL ${XC_FUNCTIONAL}
         &END XC_FUNCTIONAL
      &END XC
      &SCF
         &SMEAR
            ELECTRONIC_TEMPERATURE ${TEMPERATURE}
         &END SMEAR
      &END SCF
   &END DFT
&END FORCE_EVAL
```

### 验证层级

| 场景 | 工具 | 用途 |
|------|------|------|
| 编辑中 | LSP 诊断 | 即时反馈 |
| 保存后 | cp2klint | 快速检查 |
| 提交前 | cp2k-lsp validate | 完整验证 |
| 最终检查 | cp2k-lsp validate --dry-run | CP2K 验证 |

### 错误处理

```bash
# 在脚本中使用
if ! cp2klint input.inp; then
    echo "Syntax check failed"
    exit 1
fi

if ! cp2k-lsp validate input.inp --fail-on-error; then
    echo "Validation failed"
    exit 1
fi
```

## 常见模式 (Common Patterns)

### 条件编译

```fortran
@SET RUN_TYPE ENERGY

@IF ${RUN_TYPE} == ENERGY
   &GLOBAL
      RUN_TYPE ENERGY
   &END GLOBAL
@ENDIF

@IF ${RUN_TYPE} == GEO_OPT
   &GLOBAL
      RUN_TYPE GEO_OPT
   &END GLOBAL

   &MOTION
      &GEO_OPT
         ...
      &END GEO_OPT
   &END MOTION
@ENDIF
```

### 重复结构

```fortran
&FORCE_EVAL
   METHOD Quickstep

   @IF ${INCLUDE_DFT} == yes
   &DFT
      ...
   &END DFT
   @ENDIF

   @IF ${INCLUDE_MM} == yes
   &MM
      ...
   &END MM
   @ENDIF
&END FORCE_EVAL
```

## 参考来源 (Sources)

- `docs/agent-workflow.md`: 完整的 LSP+CLI 验证循环文档
- `raw/assets/README.md`: 工具使用示例
