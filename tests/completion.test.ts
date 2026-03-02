/**
 * Completion Provider Tests
 */

import { CompletionProvider } from '../src/features/completion';
import { KeywordDatabase } from '../src/data/keyword-database';
import { SchemaParser } from '../src/data/schema-parser';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position, CompletionItemKind } from 'vscode-languageserver/node';

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
    getTextInRange: () => content,
    lineCount: lines.length,
    positionAt: (offset: number) => {
      let currentOffset = 0;
      for (let i = 0; i < lines.length; i++) {
        if (currentOffset + lines[i].length >= offset) {
          return { line: i, character: offset - currentOffset };
        }
        currentOffset += lines[i].length + 1; // +1 for newline
      }
      return { line: 0, character: offset };
    },
    offsetAt: (position: any) => {
      let offset = 0;
      for (let i = 0; i < position.line && i < lines.length; i++) {
        offset += lines[i].length + 1; // +1 for newline
      }
      return offset + Math.min(position.character, lines[position.line]?.length || 0);
    },
  } as TextDocument;
};

describe('CompletionProvider', () => {
  let provider: CompletionProvider;
  let keywordDb: KeywordDatabase;

  beforeEach(() => {
    keywordDb = new KeywordDatabase();
    provider = new CompletionProvider(keywordDb);
  });

  describe('Basic functionality', () => {
    test('should create provider instance', () => {
      expect(provider).toBeDefined();
    });

    test('should provide completion items', () => {
      const document = createMockDocument('TES');
      const position = Position.create(0, 3);
      const items = provider.provideCompletionItems(document, position);
      
      expect(Array.isArray(items)).toBe(true);
    });

    test('should respect max items limit', () => {
      const document = createMockDocument('TEST');
      const position = Position.create(0, 4);
      
      const providerLimited = new CompletionProvider(keywordDb, undefined, { maxItems: 5 });
      const items = providerLimited.provideCompletionItems(document, position);
      
      expect(items.length).toBeLessThanOrEqual(5);
    });
  });

  describe('Section completion', () => {
    test('should provide section completions starting with &', () => {
      const document = createMockDocument('&GLO');
      const position = Position.create(0, 4);
      const items = provider.provideCompletionItems(document, position);
      
      expect(items.length).toBeGreaterThan(0);
      
      // Should have GLOBAL section
      const hasGlobal = items.some(item => 
        item.label === 'GLOBAL' && 
        item.kind === CompletionItemKind.Class
      );
      expect(hasGlobal).toBe(true);
    });

    test('should provide all sections when & is present', () => {
      const document = createMockDocument('&');
      const position = Position.create(0, 1);
      const items = provider.provideCompletionItems(document, position);
      
      expect(items.length).toBeGreaterThan(0);
      
      // All should be sections
      const allSections = items.every(item => item.kind === CompletionItemKind.Class);
      expect(allSections).toBe(true);
    });

    test('should provide snippet for sections', () => {
      const document = createMockDocument('&GLOBAL');
      const position = Position.create(0, 7);
      const items = provider.provideCompletionItems(document, position);
      
      const globalItem = items.find(item => item.label === 'GLOBAL');
      expect(globalItem?.insertText).toContain('&END GLOBAL');
    });
  });

  describe('Keyword completion', () => {
    test('should provide keywords at line start', () => {
      const document = createMockDocument('PRO');
      const position = Position.create(0, 3);
      const items = provider.provideCompletionItems(document, position);
      
      expect(items.length).toBeGreaterThan(0);
      
      // Should have PROJECT_NAME
      const hasProjectName = items.some(item => 
        item.label === 'PROJECT_NAME' &&
        item.kind === CompletionItemKind.Property
      );
      expect(hasProjectName).toBe(true);
    });

    test('should provide keywords in section context', () => {
      const document = createMockDocument(`
&GLOBAL
  PRO
&END GLOBAL
      `.trim());
      const position = Position.create(1, 4);
      const items = provider.provideCompletionItems(document, position);
      
      const hasProjectName = items.some(item => 
        item.label === 'PROJECT_NAME'
      );
      expect(hasProjectName).toBe(true);
    });

    test('should provide section-specific keywords', () => {
      const document = createMockDocument(`
&DFT
  MAX_
&END DFT
      `.trim());
      const position = Position.create(1, 4);
      const items = provider.provideCompletionItems(document, position);
      
      // MAX_SCF is in SCF section, not DFT
      // But should still provide some keywords
      expect(items.length).toBeGreaterThan(0);
    });
  });

  describe('Value completion', () => {
    test('should provide enum values for RUN_TYPE', () => {
      const document = createMockDocument('RUN_TYPE ENE');
      const position = Position.create(0, 12);
      const items = provider.provideCompletionItems(document, position);
      
      expect(items.length).toBeGreaterThan(0);
      
      // Should have ENERGY
      const hasEnergy = items.some(item => 
        item.label === 'ENERGY' &&
        item.kind === CompletionItemKind.EnumMember
      );
      expect(hasEnergy).toBe(true);
    });

    test('should provide boolean values for LOGICAL keywords', () => {
      const document = createMockDocument('MAP_CONSISTENT T');
      const position = Position.create(0, 18);
      const items = provider.provideCompletionItems(document, position);
      
      // Should provide TRUE, FALSE, etc.
      const hasTrue = items.some(item => 
        ['TRUE', '.TRUE.'].includes(item.label)
      );
      expect(hasTrue).toBe(true);
    });
  });

  describe('Unit completion', () => {
    test('should provide units after numbers', () => {
      const document = createMockDocument('CUTOFF 400 an');
      const position = Position.create(0, 12);
      const items = provider.provideCompletionItems(document, position);
      
      expect(items.length).toBeGreaterThan(0);
      
      // Should have angstrom
      const hasAngstrom = items.some(item => 
        item.label === 'angstrom' &&
        item.kind === CompletionItemKind.Unit
      );
      expect(hasAngstrom).toBe(true);
    });

    test('should provide various unit types', () => {
      const document = createMockDocument('TIMESTEP 1.0');
      const position = Position.create(0, 12);
      const items = provider.provideCompletionItems(document, position);
      
      // Should have time units
      const hasTimeUnit = items.some(item => 
        ['fs', 'ps', 's'].includes(item.label)
      );
      expect(hasTimeUnit).toBe(true);
    });
  });

  describe('Context awareness', () => {
    test('should detect current section', () => {
      const document = createMockDocument(`
&GLOBAL
  TEST
&END GLOBAL

&FORCE_EVAL
  SUBSYS
&END SUBSYS
&END FORCE_EVAL
      `.trim());
      
      // Position inside GLOBAL section
      const globalPos = Position.create(1, 4);
      const items1 = provider.provideCompletionItems(document, globalPos);
      expect(items1.length).toBeGreaterThan(0);
      
      // Position inside FORCE_EVAL section
      const fePos = Position.create(5, 4);
      const items2 = provider.provideCompletionItems(document, fePos);
      expect(items2.length).toBeGreaterThan(0);
    });
  });

  describe('Documentation', () => {
    test('should resolve completion item', () => {
      const item: any = {
        label: 'GLOBAL',
        kind: CompletionItemKind.Class
      };
      
      const resolved = provider.resolveCompletionItem(item);
      expect(resolved).toBeDefined();
      expect(resolved.documentation).toBeDefined();
    });

    test('should provide documentation for keywords', () => {
      const document = createMockDocument('PROJECT');
      const position = Position.create(0, 7);
      const items = provider.provideCompletionItems(document, position);
      
      const projectName = items.find(item => item.label === 'PROJECT_NAME');
      expect(projectName?.detail).toBeDefined();
    });
  });
});
