/**
 * Enhanced Completion Provider
 * 
 * Provides intelligent completion for CP2K input files including:
 * - Schema-based keyword completion
 * - Section name completion with snippet support
 * - Enum value completion
 * - Unit completion for physical quantities
 * - Context-aware suggestions based on current section
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
  fuzzyMatch?: boolean;
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
      fuzzyMatch: false,
      ...options
    };
  }

  /**
   * Update completion options
   */
  updateOptions(options: Partial<CompletionOptions>): void {
    this.options = { ...this.options, ...options };
  }

  /**
   * Set schema parser
   */
  setSchemaParser(schemaParser: SchemaParser): void {
    this.schemaParser = schemaParser;
  }

  /**
   * Provide completion items based on cursor position
   */
  provideCompletionItems(
    document: TextDocument,
    position: Position
  ): CompletionItem[] {
    const line = this.getLineBeforePosition(document, position);
    const trimmed = line.trim();
    
    // Section completion (&SECTION)
    if (this.isSectionContext(trimmed)) {
      return this.provideSectionCompletion(trimmed, position);
    }
    
    // Unit completion (after numbers like "400 ")
    if (this.options.enableUnitCompletion && this.isUnitContext(line)) {
      return this.provideUnitCompletion(line);
    }
    
    // Keyword value completion (KEYWORD <value>)
    if (this.isValueContext(trimmed)) {
      return this.provideValueCompletion(trimmed, position);
    }
    
    // Variable completion (${VAR})
    if (this.isVariableContext(line, position.character)) {
      return this.provideVariableCompletion(document, line);
    }
    
    // Default: keyword completion
    const sectionContext = this.getSectionContext(document, position);
    return this.provideKeywordCompletion(sectionContext, trimmed);
  }

  /**
   * Check if we're in a section completion context
   */
  private isSectionContext(trimmed: string): boolean {
    return trimmed.startsWith('&') || /^&[A-Za-z0-9_-]*$/.test(trimmed);
  }

  /**
   * Check if we're in a unit completion context (after a number)
   */
  private isUnitContext(line: string): boolean {
    // Match patterns like "400 ", "1.0e-5 ", "100.0" at end of line
    return /\d+\.?\d*\s*[A-Za-z]*$/.test(line) && !line.includes('#') && !line.includes('!');
  }

  /**
   * Check if we're in a value completion context
   */
  private isValueContext(trimmed: string): boolean {
    // Matches: KEYWORD VALUE or KEYWORD VALUE # comment
    const keywordValueMatch = trimmed.match(/^[A-Za-z_][A-Za-z0-9_-]*\s+\S*/);
    return keywordValueMatch !== null && !trimmed.startsWith('&');
  }

  /**
   * Check if we're in a variable completion context
   */
  private isVariableContext(line: string, character: number): boolean {
    const beforeCursor = line.substring(0, character);
    return beforeCursor.endsWith('${') || /\$\{[A-Za-z0-9_]*$/.test(beforeCursor);
  }

  /**
   * Get text from start of line to cursor position
   */
  private getLineBeforePosition(document: TextDocument, position: Position): string {
    return document.getText({
      start: { line: position.line, character: 0 },
      end: position,
    });
  }

  /**
   * Provide section name completions
   */
  private provideSectionCompletion(prefix: string, position: Position): CompletionItem[] {
    const items: CompletionItem[] = [];
    const sectionPrefix = prefix.replace(/^&/, '').toUpperCase();
    
    // Get sections from schema or database
    const sections = this.schemaParser 
      ? this.getSchemaSections(sectionPrefix)
      : this.keywordDb.getSections();
    
    sections.forEach((section, index) => {
      const sectionName = typeof section === 'string' ? section : section.name;
      const sectionInfo = typeof section === 'object' ? section : this.keywordDb.getSection(sectionName);
      
      const item: CompletionItem = {
        label: `&${sectionName}`,
        kind: CompletionItemKind.Class,
        detail: 'CP2K Section',
        documentation: this.formatSectionDocumentation(sectionInfo),
        sortText: this.getSortText(index),
        filterText: sectionPrefix ? sectionName : undefined
      };

      // Add snippet with section wrapper
      if (this.options.enableSnippets) {
        item.insertText = `&${sectionName}\n\t$0\n&END ${sectionName}`;
        item.insertTextFormat = InsertTextFormat.Snippet;
      }
      
      items.push(item);
    });
    
    return this.limitItems(items);
  }

  /**
   * Get sections from schema matching prefix
   */
  private getSchemaSections(prefix: string): (SchemaSection | SectionInfo)[] {
    if (!this.schemaParser) {
      return this.keywordDb.getSections();
    }
    
    const allSections = this.getAllSchemaSections();
    
    if (!prefix) {
      return allSections;
    }
    
    const upperPrefix = prefix.toUpperCase();
    return allSections.filter(s => {
      const name = typeof s === 'string' ? s : s.name;
      return name.toUpperCase().startsWith(upperPrefix);
    });
  }

  /**
   * Get all schema sections
   */
  private getAllSchemaSections(): (SchemaSection | SectionInfo)[] {
    if (!this.schemaParser) {
      return this.keywordDb.getSections();
    }
    
    const sections: (SchemaSection | SectionInfo)[] = [];
    const seen = new Set<string>();
    
    // Get from keyword DB first
    this.keywordDb.getSections().forEach(s => {
      const name = typeof s === 'string' ? s : s.name;
      if (!seen.has(name.toUpperCase())) {
        seen.add(name.toUpperCase());
        sections.push(s);
      }
    });
    
    // Add from schema
    const schema = (this.schemaParser as any)['schema'];
    if (schema?.sections) {
      for (const [name, section] of schema.sections) {
        if (!seen.has(name.toUpperCase())) {
          seen.add(name.toUpperCase());
          sections.push(section);
        }
      }
    }
    
    return sections;
  }

  /**
   * Provide keyword completion for current section context
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
        sortText: this.getSortText(index),
      };
      
      // Set insert text based on keyword type
      this.setKeywordInsertText(item, kwInfo);
      
      // Add deprecated indicator
      if (kwInfo.deprecated) {
        item.tags = [1]; // Deprecated tag
        item.detail = '⚠️ Deprecated: ' + (item.detail || '');
      }
      
      items.push(item);
    });
    
    return this.limitItems(items);
  }

  /**
   * Set insert text for keyword completion
   */
  private setKeywordInsertText(item: CompletionItem, kwInfo: KeywordInfo): void {
    if (kwInfo.isSection) {
      // Section keyword
      if (this.options.enableSnippets) {
        item.insertText = `&${kwInfo.name}\n\t$0\n&END ${kwInfo.name}`;
        item.insertTextFormat = InsertTextFormat.Snippet;
      } else {
        item.insertText = `&${kwInfo.name}`;
      }
    } else if (kwInfo.loneValue) {
      // Lone value keyword (e.g., "_" for XC_FUNCTIONAL)
      if (kwInfo.defaultValue) {
        item.insertText = `${kwInfo.name} ${kwInfo.defaultValue}`;
      } else {
        item.insertText = kwInfo.name;
      }
    } else if (kwInfo.defaultValue) {
      // Keyword with default value - use snippet
      if (this.options.enableSnippets) {
        item.insertText = `${kwInfo.name} \${1:${kwInfo.defaultValue}}`;
        item.insertTextFormat = InsertTextFormat.Snippet;
      } else {
        item.insertText = `${kwInfo.name} ${kwInfo.defaultValue}`;
      }
    } else if (kwInfo.allowedValues && kwInfo.allowedValues.length > 0) {
      // Enum keyword with allowed values
      if (this.options.enableSnippets) {
        const options = kwInfo.allowedValues.slice(0, 5).join(',');
        item.insertText = `${kwInfo.name} \${1|${options}|}`;
        item.insertTextFormat = InsertTextFormat.Snippet;
      } else {
        item.insertText = kwInfo.name;
      }
    } else {
      item.insertText = kwInfo.name;
    }
  }

  /**
   * Provide value completion for enum/allowed values
   */
  private provideValueCompletion(line: string, position: Position): CompletionItem[] {
    const items: CompletionItem[] = [];
    
    // Parse keyword name and partial value
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_-]*)\s+(.*)$/);
    if (!match) return items;
    
    const keywordName = match[1].toUpperCase();
    const valuePrefix = match[2].toUpperCase();
    
    // Get keyword info from schema or database
    const keyword = this.schemaParser?.getKeyword(keywordName) || 
                    this.keywordDb.getKeyword(keywordName);
    
    if (!keyword) return items;
    
    const allowedValues = this.isSchemaKeyword(keyword)
      ? (keyword as SchemaKeyword).allowedValues
      : (keyword as KeywordInfo).allowedValues;
    
    // Add allowed enum values
    if (allowedValues) {
      allowedValues.forEach((value, index) => {
        if (!valuePrefix || value.toUpperCase().startsWith(valuePrefix)) {
          items.push({
            label: value,
            kind: CompletionItemKind.EnumMember,
            detail: 'Allowed value',
            documentation: this.getValueDocumentation(value, keywordName),
            sortText: this.getSortText(index),
          });
        }
      });
    }
    
    // For logical keywords, add boolean values
    const dataType = this.isSchemaKeyword(keyword)
      ? (keyword as SchemaKeyword).dataType
      : (keyword as KeywordInfo).dataType;
    
    if (dataType === 'LOGICAL' || dataType === 'BOOLEAN') {
      const booleans = [
        { label: 'TRUE', detail: 'Boolean true' },
        { label: 'FALSE', detail: 'Boolean false' },
        { label: '.TRUE.', detail: 'Fortran-style true' },
        { label: '.FALSE.', detail: 'Fortran-style false' },
        { label: 'T', detail: 'Short true' },
        { label: 'F', detail: 'Short false' },
      ];
      
      booleans.forEach((b, index) => {
        if (!valuePrefix || b.label.toUpperCase().startsWith(valuePrefix)) {
          items.push({
            label: b.label,
            kind: CompletionItemKind.EnumMember,
            detail: b.detail,
            sortText: this.getSortText(allowedValues ? allowedValues.length + index : index),
          });
        }
      });
    }
    
    return this.limitItems(items);
  }

  /**
   * Provide unit completion for physical quantities
   */
  private provideUnitCompletion(line: string): CompletionItem[] {
    const items: CompletionItem[] = [];
    
    // Extract the number and partial unit
    const match = line.match(/(\d+\.?\d*)\s*([A-Za-z/]*)$/);
    if (!match) return items;
    
    const [, number, unitPrefix] = match;
    const upperPrefix = unitPrefix.toUpperCase();
    
    // Comprehensive unit list organized by physical quantity
    const unitCategories = [
      {
        category: 'Length',
        units: [
          { name: 'angstrom', desc: 'Å (10⁻¹⁰ m)' },
          { name: 'bohr', desc: 'Bohr radius (a₀)' },
          { name: 'nm', desc: 'Nanometer' },
          { name: 'pm', desc: 'Picometer' },
          { name: 'm', desc: 'Meter' },
        ]
      },
      {
        category: 'Energy',
        units: [
          { name: 'hartree', desc: 'Hartree (Eₕ)' },
          { name: 'eV', desc: 'Electron volt' },
          { name: 'kcalmol', desc: 'kcal/mol' },
          { name: 'kJmol', desc: 'kJ/mol' },
          { name: 'Ry', desc: 'Rydberg' },
          { name: 'J', desc: 'Joule' },
          { name: 'K', desc: 'Kelvin (thermal energy)' },
        ]
      },
      {
        category: 'Time',
        units: [
          { name: 'fs', desc: 'Femtosecond' },
          { name: 'ps', desc: 'Picosecond' },
          { name: 'ns', desc: 'Nanosecond' },
          { name: 's', desc: 'Second' },
          { name: 'au_time', desc: 'Atomic unit of time' },
        ]
      },
      {
        category: 'Pressure',
        units: [
          { name: 'bar', desc: 'Bar' },
          { name: 'Pa', desc: 'Pascal' },
          { name: 'kPa', desc: 'Kilopascal' },
          { name: 'MPa', desc: 'Megapascal' },
          { name: 'GPa', desc: 'Gigapascal' },
          { name: 'atm', desc: 'Atmosphere' },
        ]
      },
      {
        category: 'Force',
        units: [
          { name: 'hartree/bohr', desc: 'Hartree per Bohr' },
          { name: 'eV/angstrom', desc: 'eV/Å' },
          { name: 'N', desc: 'Newton' },
          { name: 'dyne', desc: 'Dyne' },
        ]
      },
      {
        category: 'Angle',
        units: [
          { name: 'deg', desc: 'Degree' },
          { name: 'rad', desc: 'Radian' },
        ]
      },
      {
        category: 'Mass',
        units: [
          { name: 'amu', desc: 'Atomic mass unit (Dalton)' },
          { name: 'kg', desc: 'Kilogram' },
          { name: 'g', desc: 'Gram' },
          { name: 'me', desc: 'Electron mass' },
        ]
      },
    ];
    
    let index = 0;
    unitCategories.forEach(category => {
      category.units.forEach(unit => {
        if (!upperPrefix || unit.name.toUpperCase().startsWith(upperPrefix)) {
          items.push({
            label: unit.name,
            kind: CompletionItemKind.Unit,
            detail: `${category.category}: ${unit.desc}`,
            documentation: {
              kind: MarkupKind.Markdown,
              value: `**${unit.name}** - ${unit.desc}\n\nCategory: ${category.category}`
            },
            sortText: this.getSortText(index++),
          });
        }
      });
    });
    
    return this.limitItems(items);
  }

  /**
   * Provide variable completion for preprocessor
   */
  private provideVariableCompletion(document: TextDocument, line: string): CompletionItem[] {
    const items: CompletionItem[] = [];
    
    // Find all @SET declarations in the document
    const text = document.getText();
    const setRegex = /@SET\s+(\w+)\s+/gi;
    let match;
    const variables = new Set<string>();
    
    while ((match = setRegex.exec(text)) !== null) {
      variables.add(match[1]);
    }
    
    variables.forEach((variable, index) => {
      items.push({
        label: variable,
        kind: CompletionItemKind.Variable,
        detail: 'Preprocessor variable',
        sortText: this.getSortText(index),
      });
    });
    
    return items;
  }

  /**
   * Resolve completion item (add additional documentation)
   */
  resolveCompletionItem(item: CompletionItem): CompletionItem {
    // Skip if already has documentation
    if (item.documentation) {
      return item;
    }
    
    const label = item.label;
    
    // Handle section label (starts with &)
    if (label.startsWith('&')) {
      const sectionName = label.substring(1);
      const section = this.schemaParser?.getSection(sectionName) || 
                      this.keywordDb.getSection(sectionName);
      if (section) {
        item.documentation = this.formatSectionDocumentation(section);
      }
      return item;
    }
    
    // Try as keyword
    const keyword = this.schemaParser?.getKeyword(label) ||
                    this.keywordDb.getKeyword(label);
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
    if (!this.schemaParser) {
      return this.keywordDb.getKeywordsForSection(sectionName);
    }
    
    const section = this.schemaParser.getSection(sectionName);
    if (!section) {
      return this.keywordDb.getKeywordsForSection(sectionName);
    }
    
    const keywords: (SchemaKeyword | KeywordInfo)[] = [];
    const seen = new Set<string>();
    
    // Add subsections
    for (const [name, subsection] of section.subsections) {
      if (!prefix || name.startsWith(prefix)) {
        if (!seen.has(name)) {
          seen.add(name);
          keywords.push({
            name,
            isSection: true,
            description: subsection.description
          } as any);
        }
      }
    }
    
    // Add keywords
    for (const [name, keyword] of section.keywords) {
      if (!prefix || name.startsWith(prefix)) {
        if (!seen.has(name)) {
          seen.add(name);
          keywords.push(keyword);
        }
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
      deprecated: sk.deprecated,
      required: sk.required
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
    
    let doc = `## &${section.name}\n\n`;
    
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
    
    if (kw.deprecated) {
      doc += `⚠️ **Deprecated**\n\n`;
    }
    
    return {
      kind: MarkupKind.Markdown,
      value: doc
    };
  }

  /**
   * Helper: Get value documentation
   */
  private getValueDocumentation(value: string, keywordName?: string): any {
    // First check keyword database
    const info = this.keywordDb.getValueInfo(value);
    if (info) {
      return {
        kind: MarkupKind.Markdown,
        value: info
      };
    }
    
    // Provide generic documentation for common values
    const commonValues: Record<string, string> = {
      'TRUE': 'Boolean true value',
      'FALSE': 'Boolean false value',
      'T': 'Short form of TRUE',
      'F': 'Short form of FALSE',
      '.TRUE.': 'Fortran-style boolean true',
      '.FALSE.': 'Fortran-style boolean false',
    };
    
    if (commonValues[value.toUpperCase()]) {
      return {
        kind: MarkupKind.Markdown,
        value: commonValues[value.toUpperCase()]
      };
    }
    
    return undefined;
  }

  /**
   * Helper: Get sort text for consistent ordering
   */
  private getSortText(index: number): string {
    return String(index).padStart(4, '0');
  }

  /**
   * Helper: Limit number of items
   */
  private limitItems(items: CompletionItem[]): CompletionItem[] {
    return items.slice(0, this.options.maxItems || 100);
  }
}
