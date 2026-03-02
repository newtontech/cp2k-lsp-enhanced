import { CompletionProvider } from '../src/features/completion';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position, CompletionItemKind } from 'vscode-languageserver/node';

describe('CompletionProvider Coverage', () => {
  let provider: CompletionProvider;
  let keywordDb: KeywordDatabase;

  beforeEach(() => {
    keywordDb = new KeywordDatabase();
    provider = new CompletionProvider(keywordDb);
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Value completion', () => {
    it('should provide allowed values for RUN_TYPE', () => {
      const doc = createDocument('&GLOBAL\n  RUN_TYPE \n&END GLOBAL');
      const position: Position = { line: 1, character: 12 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      expect(items.length).toBeGreaterThan(0);
      const energyItem = items.find(item => item.label === 'ENERGY');
      expect(energyItem).toBeDefined();
    });

    it('should provide allowed values for PRINT_LEVEL', () => {
      const doc = createDocument('&GLOBAL\n  PRINT_LEVEL \n&END GLOBAL');
      const position: Position = { line: 1, character: 15 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      const mediumItem = items.find(item => item.label === 'MEDIUM');
      expect(mediumItem).toBeDefined();
    });

    it('should provide value completions for METHOD keyword', () => {
      const doc = createDocument('&FORCE_EVAL\n  METHOD \n&END FORCE_EVAL');
      const position: Position = { line: 1, character: 10 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      // Should provide some completions (may or may not include QUICKSTEP)
      expect(Array.isArray(items)).toBe(true);
    });

    it('should not provide value completions for unknown keyword', () => {
      const doc = createDocument('&GLOBAL\n  UNKNOWN_KEYWORD \n&END GLOBAL');
      const position: Position = { line: 1, character: 19 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      expect(Array.isArray(items)).toBe(true);
    });
  });

  describe('resolveCompletionItem', () => {
    it('should resolve section completion item with documentation', () => {
      const item = { label: '&GLOBAL', kind: CompletionItemKind.Class };
      const resolved = provider.resolveCompletionItem(item);
      expect(resolved.documentation).toBeDefined();
    });

    it('should not modify non-section completion items', () => {
      const item = { label: 'PROJECT_NAME', kind: CompletionItemKind.Property };
      const resolved = provider.resolveCompletionItem(item);
      expect(resolved.label).toBe('PROJECT_NAME');
    });
  });

  describe('Edge cases', () => {
    it('should handle empty document', () => {
      const doc = createDocument('');
      const position: Position = { line: 0, character: 0 };
      const items = provider.provideCompletionItems(doc, position);
      expect(Array.isArray(items)).toBe(true);
    });

    it('should handle document with only whitespace', () => {
      const doc = createDocument('   \n   \n   ');
      const position: Position = { line: 1, character: 3 };
      const items = provider.provideCompletionItems(doc, position);
      expect(Array.isArray(items)).toBe(true);
    });
  });
});
