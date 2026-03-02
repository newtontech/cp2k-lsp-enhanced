/**
 * CP2K Keyword Database
 * 
 * This module provides access to CP2K keyword and section definitions.
 * In production, this would load from the official CP2K XML schema.
 */

export interface KeywordInfo {
  name: string;
  description?: string;
  dataType?: string;
  defaultValue?: string;
  allowedValues?: string[];
  units?: string[];
  loneValue?: boolean;
  repeats?: boolean;
  isSection?: boolean;
}

export interface SectionInfo {
  name: string;
  description?: string;
  notes?: string;
  keywords: string[];
  subsections: string[];
}

export class KeywordDatabase {
  private sections: Map<string, SectionInfo> = new Map();
  private keywords: Map<string, KeywordInfo> = new Map();
  private valueInfo: Map<string, string> = new Map();

  constructor() {
    this.initializeDatabase();
  }

  private initializeDatabase(): void {
    // Core sections
    this.addSection({
      name: 'GLOBAL',
      description: 'Global settings for the CP2K calculation',
      keywords: ['PROJECT_NAME', 'RUN_TYPE', 'PRINT_LEVEL', 'WALLTIME'],
      subsections: ['DBCSR', 'FM', 'PREFERRED_FFT_LIBRARY', 'TIMINGS'],
    });

    this.addSection({
      name: 'FORCE_EVAL',
      description: 'Force evaluation methods and settings',
      keywords: ['METHOD', 'STRESS_TENSOR'],
      subsections: ['DFT', 'SUBSYS', 'PROPERTIES', 'QMMM'],
    });

    this.addSection({
      name: 'DFT',
      description: 'Density Functional Theory settings',
      keywords: ['BASIS_SET_FILE_NAME', 'POTENTIAL_FILE_NAME', 'WFN_RESTART_FILE_NAME'],
      subsections: ['QS', 'SCF', 'XC', 'MGRID', 'POISSON', 'KPOINTS', 'PRINT'],
    });

    this.addSection({
      name: 'SUBSYS',
      description: 'System definition (cell, coordinates, kinds)',
      keywords: [],
      subsections: ['CELL', 'COORD', 'KIND', 'TOPOLOGY'],
    });

    this.addSection({
      name: 'SCF',
      description: 'Self-Consistent Field settings',
      keywords: ['MAX_SCF', 'EPS_SCF', 'SCF_GUESS', 'ADDED_MOS'],
      subsections: ['DIAGONALIZATION', 'MIXING', 'SMEAR', 'PRINT'],
    });

    this.addSection({
      name: 'XC',
      description: 'Exchange-Correlation functional settings',
      keywords: ['DENSITY_CUTOFF', 'GRADIENT_CUTOFF', 'TAU_CUTOFF'],
      subsections: ['XC_FUNCTIONAL', 'XC_GRID', 'HF', 'VDW_POTENTIAL'],
    });

    this.addSection({
      name: 'QS',
      description: 'Quickstep (GPW/GAPW) settings',
      keywords: ['EPS_DEFAULT', 'EXTRAPOLATION', 'METHOD', 'MAP_CONSISTENT'],
      subsections: ['WF_INTERPOLATION'],
    });

    this.addSection({
      name: 'MGRID',
      description: 'Multi-grid settings for density and potentials',
      keywords: ['CUTOFF', 'REL_CUTOFF', 'NGRIDS', 'PROGRESSION_FACTOR'],
      subsections: [],
    });

    this.addSection({
      name: 'KIND',
      description: 'Atom kind definition',
      keywords: ['ELEMENT', 'BASIS_SET', 'POTENTIAL', 'MASS', 'MAGNETIZATION'],
      subsections: ['BASIS_SET', 'POTENTIAL'],
    });

    this.addSection({
      name: 'CELL',
      description: 'Unit cell definition',
      keywords: ['A', 'B', 'C', 'ALPHA', 'BETA', 'GAMMA', 'PERIODIC', 'SYMMETRY'],
      subsections: ['CELL_REF'],
    });

    // Add more sections...
    this.addAdditionalSections();

    // Initialize keywords
    this.initializeKeywords();

    // Initialize value info
    this.initializeValueInfo();
  }

