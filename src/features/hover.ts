/**
 * Enhanced Hover Provider
 * 
 * Provides comprehensive hover information for CP2K input files:
 * - Section documentation with keywords and subsections
 * - Keyword documentation with types, defaults, and allowed values
 * - Enum value descriptions
 * - Unit information
 * - Context-aware hints
 */

import { TextDocument } from 'vscode-languageserver-textdocument';
import { Hover, Position, MarkupKind } from 'vscode-languageserver/node';
import { KeywordDatabase } from '../data/keyword-database';
import { SchemaParser } from '../data/schema-parser';

export interface HoverOptions {
  showDefaultValues?: boolean;
  showAllowedValues?: boolean;
  showTypeInfo?: boolean;
  maxEnumValues?: number;
}

export class HoverProvider {
  private keywordDb: KeywordDatabase;
  private schemaParser: SchemaParser | null = null;
  private options: HoverOptions;

  constructor(
    keywordDb: KeywordDatabase,
    schemaParser?: SchemaParser,
    options: HoverOptions = {}
  ) {
    this.keywordDb = keywordDb;
    this.schemaParser = schemaParser || null;
    this.options = {
      showDefaultValues: true,
      showAllowedValues: true,
      showTypeInfo: true,
      maxEnumValues: 20,
      ...options
    };
  }

  /**
   * Update hover options
   */
  updateOptions(options: Partial<HoverOptions>): void {
    this.options = { ...this.options, ...options };
  }

  /**
   * Set schema parser
   */
  setSchemaParser(schemaParser: SchemaParser): void {
    this.schemaParser = schemaParser;
  }

  /**
   * Provide hover information at position
   */
  provideHover(document: TextDocument, position: Position): Hover | null {
    const word = this.getWordAtPosition(document, position);
    if (!word) {
      return null;
    }
    
    const upperWord = word.toUpperCase();
    const line = this.getLineAtPosition(document, position);
    const lineContext = this.analyzeLineContext(line, position.character);
    
    // Check for section hover (&SECTION)
    if (upperWord.startsWith('&')) {
      return this.provideSectionHover(word.substring(1));
    }
    
    // Check for keyword value hover
    if (lineContext.inValuePosition) {
      const keywordHover = this.provideKeywordValueHover(lineContext.keywordName, word);
      if (keywordHover) {
        return keywordHover;
      }
    }
    
    // Check for keyword hover
    const keywordHover = this.provideKeywordHover(upperWord, lineContext.currentSection);
    if (keywordHover) {
      return keywordHover;
    }
    
    // Check for special CP2K values
    const valueHover = this.provideValueHover(upperWord);
    if (valueHover) {
      return valueHover;
    }
    
    // Check for unit hover
    const unitHover = this.provideUnitHover(word);
    if (unitHover) {
      return unitHover;
    }
    
    return null;
  }

  /**
   * Analyze the current line context
   */
  private analyzeLineContext(line: string, character: number): {
    inValuePosition: boolean;
    keywordName?: string;
    currentSection?: string;
  } {
    const beforeCursor = line.substring(0, character);
    
    // Check if we're after a keyword
    const keywordMatch = beforeCursor.match(/^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s+(\S*)$/);
    if (keywordMatch) {
      return {
        inValuePosition: true,
        keywordName: keywordMatch[2].toUpperCase()
      };
    }
    
    return { inValuePosition: false };
  }

  /**
   * Provide hover for a section
   */
  private provideSectionHover(sectionName: string): Hover | null {
    // Try schema first, then keyword DB
    const schemaSection = this.schemaParser?.getSection(sectionName);
    const dbSection = this.keywordDb.getSection(sectionName);
    
    if (!schemaSection && !dbSection) {
      return null;
    }
    
    const section = schemaSection || dbSection;
    const name = section?.name || sectionName;
    
    let doc = `## &${name}\n\n`;
    
    // Description
    if (section?.description) {
      doc += `${section.description}\n\n`;
    }
    
    // Schema-specific info
    if (schemaSection) {
      // Required/repeats flags
      const flags: string[] = [];
      if (schemaSection.required) flags.push('Required');
      if (schemaSection.repeats) flags.push('Can be repeated');
      if (schemaSection.deprecated) flags.push('⚠️ Deprecated');
      
      if (flags.length > 0) {
        doc += `**Flags:** ${flags.join(', ')}\n\n`;
      }
    }
    
    // Keywords
    let keywords: string[] = [];
    if (schemaSection?.keywords) {
      keywords = Array.from(schemaSection.keywords.keys());
    } else if (dbSection?.keywords) {
      keywords = dbSection.keywords;
    }
    
    if (keywords.length > 0) {
      doc += `**Keywords (${keywords.length}):**\n\n`;
      const displayKeywords = keywords.slice(0, 15);
      displayKeywords.forEach(kw => {
        const kwInfo = this.schemaParser?.getKeyword(kw) || this.keywordDb.getKeyword(kw);
        const deprecated = kwInfo?.deprecated ? ' ⚠️' : '';
        const required = kwInfo?.required ? ' *' : '';
        doc += `- \`${kw}\`${deprecated}${required}\n`;
      });
      if (keywords.length > 15) {
        doc += `- ... and ${keywords.length - 15} more\n`;
      }
      doc += '\n';
    }
    
    // Subsections
    let subsections: string[] = [];
    if (schemaSection?.subsections) {
      subsections = Array.from(schemaSection.subsections.keys());
    } else if (dbSection?.subsections) {
      subsections = dbSection.subsections;
    }
    
    if (subsections.length > 0) {
      doc += `**Subsections (${subsections.length}):**\n\n`;
      const displaySubsections = subsections.slice(0, 10);
      displaySubsections.forEach(sub => {
        doc += `- \`&${sub}\`\n`;
      });
      if (subsections.length > 10) {
        doc += `- ... and ${subsections.length - 10} more\n`;
      }
      doc += '\n';
    }
    
    return {
      contents: {
        kind: MarkupKind.Markdown,
        value: doc
      }
    };
  }

