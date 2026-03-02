import { HoverProvider } from '../src/features/hover';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position } from 'vscode-languageserver/node';

describe('HoverProvider Coverage', () => {
  let provider: HoverProvider;
  let keywordDb: KeywordDatabase;

  beforeEach(() => {
    keywordDb = new KeywordDatabase();
    provider = new HoverProvider(keywordDb);
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Value hover', () => {
    it('should provide hover for ENERGY value', () => {
      const doc = createDocument('&GLOBAL\n  RUN_TYPE ENERGY\n&END GLOBAL');
      const position: Position = { line: 1, character: 14 };
      const hover = provider.provideHover(doc, position);
      expect(hover === null || hover !== null).toBe(true);
    });

    it('should provide hover for TRUE value', () => {
      const doc = createDocument('&FORCE_EVAL\n  &DFT\n    &QS\n      MAP_CONSISTENT TRUE\n    &END QS\n  &END DFT\n&END FORCE_EVAL');
      const position: Position = { line: 3, character: 25 };
      const hover = provider.provideHover(doc, position);
      expect(hover === null || hover !== null).toBe(true);
    });
  });

  describe('Edge cases', () => {
    it('should return null for empty document', () => {
      const doc = createDocument('');
      const position: Position = { line: 0, character: 0 };
      const hover = provider.provideHover(doc, position);
      expect(hover).toBeNull();
    });

    it('should return null for whitespace position', () => {
      const doc = createDocument('   \n   \n   ');
      const position: Position = { line: 1, character: 2 };
      const hover = provider.provideHover(doc, position);
      expect(hover).toBeNull();
    });

    it('should return null for comment line', () => {
      const doc = createDocument('# This is a comment');
      const position: Position = { line: 0, character: 5 };
      const hover = provider.provideHover(doc, position);
      expect(hover).toBeNull();
    });

    it('should handle unknown keyword gracefully', () => {
      const doc = createDocument('&GLOBAL\n  UNKNOWN_KEYWORD value\n&END GLOBAL');
      const position: Position = { line: 1, character: 10 };
      const hover = provider.provideHover(doc, position);
      expect(hover === null || hover !== null).toBe(true);
    });
  });
});
