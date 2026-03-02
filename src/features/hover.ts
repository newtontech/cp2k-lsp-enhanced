import { TextDocument } from 'vscode-languageserver-textdocument';
import { Hover, Position } from 'vscode-languageserver/node';
import { KeywordDatabase } from '../data/keyword-database';

export class HoverProvider {
  private keywordDb: KeywordDatabase;

  constructor(keywordDb: KeywordDatabase) {
    this.keywordDb = keywordDb;
  }

  provideHover(document: TextDocument, position: Position): Hover | null {
    const word = this.getWordAtPosition(document, position);
    if (!word) {
      return null;
    }
    
    const upperWord = word.toUpperCase();
    
    // Check if it's a section
    if (upperWord.startsWith('\u0026')) {
      const sectionName = upperWord.substring(1);
      const section = this.keywordDb.getSection(sectionName);
      if (section) {
        return {
          contents: {
            kind: 'markdown',
            value: this.formatSectionDocumentation(section),
          },
        };
      }
    }
    
    // Check if it's a keyword
    const keyword = this.keywordDb.getKeyword(upperWord);
    if (keyword) {
      return {
        contents: {
          kind: 'markdown',
          value: this.formatKeywordDocumentation(keyword),
        },
      };
    }
    
    // Check if it's a special CP2K value
    const valueInfo = this.keywordDb.getValueInfo(upperWord);
    if (valueInfo) {
      return {
        contents: {
          kind: 'markdown',
          value: valueInfo,
        },
      };
    }
    
    return null;
  }

  private getWordAtPosition(document: TextDocument, position: Position): string | null {
    const line = document.getText({
      start: { line: position.line, character: 0 },
      end: { line: position.line, character: Number.MAX_VALUE },
    });
    
    // Match word at position, including & for sections
    const wordRegex = /[&]?[A-Za-z_][A-Za-z0-9_]*/g;
    let match;
    while ((match = wordRegex.exec(line)) !== null) {
      const start = match.index;
      const end = start + match[0].length;
      
      if (start <= position.character && end >= position.character) {
        return match[0];
      }
    }
    
    return null;
  }

  private formatSectionDocumentation(section: any): string {
    let doc = `## \u0026${section.name}\n\n`;
    
    if (section.description) {
      doc += section.description + '\n\n';
    }
    
    if (section.notes) {
      doc += `**Note:** ${section.notes}\n\n`;
    }
    
    if (section.keywords?.length > 0) {
      doc += '### Available Keywords\n\n';
      section.keywords.slice(0, 20).forEach((kw: string) => {
        doc += `- ${kw}\n`;
      });
      if (section.keywords.length > 20) {
        doc += `- ... and ${section.keywords.length - 20} more\n`;
      }
      doc += '\n';
    }
    
    if (section.subsections?.length > 0) {
      doc += '### Subsections\n\n';
      section.subsections.slice(0, 10).forEach((sub: string) => {
        doc += `- \u0026${sub}\n`;
      });
      if (section.subsections.length > 10) {
        doc += `- ... and ${section.subsections.length - 10} more\n`;
      }
    }
    
    return doc;
  }

  private formatKeywordDocumentation(keyword: any): string {
    let doc = `## ${keyword.name}\n\n`;
    
    if (keyword.description) {
      doc += keyword.description + '\n\n';
    }
    
    if (keyword.dataType) {
      doc += `**Type:** \`${keyword.dataType}\`\n\n`;
    }
    
    if (keyword.defaultValue) {
      doc += `**Default:** \`${keyword.defaultValue}\`\n\n`;
    }
    
    if (keyword.allowedValues?.length) {
      doc += `**Allowed values:**\n\n`;
      keyword.allowedValues.forEach((value: string) => {
        doc += `- \`${value}\`\n`;
      });
      doc += '\n';
    }
    
    if (keyword.units) {
      doc += `**Units:** ${keyword.units.join(', ')}\n\n`;
    }
    
    if (keyword.loneValue) {
      doc += '*This keyword expects a lone value*\n\n';
    }
    
    if (keyword.repeats) {
      doc += '*This keyword can be repeated*\n\n';
    }
    
    return doc;
  }
}
