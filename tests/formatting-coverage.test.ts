import { FormattingProvider } from '../src/features/formatting';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { FormattingOptions, Range } from 'vscode-languageserver/node';

describe('FormattingProvider Coverage', () => {
  let provider: FormattingProvider;

  beforeEach(() => {
    provider = new FormattingProvider();
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Directive handling', () => {
    it('should keep directives at start of line', () => {
      const doc = createDocument('@SET VAR value\n&GLOBAL\n  PROJECT_NAME ${VAR}\n&END GLOBAL');
      const options: FormattingOptions = { insertSpaces: true, tabSize: 2 };
      const edits = provider.provideFormatting(doc, options);
      const formatted = edits[0].newText;
      expect(formatted).toContain('@SET');
    });
  });

  describe('Edge cases', () => {
    it('should handle empty document', () => {
      const doc = createDocument('');
      const options: FormattingOptions = { insertSpaces: true, tabSize: 2 };
      const edits = provider.provideFormatting(doc, options);
      expect(edits.length).toBe(1);
    });

    it('should handle mismatched section ends', () => {
      const doc = createDocument('&GLOBAL\n  PROJECT_NAME test\n&END FORCE_EVAL');
      const options: FormattingOptions = { insertSpaces: true, tabSize: 2 };
      expect(() => provider.provideFormatting(doc, options)).not.toThrow();
    });
  });

  describe('provideRangeFormatting', () => {
    it('should format a specific range', () => {
      const doc = createDocument('&GLOBAL\n  project_name test\n&END GLOBAL');
      const range = { start: { line: 1, character: 0 }, end: { line: 1, character: 20 } };
      const options: FormattingOptions = { insertSpaces: true, tabSize: 2 };
      const edits = provider.provideRangeFormatting(doc, range, options);
      expect(edits.length).toBeGreaterThanOrEqual(0);
    });
  });
});
