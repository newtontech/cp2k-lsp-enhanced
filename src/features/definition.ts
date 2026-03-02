import { TextDocument } from 'vscode-languageserver-textdocument';
import { DefinitionParams, Location, Range, Position } from 'vscode-languageserver/node';
import { KeywordDatabase } from '../data/keyword-database';

export class DefinitionProvider {
  private keywordDb: KeywordDatabase;

  constructor(keywordDb: KeywordDatabase) {
    this.keywordDb = keywordDb;
  }

  provideDefinition(document: TextDocument, position: Position): Location | null {
    const word = this.getWordAtPosition(document, position);
    if (!word) {
      return null;
    }
    
    const upperWord = word.toUpperCase();
    
    // Handle section references (go to section definition)
    if (upperWord.startsWith('\u0026')) {
      return this.findSectionDefinition(document, word.substring(1));
    }
    
    // Handle @INCLUDE references
    const line = this.getLineAtPosition(document, position);
    if (line.trim().startsWith('@INCLUDE')) {
      const match = line.match(/@INCLUDE\s+["']?([^"'\s]+)["']?/i);
      if (match) {
        // Return a location indicating this is an external file reference
        return {
          uri: document.uri.replace(/[^/]*$/, '') + match[1],
          range: Range.create(0, 0, 0, 0),
        };
      }
    }
    
    // Handle variable references (${VAR})
    if (upperWord.startsWith('${') && upperWord.endsWith('}')) {
      const varName = upperWord.slice(2, -1);
      return this.findVariableDefinition(document, varName);
    }
    
    // Handle @SET variable definitions
    if (line.trim().toUpperCase().startsWith('@SET')) {
      const match = line.match(/@SET\s+(\S+)\s+/i);
      if (match && match[1].toUpperCase() === upperWord) {
        return {
          uri: document.uri,
          range: this.getWordRange(document, position, word),
        };
      }
    }
    
    return null;
  }

  private findSectionDefinition(document: TextDocument, sectionName: string): Location | null {
    const text = document.getText();
    const lines = text.split(/\r?\n/);
    const searchName = sectionName.toUpperCase();
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      
      if (trimmed.startsWith('\u0026')) {
        const match = trimmed.match(/^\u0026(\S+)/);
        if (match && match[1].toUpperCase() === searchName) {
          const charPos = line.indexOf('\u0026');
          return {
            uri: document.uri,
            range: Range.create(
              i, charPos,
              i, charPos + 1 + match[1].length
            ),
          };
        }
      }
    }
    
    return null;
  }

  private findVariableDefinition(document: TextDocument, varName: string): Location | null {
    const text = document.getText();
    const lines = text.split(/\r?\n/);
    const searchName = varName.toUpperCase();
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      
      if (trimmed.toUpperCase().startsWith('@SET')) {
        const match = trimmed.match(/@SET\s+(\S+)/i);
        if (match && match[1].toUpperCase() === searchName) {
          const charPos = line.indexOf(match[1]);
          return {
            uri: document.uri,
            range: Range.create(i, charPos, i, charPos + match[1].length),
          };
        }
      }
    }
    
    return null;
  }

  private getWordAtPosition(document: TextDocument, position: Position): string | null {
    const line = this.getLineAtPosition(document, position);
    
    // Match different patterns: sections, keywords, variables
    const patterns = [
      /[\u0026][A-Za-z_][A-Za-z0-9_]*/g,  // Sections
      /\$\{[^}]+\}/g,                      // Variables
      /[A-Za-z_][A-Za-z0-9_]*/g,          // Keywords/identifiers
    ];
    
    for (const pattern of patterns) {
      let match;
      while ((match = pattern.exec(line)) !== null) {
        const start = match.index;
        const end = start + match[0].length;
        
        if (start <= position.character && end >= position.character) {
          return match[0];
        }
      }
    }
    
    return null;
  }

  private getLineAtPosition(document: TextDocument, position: Position): string {
    return document.getText({
      start: { line: position.line, character: 0 },
      end: { line: position.line, character: Number.MAX_VALUE },
    });
  }

  private getWordRange(document: TextDocument, position: Position, word: string): Range {
    const line = this.getLineAtPosition(document, position);
    const index = line.indexOf(word);
    if (index >= 0) {
      return Range.create(
        position.line, index,
        position.line, index + word.length
      );
    }
    return Range.create(position.line, position.character, position.line, position.character);
  }
}
