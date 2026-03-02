import { TextDocument } from 'vscode-languageserver-textdocument';
import { Position, Range, Diagnostic, DiagnosticSeverity } from 'vscode-languageserver/node';

export interface CP2KToken {
  type: 'section' | 'keyword' | 'value' | 'comment' | 'string' | 'number' | 'boolean' | 'directive';
  value: string;
  position: Position;
  range: Range;
  sectionLevel?: number;
  parentSection?: string;
}

export interface CP2KSection {
  name: string;
  range: Range;
  level: number;
  parent?: string;
  keywords: CP2KKeyword[];
  subsections: CP2KSection[];
}

export interface CP2KKeyword {
  name: string;
  value: string | string[] | number | boolean;
  range: Range;
  values?: CP2KToken[];
}

export interface ParsedDocument {
  sections: CP2KSection[];
  tokens: CP2KToken[];
  diagnostics: Diagnostic[];
  version?: string;
}

export class CP2KParser {
  private diagnostics: Diagnostic[] = [];
  private tokens: CP2KToken[] = [];
  private sections: CP2KSection[] = [];
  private currentLine = 0;
  private currentChar = 0;

  parse(textDocument: TextDocument): ParsedDocument {
    this.diagnostics = [];
    this.tokens = [];
    this.sections = [];
    
    const text = textDocument.getText();
    const lines = text.split(/\r?\n/);
    
    const sectionStack: CP2KSection[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      this.currentLine = i;
      this.currentChar = 0;
      const line = lines[i];
      this.parseLine(line, i, sectionStack);
    }
    
    // Check for unclosed sections
    if (sectionStack.length > 0) {
      sectionStack.forEach(section => {
        this.diagnostics.push({
          severity: DiagnosticSeverity.Error,
          range: section.range,
          message: `Unclosed section: &${section.name}`,
          source: 'cp2k-lsp',
        });
      });
    }
    
    return {
      sections: this.sections,
      tokens: this.tokens,
      diagnostics: this.diagnostics,
    };
  }

  private parseLine(line: string, lineNum: number, sectionStack: CP2KSection[]): void {
    const trimmed = line.trim();
    
    // Skip empty lines
    if (!trimmed) {
      return;
    }
    
    // Handle comments
    if (trimmed.startsWith('#') || trimmed.startsWith('!')) {
      this.tokens.push({
        type: 'comment',
        value: trimmed,
        position: { line: lineNum, character: 0 },
        range: {
          start: { line: lineNum, character: 0 },
          end: { line: lineNum, character: line.length },
        },
      });
      return;
    }
    
    // Handle preprocessor directives (@IF, @ENDIF, @SET, @INCLUDE)
    if (trimmed.startsWith('@')) {
      this.tokens.push({
        type: 'directive',
        value: trimmed,
        position: { line: lineNum, character: 0 },
        range: {
          start: { line: lineNum, character: 0 },
          end: { line: lineNum, character: line.length },
        },
      });
      return;
    }
    
    // Handle sections (&SECTION, &END SECTION)
    if (trimmed.startsWith('&')) {
      this.parseSection(trimmed, line, lineNum, sectionStack);
      return;
    }
    
    // Handle keywords
    this.parseKeyword(trimmed, line, lineNum, sectionStack);
  }

