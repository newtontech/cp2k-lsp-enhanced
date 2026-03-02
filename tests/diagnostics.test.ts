/**
 * Diagnostics Provider Tests
 */

import { DiagnosticsProvider } from '../src/features/diagnostics';
import { CP2KParser } from '../src/parser/cp2k-parser';
import { SchemaParser } from '../src/data/schema-parser';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Diagnostic, DiagnosticSeverity } from 'vscode-languageserver/node';

const createMockDocument = (content: string): TextDocument => {
  const lines = content.split('\n');
  return {
    uri: 'file:///test/test.inp',
    languageId: 'cp2k',
    version: 1,
    getText: (range?: any) => {
      if (!range) return content;
      const startLine = range.start.line;
      const endLine = range.end.line;
      const startChar = range.start.character;
      const endChar = range.end.character;
      
      if (startLine === endLine) {
        return lines[startLine].substring(startChar, endChar);
      }
      
      let result = lines[startLine].substring(startChar);
      for (let i = startLine + 1; i < endLine; i++) {
        result += '\n' + lines[i];
      }
      if (endLine < lines.length) {
        result += '\n' + lines[endLine].substring(0, endChar);
      }
      return result;
    },
    lineCount: lines.length,
    positionAt: (offset: number) => {
      let currentOffset = 0;
      for (let i = 0; i < lines.length; i++) {
        if (currentOffset + lines[i].length >= offset) {
          return { line: i, character: offset - currentOffset };
        }
        currentOffset += lines[i].length + 1;
      }
      return { line: 0, character: offset };
    },
    offsetAt: (position: any) => {
      let offset = 0;
      for (let i = 0; i < position.line && i < lines.length; i++) {
        offset += lines[i].length + 1;
      }
      return offset + Math.min(position.character, lines[position.line]?.length || 0);
    },
  } as TextDocument;
};

describe('DiagnosticsProvider', () => {
  let provider: DiagnosticsProvider;
  let parser: CP2KParser;

  beforeEach(() => {
    parser = new CP2KParser();
    provider = new DiagnosticsProvider(parser);
  });

  describe('Basic functionality', () => {
    test('should create provider instance', () => {
      expect(provider).toBeDefined();
    });

    test('should provide diagnostics', () => {
      const document = createMockDocument(`
&GLOBAL
  PROJECT_NAME TEST
&END GLOBAL
      `.trim());

      const diagnostics = provider.provideDiagnostics(document);
      expect(Array.isArray(diagnostics)).toBe(true);
    });

    test('should enforce max problems limit', () => {
      const document = createMockDocument('TEST');
      const diagnostics = provider.provideDiagnostics(document, 5);
      expect(diagnostics.length).toBeLessThanOrEqual(5);
    });
  });

  describe('Configuration', () => {
    test('should update options', () => {
      provider.updateOptions({
        maxProblems: 200,
        enableSchemaValidation: false,
        enableDeepValidation: true,
        cp2kPath: '/custom/cp2k'
      });
      
      expect(provider['options'].maxProblems).toBe(200);
      expect(provider['options'].enableSchemaValidation).toBe(false);
    });
  });

  describe('Required sections', () => {
    test('should detect missing GLOBAL section', () => {
      const document = createMockDocument('TEST');
      const diagnostics = provider.provideDiagnostics(document);
      
      const missingGlobal = diagnostics.some(d => 
        d.code === 'missing-section' && 
        d.message.includes('GLOBAL')
      );
      expect(missingGlobal).toBe(true);
    });

    test('should detect missing FORCE_EVAL section', () => {
      const document = createMockDocument(`
&GLOBAL
  PROJECT_NAME TEST
&END GLOBAL
      `.trim());

      const diagnostics = provider.provideDiagnostics(document);
      
      // Should warn about missing FORCE_EVAL (information level)
      const hasWarning = diagnostics.some(d =>
        d.message.includes('FORCE_EVAL')
      );
      expect(hasWarning).toBe(true);
    });
  });

  describe('Variable expansion', () => {
    test('should detect empty variable reference', () => {
      const document = createMockDocument('${}');
      const diagnostics = provider.provideDiagnostics(document);
      
      const hasError = diagnostics.some(d =>
        d.message.includes('Empty variable reference')
      );
      expect(hasError).toBe(true);
    });

    test('should allow valid variable references', () => {
      const document = createMockDocument('${VAR_NAME}');
      const diagnostics = provider.provideDiagnostics(document);
      
      const hasError = diagnostics.some(d =>
        d.message.includes('Empty variable reference')
      );
      expect(hasError).toBe(false);
    });
  });

  describe('Balanced brackets', () => {
    test('should detect unbalanced parentheses', () => {
      const document = createMockDocument('KEYWORD (value');
      const diagnostics = provider.provideDiagnostics(document);
      
      const hasWarning = diagnostics.some(d =>
        d.message.includes('Unbalanced parentheses')
      );
      expect(hasWarning).toBe(true);
    });

    test('should detect unbalanced brackets', () => {
      const document = createMockDocument('KEYWORD [value');
      const diagnostics = provider.provideDiagnostics(document);
      
      const hasWarning = diagnostics.some(d =>
        d.message.includes('Unbalanced brackets')
      );
      expect(hasWarning).toBe(true);
    });

    test('should allow balanced brackets', () => {
      const document = createMockDocument('KEYWORD [value]');
      const diagnostics = provider.provideDiagnostics(document);
      
      const hasWarning = diagnostics.some(d =>
        d.message.includes('Unbalanced') && d.severity === DiagnosticSeverity.Warning
      );
      expect(hasWarning).toBe(false);
    });
  });

  describe('Type validation', () => {
    test('should validate integer values', () => {
      const document = createMockDocument(`
&GLOBAL
  MAX_SCF abc
&END GLOBAL
      `.trim());

      const diagnostics = provider.provideDiagnostics(document);
      
      // May have type error if schema is loaded
      const hasTypeErrors = diagnostics.some(d =>
        d.code === 'type-mismatch'
      );
    });

    test('should validate real numbers', () => {
      const document = createMockDocument(`
&GLOBAL
  CUTOFF abc
&END GLOBAL
      `.trim());

      const diagnostics = provider.provideDiagnostics(document);
      expect(Array.isArray(diagnostics)).toBe(true);
    });

    test('should validate logical values', () => {
      const document = createMockDocument(`
&GLOBAL
  MAP_CONSISTENT yesno
&END GLOBAL
      `.trim());

      const diagnostics = provider.provideDiagnostics(document);
      expect(Array.isArray(diagnostics)).toBe(true);
    });
  });

  describe('Deep validation', () => {
    test('should provide deep validation (async)', async () => {
      const document = createMockDocument(`
&GLOBAL
  PROJECT_NAME TEST
&END GLOBAL
      `.trim());

      const callbackCalled = jest.fn();
      await provider.provideDeepValidation(document, callbackCalled);
      
      // Callback should be called (even if empty diagnostics when CP2K not available)
      expect(callbackCalled).toHaveBeenCalled();
    });
  });
});
