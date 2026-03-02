import { DefinitionProvider } from '../src/features/definition';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position } from 'vscode-languageserver/node';

describe('DefinitionProvider Coverage', () => {
  let provider: DefinitionProvider;
  let keywordDb: KeywordDatabase;

  beforeEach(() => {
    keywordDb = new KeywordDatabase();
    provider = new DefinitionProvider(keywordDb);
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Variable definition', () => {
    it('should find variable definition for @SET variable', () => {
      const doc = createDocument('@SET PROJECT myproject\n&GLOBAL\n  PROJECT_NAME ${PROJECT}\n&END GLOBAL');
      const position: Position = { line: 2, character: 20 };
      const location = provider.provideDefinition(doc, position);
      expect(location).not.toBeNull();
      if (location) {
        expect(location.range.start.line).toBe(0);
      }
    });
  });

  describe('Include file definition', () => {
    it('should provide location for @INCLUDE reference', () => {
      const doc = createDocument('@INCLUDE "basis_sets.inc"\n&GLOBAL\n&END GLOBAL');
      const position: Position = { line: 0, character: 10 };
      const location = provider.provideDefinition(doc, position);
      expect(location).not.toBeNull();
      if (location) {
        expect(location.uri).toContain('basis_sets.inc');
      }
    });
  });

  describe('Edge cases', () => {
    it('should return null for empty document', () => {
      const doc = createDocument('');
      const position: Position = { line: 0, character: 0 };
      const location = provider.provideDefinition(doc, position);
      expect(location).toBeNull();
    });

    it('should return null for whitespace position', () => {
      const doc = createDocument('   \n   \n   ');
      const position: Position = { line: 1, character: 2 };
      const location = provider.provideDefinition(doc, position);
      expect(location).toBeNull();
    });
  });
});
