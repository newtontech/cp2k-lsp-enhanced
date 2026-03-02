import { TextDocument } from 'vscode-languageserver-textdocument';
import { CompletionItem, CompletionItemKind, Position } from 'vscode-languageserver/node';
import { KeywordDatabase } from '../data/keyword-database';

export class CompletionProvider {
  private keywordDb: KeywordDatabase;

  constructor(keywordDb: KeywordDatabase) {
    this.keywordDb = keywordDb;
  }

  provideCompletionItems(
    document: TextDocument,
    position: Position
  ): CompletionItem[] {
    const line = document.getText({
      start: { line: position.line, character: 0 },
      end: position,
    });
    
    const items: CompletionItem[] = [];
    
    // Check if we're completing a section
    if (line.trim().startsWith('\u0026')) {
      const sectionPrefix = line.trim().substring(1).toUpperCase();
      const sections = this.keywordDb.getSections();
      
      sections.forEach((section, index) => {
        if (section.name.startsWith(sectionPrefix)) {
          items.push({
            label: section.name,
            kind: CompletionItemKind.Class,
            detail: 'CP2K Section',
            documentation: {
              kind: 'markdown',
              value: section.description || `Section: ${section.name}`,
            },
            insertText: section.name + '\n\u0026END ' + section.name + '\n',
            insertTextFormat: 2, // Snippet
            sortText: String(index).padStart(3, '0'),
          });
        }
      });
    } 
    // Check if we're at the start of a line (keyword completion)
    else if (line.trim() === '' || /^\s*[A-Za-z_]*$/.test(line)) {
      // Get current section context
      const sectionContext = this.getSectionContext(document, position);
      
      // Add keywords for current section
      const keywords = this.keywordDb.getKeywordsForSection(sectionContext);
      keywords.forEach((keyword, index) => {
        const completionItem: CompletionItem = {
          label: keyword.name,
          kind: keyword.isSection 
            ? CompletionItemKind.Class 
            : CompletionItemKind.Property,
          detail: keyword.dataType || 'CP2K Keyword',
          documentation: {
            kind: 'markdown',
            value: this.formatDocumentation(keyword),
          },
          sortText: String(index).padStart(3, '0'),
        };
        
        if (keyword.isSection) {
          completionItem.insertText = '\u0026' + keyword.name + '\n\$0\n\u0026END ' + keyword.name;
          completionItem.insertTextFormat = 2;
        } else if (keyword.defaultValue) {
          completionItem.insertText = keyword.name + ' ' + keyword.defaultValue;
        }
        
        items.push(completionItem);
      });
    }
    // Value completion for known keywords
    else {
      const keywordMatch = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*/);
      if (keywordMatch) {
        const keywordName = keywordMatch[1].toUpperCase();
        const keyword = this.keywordDb.getKeyword(keywordName);
        
        if (keyword?.allowedValues) {
          keyword.allowedValues.forEach((value, index) => {
            items.push({
              label: value,
              kind: CompletionItemKind.EnumMember,
              detail: 'Allowed value',
              sortText: String(index).padStart(3, '0'),
            });
          });
        }
      }
    }
    
    return items;
  }

  resolveCompletionItem(item: CompletionItem): CompletionItem {
    // Add additional documentation if needed
    if (item.label.startsWith('\u0026')) {
      const sectionName = item.label.substring(1);
      const section = this.keywordDb.getSection(sectionName);
      if (section) {
        item.documentation = {
          kind: 'markdown',
          value: `## ${section.name}\n\n${section.description || ''}\n\n` +
                 (section.keywords?.length 
                   ? `**Keywords:** ${section.keywords.slice(0, 10).join(', ')}${section.keywords.length > 10 ? '...' : ''}`
                   : ''),
        };
      }
    }
    return item;
  }

  private getSectionContext(document: TextDocument, position: Position): string {
    const text = document.getText();
    const lines = text.substring(0, document.offsetAt(position)).split(/\r?\n/);
    
    const sectionStack: string[] = [];
    
    for (const line of lines) {
      const trimmed = line.trim();
      
      if (trimmed.startsWith('\u0026')) {
        const match = trimmed.match(/^\u0026(\S+)/);
        if (match) {
          const name = match[1].toUpperCase();
          if (name.startsWith('END')) {
            const endName = name.substring(3).trim();
            if (endName && sectionStack.length > 0 && 
                sectionStack[sectionStack.length - 1].toUpperCase() === endName) {
              sectionStack.pop();
            } else {
              sectionStack.pop();
            }
          } else {
            sectionStack.push(name);
          }
        }
      }
    }
    
    return sectionStack.length > 0 ? sectionStack[sectionStack.length - 1] : '';
  }

  private formatDocumentation(keyword: any): string {
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
      doc += `**Allowed values:** ${keyword.allowedValues.map((v: string) => `\`${v}\``).join(', ')}\n\n`;
    }
    
    return doc;
  }
}
