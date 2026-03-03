/**
 * Additional tests for schema-parser to reach 100% coverage
 */

import { SchemaParser, SchemaKeyword, SchemaSection } from '../src/data/schema-parser';
import * as fs from 'fs';
import * as path from 'path';

jest.mock('fs');
jest.mock('child_process', () => ({
  spawn: jest.fn()
}));

describe('SchemaParser Coverage', () => {
  let parser: SchemaParser;

  beforeEach(() => {
    jest.clearAllMocks();
    parser = new SchemaParser('cp2k');
  });

  describe('Data Type Parsing', () => {
    it('should parse all type variations', () => {
      const parseDataType = (parser as any).parseDataType.bind(parser);
      
      expect(parseDataType('STRING_LIST')).toBe('STRING_LIST');
      expect(parseDataType('word')).toBe('STRING_LIST');
      expect(parseDataType('WORDS')).toBe('STRING_LIST');
      expect(parseDataType('REAL_LIST')).toBe('REAL_LIST');
      expect(parseDataType('FLOAT_LIST')).toBe('REAL_LIST');
      expect(parseDataType('INTEGER_LIST')).toBe('INTEGER_LIST');
      expect(parseDataType('INT_LIST')).toBe('INTEGER_LIST');
      expect(parseDataType('INTEGER')).toBe('INTEGER');
      expect(parseDataType('INT')).toBe('INTEGER');
      expect(parseDataType('REAL')).toBe('REAL');
      expect(parseDataType('FLOAT')).toBe('REAL');
      expect(parseDataType('DOUBLE')).toBe('REAL');
      expect(parseDataType('LOGICAL')).toBe('LOGICAL');
      expect(parseDataType('BOOL')).toBe('LOGICAL');
      expect(parseDataType('ENUM')).toBe('ENUM');
      expect(parseDataType('ENUMERATION')).toBe('ENUM');
      expect(parseDataType('UNKNOWN')).toBe('STRING');
      expect(parseDataType('')).toBe('STRING');
    });
  });

  describe('Boolean Parsing', () => {
    it('should parse various boolean values', () => {
      const parseBoolean = (parser as any).parseBoolean.bind(parser);
      
      expect(parseBoolean('true')).toBe(true);
      expect(parseBoolean('TRUE')).toBe(true);
      expect(parseBoolean('1')).toBe(true);
      expect(parseBoolean('yes')).toBe(true);
      expect(parseBoolean('YES')).toBe(true);
      expect(parseBoolean('false')).toBe(false);
      expect(parseBoolean('FALSE')).toBe(false);
      expect(parseBoolean('0')).toBe(false);
      expect(parseBoolean('no')).toBe(false);
      expect(parseBoolean(undefined)).toBeUndefined();
    });
  });

  describe('Integer Parsing', () => {
    it('should parse integer values', () => {
      const parseInt = (parser as any).parseInt.bind(parser);
      
      expect(parseInt('42')).toBe(42);
      expect(parseInt('-10')).toBe(-10);
      expect(parseInt('0')).toBe(0);
      expect(parseInt('invalid')).toBeUndefined();
      expect(parseInt(undefined)).toBeUndefined();
    });
  });

  describe('List Parsing', () => {
    it('should parse comma-separated lists', () => {
      const parseList = (parser as any).parseList.bind(parser);
      
      expect(parseList('a,b,c')).toEqual(['a', 'b', 'c']);
      expect(parseList('a, b, c')).toEqual(['a', 'b', 'c']);
      expect(parseList('single')).toEqual(['single']);
      expect(parseList(undefined)).toBeUndefined();
      expect(parseList('')).toBeUndefined();
    });
  });

  describe('Attribute Extraction', () => {
    it('should extract attributes from XML', () => {
      const extractAttribute = (parser as any).extractAttribute.bind(parser);
      
      expect(extractAttribute('NAME="TEST"', 'NAME')).toBe('TEST');
      expect(extractAttribute("NAME='TEST'", 'NAME')).toBe('TEST');
      expect(extractAttribute('name="test"', 'NAME')).toBe('test');
      expect(extractAttribute('OTHER="value"', 'NAME')).toBeUndefined();
    });
  });

  describe('CDATA Extraction', () => {
    it('should extract CDATA content', () => {
      const extractCDATA = (parser as any).extractCDATA.bind(parser);
      
      const content = '<DESCRIPTION><![CDATA[This is a description]]></DESCRIPTION>';
      expect(extractCDATA(content, 'DESCRIPTION')).toBe('This is a description');
      expect(extractCDATA('<OTHER></OTHER>', 'DESCRIPTION')).toBeUndefined();
    });
  });

  describe('Search Functions', () => {
    it('should return empty array when schema is null', () => {
      expect(parser.searchSections('test')).toEqual([]);
      expect(parser.searchKeywords('test')).toEqual([]);
    });
  });
});
