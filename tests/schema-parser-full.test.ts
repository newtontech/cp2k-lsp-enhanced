/**
 * Full schema-parser tests
 */

import { SchemaParser } from '../src/data/schema-parser';

describe('SchemaParser Full Tests', () => {
  let parser: SchemaParser;

  beforeEach(() => {
    jest.clearAllMocks();
    parser = new SchemaParser('cp2k');
  });

  describe('Section Parsing', () => {
    it('should parse sections without names', () => {
      const parseSections = (parser as any).parseSections.bind(parser);
      
      const schema = {
        version: '',
        sections: new Map(),
        keywords: new Map()
      };
      
      const xml = '<SECTION></SECTION>';
      parseSections(xml, schema, []);
      
      expect(schema.sections.size).toBe(0);
    });

    it('should parse section with all attributes', () => {
      const parseSections = (parser as any).parseSections.bind(parser);
      
      const schema = {
        version: '',
        sections: new Map(),
        keywords: new Map()
      };
      
      const xml = `<SECTION NAME="TEST" ALIASES="T1,T2" REPEATS="true" REQUIRED="true" DEPRECATED="false">
        <DESCRIPTION><![CDATA[Test description]]></DESCRIPTION>
      </SECTION>`;
      
      parseSections(xml, schema, []);
      
      const section = schema.sections.get('TEST');
      expect(section).toBeDefined();
      expect(section!.aliases).toEqual(['T1', 'T2']);
      expect(section!.repeats).toBe(true);
      expect(section!.required).toBe(true);
    });
  });

  describe('Keyword Parsing', () => {
    it('should parse keywords without names', () => {
      const parseKeywords = (parser as any).parseKeywords.bind(parser);
      
      const section: any = { keywords: new Map() };
      const schema = { keywords: new Map() };
      
      const xml = '<KEYWORD></KEYWORD>';
      parseKeywords(xml, section, schema);
      
      expect(section.keywords.size).toBe(0);
    });

    it('should parse keyword with CDATA description', () => {
      const parseKeywords = (parser as any).parseKeywords.bind(parser);
      
      const section: any = { keywords: new Map() };
      const schema = { keywords: new Map() };
      
      const xml = `<KEYWORD NAME="TEST_KEYWORD" DATA_TYPE="STRING">
        <DESCRIPTION><![CDATA[Keyword description]]></DESCRIPTION>
        <ALLOWED_VALUES><![CDATA[VAL1,VAL2,VAL3]]></ALLOWED_VALUES>
      </KEYWORD>`;
      
      parseKeywords(xml, section, schema);
      
      const keyword = section.keywords.get('TEST_KEYWORD');
      expect(keyword).toBeDefined();
      expect(keyword.description).toBe('Keyword description');
      expect(keyword.allowedValues).toEqual(['VAL1', 'VAL2', 'VAL3']);
    });

    it('should parse keyword with all attributes', () => {
      const parseKeywords = (parser as any).parseKeywords.bind(parser);
      
      const section: any = { keywords: new Map() };
      const schema = { keywords: new Map() };
      
      const xml = `<KEYWORD NAME="FULL_KEYWORD" 
        DATA_TYPE="REAL" 
        DEFAULT_VALUE="1.0"
        ALIASES="FK"
        UNITS="angstrom,bohr"
        LONE_VALUE="true"
        REPEATS="false"
        DEPRECATED="true"
        REQUIRED="true"
        DEFAULT_UNIT="angstrom"
        DEFAULT_VAR="var"
        N_VAR="3">
      </KEYWORD>`;
      
      parseKeywords(xml, section, schema);
      
      const keyword = section.keywords.get('FULL_KEYWORD');
      expect(keyword).toBeDefined();
      expect(keyword.dataType).toBe('REAL');
      expect(keyword.defaultValue).toBe('1.0');
      expect(keyword.loneValue).toBe(true);
      expect(keyword.repeats).toBe(false);
      expect(keyword.deprecated).toBe(true);
      expect(keyword.nVar).toBe(3);
    });
  });

  describe('Getters', () => {
    it('should get section by name', () => {
      const section = { name: 'TEST', keywords: new Map(), subsections: new Map(), parentPath: [] };
      (parser as any).schema = {
        sections: new Map([['TEST', section]]),
        keywords: new Map()
      };
      
      expect(parser.getSection('TEST')).toBe(section);
      expect(parser.getSection('test')).toBe(section);
      expect(parser.getSection('NONEXISTENT')).toBeUndefined();
    });

    it('should get keyword by name', () => {
      const keyword = { name: 'TEST_KEY', dataType: 'STRING' };
      (parser as any).schema = {
        sections: new Map(),
        keywords: new Map([['TEST_KEY', keyword]])
      };
      
      expect(parser.getKeyword('TEST_KEY')).toBe(keyword);
      expect(parser.getKeyword('test_key')).toBe(keyword);
      expect(parser.getKeyword('NONEXISTENT')).toBeUndefined();
    });
  });

  describe('Search Functions', () => {
    it('should search sections by query matching description', () => {
      const section = { 
        name: 'FORCE_EVAL', 
        description: 'Force evaluation',
        keywords: new Map(), 
        subsections: new Map(), 
        parentPath: [] 
      };
      
      (parser as any).schema = {
        version: '2025.1',
        sections: new Map([['FORCE_EVAL', section]]),
        keywords: new Map()
      };
      
      const results = parser.searchSections('evaluation');
      expect(results).toHaveLength(1);
    });

    it('should search keywords by query matching allowed values', () => {
      const keyword = { 
        name: 'TEST_KEY', 
        description: 'Test',
        dataType: 'STRING',
        allowedValues: ['VALUE1', 'VALUE2']
      };
      
      (parser as any).schema = {
        version: '2025.1',
        sections: new Map(),
        keywords: new Map([['TEST_KEY', keyword]])
      };
      
      const results = parser.searchKeywords('VALUE1');
      expect(results).toHaveLength(1);
    });
  });
});