  private addAdditionalSections(): void {
    const additionalSections: SectionInfo[] = [
      {
        name: 'MOTION',
        description: 'Molecular dynamics and geometry optimization',
        keywords: [],
        subsections: ['MD', 'GEO_OPT', 'CELL_OPT', 'MD_ENSEMBLE', 'PRINT'],
      },
      {
        name: 'MD',
        description: 'Molecular Dynamics settings',
        keywords: ['TIMESTEP', 'STEPS', 'TEMPERATURE', 'ENSEMBLE'],
        subsections: ['THERMOSTAT', 'BAROSTAT', 'PRINT'],
      },
      {
        name: 'GEO_OPT',
        description: 'Geometry optimization settings',
        keywords: ['TYPE', 'MAX_DR', 'MAX_FORCE', 'RMS_DR', 'RMS_FORCE', 'MAX_ITER'],
        subsections: ['CG', 'BFGS', 'PRINT'],
      },
      {
        name: 'PRINT',
        description: 'Output printing options',
        keywords: [],
        subsections: ['TRAJECTORY', 'VELOCITIES', 'FORCES', 'ENERGY', 'RESTART'],
      },
      {
        name: 'TOPOLOGY',
        description: 'Molecular topology and connectivity',
        keywords: ['COORD_FILE_NAME', 'COORD_FILE_FORMAT', 'CONNECTIVITY'],
        subsections: ['BOND', 'ANGLE', 'DIHEDRAL'],
      },
      {
        name: 'POISSON',
        description: 'Poisson solver settings',
        keywords: ['POISSON_SOLVER', 'PERIODIC'],
        subsections: ['EWALD', 'IMPLICIT', 'WAVELET'],
      },
      {
        name: 'KPOINTS',
        description: 'k-point sampling for periodic systems',
        keywords: ['SCHEME', 'SYMMETRY', 'FULL_GRID', 'PARALLEL_GROUP_SIZE', 'WAVEFUNCTIONS'],
        subsections: [],
      },
      {
        name: 'XC_FUNCTIONAL',
        description: 'XC functional specification',
        keywords: ['_'],
        subsections: ['PBE', 'BLYP', 'BP', 'LDA', 'HYB_GGA_XC', 'MGGA_XC'],
      },
    ];

    additionalSections.forEach(section => this.addSection(section));
  }

