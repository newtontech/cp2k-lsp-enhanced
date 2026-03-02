/**
 * Enhanced Completion Provider
 * 
 * Provides intelligent completion for CP2K input files including:
 * - Schema-based keyword completion
 * - Enum value completion
 * - Unit completion
 * - Context-aware suggestions
 */

import { TextDocument } from 'vscode-languageserver-textdocument';
import { 
  CompletionItem, 
  CompletionItemKind, 
  Position,
  InsertTextFormat,
  MarkupKind
} from 'vscode-languageserver/node';
import { KeywordDatabase, KeywordInfo, SectionInfo } from '../data/keyword-database';
import { SchemaParser, SchemaKeyword, SchemaSection } from '../data/schema-parser';

export interface CompletionOptions {
  enableSnippets?: boolean;
  enableUnitCompletion?: boolean;
  maxItems?: number;
}

export class CompletionProvider {
  private keywordDb: KeywordDatabase;
  private schemaParser: SchemaParser | null = null;
  private options: CompletionOptions;

  constructor(
    keywordDb: KeywordDatabase,
    schemaParser?: SchemaParser,
    options: CompletionOptions = {}
  ) {
    this.keywordDb = keywordDb;
    this.schemaParser = schemaParser || null;
    this.options = {
      enableSnippets: true,
      enableUnitCompletion: true,
      maxItems: 100,
      ...options
    };
  }

  /**
   * Provide completion items
   */
  provideCompletionItems(
    document: TextDocument,
    position: Position
  ): CompletionItem[] {
    const line = document.getText({
      start: { line: position.line, character: 0 },
      end: position,
    });
    
    const items: CompletionItem[] = [];
    const lineBeforeCursor = line.substring(0, position.character);
    const trimmed = line.trim();
    
    // Section completion (&SECTION)
    if (trimmed.startsWith('&') || /^&[A-Za-z]*$/.test(trimmed)) {
      return this.provideSectionCompletion(trimmed);
    }
    
    // Unit completion (after numbers) - check before keyword value completion
    if (this.options.enableUnitCompletion) {
      const unitMatch = lineBeforeCursor.match(/\d+\s*([A-Za-z]*)$/);
      if (unitMatch) {
        return this.provideUnitCompletion(unitMatch[1]);
      }
    }
    
    // Keyword value completion (KEYWORD <value>)
    const keywordMatch = lineBeforeCursor.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$/);
    if (keywordMatch) {
      const keywordName = keywordMatch[1].toUpperCase();
      const valuePrefix = keywordMatch[2];
      return this.provideValueCompletion(keywordName, valuePrefix);
    }
    
