import * as parserIndex from '../src/parser/index';
import { CP2KParser, CP2KToken, CP2KSection, CP2KKeyword, ParsedDocument } from '../src/parser/cp2k-parser';
import { TextDocument } from 'vscode-languageserver-textdocument';

describe('Parser Index', () => {
  it('should export CP2KParser', () => {
    expect(parserIndex.CP2KParser).toBe(CP2KParser);
  });

  it('should be able to create CP2KParser instance', () => {
    const parser = new parserIndex.CP2KParser();
    expect(parser).toBeInstanceOf(CP2KParser);
    expect(typeof parser.parse).toBe('function');
    expect(typeof parser.getTokenAtPosition).toBe('function');
    expect(typeof parser.getSectionAtPosition).toBe('function');
  });

  it('should be able to parse document using exported parser', () => {
    const parser = new parserIndex.CP2KParser();
    const doc = TextDocument.create('test://test.inp', 'cp2k', 1, '&GLOBAL\n&END GLOBAL');
    const result = parser.parse(doc);
    
    expect(result.sections).toHaveLength(1);
    expect(result.sections[0].name).toBe('GLOBAL');
  });
});
