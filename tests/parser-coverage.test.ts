import { CP2KParser } from '../src/parser/cp2k-parser';
import { TextDocument } from 'vscode-languageserver-textdocument';

describe('CP2KParser Coverage', () => {
  let parser: CP2KParser;

  beforeEach(() => {
    parser = new CP2KParser();
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Keyword parsing', () => {
    it('should parse keyword with no value', () => {
      const doc = createDocument('&GLOBAL\n  DEBUG\n&END GLOBAL');
      const result = parser.parse(doc);
      expect(result.sections[0].keywords).toHaveLength(1);
      expect(result.sections[0].keywords[0].name).toBe('DEBUG');
      expect(result.sections[0].keywords[0].value).toBe('');
    });

    it('should parse keyword with boolean value', () => {
      const doc = createDocument('&FORCE_EVAL\n  &DFT\n    &QS\n      MAP_CONSISTENT TRUE\n    &END QS\n  &END DFT\n&END FORCE_EVAL');
      const result = parser.parse(doc);
      expect(result.tokens.some(t => t.type === 'boolean')).toBe(true);
    });

    it('should parse keyword with Fortran-style boolean', () => {
      const doc = createDocument('&FORCE_EVAL\n  &DFT\n    &QS\n      MAP_CONSISTENT .TRUE.\n    &END QS\n  &END DFT\n&END FORCE_EVAL');
      const result = parser.parse(doc);
      expect(result.tokens.some(t => t.type === 'boolean')).toBe(true);
    });

    it('should parse keyword with scientific notation', () => {
      const doc = createDocument('&FORCE_EVAL\n  &DFT\n    &SCF\n      EPS_SCF 1.0E-7\n    &END SCF\n  &END DFT\n&END FORCE_EVAL');
      const result = parser.parse(doc);
      expect(result.tokens.some(t => t.value === '1.0E-7' && t.type === 'number')).toBe(true);
    });
  });

  describe('Error detection', () => {
    it('should detect unclosed sections', () => {
      const doc = createDocument('&GLOBAL\n  PROJECT_NAME test');
      const result = parser.parse(doc);
      const errors = result.diagnostics.filter(d => d.message.includes('Unclosed'));
      expect(errors.length).toBeGreaterThan(0);
    });
  });

  describe('Edge cases', () => {
    it('should handle document with only newlines', () => {
      const doc = createDocument('\n\n\n\n');
      const result = parser.parse(doc);
      expect(result.sections).toHaveLength(0);
      expect(result.tokens).toHaveLength(0);
    });

    it('should handle Windows line endings', () => {
      const doc = createDocument('&GLOBAL\r\n  PROJECT_NAME test\r\n&END GLOBAL');
      const result = parser.parse(doc);
      expect(result.sections).toHaveLength(1);
      expect(result.sections[0].name).toBe('GLOBAL');
    });

    it('should handle malformed section syntax', () => {
      const doc = createDocument('&\n&END');
      const result = parser.parse(doc);
      expect(result).toBeDefined();
    });
  });
});
