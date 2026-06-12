# Wiki Log

## 2026-06-13 -- Documentation Expansion

### Raw Assets Added (5 files)

- `raw/assets/cp2k-input-sections-reference.md` -- Complete CP2K input section hierarchy and FORCE_EVAL tree from official manual
- `raw/assets/cp2k-dft-qs-reference.md` -- QS (Quickstep) module keyword reference including METHOD, precision control, EXTRAPOLATION, GAPW settings
- `raw/assets/cp2k-md-tutorials.md` -- Complete MD section reference with ENSEMBLE types, thermostat/barostat configuration, and NVT/NPT/NVE/Langevin input examples
- `raw/assets/cp2k-output-format.md` -- Output file format reference covering .out, .ener, trajectory, restart, and cube files with parsing patterns
- `raw/assets/cp2k-ml-potentials.md` -- ML potential interfaces reference covering NNP (n2p2), NequIP/Allegro, DeePMD-kit, ACE, PAO-ML, and NEP external workflow

### Wiki Entities Added (3 pages)

- `wiki/entities/md-section.md` -- MD section entity with ENSEMBLE types, thermostat/barostat subsections, NVT/NPT examples
- `wiki/entities/qs-section.md` -- QS section entity with METHOD options, precision keywords, EXTRAPOLATION strategies
- `wiki/entities/ml-potentials.md` -- ML potentials entity cataloging NNP, NequIP, DeePMD, ACE, PAO-ML, NEP

### Wiki Concepts Added (3 pages)

- `wiki/concepts/thermostats-barostats.md` -- Thermostat (Nose-Hoover, CSVR, Berendsen, Langevin) and barostat algorithms, ensemble recommendations
- `wiki/concepts/machine-learning-potentials.md` -- ML potential theory, descriptor/model/training pipeline, accuracy-efficiency trade-offs
- `wiki/concepts/output-parsing.md` -- Output file parsing, regex patterns, energy/force/trajectory extraction, conversion tools

### Wiki Synthesis Added (1 page)

- `wiki/synthesis/md-setup-guide.md` -- Practical MD setup guide: system preparation, DFT settings, equilibration, production, restart, troubleshooting

### Wiki Infrastructure

- `wiki/index.md` -- Created complete index listing all 12 entities, 12 concepts, and 7 synthesis pages
- `wiki/log.md` -- Created this log file

### Sources

- https://manual.cp2k.org/trunk/CP2K_INPUT.html
- https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS.html
- https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/MD.html
- https://manual.cp2k.org/trunk/methods/machine_learning/nequip.html
- https://manual.cp2k.org/trunk/methods/machine_learning/deepmd.html
- https://manual.cp2k.org/trunk/methods/machine_learning/ace.html
- https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/NNP.html
