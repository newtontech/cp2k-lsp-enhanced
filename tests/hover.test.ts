import { HoverProvider } from '../src/features/hover';
import { KeywordDatabase } from '../src/data/keyword-database';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position } from 'vscode-languageserver/node';

describe('HoverProvider', () => {
  let provider: HoverProvider;
  let keywordDb: KeywordDatabase;

  beforeEach(() => {
    keywordDb = new KeywordDatabase();
    provider = new HoverProvider(keywordDb);
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Section hover', () => {
    it('should provide hover for sections', () => {
      const doc = createDocument(`
&GLOBAL
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 2 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
      expect(hover?.contents).toBeDefined();
    });

    it('should include section description', () => {
      const doc = createDocument(`
&GLOBAL
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 2 };
      
      const hover = provider.provideHover(doc, position);
      const content = hover?.contents as { kind: string; value: string };
      
      expect(content.value).toContain('GLOBAL');
    });
  });

  describe('Keyword hover', () => {
    it('should provide hover for keywords', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME test
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 5 };
      
      const hover = provider.provideHover(doc, position);
      
      expect(hover).toBeDefined();
    });

    it('should include keyword details', () => {
      const doc = createDocument(`
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL
      `);
      const position: Position = { line: 1, character: 5 };
      
      const hover = provider.provideHover(doc, position);
      const content = hover?.contents as { kind: string; value: string };
      
      expect(content.value).toContain('RUN_TYPE');
    });
  });
});