    // Default: keyword completion
    const sectionContext = this.getSectionContext(document, position);
    return this.provideKeywordCompletion(sectionContext, trimmed);
  }

  /**
   * Provide section completion
   */
  private provideSectionCompletion(prefix: string): CompletionItem[] {
    const items: CompletionItem[] = [];
    const sectionPrefix = prefix.replace(/^&/, '').toUpperCase();
    
    // Get sections from schema or database
    const sections = this.schemaParser 
      ? this.getSchemaSections(sectionPrefix)
      : this.keywordDb.getSections();
    
    sections.forEach((section, index) => {
      const sectionName = typeof section === 'string' ? section : section.name;
      const sectionInfo = typeof section === 'object' ? section : this.keywordDb.getSection(sectionName);
      
      items.push({
        label: sectionName,
        kind: CompletionItemKind.Class,
        detail: 'CP2K Section',
        documentation: this.formatSectionDocumentation(sectionInfo),
        insertText: this.options.enableSnippets 
          ? `${sectionName}\n$0\n&END ${sectionName}`
          : sectionName,
        insertTextFormat: this.options.enableSnippets 
          ? InsertTextFormat.Snippet 
          : InsertTextFormat.PlainText,
        sortText: String(index).padStart(3, '0'),
        filterText: sectionPrefix ? sectionName : undefined
      });
    });
    
    return items.slice(0, this.options.maxItems);
  }

  /**
   * Get sections from schema matching prefix
   */
  private getSchemaSections(prefix: string): (SchemaSection | SectionInfo)[] {
    if (!this.schemaParser) {
      return this.keywordDb.getSections();
    }
    
    const allSections = Array.from(this.schemaParser['schema']?.sections?.values() || []);
    return allSections.filter(s => s.name.startsWith(prefix));
  }

  /**
   * Provide keyword completion
   */
  private provideKeywordCompletion(sectionContext: string, prefix: string): CompletionItem[] {
    const items: CompletionItem[] = [];
    const upperPrefix = prefix.toUpperCase().trim();
    
    // Get keywords from schema or database
    const keywords = this.schemaParser
      ? this.getSchemaKeywords(sectionContext, upperPrefix)
      : this.keywordDb.getKeywordsForSection(sectionContext);
    
    keywords.forEach((keyword, index) => {
      const kwInfo = this.isSchemaKeyword(keyword) 
        ? this.convertSchemaKeyword(keyword as SchemaKeyword)
        : keyword as KeywordInfo;
      
      const item: CompletionItem = {
        label: kwInfo.name,
        kind: kwInfo.isSection 
          ? CompletionItemKind.Class 
          : CompletionItemKind.Property,
        detail: this.getKeywordDetail(kwInfo),
        documentation: this.formatKeywordDocumentation(kwInfo),
        sortText: String(index).padStart(3, '0'),
      };
      
      // Add insert text based on type
      if (kwInfo.isSection) {
        item.insertText = this.options.enableSnippets
          ? `&${kwInfo.name}\n$0\n&END ${kwInfo.name}`
          : `&${kwInfo.name}`;
        item.insertTextFormat = this.options.enableSnippets
          ? InsertTextFormat.Snippet
          : InsertTextFormat.PlainText;
      } else if (kwInfo.loneValue) {
        item.insertText = kwInfo.defaultValue 
          ? `${kwInfo.name} ${kwInfo.defaultValue}`
          : kwInfo.name;
      } else if (kwInfo.defaultValue) {
        item.insertText = `${kwInfo.name} \${1:${kwInfo.defaultValue}}`;
        item.insertTextFormat = InsertTextFormat.Snippet;
      } else {
        item.insertText = kwInfo.name;
      }
      
      // Add deprecated indicator
      if (kwInfo.deprecated) {
        item.tags = [1]; // Deprecated tag
        item.detail = '⚠️ Deprecated: ' + (item.detail || '');
      }
      
      items.push(item);
    });
    
    return items.slice(0, this.options.maxItems);
  }

  /**
   * Provide value completion for enum/allowed values
   */
  private provideValueCompletion(keywordName: string, valuePrefix: string): CompletionItem[] {
    const items: CompletionItem[] = [];
    
    // Get keyword info from schema or database
    const keyword = this.schemaParser?.getKeyword(keywordName) || 
                    this.keywordDb.getKeyword(keywordName);
    
    if (!keyword) return items;
    
    const allowedValues = this.isSchemaKeyword(keyword)
      ? (keyword as SchemaKeyword).allowedValues
      : (keyword as KeywordInfo).allowedValues;
    
    if (allowedValues) {
      allowedValues.forEach((value, index) => {
        items.push({
          label: value,
          kind: CompletionItemKind.EnumMember,
          detail: 'Allowed value',
          documentation: this.getValueDocumentation(value),
          sortText: String(index).padStart(3, '0'),
        });
      });
    }
    
    // For logical keywords
    const dataType = this.isSchemaKeyword(keyword)
      ? (keyword as SchemaKeyword).dataType
      : (keyword as KeywordInfo).dataType;
    
    if (dataType === 'LOGICAL') {
      ['TRUE', 'FALSE', '.TRUE.', '.FALSE.'].forEach((value, index) => {
        items.push({
          label: value,
          kind: CompletionItemKind.EnumMember,
          detail: 'Boolean value',
          sortText: String(index).padStart(3, '0'),
        });
      });
    }
    
    return items;
  }

  /**
   * Provide unit completion
   */
  private provideUnitCompletion(prefix: string): CompletionItem[] {
    const items: CompletionItem[] = [];
    
    const units = [
      // Length
      { name: 'angstrom', desc: 'Angstrom (Å)' },
      { name: 'bohr', desc: 'Bohr radius (atomic units)' },
      { name: 'nm', desc: 'Nanometer' },
      { name: 'pm', desc: 'Picometer' },
      { name: 'm', desc: 'Meter' },
      
      // Energy
      { name: 'hartree', desc: 'Hartree (atomic units)' },
      { name: 'eV', desc: 'Electron volt' },
      { name: 'kcalmol', desc: 'Kilocalorie per mole' },
      { name: 'kJmol', desc: 'Kilojoule per mole' },
      { name: 'Ry', desc: 'Rydberg' },
      { name: 'J', desc: 'Joule' },
      
      // Time
      { name: 'fs', desc: 'Femtosecond' },
      { name: 'ps', desc: 'Picosecond' },
      { name: 's', desc: 'Second' },
      
      // Temperature
      { name: 'K', desc: 'Kelvin' },
      
      // Pressure
      { name: 'bar', desc: 'Bar' },
      { name: 'atm', desc: 'Atmosphere' },
      { name: 'Pa', desc: 'Pascal' },
      { name: 'GPa', desc: 'Gigapascal' },
      
      // Mass
      { name: 'amu', desc: 'Atomic mass unit' },
      
      // Angle
      { name: 'deg', desc: 'Degree' },
      { name: 'rad', desc: 'Radian' },
      
      // Force
      { name: 'hartree/bohr', desc: 'Hartree per Bohr' },
    ];
    
    const upperPrefix = prefix.toUpperCase();
    
    units.forEach((unit, index) => {
      if (!upperPrefix || unit.name.toUpperCase().startsWith(upperPrefix)) {
        items.push({
          label: unit.name,
          kind: CompletionItemKind.Unit,
          detail: unit.desc,
          sortText: String(index).padStart(3, '0'),
        });
      }
    });
    
    return items;
  }

  /**
   * Resolve completion item
   */
  resolveCompletionItem(item: CompletionItem): CompletionItem {
    // Add additional documentation if needed
    // First try as section (with or without &)
    let sectionName = item.label.toUpperCase();
    if (item.label.startsWith('&')) {
      sectionName = item.label.substring(1).toUpperCase();
    }
    
    // Check if it's a section (by kind or by lookup)
    const isSection = item.kind === CompletionItemKind.Class || 
                      item.kind === CompletionItemKind.Module ||
                      this.keywordDb.getSection(sectionName);
    
    if (isSection) {
      const section = this.schemaParser?.getSection(sectionName) || 
                      this.keywordDb.getSection(sectionName);
      if (section) {
        item.documentation = this.formatSectionDocumentation(section);
        return item;
      }
    }
    
    // Try as keyword
    const keyword = this.schemaParser?.getKeyword(item.label) ||
                    this.keywordDb.getKeyword(item.label);
    if (keyword) {
      const kwInfo = this.isSchemaKeyword(keyword)
        ? this.convertSchemaKeyword(keyword as SchemaKeyword)
        : keyword as KeywordInfo;
      item.documentation = this.formatKeywordDocumentation(kwInfo);
    }
    
    return item;
  }

  /**
   * Get section context from document
   */
  private getSectionContext(document: TextDocument, position: Position): string {
    const text = document.getText();
    const lines = text.substring(0, document.offsetAt(position)).split(/\r?\n/);
    
    const sectionStack: string[] = [];
    
    for (const line of lines) {
      const trimmed = line.trim();
      
      if (trimmed.startsWith('&')) {
        const match = trimmed.match(/^&(\S+)/);
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

  /**
   * Get keywords from schema for section
   */
  private getSchemaKeywords(sectionName: string, prefix: string): (SchemaKeyword | KeywordInfo)[] {
    if (!this.schemaParser || !this.schemaParser['schema']) {
      return this.keywordDb.getKeywordsForSection(sectionName);
    }
    
    const section = this.schemaParser.getSection(sectionName);
    if (!section) {
      return this.keywordDb.getKeywordsForSection(sectionName);
    }
    
    const keywords: (SchemaKeyword | KeywordInfo)[] = [];
    
    // Add subsections
    for (const [name, subsection] of section.subsections) {
      if (!prefix || name.startsWith(prefix)) {
        keywords.push({
          name,
          isSection: true,
          description: subsection.description
        } as any);
      }
    }
    
    // Add keywords
    for (const [name, keyword] of section.keywords) {
      if (!prefix || name.startsWith(prefix)) {
        keywords.push(keyword);
      }
    }
    
    return keywords;
  }

  /**
   * Helper: Check if object is SchemaKeyword
   */
  private isSchemaKeyword(obj: any): obj is SchemaKeyword {
    return obj && 'dataType' in obj;
  }

  /**
   * Helper: Convert SchemaKeyword to KeywordInfo
   */
  private convertSchemaKeyword(sk: SchemaKeyword): KeywordInfo {
    return {
      name: sk.name,
      description: sk.description,
      dataType: sk.dataType,
      defaultValue: sk.defaultValue,
      allowedValues: sk.allowedValues,
      units: sk.units,
      loneValue: sk.loneValue,
      repeats: sk.repeats,
      isSection: false,
      deprecated: sk.deprecated
    };
  }

  /**
   * Helper: Get keyword detail text
   */
  private getKeywordDetail(kw: KeywordInfo): string {
    let detail = kw.dataType || 'CP2K Keyword';
    
    if (kw.defaultValue) {
      detail += ` (default: ${kw.defaultValue})`;
    }
    
    if (kw.required) {
      detail = '⚠️ Required: ' + detail;
    }
    
    return detail;
  }

  /**
   * Helper: Format section documentation
   */
  private formatSectionDocumentation(section: any): any {
    if (!section) return undefined;
    
    let doc = `## ${section.name}\n\n`;
    
    if (section.description) {
      doc += section.description + '\n\n';
    }
    
    const keywords = section.keywords 
      ? (section.keywords instanceof Map 
          ? Array.from(section.keywords.keys())
          : section.keywords)
      : [];
    
    const subsections = section.subsections
      ? (section.subsections instanceof Map
          ? Array.from(section.subsections.keys())
          : section.subsections)
      : [];
    
    if (keywords.length > 0) {
      doc += `**Keywords:** ${keywords.slice(0, 10).join(', ')}${keywords.length > 10 ? '...' : ''}\n\n`;
    }
    
    if (subsections.length > 0) {
      doc += `**Subsections:** ${subsections.slice(0, 10).join(', ')}${subsections.length > 10 ? '...' : ''}\n\n`;
    }
    
    return {
      kind: MarkupKind.Markdown,
      value: doc
    };
  }

  /**
   * Helper: Format keyword documentation
   */
  private formatKeywordDocumentation(kw: KeywordInfo): any {
    let doc = `## ${kw.name}\n\n`;
    
    if (kw.description) {
      doc += kw.description + '\n\n';
    }
    
    if (kw.dataType) {
      doc += `**Type:** \`${kw.dataType}\`\n\n`;
    }
    
    if (kw.defaultValue) {
      doc += `**Default:** \`${kw.defaultValue}\`\n\n`;
    }
    
    if (kw.allowedValues?.length) {
      doc += `**Allowed values:** ${kw.allowedValues.map((v: string) => `\`${v}\``).join(', ')}\n\n`;
    }
    
    if (kw.units?.length) {
      doc += `**Units:** ${kw.units.map((u: string) => `\`${u}\``).join(', ')}\n\n`;
    }
    
    if (kw.repeats) {
      doc += `*Can be repeated*\n\n`;
    }
    
    return {
      kind: MarkupKind.Markdown,
      value: doc
    };
  }

  /**
   * Helper: Get value documentation
   */
  private getValueDocumentation(value: string): any {
    const info = this.keywordDb.getValueInfo(value);
    if (info) {
      return {
        kind: MarkupKind.Markdown,
        value: info
      };
    }
    return undefined;
  }
}
