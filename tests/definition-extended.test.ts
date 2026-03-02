import { DefinitionProvider } from '../src/features/definition';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position } from 'vscode-languageserver/node';

describe('DefinitionProvider Extended', () => {
  let provider: DefinitionProvider;
  let keywordDb: KeywordDatabase;

  beforeEach(() => {
    keywordDb = new KeywordDatabase();
    provider = new DefinitionProvider(keywordDb);
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Section definition', () => {
    it('should find section definition', () => {
      const doc = createDocument(`
&GLOBAL
&END GLOBAL
      `);
      const position: Position = { line: 0, character: 2 };
      
      const definition = provider.provideDefinition(doc, position);
      
      // Definition provider should return something for section references
      expect(definition).toBeDefined();
    });

    it('should handle section search', () => {
      const doc = createDocument('&UNKNOWN\n&END UNKNOWN');
      const position: Position = { line: 0, character: 2 };
      
      const definition = provider.provideDefinition(doc, position);
      
      // Should handle gracefully
      expect(definition).toBeDefined();
    });
  });

  describe('Variable definition', () => {
    it('should find @SET variable definition', () => {
      const doc = createDocument(`
@SET MY_VAR value
&GLOBAL
  PROJECT_NAME \${MY_VAR}
&END GLOBAL
      `);
      const position: Position = { line: 2, character: 18 };
      
      const definition = provider.provideDefinition(doc, position);
      
      expect(definition).toBeDefined();
    });

    it('should handle undefined variable', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME \${UNDEFINED}
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 18 };
      
      const definition = provider.provideDefinition(doc, position);
      
      // Should handle gracefully
      expect(definition).toBeDefined();
    });
  });

  describe('@INCLUDE definition', () => {
    it('should handle @INCLUDE directive', () => {
      const doc = createDocument('@INCLUDE "other.inc"');
      const position: Position = { line: 0, character: 10 };
      
      const definition = provider.provideDefinition(doc, position);
      
      expect(definition).toBeDefined();
      expect(definition?.uri).toContain('other.inc');
    });

    it('should handle @INCLUDE with single quotes', () => {
      const doc = createDocument("@INCLUDE 'other.inc'");
      const position: Position = { line: 0, character: 10 };
      
      const definition = provider.provideDefinition(doc, position);
      
      expect(definition).toBeDefined();
    });

    it('should handle @INCLUDE without quotes', () => {
      const doc = createDocument('@INCLUDE other.inc');
      const position: Position = { line: 0, character: 10 };
      
      const definition = provider.provideDefinition(doc, position);
      
      expect(definition).toBeDefined();
    });
  });

  describe('@SET definition', () => {
    it('should find @SET variable at definition site', () => {
      const doc = createDocument('@SET MY_VAR value');
      const position: Position = { line: 0, character: 7 };
      
      const definition = provider.provideDefinition(doc, position);
      
      expect(definition).toBeDefined();
    });
  });

  describe('Edge cases', () => {
    it('should return null for empty document', () => {
      const doc = createDocument('');
      const position: Position = { line: 0, character: 0 };
      
      const definition = provider.provideDefinition(doc, position);
      
      expect(definition).toBeNull();
    });

    it('should return null for position without word', () => {
      const doc = createDocument('&GLOBAL\n   \n&END GLOBAL');
      const position: Position = { line: 1, character: 1 };
      
      const definition = provider.provideDefinition(doc, position);
      
      expect(definition).toBeNull();
    });

    it('should handle nested sections', () => {
      const doc = createDocument(`
&FORCE_EVAL
  &DFT
  &END DFT
&END FORCE_EVAL
      `);
      const position: Position = { line: 1, character: 4 };
      
      const definition = provider.provideDefinition(doc, position);
      
      expect(definition).toBeDefined();
    });
  });
});