  /**
   * Provide hover for a keyword
   */
  private provideKeywordHover(keywordName: string, currentSection?: string): Hover | null {
    // Try to find keyword in schema first
    let keyword = this.schemaParser?.getKeyword(keywordName);
    
    // Fall back to keyword DB
    if (!keyword) {
      keyword = this.keywordDb.getKeyword(keywordName);
    }
    
    if (!keyword) {
      return null;
    }
    
    let doc = `## ${keyword.name}\n\n`;
    
    // Description
    if (keyword.description) {
      doc += `${keyword.description}\n\n`;
    }
    
    // Type information
    if (this.options.showTypeInfo && keyword.dataType) {
      doc += `**Type:** \`${keyword.dataType}\`\n\n`;
    }
    
    // Default value
    if (this.options.showDefaultValues && keyword.defaultValue) {
      doc += `**Default:** \`${keyword.defaultValue}\`\n\n`;
    }
    
    // Allowed values (enums)
    if (this.options.showAllowedValues && keyword.allowedValues?.length) {
      doc += `**Allowed Values:**\n\n`;
      const maxValues = this.options.maxEnumValues || 20;
      const displayValues = keyword.allowedValues.slice(0, maxValues);
      
      displayValues.forEach(value => {
        const valueInfo = this.keywordDb.getValueInfo(value);
        if (valueInfo) {
          doc += `- \`${value}\`: ${valueInfo}\n`;
        } else {
          doc += `- \`${value}\`\n`;
        }
      });
      
      if (keyword.allowedValues.length > maxValues) {
        doc += `- ... and ${keyword.allowedValues.length - maxValues} more\n`;
      }
      doc += '\n';
    }
    
    // Units
    if (keyword.units?.length) {
      doc += `**Units:** ${keyword.units.map((u: string) => `\`${u}\``).join(', ')}\n\n`;
    }
    
    // Flags
    const flags: string[] = [];
    if (keyword.required) flags.push('⚠️ **Required**');
    if (keyword.repeats) flags.push('*Can be repeated*');
    if (keyword.loneValue) flags.push('*Lone value keyword*');
    if (keyword.deprecated) flags.push('⚠️ **Deprecated**');
    
    if (flags.length > 0) {
      doc += flags.join('  \n') + '\n\n';
    }
    
    return {
      contents: {
        kind: MarkupKind.Markdown,
        value: doc
      }
    };
  }

  /**
   * Provide hover for a keyword value (enum value)
   */
  private provideKeywordValueHover(keywordName: string | undefined, value: string): Hover | null {
    if (!keywordName) {
      return null;
    }
    
    // Find the keyword
    const keyword = this.schemaParser?.getKeyword(keywordName) ||
                    this.keywordDb.getKeyword(keywordName);
    
    if (!keyword || !keyword.allowedValues) {
      return null;
    }
    
    // Check if value is in allowed values
    const upperValue = value.toUpperCase();
    const isValid = keyword.allowedValues.some(v => v.toUpperCase() === upperValue);
    
    if (!isValid && keyword.dataType !== 'LOGICAL') {
      return null;
    }
    
    let doc = `## \`${value}\`\n\n`;
    doc += `Value for keyword **${keyword.name}**\n\n`;
    
    // Get value-specific documentation
    const valueInfo = this.keywordDb.getValueInfo(value);
    if (valueInfo) {
      doc += `${valueInfo}\n\n`;
    }
    
