/**
 * Data Module Extended Tests
 * Additional tests to improve coverage for data module
 */

import { KeywordDatabase } from '../src/data/keyword-database';
import { SchemaParser } from '../src/data/schema-parser';

describe('KeywordDatabase Extended', () => {
  let db: KeywordDatabase;

  beforeEach(() => {
    db = new KeywordDatabase();
  });

  describe('Comprehensive section tests', () => {
    // Only test sections that exist in the database
    const existingSections = ['GLOBAL', 'FORCE_EVAL', 'DFT', 'SUBSYS', 'SCF', 'XC', 'QS', 'MGRID', 'KIND', 'CELL', 'TOPOLOGY'];

    existingSections.forEach(sectionName => {
      it(`should get ${sectionName} section`, () => {
        const section = db.getSection(sectionName);
        expect(section).toBeDefined();
        if (section) {
          expect(section.name).toBe(sectionName);
          expect(Array.isArray(section.keywords)).toBe(true);
          expect(Array.isArray(section.subsections)).toBe(true);
        }
      });
    });

    it('should handle case variations', () => {
      const variations = ['global', 'Global', 'GLOBAL', 'gLoBaL'];
      variations.forEach(variant => {
        const section = db.getSection(variant);
        expect(section).toBeDefined();
      });
    });

    it('should return undefined for non-existent sections', () => {
      const section = db.getSection('NON_EXISTENT_SECTION');
      expect(section).toBeUndefined();
    });
  });

  describe('Comprehensive keyword tests', () => {
    const keywords = [
      'PROJECT_NAME', 'RUN_TYPE', 'PRINT_LEVEL', 'WALLTIME',
      'MAX_SCF', 'EPS_SCF', 'SCF_GUESS', 'ADDED_MOS',
      'CUTOFF', 'REL_CUTOFF', 'NGRIDS', 'PROGRESSION_FACTOR',
      'EPS_DEFAULT', 'EXTRAPOLATION', 'METHOD', 'MAP_CONSISTENT',
      'BASIS_SET', 'POTENTIAL', 'ELEMENT', 'MASS'
    ];

    keywords.forEach(keywordName => {
      it(`should get ${keywordName} keyword`, () => {
        const keyword = db.getKeyword(keywordName);
        expect(keyword).toBeDefined();
        if (keyword) {
          expect(keyword.name).toBe(keywordName);
        }
      });
    });

    it('should return undefined for non-existent keywords', () => {
      const keyword = db.getKeyword('NON_EXISTENT_KEYWORD');
      expect(keyword).toBeUndefined();
    });
  });

  describe('Data types', () => {
    it('should have keywords with different data types', () => {
      const stringKw = db.getKeyword('PROJECT_NAME');
      expect(stringKw?.dataType).toBe('STRING');

      const intKw = db.getKeyword('MAX_SCF');
      expect(intKw?.dataType).toBe('INTEGER');

      const realKw = db.getKeyword('EPS_SCF');
      expect(realKw?.dataType).toBe('REAL');

      const logicalKw = db.getKeyword('MAP_CONSISTENT');
      expect(logicalKw?.dataType).toBe('LOGICAL');
    });

    it('should have keywords with allowed values', () => {
      const runType = db.getKeyword('RUN_TYPE');
      expect(runType?.allowedValues).toBeDefined();
      expect(runType?.allowedValues?.length).toBeGreaterThan(0);
    });

    it('should have keywords with default values', () => {
      const maxScf = db.getKeyword('MAX_SCF');
      expect(maxScf?.defaultValue).toBeDefined();

      const epsScf = db.getKeyword('EPS_SCF');
      expect(epsScf?.defaultValue).toBeDefined();
    });
  });

  describe('Keyword search', () => {
    it('should search with partial matches', () => {
      const results = db.searchKeywords('SCF');
      expect(results.length).toBeGreaterThan(0);
    });

    it('should search case-insensitively', () => {
      const results1 = db.searchKeywords('scf');
      const results2 = db.searchKeywords('SCF');
      expect(results1.length).toBe(results2.length);
    });

    it('should return empty array for non-existent search', () => {
      const results = db.searchKeywords('XYZ_NONEXISTENT');
      expect(results).toEqual([]);
    });
  });

  describe('Section keywords', () => {
    it('should get keywords for all major sections', () => {
      const sections = ['GLOBAL', 'SCF', 'XC', 'QS', 'MGRID'];
      sections.forEach(sectionName => {
        const keywords = db.getKeywordsForSection(sectionName);
        expect(Array.isArray(keywords)).toBe(true);
        expect(keywords.length).toBeGreaterThan(0);
      });
    });

    it('should handle unknown sections gracefully', () => {
      const keywords = db.getKeywordsForSection('UNKNOWN_SECTION_XYZ');
      expect(Array.isArray(keywords)).toBe(true);
    });
  });

  describe('Value info', () => {
    it('should provide info for boolean values', () => {
      const trueInfo = db.getValueInfo('TRUE');
      expect(trueInfo).toBeDefined();

      const falseInfo = db.getValueInfo('FALSE');
      expect(falseInfo).toBeDefined();
    });

    it('should return undefined for unknown values', () => {
      const info = db.getValueInfo('UNKNOWN_VALUE_XYZ');
      expect(info).toBeUndefined();
    });
  });

  describe('Get all sections', () => {
    it('should return all sections', () => {
      const sections = db.getSections();
      expect(Array.isArray(sections)).toBe(true);
      expect(sections.length).toBeGreaterThan(5);
    });
  });
});

describe('SchemaParser Extended', () => {
  let parser: SchemaParser;

  beforeEach(() => {
    parser = new SchemaParser('/usr/bin/cp2k');
  });

  describe('Initialization', () => {
    it('should create parser with custom path', () => {
      const customParser = new SchemaParser('/custom/path/cp2k');
      expect(customParser).toBeDefined();
    });

    it('should create parser without path', () => {
      const noPathParser = new SchemaParser();
      expect(noPathParser).toBeDefined();
    });

    it('should create parser with cache dir', () => {
      const cachedParser = new SchemaParser('cp2k', '/tmp/cache');
      expect(cachedParser).toBeDefined();
    });
  });

  describe('Schema operations', () => {
    it('should handle schema not loaded', () => {
      const section = parser.getSection('GLOBAL');
      expect(section).toBeUndefined();

      const keyword = parser.getKeyword('PROJECT_NAME');
      expect(keyword).toBeUndefined();
    });

    it('should return empty array when searching unloaded schema', () => {
      const sections = parser.searchSections('GLOBAL');
      expect(sections).toEqual([]);

      const keywords = parser.searchKeywords('PROJECT');
      expect(keywords).toEqual([]);
    });
  });

  describe('Load schema', () => {
    it('should load empty schema when CP2K not available', async () => {
      const schema = await parser.loadSchema();
      expect(schema).toBeDefined();
      expect(schema.sections).toBeDefined();
      expect(schema.keywords).toBeDefined();
    });

    it('should return cached schema on second call', async () => {
      await parser.loadSchema();
      const schema2 = await parser.loadSchema();
      expect(schema2).toBeDefined();
    });
  });
});
