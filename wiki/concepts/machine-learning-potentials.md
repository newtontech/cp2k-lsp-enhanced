# Machine Learning Potentials / 机器学习势

## Definition / 定义

Machine learning potentials (MLPs or MLIPs) are interatomic potentials trained on ab initio reference data (typically DFT energies, forces, and stresses) that can achieve near-DFT accuracy at a fraction of the computational cost. CP2K supports multiple MLP frameworks through dedicated input sections.

机器学习势（MLP 或 MLIP）是基于从头算参考数据（通常是 DFT 能量、力和应力）训练的原子间势，能够以一小部分的计算成本实现接近 DFT 的精度。CP2K 通过专用输入部分支持多种 MLP 框架。

## Core Concept / 核心概念

MLPs work by learning a mapping from local atomic environments to atomic energies:

1. **Descriptor**: A mathematical representation of the local atomic environment (symmetry functions, ACE descriptors, equivariant features, etc.)
2. **Model**: A machine learning model (neural network, linear regression, Gaussian process) that maps descriptors to energies
3. **Training**: Fitting model parameters to minimize the error on reference DFT data
4. **Inference**: Using the trained model to predict energies and forces for new configurations

MLP 通过学习从局部原子环境到原子能量的映射来工作：

1. **描述符**：局部原子环境的数学表示
2. **模型**：将描述符映射到能量的机器学习模型
3. **训练**：拟合模型参数以最小化参考 DFT 数据上的误差
4. **推理**：使用训练好的模型预测新构型的能量和力

## Methods Available in CP2K / CP2K 中可用的方法

### Neural Network Potentials (Behler-Parrinello style)

- High-dimensional neural network potentials (HDNNPs)
- Each atom has its own atomic neural network
- Input: symmetry functions (Behler-style descriptors)
- Interface: n2p2/RuNNer format via `&NNP` section

### NequIP / Allegro (Equivariant Neural Networks)

- E(3)-equivariant neural network architectures
- Full rotational and translational equivariance
- Higher accuracy with fewer training data
- Interface: via `&NEQUIP` section under NONBONDED
- Requires LibTorch for inference

### DeePMD-kit (Deep Potential)

- Deep learning-based interatomic potentials
- Smooth and differentiable energy/force predictions
- Wide adoption in materials science community
- Interface: via `&DEEPMD` section under NONBONDED

### Atomic Cluster Expansion (ACE)

- Complete basis for atomic environments
- Linear or nonlinear regression
- Fast evaluation, systematic improvability
- Interface: via `&ACE` section under NONBONDED

### PAO-ML (GAP-like)

- Built-in Gaussian process regression
- Integrated with CP2K's LS-SCF framework
- Descriptors and GP hyperparameters configurable

## Typical Workflow / 典型工作流

### Phase 1: Generate Reference Data with CP2K

```
CP2K AIMD (PBE + DZVP + D3)
  -> Trajectory with energies, forces, stresses
  -> Sample diverse configurations
```

### Phase 2: Train ML Potential

```
Select MLP framework (NequIP, DeePMD, ACE, etc.)
  -> Prepare training/validation datasets
  -> Train model with appropriate framework
  -> Validate accuracy on test set
```

### Phase 3: Production MD with CP2K

```
CP2K + trained ML potential
  -> Large-scale MD simulation
  -> Properties calculation
```

## Accuracy vs Efficiency Trade-off / 精度与效率权衡

| Method | Typical RMSE (Energy) | Speed vs DFT | GPU Support |
|--------|----------------------|---------------|-------------|
| NNP (n2p2) | 1-5 meV/atom | 1000-10000x | No |
| NequIP | 0.1-1 meV/atom | 100-1000x | Yes |
| DeePMD | 1-5 meV/atom | 1000-10000x | Yes |
| ACE | 1-5 meV/atom | 1000-10000x | Yes |

## Related Concepts / 相关概念

- molecular-dynamics.md -- MD simulations using ML potentials
- force-field.md -- Classical force fields (MM method)

## Related Entities / 相关实体

- ml-potentials.md -- Input sections and compilation details

## References / 参考资料

1. Behler, J. Chem. Phys. 134, 074106 (2011)
2. Batzner et al., Nature Communications 13, 2453 (2022)
3. Drautz, Phys. Rev. B 99, 014104 (2019)
4. Wang et al., "DeePMD-kit" (2018)
5. CP2K ML Methods: https://manual.cp2k.org/trunk/methods/machine_learning/

## Sources

- CP2K official documentation and repository assets (synthesized wiki entry).
