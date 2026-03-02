import { CompletionProvider } from '../src/features/completion';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position } from 'vscode-languageserver/node';

describe('CompletionProvider', () => {
  let provider: CompletionProvider;
  let keywordDb: KeywordDatabase;

  beforeEach(() => {
    keywordDb = new KeywordDatabase();
    provider = new CompletionProvider(keywordDb);
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Section completion', () => {
    it('should complete sections when typing &', () => {
      const doc = createDocument('&GLO');
      const position: Position = { line: 0, character: 4 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      const globalSection = items.find(item => item.label === 'GLOBAL');
      expect(globalSection).toBeDefined();
      expect(globalSection?.kind).toBe(7); // CompletionItemKind.Class
    });

    it('should include section description', () => {
      const doc = createDocument('&GLO');
      const position: Position = { line: 0, character: 4 };
      
      const items = provider.provideCompletionItems(doc, position);
      const globalSection = items.find(item => item.label === 'GLOBAL');
      
      expect(globalSection?.documentation).toBeDefined();
    });
  });

  describe('Keyword completion', () => {
    it('should provide completions', () => {
      const doc = createDocument(`
&GLOBAL
  PRO
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 6 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      expect(items.length).toBeGreaterThan(0);
    });
  });
});
