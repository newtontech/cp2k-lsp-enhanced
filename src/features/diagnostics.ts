import { TextDocument } from 'vscode-languageserver-textdocument';
import { Diagnostic, DiagnosticSeverity, Range } from 'vscode-languageserver/node';
import { CP2KParser } from '../parser/cp2k-parser';

export class DiagnosticsProvider {
  private parser: CP2KParser;

  constructor(parser: CP2KParser) {
    this.parser = parser;
  }

  provideDiagnostics(textDocument: TextDocument, maxProblems: number): Diagnostic[] {
    const parsed = this.parser.parse(textDocument);
    let diagnostics = parsed.diagnostics;
    
    // Add additional validation
    const additionalDiagnostics = this.validateDocument(textDocument, parsed);
    diagnostics = diagnostics.concat(additionalDiagnostics);
    
    return diagnostics.slice(0, maxProblems);
  }

  private validateDocument(textDocument: TextDocument, parsed: any): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];
    const text = textDocument.getText();
    const lines = text.split(/\r?\n/);
    
    // Check for required GLOBAL section
    const hasGlobal = parsed.sections.some((s: any) => s.name.toUpperCase() === 'GLOBAL');
    if (!hasGlobal) {
      diagnostics.push({
        severity: DiagnosticSeverity.Warning,
        range: Range.create(0, 0, 0, 0),
        message: 'Missing GLOBAL section. CP2K input files should have a GLOBAL section.',
        source: 'cp2k-lsp',
      });
    }
    
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
    
    // Check for unbalanced parentheses or brackets
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
    
    return diagnostics;
  }
}
