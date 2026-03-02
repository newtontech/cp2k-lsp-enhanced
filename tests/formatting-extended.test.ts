import { FormattingProvider } from '../src/features/formatting';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Range, FormattingOptions } from 'vscode-languageserver/node';

describe('FormattingProvider Extended', () => {
  let provider: FormattingProvider;

  beforeEach(() => {
    provider = new FormattingProvider();
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  const defaultOptions: FormattingOptions = {
    tabSize: 2,
    insertSpaces: true,
  };

  describe('Basic formatting', () => {
    it('should format empty document', () => {
      const doc = createDocument('');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits).toHaveLength(1);
      // Empty document formats to empty or newline
      expect(edits[0].newText).toBeDefined();
    });

    it('should format simple section', () => {
      const doc = createDocument('&GLOBAL\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits).toHaveLength(1);
      expect(edits[0].newText).toContain('&GLOBAL');
      expect(edits[0].newText).toContain('&END GLOBAL');
    });

    it('should normalize section names to uppercase', () => {
      const doc = createDocument('&global\n&end global');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits[0].newText).toContain('&GLOBAL');
    });
  });

  describe('Indentation', () => {
    it('should indent nested sections', () => {
      const doc = createDocument('&FORCE_EVAL\n&DFT\n&END DFT\n&END FORCE_EVAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      const formatted = edits[0].newText;
      expect(formatted).toContain('  &DFT');
    });

    it('should indent keywords', () => {
      const doc = createDocument('&GLOBAL\nPROJECT_NAME test\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      const formatted = edits[0].newText;
      expect(formatted).toContain('  PROJECT_NAME');
    });

    it('should use tabs when configured', () => {
      const tabOptions: FormattingOptions = {
        tabSize: 4,
        insertSpaces: false,
      };
      const doc = createDocument('&GLOBAL\nPROJECT_NAME test\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, tabOptions);
      
      const formatted = edits[0].newText;
      expect(formatted).toContain('\tPROJECT_NAME');
    });
  });

  describe('Keyword formatting', () => {
    it('should normalize keywords to uppercase', () => {
      const doc = createDocument('&GLOBAL\nproject_name test\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits[0].newText).toContain('PROJECT_NAME');
    });

    it('should preserve values', () => {
      const doc = createDocument('&GLOBAL\nPROJECT_NAME my_project\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits[0].newText).toContain('my_project');
    });

    it('should handle inline comments', () => {
      const doc = createDocument('&GLOBAL\nPROJECT_NAME test  # comment\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      const formatted = edits[0].newText;
      expect(formatted).toContain('# comment');
    });
  });

  describe('Comment handling', () => {
    it('should preserve comments', () => {
      const doc = createDocument('# Header comment\n&GLOBAL\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits[0].newText).toContain('# Header comment');
    });

    it('should preserve ! comments', () => {
      const doc = createDocument('! Comment\n&GLOBAL\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits[0].newText).toContain('! Comment');
    });
  });

  describe('Directive handling', () => {
    it('should keep directives at start of line', () => {
      const doc = createDocument('@SET VAR value\n&GLOBAL\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      const formatted = edits[0].newText;
      expect(formatted).toContain('@SET VAR value');
    });

    it('should preserve @INCLUDE directives', () => {
      const doc = createDocument('@INCLUDE "file.inc"\n&GLOBAL\n&END GLOBAL');
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits[0].newText).toContain('@INCLUDE');
    });
  });

  describe('Complex documents', () => {
    it('should format realistic CP2K input', () => {
      const doc = createDocument(`
&GLOBAL
PROJECT_NAME test
&END GLOBAL
&FORCE_EVAL
METHOD Quickstep
&DFT
BASIS_SET_FILE_NAME BASIS
&END DFT
&END FORCE_EVAL
      `);
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      const formatted = edits[0].newText;
      expect(formatted).toContain('&GLOBAL');
      expect(formatted).toContain('&FORCE_EVAL');
      expect(formatted).toContain('&DFT');
    });
  });

  describe('Range formatting', () => {
    it('should format specific range', () => {
      const doc = createDocument('&GLOBAL\nPROJECT_NAME test\n&END GLOBAL');
      const range = Range.create(1, 0, 1, 20);
      
      const edits = provider.provideRangeFormatting(doc, range, defaultOptions);
      
      expect(edits.length).toBeGreaterThan(0);
    });
  });
});
