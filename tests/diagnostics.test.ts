import { DiagnosticsProvider } from '../src/features/diagnostics';
import { CP2KParser } from '../src/parser/cp2k-parser';
import { TextDocument } from 'vscode-languageserver-textdocument';

describe('DiagnosticsProvider', () => {
  let provider: DiagnosticsProvider;
  let parser: CP2KParser;

  beforeEach(() => {
    parser = new CP2KParser();
    provider = new DiagnosticsProvider(parser);
  });

  function createDocument(content: string): TextDocument {
    return TextDocument.create('test://test.inp', 'cp2k', 1, content);
  }

  describe('Validation', () => {
    it('should warn about missing GLOBAL section', () => {
      const doc = createDocument(`
&FORCE_EVAL
  METHOD Quickstep
&END FORCE_EVAL
      `);
      
      const diagnostics = provider.provideDiagnostics(doc, 100);
      
      const warning = diagnostics.find(d => d.message.includes('Missing GLOBAL'));
      expect(warning).toBeDefined();
      expect(warning?.severity).toBe(2); // DiagnosticSeverity.Warning
    });

    it('should inform about missing FORCE_EVAL', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME test
&END GLOBAL
      `);
      
      const diagnostics = provider.provideDiagnostics(doc, 100);
      
      const info = diagnostics.find(d => d.message.includes('FORCE_EVAL'));
      expect(info).toBeDefined();
      expect(info?.severity).toBe(3); // DiagnosticSeverity.Information
    });

    it('should detect empty variable references', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME \${}
&END GLOBAL
      `);
      
      const diagnostics = provider.provideDiagnostics(doc, 100);
      
      const error = diagnostics.find(d => d.message.includes('Empty variable'));
      expect(error).toBeDefined();
      expect(error?.severity).toBe(1); // DiagnosticSeverity.Error
    });

    it('should detect unbalanced parentheses', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME test(
&END GLOBAL
      `);
      
      const diagnostics = provider.provideDiagnostics(doc, 100);
      
      const warning = diagnostics.find(d => d.message.includes('parentheses'));
      expect(warning).toBeDefined();
    });

    it('should limit number of diagnostics', () => {
      const doc = createDocument(`
&GLOBAL
  PROJECT_NAME test(
  RUN_TYPE ENERGY
  PRINT_LEVEL MEDIUM
&END GLOBAL
      `);
      
      const diagnostics = provider.provideDiagnostics(doc, 1);
      
      expect(diagnostics.length).toBeLessThanOrEqual(1);
    });
  });
});
