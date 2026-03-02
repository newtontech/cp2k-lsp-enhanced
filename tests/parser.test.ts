import { CP2KParser } from '../src/parser/cp2k-parser';
import { TextDocument } from 'vscode-languageserver-textdocument';

describe('CP2KParser', () => {
  let parser: CP2KParser;

  beforeEach(() => {
    parser = new CP2KParser();
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Basic parsing', () => {
    it('should parse empty document', () => {
      const doc = createDocument('');
      const result = parser.parse(doc);
      
      expect(result.sections).toHaveLength(0);
      expect(result.tokens).toHaveLength(0);
      expect(result.diagnostics).toHaveLength(0);
    });

    it('should parse a simple section', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME test
&END GLOBAL
      `);
      
      const result = parser.parse(doc);
      
      expect(result.sections).toHaveLength(1);
      expect(result.sections[0].name).toBe('GLOBAL');
      expect(result.sections[0].level).toBe(0);
    });

    it('should parse nested sections', () => {
      const doc = createDocument(`
&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME ./BASIS_SETS
  &END DFT
&END FORCE_EVAL
      `);
      
      const result = parser.parse(doc);
      
      expect(result.sections).toHaveLength(1);
      expect(result.sections[0].name).toBe('FORCE_EVAL');
      expect(result.sections[0].subsections).toHaveLength(1);
      expect(result.sections[0].subsections[0].name).toBe('DFT');
    });

    it('should parse keywords with values', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME my_project
  RUN_TYPE ENERGY
  PRINT_LEVEL MEDIUM
&END GLOBAL
      `);
      
      const result = parser.parse(doc);
      
      expect(result.sections[0].keywords).toHaveLength(3);
      expect(result.sections[0].keywords[0].name).toBe('PROJECT_NAME');
      expect(result.sections[0].keywords[0].value).toBe('my_project');
    });
  });

  describe('Token parsing', () => {
    it('should identify section tokens', () => {
      const doc = createDocument(`
&GLOBAL
&END GLOBAL
      `);
      
      const result = parser.parse(doc);
      
      const sectionTokens = result.tokens.filter(t => t.type === 'section');
      expect(sectionTokens).toHaveLength(2);
    });

    it('should identify keyword tokens', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME test
&END GLOBAL
      `);
      
      const result = parser.parse(doc);
      
      const keywordTokens = result.tokens.filter(t => t.type === 'keyword');
      expect(keywordTokens).toHaveLength(1);
      expect(keywordTokens[0].value).toBe('PROJECT_NAME');
    });

    it('should identify comment tokens', () => {
      const doc = createDocument(`
# This is a comment
&GLOBAL
&END GLOBAL
      `);
      
      const result = parser.parse(doc);
      
      const commentTokens = result.tokens.filter(t => t.type === 'comment');
      expect(commentTokens).toHaveLength(1);
      expect(commentTokens[0].value).toBe('# This is a comment');
    });

    it('should identify directive tokens', () => {
      const doc = createDocument(`
@SET VAR value
@IF \${VAR}
@ENDIF
      `);
      
      const result = parser.parse(doc);
      
      const directiveTokens = result.tokens.filter(t => t.type === 'directive');
      expect(directiveTokens).toHaveLength(3);
    });
  });

  describe('Diagnostics', () => {
    it('should detect unclosed sections', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME test
      `);
      
      const result = parser.parse(doc);
      
      const errors = result.diagnostics.filter(d => d.message.includes('Unclosed'));
      expect(errors.length).toBeGreaterThan(0);
    });

    it('should detect unexpected END sections', () => {
      const doc = createDocument(`
&END GLOBAL
      `);
      
      const result = parser.parse(doc);
      
      const errors = result.diagnostics.filter(d => d.message.includes('Unexpected'));
      expect(errors.length).toBeGreaterThan(0);
    });
  });

  describe('Position lookup', () => {
    it('should get token at position', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME test
&END GLOBAL
      `);
      
      parser.parse(doc);
      const token = parser.getTokenAtPosition({ line: 1, character: 3 });
      
      expect(token).toBeDefined();
      expect(token?.type).toBe('section');
    });

    it('should get section at position', () => {
      const doc = createDocument(`
&FORCE_EVAL
  &DFT
  &END DFT
&END FORCE_EVAL
      `);
      
      const result = parser.parse(doc);
      const section = parser.getSectionAtPosition({ line: 2, character: 3 });
      
      expect(section).toBeDefined();
    });
  });
});