    // Show other allowed values for context
    if (keyword.allowedValues.length > 1) {
      doc += `**Other allowed values:** ${keyword.allowedValues
        .filter(v => v.toUpperCase() !== upperValue)
        .slice(0, 10)
        .map(v => `\`${v}\``)
        .join(', ')}\n\n`;
    }
    
    return {
      contents: {
        kind: MarkupKind.Markdown,
        value: doc
      }
    };
  }

  /**
   * Provide hover for special CP2K values
   */
  private provideValueHover(value: string): Hover | null {
    const valueInfo = this.keywordDb.getValueInfo(value);
    
    if (!valueInfo) {
      // Check for common values
      const commonValues: Record<string, string> = {
        'TRUE': 'Boolean true value. Equivalent to T, .TRUE., ON, YES.',
        'FALSE': 'Boolean false value. Equivalent to F, .FALSE., OFF, NO.',
        'T': 'Short form of TRUE',
        'F': 'Short form of FALSE',
        '.TRUE.': 'Fortran-style boolean true',
        '.FALSE.': 'Fortran-style boolean false',
        'ON': 'Enabled / Boolean true',
        'OFF': 'Disabled / Boolean false',
        'YES': 'Boolean true',
        'NO': 'Boolean false',
      };
      
      if (commonValues[value]) {
        return {
          contents: {
            kind: MarkupKind.Markdown,
            value: `## \`${value}\`\n\n${commonValues[value]}`
          }
        };
      }
      
      return null;
    }
    
    return {
      contents: {
        kind: MarkupKind.Markdown,
        value: `## \`${value}\`\n\n${valueInfo}`
      }
    };
  }

  /**
   * Provide hover for units
   */
  private provideUnitHover(unit: string): Hover | null {
    const unitDocs: Record<string, { desc: string; dimension: string }> = {
      'angstrom': { desc: 'Å (10⁻¹⁰ m)', dimension: 'Length' },
      'bohr': { desc: 'Bohr radius (a₀ ≈ 0.529 Å)', dimension: 'Length' },
      'nm': { desc: 'Nanometer (10⁻⁹ m)', dimension: 'Length' },
      'pm': { desc: 'Picometer (10⁻¹² m)', dimension: 'Length' },
      'hartree': { desc: 'Hartree (Eₕ ≈ 27.211 eV)', dimension: 'Energy' },
      'ev': { desc: 'Electron volt', dimension: 'Energy' },
      'kcalmol': { desc: 'Kilocalorie per mole', dimension: 'Energy' },
      'kjmol': { desc: 'Kilojoule per mole', dimension: 'Energy' },
      'ry': { desc: 'Rydberg (≈ 13.606 eV)', dimension: 'Energy' },
      'fs': { desc: 'Femtosecond (10⁻¹⁵ s)', dimension: 'Time' },
      'ps': { desc: 'Picosecond (10⁻¹² s)', dimension: 'Time' },
      'ns': { desc: 'Nanosecond (10⁻⁹ s)', dimension: 'Time' },
      'bar': { desc: 'Bar (10⁵ Pa)', dimension: 'Pressure' },
      'pa': { desc: 'Pascal', dimension: 'Pressure' },
      'gpa': { desc: 'Gigapascal (10⁹ Pa)', dimension: 'Pressure' },
      'atm': { desc: 'Standard atmosphere', dimension: 'Pressure' },
      'k': { desc: 'Kelvin', dimension: 'Temperature' },
      'amu': { desc: 'Atomic mass unit (Dalton)', dimension: 'Mass' },
      'deg': { desc: 'Degree', dimension: 'Angle' },
      'rad': { desc: 'Radian', dimension: 'Angle' },
      'hartree/bohr': { desc: 'Hartree per Bohr', dimension: 'Force' },
      'ev/angstrom': { desc: 'eV per Å', dimension: 'Force' },
    };
    
    const upperUnit = unit.toLowerCase();
    const unitInfo = unitDocs[upperUnit];
    
    if (!unitInfo) {
      return null;
    }
    
    return {
      contents: {
        kind: MarkupKind.Markdown,
        value: `## \`${unit}\`\n\n**${unitInfo.dimension}**\n\n${unitInfo.desc}`
      }
    };
  }

  /**
   * Get word at position (including & for sections)
   */
  private getWordAtPosition(document: TextDocument, position: Position): string | null {
    const line = document.getText({
      start: { line: position.line, character: 0 },
      end: { line: position.line, character: Number.MAX_VALUE },
    });
    
    // Match different patterns: sections, keywords, variables
    const patterns = [
      /[&][A-Za-z_][A-Za-z0-9_-]*/g,    // Sections
      /\$\{[^}]+\}/g,                      // Variables
      /[A-Za-z_][A-Za-z0-9_-]*/g,         // Keywords/identifiers
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

  /**
   * Get line text at position
   */
  private getLineAtPosition(document: TextDocument, position: Position): string {
    return document.getText({
      start: { line: position.line, character: 0 },
      end: { line: position.line, character: Number.MAX_VALUE },
    });
  }
}
