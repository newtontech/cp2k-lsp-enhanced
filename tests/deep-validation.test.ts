/**
 * Deep Validation Provider Tests
 */

import { DeepValidationProvider, CP2KValidationOptions } from '../src/features/deep-validation';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Diagnostic, DiagnosticSeverity } from 'vscode-languageserver/node';

// Mock TextDocument
const createMockDocument = (content: string): TextDocument => {
  return {
    uri: 'file:///test/test.inp',
    languageId: 'cp2k',
    version: 1,
    getText: () => content,
    lineCount: content.split('\n').length,
    positionAt: (offset: number) => ({ line: 0, character: offset }),
    offsetAt: (position) => position.character,
  } as TextDocument;
};

describe('DeepValidationProvider', () => {
  let provider: DeepValidationProvider;

  beforeEach(() => {
    provider = new DeepValidationProvider({
      cp2kPath: 'cp2k',
      timeout: 5000,
      enabled: true
    });
  });

  afterEach(() => {
    provider.dispose();
  });

  describe('Basic functionality', () => {
    test('should create provider instance', () => {
      expect(provider).toBeDefined();
    });

    test('should check CP2K availability', async () => {
      const available = await provider.isCP2KAvailable();
      expect(typeof available).toBe('boolean');
    });
  });

  describe('Configuration', () => {
    test('should update options', () => {
      provider.updateOptions({
        cp2kPath: '/custom/path/cp2k',
        timeout: 10000,
        enabled: false
      });

      expect(provider['cp2kPath']).toBe('/custom/path/cp2k');
      expect(provider['timeout']).toBe(10000);
      expect(provider['enabled']).toBe(false);
    });

    test('should find CP2K executable', () => {
      const path = provider['findCP2KExecutable']();
      expect(typeof path).toBe('string');
      expect(path.length).toBeGreaterThan(0);
    });
  });

  describe('Validation', () => {
    test('should validate document with CP2K', async () => {
      const document = createMockDocument(`
&GLOBAL
  PROJECT_NAME TEST
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  SUBSYS
    &KIND O
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q6
    &END KIND
  END SUBSYS
&END FORCE_EVAL
      `.trim());

      const diagnostics = await provider.validateWithCP2K(document);
      expect(Array.isArray(diagnostics)).toBe(true);
    });

    test('should handle disabled validation', async () => {
      provider.updateOptions({ enabled: false });
      const document = createMockDocument('TEST');
      const diagnostics = await provider.validateWithCP2K(document);
      expect(diagnostics.length).toBe(0);
    });

    test('should parse CP2K output', () => {
      const document = createMockDocument('TEST');
      const output = `
CP2K| ERROR! Invalid keyword in line 5 of file test.inp
WARNING! Missing required section in line 10
      `.trim();

      const diagnostics = provider['parseCP2KOutput'](output, document);
      expect(diagnostics.length).toBeGreaterThan(0);
    });
  });

  describe('Cancellation', () => {
    test('should cancel validation', () => {
      const uri = 'file:///test/test.inp';
      provider.cancelValidation(uri);
      // Should not throw
    });
  });
});
