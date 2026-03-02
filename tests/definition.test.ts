import { DefinitionProvider } from '../src/features/definition';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position } from 'vscode-languageserver/node';

describe('DefinitionProvider', () => {
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
  PROJECT_NAME test
&END GLOBAL
      `);
      const position: Position = { line: 2, character: 2 }; // On &END GLOBAL
      
      const location = provider.provideDefinition(doc, position);
      
      expect(location).toBeDefined();
    });

    it('should return null for non-identifier positions', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME test
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 20 }; // On value
      
      const location = provider.provideDefinition(doc, position);
      
      expect(location).toBeNull();
    });
  });

  describe('Variable definition', () => {
    it('should find @SET variable definition', () => {
      const doc = createDocument(`
@SET MY_VAR my_value
&GLOBAL
  PROJECT_NAME \${MY_VAR}
&END GLOBAL
      `);
      const position: Position = { line: 3, character: 18 }; // On \${MY_VAR}
      
      const location = provider.provideDefinition(doc, position);
      
      expect(location).toBeDefined();
    });
  });
});
