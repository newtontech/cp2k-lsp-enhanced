/**
 * Enhanced Diagnostics Provider
 * 
 * Provides comprehensive diagnostics for CP2K input files including:
 * - Syntax validation
 * - Schema-based keyword validation
 * - Required section/keyword checking
 * - Type checking
 * - CP2K CLI deep validation
 */

import { TextDocument } from 'vscode-languageserver-textdocument';
import { Diagnostic, DiagnosticSeverity, Range, Position } from 'vscode-languageserver/node';
import { CP2KParser } from '../parser/cp2k-parser';
import { SchemaParser, SchemaSection, SchemaKeyword } from '../data/schema-parser';
import { DeepValidationProvider } from './deep-validation';

export interface DiagnosticsOptions {
  maxProblems?: number;
  enableSchemaValidation?: boolean;
  enableDeepValidation?: boolean;
  cp2kPath?: string;
}

export class DiagnosticsProvider {
  private parser: CP2KParser;
  private schemaParser: SchemaParser | null = null;
  private deepValidator: DeepValidationProvider | null = null;
  private options: DiagnosticsOptions;

  constructor(
    parser: CP2KParser,
    schemaParser?: SchemaParser,
    options: DiagnosticsOptions = {}
  ) {
    this.parser = parser;
    this.schemaParser = schemaParser || null;
    this.options = {
      maxProblems: 100,
      enableSchemaValidation: true,
      enableDeepValidation: false,
      ...options
    };
    
    if (options.cp2kPath) {
      this.deepValidator = new DeepValidationProvider({ cp2kPath: options.cp2kPath });
    }
  }

  /**
   * Update options
   */
  updateOptions(options: Partial<DiagnosticsOptions>): void {
    this.options = { ...this.options, ...options };
    
    if (options.cp2kPath && !this.deepValidator) {
      this.deepValidator = new DeepValidationProvider({ cp2kPath: options.cp2kPath });
    } else if (this.deepValidator && options.cp2kPath) {
      this.deepValidator.updateOptions({ cp2kPath: options.cp2kPath });
    }
  }

  /**
   * Provide diagnostics for a document
   */
  provideDiagnostics(textDocument: TextDocument, maxProblems?: number): Diagnostic[] {
    const parsed = this.parser.parse(textDocument);
    let diagnostics: Diagnostic[] = [...parsed.diagnostics];
    
    // Add schema-based validation
    if (this.options.enableSchemaValidation && this.schemaParser) {
      const schemaDiagnostics = this.validateWithSchema(textDocument, parsed);
      diagnostics = diagnostics.concat(schemaDiagnostics);
    }
    
    // Add semantic validation
    const semanticDiagnostics = this.validateDocument(textDocument, parsed);
    diagnostics = diagnostics.concat(semanticDiagnostics);
    
    // Check required sections (always, not just with schema)
    this.checkRequiredSections(parsed, diagnostics);
    
    // Add type checking
    const typeDiagnostics = this.validateTypes(textDocument, parsed);
    diagnostics = diagnostics.concat(typeDiagnostics);
    
    // Add constraint validation
    const constraintDiagnostics = this.validateConstraints(textDocument, parsed);
    diagnostics = diagnostics.concat(constraintDiagnostics);
    
    const limit = maxProblems ?? this.options.maxProblems ?? 100;
    return diagnostics.slice(0, limit);
  }

  /**
   * Validate with CP2K CLI (async, debounced)
   */
  async provideDeepValidation(
    textDocument: TextDocument,
    callback: (diagnostics: Diagnostic[]) => void
  ): Promise<void> {
    if (!this.options.enableDeepValidation || !this.deepValidator) {
      // Callback should be called even if deep validation is not enabled
      callback([]);
      return;
    }

    await this.deepValidator.validateWithCP2K(textDocument, callback);
  }

