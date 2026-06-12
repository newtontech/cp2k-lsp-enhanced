# JSON/YAML 格式规范 (JSON/YAML Format Specifications)

## 概述 (Overview)

CP2K 输入工具支持将输入文件转换为 JSON 或 YAML 格式，便于自动化处理和版本控制。

## 格式类型 (Format Types)

### Canonical Format (规范格式)

严格映射 CP2K 结构：

**规则：**
1. 节名前缀 `+`
2. 可重复元素始终为列表
3. 节参数存储在 `_` 键
4. 默认节关键字存储在 `*` 键

**示例：**

```json
{
  "+global": {
    "print_level": "medium",
    "project_name": "test"
  },
  "+force_eval": [
    {
      "method": "quickstep",
      "+DFT": {
        "basis_set_file_name": ["./BASIS_SETS"],
        "potential_file_name": "./POTENTIALS"
      },
      "+XC": {
        "+xc_functional": {
          "_": "PBE"
        }
      },
      "+subsys": {
        "cell": {
          "A": [4.07419, 0, 0],
          "B": [2.037095, 3.52835204, 0],
          "C": [2.037095, 1.17611735, 3.32656221],
          "periodic": "XYZ"
        },
        "+kind": [
          {
            "_": "Ge",
            "element": "Ge",
            "potential": "ALL-q32",
            "basis_set": [["ORB", "pob-TZVP"]]
          }
        ],
        "+topology": {
          "coord_file_name": "./struct.xyz",
          "coord_file_format": "XYZ"
        }
      }
    }
  ]
}
```

### Simplified Format (简化格式)

更易读的格式：

**规则：**
1. 仅在名称冲突时使用 `+` 前缀
2. 单元素可省略列表
3. 节参数可作为字典值（如果唯一）

**示例：**

```json
{
  "global": {
    "print_level": "medium",
    "project_name": "test",
    "run_type": "energy"
  },
  "force_eval": {
    "method": "quickstep",
    "DFT": {
      "basis_set_file_name": "./BASIS_SETS",
      "potential_file_name": "./POTENTIALS"
    },
    "XC": {
      "xc_functional": {
        "_": "PBE"
      }
    },
    "subsys": {
      "cell": {
        "A": [4.07419, 0, 0],
        "B": [2.037095, 3.52835204, 0],
        "C": [2.037095, 1.17611735, 3.32656221],
        "periodic": "XYZ"
      },
      "kind": {
        "_": "Ge",
        "element": "Ge",
        "potential": "ALL-q32",
        "basis_set": ["ORB", "pob-TZVP"]
      },
      "topology": {
        "coord_file_name": "./struct.xyz",
        "coord_file_format": "XYZ"
      }
    }
  }
}
```

### YAML 简化格式

YAML 格式更简洁：

```yaml
global:
  print_level: medium
  project_name: test
  run_type: energy

force_eval:
  method: quickstep
  DFT:
    basis_set_file_name: ./BASIS_SETS
    potential_file_name: ./POTENTIALS
  XC:
    xc_functional:
      _: PBE
  subsys:
    cell:
      A: [4.07419, 0.0, 0.0]
      B: [2.037095, 3.52835204, 0.0]
      C: [2.037095, 1.17611735, 3.32656221]
      periodic: XYZ
    kind:
      Ge:
        basis_set: [ORB, pob-TZVP]
        element: Ge
        potential: ALL-q32
    topology:
      coord_file_format: XYZ
      coord_file_name: ./struct.xyz
```

## 映射规则 (Mapping Rules)

### 节 (Sections)

| CP2K | Canonical | Simplified |
|------|-----------|------------|
| `&GLOBAL` | `"+global"` | `"global"` |
| `&FORCE_EVAL` | `"+force_eval"` | `"force_eval"` |
| `&DFT` | `"+DFT"` | `"DFT"` |

### 关键字 (Keywords)

| CP2K | JSON |
|------|------|
| `PROJECT test` | `"project_name": "test"` |
| `RUN_TYPE ENERGY` | `"run_type": "energy"` |

### 节参数 (Section Parameters)

| CP2K | Canonical | Simplified |
|------|-----------|------------|
| `&KIND Na` | `"_"+ "Na"` | `"_": "Na"` 或 `"Na": {...}` |
| `&XC_FUNCTIONAL PBE` | `"_"+ "PBE"` | `"_": "PBE"` |

### 可重复元素 (Repeatable Elements)

| 类型 | Canonical | Simplified |
|------|-----------|------------|
| 单个 | `[{...}]` 或 `{...}` | `{...}` |
| 多个 | `[{...}, {...}]` | `[{...}, {...}]` |

## 数据类型映射 (Data Type Mapping)

| CP2K 类型 | JSON 类型 | 示例 |
|-----------|-----------|------|
| INTEGER | number | `42` |
| FLOAT | number | `3.14` |
| BOOLEAN | boolean | `true`, `false` |
| STRING | string | `"test"` |
| ENUM | string | `"PBE"` |
| LIST | array | `[1, 2, 3]` |
| KEYWORD_VALUE | array | `["VALUE", 1.0]` |

## 转换工具 (Conversion Tools)

### CP2K → JSON

```bash
fromcp2k input.inp > output.json
fromcp2k --canonical input.inp > output_canonical.json
```

### CP2K → YAML

```bash
fromcp2k -y input.inp > output.yaml
```

### JSON → CP2K

```bash
tocp2k input.json > output.inp
```

### YAML → CP2K

```bash
tocp2k -y input.yaml > output.inp
```

## API 使用 (API Usage)

### Python

```python
from cp2k_input_tools.parser import CP2KInputParser
from cp2k_input_tools.generator import CP2KInputGenerator
import json

# 解析
parser = CP2KInputParserSimplified()
with open("input.inp") as f:
    tree = parser.parse(f)

# 转换为 JSON
json_str = json.dumps(tree, indent=2)

# 生成 CP2K 输入
generator = CP2KInputGenerator()
with open("output.inp", "w") as f:
    for line in generator.line_iter(tree):
        f.write(f"{line}\n")
```

### JavaScript

```javascript
// 需要先将 .inp 转换为 JSON
const fs = require('fs');
const tree = JSON.parse(fs.readFileSync('input.json', 'utf8'));

// 处理树结构
console.log(tree.force_eval.DFT.xc.xc_functional);
```

## 参考来源 (Sources)

- `raw/assets/README.md`: JSON/YAML 格式文档
- `cp2k_input_tools/parser.py`: 解析器实现
- `cp2k_input_tools/generator.py`: 生成器实现
