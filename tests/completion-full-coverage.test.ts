/**
 * Additional completion tests for 100% coverage
 */

import { CompletionProvider, CompletionOptions } from '../src/features/completion';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';

describe('CompletionProvider Full Coverage', () => {
  let keywordDb: KeywordDatabase;
  let provider: CompletionProvider;

  beforeEach(() => {
    keywordDb = new KeywordDatabase();
    provider = new CompletionProvider(keywordDb);
  });

  describe('Schema Integration', () => {
    it('should get schema sections with prefix', () => {
      const getSchemaSections = (provider as any).getSchemaSections.bind(provider);
      const sections = getSchemaSections('GLOBAL');
      expect(Array.isArray(sections)).toBe(true);
    });

    it('should get schema keywords for section', () => {
      const getSchemaKeywords = (provider as any).getSchemaKeywords.bind(provider);
      const keywords = getSchemaKeywords('GLOBAL', '');
      expect(Array.isArray(keywords)).toBe(true);
    });

    it('should check if object is SchemaKeyword', () => {
      const isSchemaKeyword = (provider as any).isSchemaKeyword.bind(provider);
      expect(isSchemaKeyword({ dataType: 'STRING' })).toBe(true);
      expect(isSchemaKeyword({ name: 'TEST' })).toBe(false);
    });

    it('should convert SchemaKeyword to KeywordInfo', () => {
      const convertSchemaKeyword = (provider as any).convertSchemaKeyword.bind(provider);
      
      const schemaKeyword = {
        name: 'TEST',
        description: 'Test description',
        dataType: 'STRING',
        defaultValue: 'default',
        allowedValues: ['a', 'b'],
        units: ['angstrom'],
        loneValue: false,
        repeats: true,
        deprecated: false
      };
      
      const result = convertSchemaKeyword(schemaKeyword);
      expect(result.name).toBe('TEST');
      expect(result.dataType).toBe('STRING');
    });
  });

  describe('Value Documentation', () => {
    it('should get value documentation', () => {
      const getValueDocumentation = (provider as any).getValueDocumentation.bind(provider);
      const result = getValueDocumentation('TEST_VALUE');
      expect(result === undefined || result.kind === 'markdown').toBe(true);
    });
  });

  describe('Documentation Formatting', () => {
    it('should format section documentation', () => {
      const formatSectionDocumentation = (provider as any).formatSectionDocumentation.bind(provider);
      
      const section = {
        name: 'TEST_SECTION',
        description: 'Test section description',
        notes: 'Some notes',
        keywords: ['KEY1', 'KEY2', 'KEY3'],
        subsections: ['SUB1', 'SUB2']
      };
      
      const result = formatSectionDocumentation(section);
      expect(result.kind).toBe('markdown');
      expect(result.value).toContain('TEST_SECTION');
      expect(result.value).toContain('Test section description');
    });

    it('should format section with many keywords', () => {
      const formatSectionDocumentation = (provider as any).formatSectionDocumentation.bind(provider);
      
      const section = {
        name: 'BIG_SECTION',
        keywords: Array.from({ length: 25 }, (_, i) => `KEY${i}`),
        subsections: Array.from({ length: 15 }, (_, i) => `SUB${i}`)
      };
      
      const result = formatSectionDocumentation(section);
      expect(result.value).toContain('...');
    });

    it('should handle section without description', () => {
      const formatSectionDocumentation = (provider as any).formatSectionDocumentation.bind(provider);
      const result = formatSectionDocumentation(null);
      expect(result).toBeUndefined();
    });

    it('should format keyword documentation', () => {
      const formatKeywordDocumentation = (provider as any).formatKeywordDocumentation.bind(provider);
      
      const keyword = {
        name: 'TEST_KEYWORD',
        description: 'Test keyword',
        dataType: 'REAL',
        defaultValue: '1.0',
        allowedValues: ['A', 'B', 'C'],
        units: ['angstrom', 'bohr'],
        loneValue: true,
        repeats: true
      };
      
      const result = formatKeywordDocumentation(keyword);
      expect(result.kind).toBe('markdown');
      expect(result.value).toContain('TEST_KEYWORD');
      expect(result.value).toContain('REAL');
      expect(result.value).toContain('1.0');
    });
  });

  describe('Keyword Detail', () => {
    it('should get keyword detail with default value', () => {
      const getKeywordDetail = (provider as any).getKeywordDetail.bind(provider);
      
      const keyword = {
        name: 'TEST',
        dataType: 'INTEGER',
        defaultValue: '10'
      };
      
      const detail = getKeywordDetail(keyword);
      expect(detail).toContain('INTEGER');
      expect(detail).toContain('default: 10');
    });

    it('should get keyword detail for required keyword', () => {
      const getKeywordDetail = (provider as any).getKeywordDetail.bind(provider);
      
      const keyword = {
        name: 'TEST',
        dataType: 'STRING',
        required: true
      };
      
      const detail = getKeywordDetail(keyword);
      expect(detail).toContain('Required');
    });
  });

  describe('Section Context', () => {
    it('should get section context from document', () => {
      const getSectionContext = (provider as any).getSectionContext.bind(provider);
      
      const content = `&GLOBAL
  PROJECT test
  &SUBSECTION
    KEYWORD value
  &END SUBSECTION
&END GLOBAL
&FORCE_EVAL`;
      
      const document = TextDocument.create('test://test.inp', 'cp2k', 1, content);
      const position = { line: 7, character: 0 };
      
      const context = getSectionContext(document, position);
      expect(typeof context).toBe('string');
    });

    it('should handle nested sections', () => {
      const getSectionContext = (provider as any).getSectionContext.bind(provider);
      
      const content = `&GLOBAL
  &PRINT
    &EACH
      KEYWORD value`;
      
      const document = TextDocument.create('test://test.inp', 'cp2k', 1, content);
      const position = { line: 3, character: 10 };
      
      const context = getSectionContext(document, position);
      expect(context).toBe('EACH');
    });

    it('should handle section end without name', () => {
      const getSectionContext = (provider as any).getSectionContext.bind(provider);
      
      const content = `&GLOBAL
  PROJECT test
&END`;
      
      const document = TextDocument.create('test://test.inp', 'cp2k', 1, content);
      const position = { line: 3, character: 0 };
      
      const context = getSectionContext(document, position);
      expect(context).toBe('');
    });
  });
});
