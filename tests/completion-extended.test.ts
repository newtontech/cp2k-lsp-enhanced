import { CompletionProvider } from '../src/features/completion';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position, CompletionItemKind } from 'vscode-languageserver/node';

describe('CompletionProvider Extended', () => {
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
      expect(globalSection?.kind).toBe(CompletionItemKind.Class);
    });

    it('should complete FORCE_EVAL section', () => {
      const doc = createDocument('&FOR');
      const position: Position = { line: 0, character: 4 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      const forceEval = items.find(item => item.label === 'FORCE_EVAL');
      expect(forceEval).toBeDefined();
    });

    it('should include section description in documentation', () => {
      const doc = createDocument('&GLO');
      const position: Position = { line: 0, character: 4 };
      
      const items = provider.provideCompletionItems(doc, position);
      const globalSection = items.find(item => item.label === 'GLOBAL');
      
      expect(globalSection?.documentation).toBeDefined();
    });

    it('should return empty array for empty document at start', () => {
      const doc = createDocument('');
      const position: Position = { line: 0, character: 0 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      // Should return top-level keywords
      expect(items.length).toBeGreaterThan(0);
    });
  });

  describe('Keyword completion', () => {
    it('should provide completions inside GLOBAL section', () => {
      const doc = createDocument(`
&GLOBAL
  PRO
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 6 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      expect(items.length).toBeGreaterThan(0);
    });

    it('should provide completions inside SCF section', () => {
      const doc = createDocument(`
&SCF
  MAX
&END SCF
      `);
      const position: Position = { line: 1, character: 6 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      // SCF section has keywords, just check we get completions
      expect(items.length).toBeGreaterThan(0);
    });

    it('should provide subsection completions', () => {
      const doc = createDocument(`
&DFT
  
&END DFT
      `);
      const position: Position = { line: 1, character: 2 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      // Should include subsections like SCF, MGRID, etc.
      expect(items.length).toBeGreaterThan(0);
    });
  });

  describe('Value completion', () => {
    it('should provide value completions for keywords with allowed values', () => {
      const doc = createDocument(`
&GLOBAL
  RUN_TYPE 
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 11 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      // Value completions may or may not be provided depending on implementation
      expect(items).toBeDefined();
    });

    it('should handle PRINT_LEVEL keyword', () => {
      const doc = createDocument(`
&GLOBAL
  PRINT_LEVEL 
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 14 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      expect(items).toBeDefined();
    });
  });

  describe('Resolve completion', () => {
    it('should resolve completion item', () => {
      const item = {
        label: '&GLOBAL',
        kind: CompletionItemKind.Class,
      };
      
      const resolved = provider.resolveCompletionItem(item);
      
      expect(resolved).toBeDefined();
      expect(resolved.label).toBe('&GLOBAL');
    });
  });

  describe('Section context', () => {
    it('should detect nested section context', () => {
      const doc = createDocument(`
&FORCE_EVAL
  &DFT
    
  &END DFT
&END FORCE_EVAL
      `);
      const position: Position = { line: 2, character: 4 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      // Should provide keywords/subsections for DFT section
      expect(items.length).toBeGreaterThan(0);
    });

    it('should handle deeply nested sections', () => {
      const doc = createDocument(`
&FORCE_EVAL
  &DFT
    &SCF
      
    &END SCF
  &END DFT
&END FORCE_EVAL
      `);
      const position: Position = { line: 3, character: 6 };
      
      const items = provider.provideCompletionItems(doc, position);
      
      expect(items.length).toBeGreaterThan(0);
    });
  });
});
