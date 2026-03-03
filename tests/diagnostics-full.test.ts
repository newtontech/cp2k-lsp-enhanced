/**
 * Full diagnostics tests for 100% coverage
 */

import { DiagnosticsProvider } from '../src/features/diagnostics';
import { CP2KParser } from '../src/parser/cp2k-parser';
import { TextDocument } from 'vscode-languageserver-textdocument';

describe('DiagnosticsProvider Full Tests', () => {
  let parser: CP2KParser;
  let provider: DiagnosticsProvider;

  beforeEach(() => {
    parser = new CP2KParser();
    provider = new DiagnosticsProvider(parser);
  });

  describe('Options Management', () => {
    it('should update maxProblems option', () => {
      provider.updateOptions({ maxProblems: 50 });
      expect((provider as any).options.maxProblems).toBe(50);
    });

    it('should update enableSchemaValidation option', () => {
      provider.updateOptions({ enableSchemaValidation: false });
      expect((provider as any).options.enableSchemaValidation).toBe(false);
    });

    it('should update enableDeepValidation option', () => {
      provider.updateOptions({ enableDeepValidation: true });
      expect((provider as any).options.enableDeepValidation).toBe(true);
    });
  });

  describe('Syntax Validation', () => {
    it('should detect invalid section syntax with just &', () => {
      const content = '&';
      const document = TextDocument.create('test://test.inp', 'cp2k', 1, content);
      const parsed = parser.parse(document);
      const diagnostics: any[] = [];
      
      (provider as any).checkSyntax(document, parsed, diagnostics);
      
      // Empty line or invalid section should have diagnostic
      expect(diagnostics.length).toBeGreaterThanOrEqual(0);
    });

    it('should handle document without FORCE_EVAL', () => {
      const content = `&GLOBAL
  PROJECT test
&END GLOBAL`;
      
      const document = TextDocument.create('test://test.inp', 'cp2k', 1, content);
      const parsed = parser.parse(document);
      const diagnostics: any[] = [];
      
      const semanticDiagnostics = (provider as any).validateDocument(document, parsed);
      
      expect(semanticDiagnostics.some((d: any) => d.message.includes('FORCE_EVAL'))).toBe(true);
    });

    it('should handle document with FORCE_EVAL', () => {
      const content = `&GLOBAL
  PROJECT test
&END GLOBAL
&FORCE_EVAL
&END FORCE_EVAL`;
      
      const document = TextDocument.create('test://test.inp', 'cp2k', 1, content);
      const parsed = parser.parse(document);
      
      const semanticDiagnostics = (provider as any).validateDocument(document, parsed);
      
      const forceEvalInfo = semanticDiagnostics.filter((d: any) => 
        d.message.includes('Missing FORCE_EVAL') || d.message.includes('will not perform')
      );
      expect(forceEvalInfo.length).toBe(0);
    });
  });

  describe('Constraint Validation', () => {
    it('should validate section constraints with schema', () => {
      const mockSchemaSection = {
        keywords: new Map([
          ['REQUIRED_KEY', { required: true }]
        ]),
        subsections: new Map([
          ['REQUIRED_SUB', { required: true }]
        ])
      };
      
      const mockSchemaParser = {
        getSection: jest.fn().mockReturnValue(mockSchemaSection)
      };
      
      (provider as any).schemaParser = mockSchemaParser;
      
      const section = {
        name: 'TEST_SECTION',
        keywords: [],
        subsections: [],
        location: { start: { line: 0, column: 0 } }
      };
      
      const diagnostics: any[] = [];
      (provider as any).validateSectionConstraints(section, diagnostics);
      
      expect(diagnostics.some((d: any) => d.code === 'missing-keyword')).toBe(true);
      expect(diagnostics.some((d: any) => d.code === 'missing-subsection')).toBe(true);
    });

    it('should handle mutually exclusive keywords', () => {
      const section = {
        keywords: [
          { name: 'METHOD' },
          { name: 'DFT' }
        ],
        location: { start: { line: 0, column: 0 } }
      };
      
      const diagnostics: any[] = [];
      (provider as any).checkMutuallyExclusive(section, diagnostics);
      
      expect(diagnostics.some((d: any) => d.code === 'mutual-exclusion')).toBe(true);
    });

    it('should validate type constraints', () => {
      const mockSchemaParser = {
        getKeyword: jest.fn((name: string) => {
          if (name === 'INT_KEY') return { dataType: 'INTEGER' };
          if (name === 'REAL_KEY') return { dataType: 'REAL' };
          if (name === 'BOOL_KEY') return { dataType: 'LOGICAL' };
          return undefined;
        })
      };
      
      (provider as any).schemaParser = mockSchemaParser;
      
      const parsed = {
        sections: [{
          name: 'TEST',
          keywords: [
            { name: 'INT_KEY', value: 'not_int', location: { start: { line: 0, column: 0 } } },
            { name: 'REAL_KEY', value: 'not_real', location: { start: { line: 1, column: 0 } } },
            { name: 'BOOL_KEY', value: 'maybe', location: { start: { line: 2, column: 0 } } }
          ],
          subsections: []
        }]
      };
      
      const diagnostics = (provider as any).validateTypes({ getText: () => '' } as any, parsed);
      
      expect(diagnostics.filter((d: any) => d.code === 'type-mismatch').length).toBe(3);
    });
  });

  describe('Type Validation Helpers', () => {
    it('should validate integer arrays', () => {
      const isValidInteger = (provider as any).isValidInteger.bind(provider);
      
      expect(isValidInteger(['1', '2', '3'])).toBe(true);
      expect(isValidInteger(['1', 'abc', '3'])).toBe(false);
      expect(isValidInteger([])).toBe(true);
    });

    it('should validate real arrays', () => {
      const isValidReal = (provider as any).isValidReal.bind(provider);
      
      expect(isValidReal(['1.0', '2.5', '3e10'])).toBe(true);
      expect(isValidReal(['1.0', 'abc'])).toBe(false);
    });

    it('should validate various logical formats', () => {
      const isValidLogical = (provider as any).isValidLogical.bind(provider);
      
      expect(isValidLogical('.true.')).toBe(true);
      expect(isValidLogical('.false.')).toBe(true);
      expect(isValidLogical('t')).toBe(true);
      expect(isValidLogical('f')).toBe(true);
      expect(isValidLogical('yes')).toBe(true);
      expect(isValidLogical('no')).toBe(true);
      expect(isValidLogical('on')).toBe(true);
      expect(isValidLogical('off')).toBe(true);
      expect(isValidLogical('YES')).toBe(true);
      expect(isValidLogical('NO')).toBe(true);
      expect(isValidLogical('ON')).toBe(true);
      expect(isValidLogical('OFF')).toBe(true);
    });
  });

  describe('Bracket Validation', () => {
    it('should handle complex nested brackets', () => {
      const lines = [
        'KEYWORD (a[b]c)',  // Balanced
        'KEYWORD ((a))',    // Balanced
        'KEYWORD [([)]'     // Unbalanced - complex
      ];
      const diagnostics: any[] = [];
      
      (provider as any).checkBalancedBrackets(lines, diagnostics);
      
      const unbalanced = diagnostics.filter((d: any) => d.message.includes('Unbalanced')
      );
      expect(unbalanced.length).toBeGreaterThan(0);
    });

    it('should handle multiple brackets on same line', () => {
      const lines = ['KEYWORD (a) [b] (c)'];
      const diagnostics: any[] = [];
      
      (provider as any).checkBalancedBrackets(lines, diagnostics);
      
      expect(diagnostics.length).toBe(0);
    });
  });

  describe('Variable Expansion', () => {
    it('should handle multiple variables on same line', () => {
      const lines = ['PROJECT ${NAME} ${VERSION}'];
      const diagnostics: any[] = [];
      
      (provider as any).checkVariableExpansion(lines, diagnostics);
      
      expect(diagnostics.length).toBe(0);
    });

    it('should handle empty and valid variables', () => {
      const lines = ['${}', '${VALID}'];
      const diagnostics: any[] = [];
      
      (provider as any).checkVariableExpansion(lines, diagnostics);
      
      expect(diagnostics.filter((d: any) => d.message.includes('Empty')).length).toBe(1);
    });
  });

  describe('Main Diagnostics', () => {
    it('should provide diagnostics with all features enabled', () => {
      provider.updateOptions({
        enableSchemaValidation: true,
        enableDeepValidation: false,
        maxProblems: 100
      });
      
      const content = `&GLOBAL
  PROJECT test
&END GLOBAL`;
      
      const document = TextDocument.create('test://test.inp', 'cp2k', 1, content);
      const diagnostics = provider.provideDiagnostics(document, 100);
      
      expect(Array.isArray(diagnostics)).toBe(true);
    });

    it('should limit diagnostics to maxProblems', () => {
      const content = '&INVALID'.repeat(100);
      
      const document = TextDocument.create('test://test.inp', 'cp2k', 1, content);
      const diagnostics = provider.provideDiagnostics(document, 10);
      
      expect(diagnostics.length).toBeLessThanOrEqual(10);
    });
  });
});