  private initializeKeywords(): void {
    const keywordData: KeywordInfo[] = [
      // GLOBAL keywords
      { name: 'PROJECT_NAME', description: 'Project name prefix for output files', dataType: 'STRING', defaultValue: 'PROJECT' },
      { 
        name: 'RUN_TYPE', 
        description: 'Type of calculation to perform',
        dataType: 'ENUM',
        allowedValues: ['ENERGY', 'ENERGY_FORCE', 'WAVEFUNCTION_OPTIMIZATION', 'GEOMETRY_OPTIMIZATION', 'MOLECULAR_DYNAMICS', 'CELL_OPTIMIZATION', 'MOLECULAR_STATICS', 'MONTECARLO', 'ELECTRONIC_SPECTROSCOPY', 'CORE_SPECTROSCOPY', 'DEBUG', 'NONE']
      },
      { 
        name: 'PRINT_LEVEL', 
        description: 'Amount of output to generate',
        dataType: 'ENUM',
        defaultValue: 'MEDIUM',
        allowedValues: ['SILENT', 'LOW', 'MEDIUM', 'HIGH', 'DEBUG']
      },
      { name: 'WALLTIME', description: 'Maximum walltime in seconds', dataType: 'INTEGER' },

      // FORCE_EVAL keywords
      { 
        name: 'METHOD', 
        description: 'Electronic structure method',
        dataType: 'ENUM',
        defaultValue: 'QUICKSTEP',
        allowedValues: ['QUICKSTEP', 'SIRIUS', 'EIP', 'MIXED', 'QMMM', 'FIST', 'EMBED']
      },
      { name: 'STRESS_TENSOR', description: 'Calculate stress tensor', dataType: 'ENUM', allowedValues: ['ANALYTICAL', 'NUMERICAL', 'NONE'] },

      // DFT keywords
      { name: 'BASIS_SET_FILE_NAME', description: 'Path to basis set file', dataType: 'STRING', repeats: true },
      { name: 'POTENTIAL_FILE_NAME', description: 'Path to potential file', dataType: 'STRING', repeats: true },
      { name: 'WFN_RESTART_FILE_NAME', description: 'Wavefunction restart file', dataType: 'STRING' },

      // SCF keywords
      { name: 'MAX_SCF', description: 'Maximum number of SCF iterations', dataType: 'INTEGER', defaultValue: '50' },
      { name: 'EPS_SCF', description: 'SCF convergence threshold', dataType: 'REAL', defaultValue: '1.0E-7' },
      { 
        name: 'SCF_GUESS', 
        description: 'Initial guess for wavefunction',
        dataType: 'ENUM',
        defaultValue: 'ATOMIC',
        allowedValues: ['ATOMIC', 'CORE', 'RANDOM', 'RESTART', 'SPARSE', 'MOPAC']
      },
      { name: 'ADDED_MOS', description: 'Additional molecular orbitals', dataType: 'INTEGER', defaultValue: '0' },

      // QS keywords
      { name: 'EPS_DEFAULT', description: 'Default numerical accuracy', dataType: 'REAL', defaultValue: '1.0E-10' },
      { 
        name: 'EXTRAPOLATION', 
        description: 'Wavefunction extrapolation method',
        dataType: 'ENUM',
        defaultValue: 'USE_GUESS',
        allowedValues: ['USE_GUESS', 'ASPC', 'USE_PREV_P', 'USE_PREV_WF']
      },
      { 
        name: 'METHOD', 
        description: 'QS method',
        dataType: 'ENUM',
        defaultValue: 'GAPW',
        allowedValues: ['GAPW', 'GPW', 'LRIGPW', 'RIGPW', 'OFDFT', 'OFGAPW']
      },
      { name: 'MAP_CONSISTENT', description: 'Use consistent mapping', dataType: 'LOGICAL', defaultValue: 'TRUE' },

      // MGRID keywords
      { name: 'CUTOFF', description: 'Plane wave cutoff in Ry', dataType: 'REAL', defaultValue: '400', units: ['Ry'] },
      { name: 'REL_CUTOFF', description: 'Relative cutoff for Gaussian products', dataType: 'REAL', defaultValue: '50', units: ['Ry'] },
      { name: 'NGRIDS', description: 'Number of multigrids', dataType: 'INTEGER', defaultValue: '4' },
      { name: 'PROGRESSION_FACTOR', description: 'Grid progression factor', dataType: 'REAL', defaultValue: '3' },

      // KIND keywords
      { name: 'ELEMENT', description: 'Chemical element symbol', dataType: 'STRING' },
      { name: 'BASIS_SET', description: 'Basis set specification', dataType: 'STRING_LIST', loneValue: true, repeats: true },
      { name: 'POTENTIAL', description: 'Pseudopotential', dataType: 'STRING', loneValue: true },
      { name: 'MASS', description: 'Atomic mass', dataType: 'REAL', units: ['amu'] },
      { name: 'MAGNETIZATION', description: 'Initial magnetic moment', dataType: 'REAL' },

      // CELL keywords
      { name: 'A', description: 'Cell vector A', dataType: 'REAL_LIST', units: ['angstrom', 'bohr'] },
      { name: 'B', description: 'Cell vector B', dataType: 'REAL_LIST', units: ['angstrom', 'bohr'] },
      { name: 'C', description: 'Cell vector C', dataType: 'REAL_LIST', units: ['angstrom', 'bohr'] },
      { name: 'ALPHA', description: 'Cell angle alpha', dataType: 'REAL' },
      { name: 'BETA', description: 'Cell angle beta', dataType: 'REAL' },
      { name: 'GAMMA', description: 'Cell angle gamma', dataType: 'REAL' },
      { 
        name: 'PERIODIC', 
        description: 'Periodic boundary conditions',
        dataType: 'ENUM',
        defaultValue: 'XYZ',
        allowedValues: ['X', 'XY', 'XYZ', 'XZ', 'Y', 'YZ', 'Z', 'NONE']
      },
      { 
        name: 'SYMMETRY', 
        description: 'Cell symmetry',
        dataType: 'ENUM',
        allowedValues: ['CUBIC', 'ORTHORHOMBIC', 'TETRAGONAL', 'HEXAGONAL', 'MONOCLINIC', 'TRICLINIC', 'RHOMBIC', 'NONE']
      },

      // MD keywords
      { name: 'TIMESTEP', description: 'MD timestep', dataType: 'REAL', defaultValue: '1.0', units: ['fs'] },
      { name: 'STEPS', description: 'Number of MD steps', dataType: 'INTEGER' },
      { name: 'TEMPERATURE', description: 'Target temperature', dataType: 'REAL', units: ['K'] },
      { 
        name: 'ENSEMBLE', 
        description: 'Statistical ensemble',
        dataType: 'ENUM',
        defaultValue: 'NVE',
        allowedValues: ['NVE', 'NVT', 'NPT_F', 'NPT_I', 'NPAT', 'NPH', 'REFTRAJ', 'LANGEVIN', 'ISOKIN']
      },

      // GEO_OPT keywords
      { 
        name: 'TYPE', 
        description: 'Optimization algorithm',
        dataType: 'ENUM',
        defaultValue: 'MINIMIZATION',
        allowedValues: ['MINIMIZATION', 'TRANSITION_STATE']
      },
      { name: 'MAX_DR', description: 'Maximum geometry change', dataType: 'REAL', defaultValue: '3.0E-3', units: ['bohr'] },
      { name: 'MAX_FORCE', description: 'Maximum force component', dataType: 'REAL', defaultValue: '4.5E-4', units: ['hartree/bohr'] },
      { name: 'RMS_DR', description: 'RMS geometry change', dataType: 'REAL', defaultValue: '1.5E-3', units: ['bohr'] },
      { name: 'RMS_FORCE', description: 'RMS force', dataType: 'REAL', defaultValue: '3.0E-4', units: ['hartree/bohr'] },
      { name: 'MAX_ITER', description: 'Maximum optimization steps', dataType: 'INTEGER', defaultValue: '200' },

      // KPOINTS keywords
      { 
        name: 'SCHEME', 
        description: 'k-point sampling scheme',
        dataType: 'STRING',
        defaultValue: 'MONKHORST-PACK 1 1 1'
      },
      { name: 'SYMMETRY', description: 'Use k-point symmetry', dataType: 'LOGICAL', defaultValue: 'TRUE' },
      { name: 'FULL_GRID', description: 'Use full k-point grid', dataType: 'LOGICAL', defaultValue: 'FALSE' },
      { name: 'WAVEFUNCTIONS', description: 'Write wavefunctions at k-points', dataType: 'LOGICAL', defaultValue: 'FALSE' },

      // TOPOLOGY keywords
      { name: 'COORD_FILE_NAME', description: 'Coordinate file path', dataType: 'STRING' },
      { 
        name: 'COORD_FILE_FORMAT', 
        description: 'Coordinate file format',
        dataType: 'ENUM',
        allowedValues: ['XYZ', 'PDB', 'CRD', 'CIF', 'G96', 'DCD', 'CP2K']
      },
      { 
        name: 'CONNECTIVITY', 
        description: 'Connectivity source',
        dataType: 'ENUM',
        allowedValues: ['GENERATE', 'PSF', 'MOL_SET', 'UPSAMPLING', 'OFF']
      },

      // XC keywords
      { name: '_', description: 'XC functional name (lone value)', dataType: 'STRING', loneValue: true },
      { name: 'DENSITY_CUTOFF', description: 'Density cutoff', dataType: 'REAL', defaultValue: '1.0E-10' },
      { name: 'GRADIENT_CUTOFF', description: 'Gradient cutoff', dataType: 'REAL', defaultValue: '1.0E-10' },
      { name: 'TAU_CUTOFF', description: 'Kinetic energy density cutoff', dataType: 'REAL', defaultValue: '1.0E-10' },

      // POISSON keywords
      { 
        name: 'POISSON_SOLVER', 
        description: 'Poisson solver method',
        dataType: 'ENUM',
        defaultValue: 'PERIODIC',
        allowedValues: ['PERIODIC', 'ANALYTIC', 'MT', 'WAVELET', 'IMPLICIT']
      },
      { 
        name: 'PERIODIC', 
        description: 'Poisson periodicity',
        dataType: 'ENUM',
        defaultValue: 'XYZ',
        allowedValues: ['X', 'XY', 'XYZ', 'XZ', 'Y', 'YZ', 'Z', 'NONE']
      },
    ];

    keywordData.forEach(kw => this.addKeyword(kw));
  }

