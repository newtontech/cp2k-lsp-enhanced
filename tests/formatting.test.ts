import { FormattingProvider } from '../src/features/formatting';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { FormattingOptions } from 'vscode-languageserver/node';

describe('FormattingProvider', () => {
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
    it('should format section names', () => {
      const doc = createDocument(`
&global
  PROJECT_NAME test
&END global
      `);
      
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits).toHaveLength(1);
      expect(edits[0].newText).toContain('&global'.toUpperCase());
    });

    it('should add proper indentation', () => {
      const doc = createDocument(`
&GLOBAL
PROJECT_NAME test
&END GLOBAL
      `);
      
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      const lines = edits[0].newText.split('\n');
      const projectNameLine = lines.find(l => l.includes('PROJECT_NAME'));
      expect(projectNameLine).toMatch(/^\s+PROJECT_NAME/);
    });

    it('should format nested sections', () => {
      const doc = createDocument(`
&FORCE_EVAL
&DFT
BASIS_SET_FILE_NAME test
&END DFT
&END FORCE_EVAL
      `);
      
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      const lines = edits[0].newText.split('\n');
      const dftLine = lines.find(l => l.includes('&DFT'));
      const basisLine = lines.find(l => l.includes('BASIS_SET_FILE_NAME'));
      
      expect(dftLine).toMatch(/^\s{2}\u0026DFT/);
      expect(basisLine).toMatch(/^\s{4}BASIS_SET_FILE_NAME/);
    });

    it('should preserve preprocessor directives at start of line', () => {
      const doc = createDocument(`
  @SET VAR value
&GLOBAL
&END GLOBAL
      `);
      
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      const lines = edits[0].newText.split('\n');
      const setLine = lines.find(l => l.includes('@SET'));
      expect(setLine).toMatch(/^@SET/);
    });

    it('should use tabs when insertSpaces is false', () => {
      const doc = createDocument(`
&GLOBAL
PROJECT_NAME test
&END GLOBAL
      `);
      
      const options: FormattingOptions = {
        tabSize: 4,
        insertSpaces: false,
      };
      
      const edits = provider.provideFormatting(doc, options);
      
      const lines = edits[0].newText.split('\n');
      const projectNameLine = lines.find(l => l.includes('PROJECT_NAME'));
      expect(projectNameLine).toMatch(/^\t/);
    });
  });

  describe('Keyword formatting', () => {
    it('should normalize keywords to uppercase', () => {
      const doc = createDocument(`
&GLOBAL
  project_name test
&END GLOBAL
      `);
      
      const edits = provider.provideFormatting(doc, defaultOptions);
      
      expect(edits[0].newText).toContain('PROJECT_NAME');
    });
  });
});
