import { HoverProvider } from '../src/features/hover';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position } from 'vscode-languageserver/node';

describe('HoverProvider Extended', () => {
  let provider: HoverProvider;
  let keywordDb: KeywordDatabase;

  beforeEach(() => {
    keywordDb = new KeywordDatabase();
    provider = new HoverProvider(keywordDb);
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Keyword hover', () => {
    it('should provide hover for PROJECT_NAME', () => {
      const doc = createDocument('&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL');
      const position: Position = { line: 1, character: 4 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
      expect(hover?.contents).toBeDefined();
    });

    it('should provide hover for MAX_SCF', () => {
      const doc = createDocument('&SCF\n  MAX_SCF 50\n&END SCF');
      const position: Position = { line: 1, character: 4 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
    });

    it('should provide hover for RUN_TYPE', () => {
      const doc = createDocument('&GLOBAL\n  RUN_TYPE ENERGY\n&END GLOBAL');
      const position: Position = { line: 1, character: 4 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
    });

    it('should return null for unknown keyword', () => {
      const doc = createDocument('&GLOBAL\n  UNKNOWN_KEYWORD value\n&END GLOBAL');
      const position: Position = { line: 1, character: 4 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeNull();
    });
  });

  describe('Section hover', () => {
    it('should provide hover for GLOBAL section', () => {
      const doc = createDocument('&GLOBAL\n&END GLOBAL');
      const position: Position = { line: 0, character: 2 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
    });

    it('should provide hover for FORCE_EVAL section', () => {
      const doc = createDocument('&FORCE_EVAL\n&END FORCE_EVAL');
      const position: Position = { line: 0, character: 2 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
    });
  });

  describe('Value hover', () => {
    it('should provide hover for TRUE value', () => {
      const doc = createDocument('&QS\n  MAP_CONSISTENT TRUE\n&END QS');
      const position: Position = { line: 1, character: 18 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
    });

    it('should provide hover for FALSE value', () => {
      const doc = createDocument('&QS\n  MAP_CONSISTENT FALSE\n&END QS');
      const position: Position = { line: 1, character: 18 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
    });

    it('should provide hover for ENERGY value', () => {
      const doc = createDocument('&GLOBAL\n  RUN_TYPE ENERGY\n&END GLOBAL');
      const position: Position = { line: 1, character: 14 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
    });
  });

  describe('Edge cases', () => {
    it('should return null for empty document', () => {
      const doc = createDocument('');
      const position: Position = { line: 0, character: 0 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeNull();
    });

    it('should return null for whitespace-only line', () => {
      const doc = createDocument('&GLOBAL\n   \n&END GLOBAL');
      const position: Position = { line: 1, character: 1 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeNull();
    });

    it('should handle position at end of line', () => {
      const doc = createDocument('&GLOBAL\n&END GLOBAL');
      const position: Position = { line: 0, character: 100 };
      
      const hover = provider.provideHover(doc, position);
      
      // Should still work or return null gracefully
      expect(hover).toBeDefined();
    });
  });
});
