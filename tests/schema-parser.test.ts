/**
 * Schema Parser Tests
 */

import { SchemaParser, SchemaSection, SchemaKeyword } from '../src/data/schema-parser';

describe('SchemaParser', () => {
  let parser: SchemaParser;

  beforeEach(() => {
    parser = new SchemaParser('cp2k', '/tmp/test-cache');
  });

  describe('Basic functionality', () => {
    test('should create parser instance', () => {
      expect(parser).toBeDefined();
    });

    test('should load empty schema when CP2K not available', async () => {
      const schema = await parser.loadSchema();
      expect(schema).toBeDefined();
      expect(schema.sections).toBeInstanceOf(Map);
      expect(schema.keywords).toBeInstanceOf(Map);
    });
  });

  describe('Section queries', () => {
    test('should return undefined for non-existent section', () => {
      const section = parser.getSection('NONEXISTENT');
      expect(section).toBeUndefined();
    });

    test('should search sections', () => {
      const results = parser.searchSections('GLOBAL');
      expect(Array.isArray(results)).toBe(true);
    });
  });

  describe('Keyword queries', () => {
    test('should return undefined for non-existent keyword', () => {
      const keyword = parser.getKeyword('NONEXISTENT');
      expect(keyword).toBeUndefined();
    });

    test('should search keywords', () => {
      const results = parser.searchKeywords('FORCE');
      expect(Array.isArray(results)).toBe(true);
    });
  });
});
