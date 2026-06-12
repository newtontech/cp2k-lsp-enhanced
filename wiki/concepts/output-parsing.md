# Output Parsing / 输出解析

## Definition / 定义

Output parsing is the process of extracting structured data (energies, forces, coordinates, thermodynamic quantities) from CP2K's text-based and binary output files. Understanding the output format is essential for post-processing, analysis, and interfacing with external tools.

输出解析是从 CP2K 的文本和二进制输出文件中提取结构化数据（能量、力、坐标、热力学量）的过程。理解输出格式对于后处理、分析和与外部工具接口至关重要。

## Output File Types / 输出文件类型

| File | Extension | Content / 内容 |
|------|-----------|----------------|
| Main output | `.out` | Complete calculation log / 完整计算日志 |
| Energy | `.ener` | Per-step thermodynamic data / 每步热力学数据 |
| Position trajectory | `-pos-1.xyz` | Atomic coordinates / 原子坐标 |
| Velocity trajectory | `-vel-1.xyz` | Atomic velocities / 原子速度 |
| Force trajectory | `-frc-1.xyz` | Atomic forces / 原子力 |
| Cell trajectory | `-1.cell` | Cell parameters / 晶胞参数 |
| Restart | `.restart` | Complete simulation state / 完整模拟状态 |
| Cube | `.cube` | Volumetric data (density, potential) / 体积数据 |
| Wavefunction | `.wfn` | Wavefunction coefficients / 波函数系数 |

## Energy Parsing / 能量解析

### From Main Output

Pattern: `ENERGY| Total FORCE_EVAL ( F= <float> E= <float> )`

```python
import re
energy_re = re.compile(
    r'ENERGY\| Total FORCE_EVAL\s+\( F=\s+([-\d.E+]+)\s+E=\s+([-\d.E+]+)\s+\)'
)
```

### From .ener File

Tab-separated columns: StepNr, Time[fs], Kin.[a.u.], Temp[K], Pot.[a.u.], ConsQty[a.u.], UsedTime[s]

```python
def parse_ener(path):
    results = []
    with open(path) as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 7:
                results.append({
                    'step': int(parts[0]),
                    'time_fs': float(parts[1]),
                    'kinetic_au': float(parts[2]),
                    'temperature_K': float(parts[3]),
                    'potential_au': float(parts[4]),
                    'conserved_au': float(parts[5]),
                    'wall_s': float(parts[6])
                })
    return results
```

## Force Parsing / 力解析

Force blocks in main output follow the pattern:

```
 Atom   Kind Element          X             Y             Z
    1     1  Si         0.00123456   -0.00234567    0.00012345
```

Forces are in Hartree/Bohr by default unless units specified.

## Trajectory Parsing / 轨迹解析

XYZ trajectories follow extended XYZ format:
- Line 1: atom count
- Line 2: comment (step, energy)
- Lines 3+: element, x, y, z

Standard tools: MDAnalysis, MDTraj, ASE, VMD.

## Conversion Tools / 转换工具

| Tool | Input | Output | Use Case |
|------|-------|--------|----------|
| cp2k_2_deepmdkit | CP2K output | DeePMD format | ML training data |
| ORNL converter | CP2K trajectory | DeePMD raw | ML training data |
| cclib | CP2K output | Standard format | General analysis |
| ASE | CP2K I/O | Multiple formats | General workflow |

## Related / 相关

- Entity: output-files.md (file format details / 文件格式详情)
- Synthesis: typical-workflow.md (analysis workflow / 分析工作流)

## 参考来源 (Sources)

1. BioExcel CP2K Output Guide: https://docs.bioexcel.eu/qmmm_bpg/en/main/running_cp2k/cp2k_output.html
2. ORNL Converter: https://calvera.ornl.gov/docs/user_guide/tools/Chemical%20Spectroscopy/neutrons_amml_cp2k_convert/
3. MDAnalysis: https://www.mdanalysis.org/