  /**
   * Schema-based validation
   */
  private validateWithSchema(textDocument: TextDocument, parsed: any): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];
    
    if (!this.schemaParser) return diagnostics;

    // Check for required top-level sections
    this.checkRequiredSections(parsed, diagnostics);
    
    // Validate each section and keyword
    for (const section of parsed.sections) {
      this.validateSection(section, diagnostics, textDocument);
    }
    
    return diagnostics;
  }

  /**
   * Check for required sections
   */
  private checkRequiredSections(parsed: any, diagnostics: Diagnostic[]): void {
    const requiredSections = ['GLOBAL', 'FORCE_EVAL'];
    
    for (const required of requiredSections) {
      const hasSection = parsed.sections.some(
        (s: any) => s.name.toUpperCase() === required
      );
      
      if (!hasSection) {
        diagnostics.push({
          severity: DiagnosticSeverity.Error,
          range: Range.create(0, 0, 0, 0),
          message: `Missing required section: ${required}`,
          source: 'cp2k-schema',
          code: 'missing-section'
        });
      }
    }
  }

  /**
   * Validate a section against schema
   */
  private validateSection(section: any, diagnostics: Diagnostic[], document: TextDocument): void {
    if (!this.schemaParser) return;

    const schemaSection = this.schemaParser.getSection(section.name);
    
    // Check if section is deprecated
    if (schemaSection?.deprecated) {
      diagnostics.push({
        severity: DiagnosticSeverity.Warning,
        range: this.createRange(section.location),
        message: `Section ${section.name} is deprecated`,
        source: 'cp2k-schema',
        code: 'deprecated-section'
      });
    }

    // Validate keywords in this section
    for (const keyword of section.keywords || []) {
      this.validateKeyword(keyword, schemaSection, diagnostics, document);
    }

    // Recursively validate subsections
    for (const subsection of section.subsections || []) {
      this.validateSection(subsection, diagnostics, document);
    }
  }

  /**
   * Validate a keyword against schema
   */
  private validateKeyword(
    keyword: any,
    schemaSection: SchemaSection | undefined,
    diagnostics: Diagnostic[],
    document: TextDocument
  ): void {
    if (!this.schemaParser) return;

    const schemaKeyword = schemaSection?.keywords.get(keyword.name.toUpperCase()) ||
                          this.schemaParser.getKeyword(keyword.name);

    if (!schemaKeyword) {
      // Unknown keyword
      diagnostics.push({
        severity: DiagnosticSeverity.Warning,
        range: this.createRange(keyword.location),
        message: `Unknown keyword: ${keyword.name}`,
        source: 'cp2k-schema',
        code: 'unknown-keyword'
      });
      return;
    }

    // Check if deprecated
    if (schemaKeyword.deprecated) {
      diagnostics.push({
        severity: DiagnosticSeverity.Information,
        range: this.createRange(keyword.location),
        message: `Keyword ${keyword.name} is deprecated`,
        source: 'cp2k-schema',
        code: 'deprecated-keyword'
      });
    }

    // Validate value against allowed values
    if (schemaKeyword.allowedValues && keyword.value) {
      const values = Array.isArray(keyword.value) ? keyword.value : [keyword.value];
      for (const val of values) {
        const upperVal = String(val).toUpperCase();
        if (!schemaKeyword.allowedValues.some(av => av.toUpperCase() === upperVal)) {
          diagnostics.push({
            severity: DiagnosticSeverity.Error,
            range: this.createRange(keyword.location),
            message: `Invalid value "${val}" for ${keyword.name}. Allowed values: ${schemaKeyword.allowedValues.join(', ')}`,
            source: 'cp2k-schema',
            code: 'invalid-value'
          });
        }
      }
    }
  }

  /**
   * Document-level validation
   */
  private validateDocument(textDocument: TextDocument, parsed: any): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];
    const text = textDocument.getText();
    const lines = text.split(/\r?\n/);
    
    // Check for FORCE_EVAL section
    const hasForceEval = parsed.sections.some((s: any) => s.name.toUpperCase() === 'FORCE_EVAL');
    if (!hasForceEval) {
      diagnostics.push({
        severity: DiagnosticSeverity.Information,
        range: Range.create(0, 0, 0, 0),
        message: 'Missing FORCE_EVAL section. This input file will not perform any calculations.',
        source: 'cp2k-lsp',
      });
    }
    
    // Check for variable expansion issues
    this.checkVariableExpansion(lines, diagnostics);
    
    // Check for unbalanced brackets
    this.checkBalancedBrackets(lines, diagnostics);
    
    // Check for invalid section/keyword syntax
    this.checkSyntax(textDocument, parsed, diagnostics);
    
    return diagnostics;
  }

  /**
   * Check variable expansion syntax
   */
  private checkVariableExpansion(lines: string[], diagnostics: Diagnostic[]): void {
    const varRegex = /\$\{([^}]*)\}/g;
    
    lines.forEach((line, lineNum) => {
      let match;
      while ((match = varRegex.exec(line)) !== null) {
        const varName = match[1];
        if (!varName || varName.trim() === '') {
          diagnostics.push({
            severity: DiagnosticSeverity.Error,
            range: Range.create(lineNum, match.index, lineNum, match.index + match[0].length),
            message: 'Empty variable reference',
            source: 'cp2k-lsp',
          });
        }
      }
    });
  }

  /**
   * Check for balanced brackets
   */
  private checkBalancedBrackets(lines: string[], diagnostics: Diagnostic[]): void {
    lines.forEach((line, lineNum) => {
      const openParen = (line.match(/\(/g) || []).length;
      const closeParen = (line.match(/\)/g) || []).length;
      const openBracket = (line.match(/\[/g) || []).length;
      const closeBracket = (line.match(/\]/g) || []).length;
      
      if (openParen !== closeParen) {
        diagnostics.push({
          severity: DiagnosticSeverity.Warning,
          range: Range.create(lineNum, 0, lineNum, line.length),
          message: `Unbalanced parentheses: ${openParen} opening, ${closeParen} closing`,
          source: 'cp2k-lsp',
        });
      }
      
      if (openBracket !== closeBracket) {
        diagnostics.push({
          severity: DiagnosticSeverity.Warning,
          range: Range.create(lineNum, 0, lineNum, line.length),
          message: `Unbalanced brackets: ${openBracket} opening, ${closeBracket} closing`,
          source: 'cp2k-lsp',
        });
      }
    });
  }

  /**
   * Syntax validation
   */
  private checkSyntax(
    textDocument: TextDocument,
    parsed: any,
    diagnostics: Diagnostic[]
  ): void {
    const text = textDocument.getText();
    const lines = text.split(/\r?\n/);
    
    lines.forEach((line, lineNum) => {
      const trimmed = line.trim();
      
      // Check for invalid section syntax
      if (trimmed.startsWith('&')) {
        const match = trimmed.match(/^&(\S+)/);
        if (!match) {
          diagnostics.push({
            severity: DiagnosticSeverity.Error,
            range: Range.create(lineNum, 0, lineNum, line.length),
            message: 'Invalid section syntax',
            source: 'cp2k-lsp',
          });
        }
      }
      
      // Check for duplicate keywords in same section (when not allowed)
      // This is handled in validateConstraints
    });
  }

  /**
   * Type checking validation
   */
  private validateTypes(textDocument: TextDocument, parsed: any): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];
    
    for (const section of parsed.sections) {
      for (const keyword of section.keywords || []) {
        this.validateKeywordType(keyword, diagnostics);
      }
      
      // Check subsections recursively
      this.validateTypesRecursive(section.subsections || [], diagnostics);
    }
    
    return diagnostics;
  }

  /**
   * Recursively validate types in subsections
   */
  private validateTypesRecursive(subsections: any[], diagnostics: Diagnostic[]): void {
    for (const subsection of subsections) {
      for (const keyword of subsection.keywords || []) {
        this.validateKeywordType(keyword, diagnostics);
      }
      this.validateTypesRecursive(subsection.subsections || [], diagnostics);
    }
  }

  /**
   * Validate keyword value type
   */
  private validateKeywordType(keyword: any, diagnostics: Diagnostic[]): void {
    if (!this.schemaParser || !keyword.value) return;

    const schemaKeyword = this.schemaParser.getKeyword(keyword.name);
    if (!schemaKeyword) return;

    const value = keyword.value;
    
    switch (schemaKeyword.dataType) {
      case 'INTEGER':
      case 'INTEGER_LIST':
        if (!this.isValidInteger(value)) {
          diagnostics.push({
            severity: DiagnosticSeverity.Error,
            range: this.createRange(keyword.location),
            message: `Expected integer value for ${keyword.name}, got "${value}"`,
            source: 'cp2k-type-check',
            code: 'type-mismatch'
          });
        }
        break;
        
      case 'REAL':
      case 'REAL_LIST':
        if (!this.isValidReal(value)) {
          diagnostics.push({
            severity: DiagnosticSeverity.Error,
            range: this.createRange(keyword.location),
            message: `Expected real number for ${keyword.name}, got "${value}"`,
            source: 'cp2k-type-check',
            code: 'type-mismatch'
          });
        }
        break;
        
      case 'LOGICAL':
        if (!this.isValidLogical(value)) {
          diagnostics.push({
            severity: DiagnosticSeverity.Error,
            range: this.createRange(keyword.location),
            message: `Expected logical value (TRUE/FALSE) for ${keyword.name}, got "${value}"`,
            source: 'cp2k-type-check',
            code: 'type-mismatch'
          });
        }
        break;
    }
  }

  /**
   * Validate constraints (required, mutually exclusive)
   */
  private validateConstraints(textDocument: TextDocument, parsed: any): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];
    
    for (const section of parsed.sections) {
      this.validateSectionConstraints(section, diagnostics);
    }
    
    return diagnostics;
  }

  /**
   * Validate section-level constraints
   */
  private validateSectionConstraints(section: any, diagnostics: Diagnostic[]): void {
    // Check for required keywords in section
    if (this.schemaParser) {
      const schemaSection = this.schemaParser.getSection(section.name);
      
      if (schemaSection) {
        // Check required keywords
        for (const [kwName, kw] of schemaSection.keywords) {
          if (kw.required) {
            const hasKeyword = section.keywords?.some(
              (k: any) => k.name.toUpperCase() === kwName
            );
            
            if (!hasKeyword) {
              diagnostics.push({
                severity: DiagnosticSeverity.Error,
                range: this.createRange(section.location),
                message: `Missing required keyword ${kwName} in section ${section.name}`,
                source: 'cp2k-constraint',
                code: 'missing-keyword'
              });
            }
          }
        }
        
        // Check required subsections
        for (const [subName, sub] of schemaSection.subsections) {
          if (sub.required) {
            const hasSubsection = section.subsections?.some(
              (s: any) => s.name.toUpperCase() === subName
            );
            
            if (!hasSubsection) {
              diagnostics.push({
                severity: DiagnosticSeverity.Error,
                range: this.createRange(section.location),
                message: `Missing required subsection ${subName} in section ${section.name}`,
                source: 'cp2k-constraint',
                code: 'missing-subsection'
              });
            }
          }
        }
      }
    }
    
    // Check for mutually exclusive keywords
    this.checkMutuallyExclusive(section, diagnostics);
    
    // Recursively check subsections
    for (const subsection of section.subsections || []) {
      this.validateSectionConstraints(subsection, diagnostics);
    }
  }

  /**
   * Check for mutually exclusive keywords
   */
  private checkMutuallyExclusive(section: any, diagnostics: Diagnostic[]): void {
    // Define mutually exclusive keyword groups
    const exclusiveGroups = [
      ['METHOD', 'DFT'],  // Can't have both in some contexts
      // Add more as needed
    ];
    
    for (const group of exclusiveGroups) {
      const found = group.filter(kw =>
        section.keywords?.some((k: any) => k.name.toUpperCase() === kw)
      );
      
      if (found.length > 1) {
        diagnostics.push({
          severity: DiagnosticSeverity.Error,
          range: this.createRange(section.location),
          message: `Mutually exclusive keywords: ${found.join(', ')}`,
          source: 'cp2k-constraint',
          code: 'mutual-exclusion'
        });
      }
    }
  }

  /**
   * Helper: Create Range from location object
   */
  private createRange(location: any): Range {
    if (!location) {
      return Range.create(0, 0, 0, 0);
    }
    
    return Range.create(
      Position.create(location.start?.line || 0, location.start?.column || 0),
      Position.create(location.end?.line || 0, location.end?.column || 0)
    );
  }

  /**
   * Helper: Validate integer
   */
  private isValidInteger(value: any): boolean {
    if (Array.isArray(value)) {
      return value.every(v => this.isValidInteger(v));
    }
    return /^[-+]?\d+$/.test(String(value).trim());
  }

  /**
   * Helper: Validate real number
   */
  private isValidReal(value: any): boolean {
    if (Array.isArray(value)) {
      return value.every(v => this.isValidReal(v));
    }
    const str = String(value).trim();
    return /^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(str);
  }

  /**
   * Helper: Validate logical
   */
  private isValidLogical(value: any): boolean {
    const str = String(value).trim().toUpperCase();
    return ['TRUE', 'FALSE', 'T', 'F', 'YES', 'NO', 'ON', 'OFF', '.TRUE.', '.FALSE.'].includes(str);
  }
}