  private initializeValueInfo(): void {
    this.valueInfo.set('TRUE', 'Boolean true value');
    this.valueInfo.set('FALSE', 'Boolean false value');
    this.valueInfo.set('ON', 'Boolean true / Enabled');
    this.valueInfo.set('OFF', 'Boolean false / Disabled');
    this.valueInfo.set('YES', 'Boolean true');
    this.valueInfo.set('NO', 'Boolean false');
    this.valueInfo.set('T', 'Boolean true (short)');
    this.valueInfo.set('F', 'Boolean false (short)');
    this.valueInfo.set('.TRUE.', 'Fortran-style boolean true');
    this.valueInfo.set('.FALSE.', 'Fortran-style boolean false');
    
    this.valueInfo.set('ENERGY', 'Single point energy calculation');
    this.valueInfo.set('ENERGY_FORCE', 'Energy and forces calculation');
    this.valueInfo.set('GEOMETRY_OPTIMIZATION', 'Geometry optimization');
    this.valueInfo.set('MOLECULAR_DYNAMICS', 'Molecular dynamics simulation');
    this.valueInfo.set('CELL_OPTIMIZATION', 'Unit cell optimization');
    
    this.valueInfo.set('QUICKSTEP', 'DFT using GPW/GAPW method');
    this.valueInfo.set('FIST', 'Molecular mechanics (force field)');
    this.valueInfo.set('QMMM', 'Quantum mechanics / molecular mechanics');
    
    this.valueInfo.set('GAPW', 'Gaussian Augmented Plane Waves');
    this.valueInfo.set('GPW', 'Gaussian Plane Waves');
    
    this.valueInfo.set('NVE', 'Microcanonical ensemble (constant N, V, E)');
    this.valueInfo.set('NVT', 'Canonical ensemble (constant N, V, T)');
    this.valueInfo.set('NPT_F', 'Isotropic NPT ensemble');
    this.valueInfo.set('NPT_I', 'Anisotropic NPT ensemble');
  }

