/**
 * Additional diagnostic tests to reach 100% coverage
 */

import { DiagnosticsProvider, DiagnosticsOptions } from '../src/features/diagnostics';
import { CP2KParser } from '../src/parser/cp2k-parser';
import { TextDocument } from 'vscode-languageserver-textdocument';

jest.mock('../src/features/deep-validation', () => ({
  DeepValidationProvider: jest.fn().mockImplementation(() => ({
    validateWithCP2K: jest.fn(),
    updateOptions: jest.fn()
  }))
}));

describe('DiagnosticsProvider Coverage', () => {
  let parser: CP2KParser;
  let provider: DiagnosticsProvider;

  beforeEach(() => {
    parser = new CP2KParser();
    provider = new DiagnosticsProvider(parser);
  });

  describe('Type Validation', () => {
    it('should validate INTEGER type correctly', () => {
      const isValidInteger = (provider as any).isValidInteger.bind(provider);
      
      expect(isValidInteger('42')).toBe(true);
      expect(isValidInteger('-10')).toBe(true);
      expect(isValidInteger('+5')).toBe(true);
      expect(isValidInteger('3.14')).toBe(false);
      expect(isValidInteger('abc')).toBe(false);
      expect(isValidInteger(['1', '2', '3'])).toBe(true);
      expect(isValidInteger(['1', 'abc'])).toBe(false);
    });

    it('should validate REAL type correctly', () => {
      const isValidReal = (provider as any).isValidReal.bind(provider);
      
      expect(isValidReal('3.14')).toBe(true);
      expect(isValidReal('-2.5')).toBe(true);
      expect(isValidReal('.5')).toBe(true);
      expect(isValidReal('1e10')).toBe(true);
      expect(isValidReal('1.5e-3')).toBe(true);
      expect(isValidReal('42')).toBe(true);
      expect(isValidReal('abc')).toBe(false);
      expect(isValidReal(['1.0', '2.5'])).toBe(true);
      expect(isValidReal(['1.0', 'abc'])).toBe(false);
    });

    it('should validate LOGICAL type correctly', () => {
      const isValidLogical = (provider as any).isValidLogical.bind(provider);
      
      expect(isValidLogical('TRUE')).toBe(true);
      expect(isValidLogical('FALSE')).toBe(true);
      expect(isValidLogical('.TRUE.')).toBe(true);
      expect(isValidLogical('.FALSE.')).toBe(true);
      expect(isValidLogical('T')).toBe(true);
      expect(isValidLogical('F')).toBe(true);
      expect(isValidLogical('YES')).toBe(true);
      expect(isValidLogical('NO')).toBe(true);
      expect(isValidLogical('ON')).toBe(true);
      expect(isValidLogical('OFF')).toBe(true);
      expect(isValidLogical('maybe')).toBe(false);
    });
  });

  describe('Range Creation', () => {
    it('should create range from location', () => {
      const createRange = (provider as any).createRange.bind(provider);
      
      const location = {
        start: { line: 5, column: 10 },
        end: { line: 5, column: 20 }
      };
      
      const range = createRange(location);
      expect(range.start.line).toBe(5);
      expect(range.start.character).toBe(10);
    });

    it('should handle missing location', () => {
      const createRange = (provider as any).createRange.bind(provider);
      const range = createRange(null);
      expect(range.start.line).toBe(0);
    });
  });

  describe('Variable Expansion Check', () => {
    it('should detect empty variable references', () => {
      const lines = ['PROJECT ${}'];
      const diagnostics: any[] = [];
      
      (provider as any).checkVariableExpansion(lines, diagnostics);
      
      expect(diagnostics.length).toBeGreaterThan(0);
    });

    it('should handle valid variable references', () => {
      const lines = ['PROJECT ${NAME}'];
      const diagnostics: any[] = [];
      
      (provider as any).checkVariableExpansion(lines, diagnostics);
      
      expect(diagnostics.length).toBe(0);
    });
  });

  describe('Balanced Brackets Check', () => {
    it('should detect unbalanced parentheses', () => {
      const lines = ['KEYWORD (value'];
      const diagnostics: any[] = [];
      
      (provider as any).checkBalancedBrackets(lines, diagnostics);
      
      expect(diagnostics.length).toBeGreaterThan(0);
    });

    it('should handle balanced brackets', () => {
      const lines = ['KEYWORD (value)', 'KEYWORD [value]'];
      const diagnostics: any[] = [];
      
      (provider as any).checkBalancedBrackets(lines, diagnostics);
      
      expect(diagnostics.length).toBe(0);
    });
  });

  describe('Required Sections Check', () => {
    it('should add diagnostics for missing required sections', () => {
      const parsed = { sections: [] };
      const diagnostics: any[] = [];
      
      (provider as any).checkRequiredSections(parsed, diagnostics);
      
      expect(diagnostics.length).toBeGreaterThanOrEqual(2);
    });

    it('should not add diagnostics when required sections exist', () => {
      const parsed = {
        sections: [
          { name: 'GLOBAL' },
          { name: 'FORCE_EVAL' }
        ]
      };
      const diagnostics: any[] = [];
      
      (provider as any).checkRequiredSections(parsed, diagnostics);
      
      const missingDiagnostics = diagnostics.filter(d => d.code === 'missing-section');
      expect(missingDiagnostics.length).toBe(0);
    });
  });
});
