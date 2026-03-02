import { TextDocument } from 'vscode-languageserver-textdocument';
import { TextEdit, Range, FormattingOptions } from 'vscode-languageserver/node';

export class FormattingProvider {
  provideFormatting(
    document: TextDocument,
    options: FormattingOptions
  ): TextEdit[] {
    const text = document.getText();
    const lines = text.split(/\r?\n/);
    const formattedLines: string[] = [];
    
    let indentLevel = 0;
    const indentString = options.insertSpaces 
      ? ' '.repeat(options.tabSize) 
      : '\t';
    
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];
      const trimmed = line.trim();
      
      // Skip empty lines
      if (!trimmed) {
        formattedLines.push('');
        continue;
      }
      
      // Handle preprocessor directives - keep at start of line
      if (trimmed.startsWith('@')) {
        formattedLines.push(trimmed);
        continue;
      }
      
      // Handle comments - preserve position
      if (trimmed.startsWith('#') || trimmed.startsWith('!')) {
        // Align comments to current indent level or keep original
        formattedLines.push(indentString.repeat(indentLevel) + trimmed);
        continue;
      }
      
      // Handle section ends - decrease indent before processing
      if (trimmed.match(/^\u0026END\b/i)) {
        indentLevel = Math.max(0, indentLevel - 1);
      }
      
      // Format the line
      if (trimmed.startsWith('\u0026')) {
        // Section header
        const sectionMatch = trimmed.match(/^\u0026(\S+)(.*)$/);
        if (sectionMatch) {
          const [, name, rest] = sectionMatch;
          const params = rest.trim();
          const formatted = `\u0026${name.toUpperCase()}${params ? ' ' + params : ''}`;
          formattedLines.push(indentString.repeat(indentLevel) + formatted);
        } else {
          formattedLines.push(indentString.repeat(indentLevel) + trimmed);
        }
      } else {
        // Regular keyword line
        const formatted = this.formatKeywordLine(trimmed);
        formattedLines.push(indentString.repeat(indentLevel) + formatted);
      }
      
      // Handle section starts - increase indent after processing
      if (trimmed.match(/^\u0026(?!END\b)\S+/i)) {
        indentLevel++;
      }
    }
    
    // Remove trailing whitespace and ensure single newline at end
    let result = formattedLines.map(l => l.trimEnd()).join('\n');
    result = result.replace(/\n+$/, '\n');
    
    return [
      {
        range: Range.create(0, 0, lines.length, lines[lines.length - 1]?.length || 0),
        newText: result,
      },
    ];
  }

  private formatKeywordLine(line: string): string {
    // Normalize keyword to uppercase
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$/);
    if (!match) {
      return line;
    }
    
    const [, keyword, rest] = match;
    const upperKeyword = keyword.toUpperCase();
    
    // Extract value and inline comment
    let value = rest;
    let comment = '';
    
    const commentIndex = value.search(/[#!]/);
    if (commentIndex !== -1) {
      comment = '  ' + value.substring(commentIndex);
      value = value.substring(0, commentIndex).trim();
    }
    
    // Format based on keyword type
    if (value) {
      // Align values at column 30
      const padding = Math.max(1, 30 - upperKeyword.length);
      return upperKeyword + ' '.repeat(padding) + value + comment;
    }
    
    return upperKeyword + comment;
  }

  provideRangeFormatting(
    document: TextDocument,
    range: Range,
    options: FormattingOptions
  ): TextEdit[] {
    // Extract the range text
    const rangeText = document.getText(range);
    const tempDoc = TextDocument.create(
      'temp://temp',
      'cp2k',
      1,
      rangeText
    );
    
    const edits = this.provideFormatting(tempDoc, options);
    
    // Adjust the range
    if (edits.length > 0) {
      return [{
        range: range,
        newText: edits[0].newText,
      }];
    }
    
    return [];
  }
}