  private parseSection(trimmed: string, line: string, lineNum: number, sectionStack: CP2KSection[]): void {
    const sectionMatch = trimmed.match(/^\u0026(\S+)(.*)$/);
    if (!sectionMatch) {
      return;
    }
    
    const [, name, rest] = sectionMatch;
    const isEndSection = name.toUpperCase().startsWith('END');
    
    if (isEndSection) {
      const sectionName = name.substring(3).trim() || '';
      
      if (sectionStack.length === 0) {
        this.diagnostics.push({
          severity: DiagnosticSeverity.Error,
          range: {
            start: { line: lineNum, character: line.indexOf('&') },
            end: { line: lineNum, character: line.length },
          },
          message: `Unexpected \u0026END ${sectionName}: no matching opening section`,
          source: 'cp2k-lsp',
        });
        return;
      }
      
      const openedSection = sectionStack.pop();
      if (sectionName && openedSection && openedSection.name.toUpperCase() !== sectionName.toUpperCase()) {
        this.diagnostics.push({
          severity: DiagnosticSeverity.Warning,
          range: {
            start: { line: lineNum, character: line.indexOf('&') },
            end: { line: lineNum, character: line.length },
          },
          message: `Mismatched section: expected \u0026END ${openedSection.name}, found \u0026END ${sectionName}`,
          source: 'cp2k-lsp',
        });
      }
      
      this.tokens.push({
        type: 'section',
        value: name,
        position: { line: lineNum, character: line.indexOf('&') },
        range: {
          start: { line: lineNum, character: line.indexOf('&') },
          end: { line: lineNum, character: line.length },
        },
        sectionLevel: sectionStack.length,
      });
    } else {
      const section: CP2KSection = {
        name: name,
        range: {
          start: { line: lineNum, character: line.indexOf('&') },
          end: { line: lineNum, character: line.length },
        },
        level: sectionStack.length,
        parent: sectionStack.length > 0 ? sectionStack[sectionStack.length - 1].name : undefined,
        keywords: [],
        subsections: [],
      };
      
      if (sectionStack.length > 0) {
        sectionStack[sectionStack.length - 1].subsections.push(section);
      } else {
        this.sections.push(section);
      }
      
      sectionStack.push(section);
      
      this.tokens.push({
        type: 'section',
        value: name,
        position: { line: lineNum, character: line.indexOf('&') },
        range: {
          start: { line: lineNum, character: line.indexOf('&') },
          end: { line: lineNum, character: line.length },
        },
        sectionLevel: sectionStack.length - 1,
        parentSection: section.parent,
      });
      
      // Handle section parameters (e.g., &KIND Ge)
      const params = rest.trim();
      if (params) {
        this.tokens.push({
          type: 'value',
          value: params,
          position: { line: lineNum, character: line.indexOf(params) },
          range: {
            start: { line: lineNum, character: line.indexOf(params) },
            end: { line: lineNum, character: line.length },
          },
        });
      }
    }
  }

  private parseKeyword(trimmed: string, line: string, lineNum: number, sectionStack: CP2KSection[]): void {
    // Match keyword pattern: KEYWORD [value] [# comment]
    const keywordMatch = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$/);
    if (!keywordMatch) {
      return;
    }
    
    const [, name, rest] = keywordMatch;
    
    // Extract value (remove inline comments)
    let value = rest;
    const commentIndex = value.search(/[#!]/);
    if (commentIndex !== -1) {
      value = value.substring(0, commentIndex).trim();
    }
    
    const keywordStart = line.indexOf(name);
    
    const keyword: CP2KKeyword = {
      name: name,
      value: value,
      range: {
        start: { line: lineNum, character: keywordStart },
        end: { line: lineNum, character: keywordStart + name.length },
      },
    };
    
    if (sectionStack.length > 0) {
      sectionStack[sectionStack.length - 1].keywords.push(keyword);
    }
    
    this.tokens.push({
      type: 'keyword',
      value: name,
      position: { line: lineNum, character: keywordStart },
      range: keyword.range,
      parentSection: sectionStack.length > 0 ? sectionStack[sectionStack.length - 1].name : undefined,
    });
    
    if (value) {
      this.parseValue(value, line, lineNum, keywordStart + name.length + 1);
    }
  }

  private parseValue(value: string, line: string, lineNum: number, startChar: number): void {
    // Try to determine the value type
    let type: 'string' | 'number' | 'boolean' = 'string';
    
    const upperValue = value.toUpperCase();
    if (upperValue === 'TRUE' || upperValue === 'FALSE' || upperValue === '.TRUE.' || upperValue === '.FALSE.' ||
        upperValue === 'T' || upperValue === 'F' || upperValue === 'YES' || upperValue === 'NO' ||
        upperValue === 'ON' || upperValue === 'OFF') {
      type = 'boolean';
    } else if (/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(value.trim())) {
      type = 'number';
    }
    
    this.tokens.push({
      type: type,
      value: value,
      position: { line: lineNum, character: startChar },
      range: {
        start: { line: lineNum, character: startChar },
        end: { line: lineNum, character: startChar + value.length },
      },
    });
  }

  getTokenAtPosition(position: Position): CP2KToken | undefined {
    return this.tokens.find(token => 
      token.position.line === position.line &&
      token.range.start.character <= position.character &&
      token.range.end.character >= position.character
    );
  }

  getSectionAtPosition(position: Position): CP2KSection | undefined {
    return this.sections.find(section => 
      section.range.start.line <= position.line &&
      this.getSectionEndLine(section) >= position.line
    );
  }

  private getSectionEndLine(section: CP2KSection): number {
    if (section.subsections.length === 0 && section.keywords.length === 0) {
      return section.range.end.line;
    }
    
    let maxLine = section.range.end.line;
    
    section.subsections.forEach(sub => {
      maxLine = Math.max(maxLine, this.getSectionEndLine(sub));
    });
    
    section.keywords.forEach(kw => {
      maxLine = Math.max(maxLine, kw.range.end.line);
    });
    
    return maxLine;
  }
}
