import { KeywordDatabase } from '../src/data/keyword-database';

describe('KeywordDatabase', () => {
  let db: KeywordDatabase;

  beforeEach(() => {
    db = new KeywordDatabase();
  });

  describe('Section lookup', () => {
    it('should get GLOBAL section', () => {
      const section = db.getSection('GLOBAL');
      expect(section).toBeDefined();
      expect(section?.name).toBe('GLOBAL');
      expect(section?.description).toContain('Global settings');
    });

    it('should get FORCE_EVAL section', () => {
      const section = db.getSection('FORCE_EVAL');
      expect(section).toBeDefined();
      expect(section?.name).toBe('FORCE_EVAL');
    });

    it('should get DFT section', () => {
      const section = db.getSection('DFT');
      expect(section).toBeDefined();
      expect(section?.keywords).toContain('BASIS_SET_FILE_NAME');
    });

    it('should return undefined for unknown section', () => {
      const section = db.getSection('UNKNOWN_SECTION');
      expect(section).toBeUndefined();
    });

    it('should be case-insensitive', () => {
      const section1 = db.getSection('global');
      const section2 = db.getSection('GLOBAL');
      expect(section1).toEqual(section2);
    });

    it('should get all sections', () => {
      const sections = db.getSections();
      expect(sections.length).toBeGreaterThan(5);
      expect(sections.map(s => s.name)).toContain('GLOBAL');
    });
  });

  describe('Keyword lookup', () => {
    it('should get PROJECT_NAME keyword', () => {
      const keyword = db.getKeyword('PROJECT_NAME');
      expect(keyword).toBeDefined();
      expect(keyword?.dataType).toBe('STRING');
      expect(keyword?.defaultValue).toBe('PROJECT');
    });

    it('should get RUN_TYPE keyword with allowed values', () => {
      const keyword = db.getKeyword('RUN_TYPE');
      expect(keyword).toBeDefined();
      expect(keyword?.allowedValues).toBeDefined();
      expect(keyword?.allowedValues).toContain('ENERGY');
      expect(keyword?.allowedValues).toContain('MOLECULAR_DYNAMICS');
    });

    it('should get MAX_SCF keyword', () => {
      const keyword = db.getKeyword('MAX_SCF');
      expect(keyword).toBeDefined();
      expect(keyword?.dataType).toBe('INTEGER');
      expect(keyword?.defaultValue).toBe('50');
    });

    it('should return undefined for unknown keyword', () => {
      const keyword = db.getKeyword('UNKNOWN_KEYWORD');
      expect(keyword).toBeUndefined();
    });

    it('should be case-insensitive', () => {
      const kw1 = db.getKeyword('project_name');
      const kw2 = db.getKeyword('PROJECT_NAME');
      expect(kw1).toEqual(kw2);
    });
  });

  describe('Section keywords', () => {
    it('should get keywords for GLOBAL section', () => {
      const keywords = db.getKeywordsForSection('GLOBAL');
      expect(keywords.length).toBeGreaterThan(0);
      expect(keywords.map(k => k.name)).toContain('PROJECT_NAME');
    });

    it('should get keywords for SCF section', () => {
      const keywords = db.getKeywordsForSection('SCF');
      expect(keywords.length).toBeGreaterThan(0);
    });

    it('should return empty array for unknown section', () => {
      const keywords = db.getKeywordsForSection('UNKNOWN');
      expect(keywords).toEqual([]);
    });

    it('should return default keywords when no section specified', () => {
      const keywords = db.getKeywordsForSection('');
      expect(keywords.length).toBeGreaterThan(0);
    });
  });

  describe('Value info', () => {
    it('should get TRUE value info', () => {
      const info = db.getValueInfo('TRUE');
      expect(info).toBeDefined();
      expect(info).toContain('true');
    });

    it('should get FALSE value info', () => {
      const info = db.getValueInfo('FALSE');
      expect(info).toBeDefined();
      expect(info).toContain('false');
    });

    it('should return undefined for unknown value', () => {
      const info = db.getValueInfo('UNKNOWN_VALUE');
      expect(info).toBeUndefined();
    });
  });

  describe('Search', () => {
    it('should search keywords by name', () => {
      const results = db.searchKeywords('PROJECT');
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].name).toBe('PROJECT_NAME');
    });

    it('should return empty array for no matches', () => {
      const results = db.searchKeywords('NONEXISTENT_KEYWORD');
      expect(results).toEqual([]);
    });
  });
});