  private addSection(section: SectionInfo): void {
    this.sections.set(section.name.toUpperCase(), section);
  }

  private addKeyword(keyword: KeywordInfo): void {
    this.keywords.set(keyword.name.toUpperCase(), keyword);
  }

  getSection(name: string): SectionInfo | undefined {
    return this.sections.get(name.toUpperCase());
  }

  getSections(): SectionInfo[] {
    return Array.from(this.sections.values());
  }

  getKeyword(name: string): KeywordInfo | undefined {
    return this.keywords.get(name.toUpperCase());
  }

  getKeywordsForSection(sectionName: string): KeywordInfo[] {
    if (!sectionName) {
      // Return top-level keywords
      return Array.from(this.keywords.values()).filter(kw => !kw.isSection).slice(0, 50);
    }
    
    const section = this.getSection(sectionName.toUpperCase());
    if (!section) {
      return [];
    }
    
    const keywords: KeywordInfo[] = [];
    
    // Add subsections as keywords
    section.subsections.forEach(subName => {
      keywords.push({
        name: subName,
        isSection: true,
        description: this.getSection(subName)?.description,
      });
    });
    
    // Add regular keywords
    section.keywords.forEach(kwName => {
      const kw = this.getKeyword(kwName);
      if (kw) {
        keywords.push(kw);
      } else {
        keywords.push({ name: kwName });
      }
    });
    
    return keywords;
  }

  getValueInfo(value: string): string | undefined {
    return this.valueInfo.get(value.toUpperCase());
  }

  searchKeywords(query: string): KeywordInfo[] {
    const upperQuery = query.toUpperCase();
    return Array.from(this.keywords.values()).filter(kw =>
      kw.name.includes(upperQuery) ||
      kw.description?.toUpperCase().includes(upperQuery)
    );
  }
}
