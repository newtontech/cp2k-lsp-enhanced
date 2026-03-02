/**
 * CP2K CLI Deep Validation
 * 
 * Integrates CP2K's native syntax checking (cp2k -c) with LSP diagnostics.
 */

import { spawn, ChildProcess } from 'child_process';
import { TextDocument } from 'vscode-languageserver-textdocument';
import { Diagnostic, DiagnosticSeverity, Range, Position } from 'vscode-languageserver/node';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

export interface CP2KValidationOptions {
  cp2kPath?: string;
  timeout?: number;
  enabled?: boolean;
}

export interface CP2KDiagnostic {
  file: string;
  line: number;
  column?: number;
  severity: 'error' | 'warning' | 'info';
  message: string;
  code?: string;
}

export class DeepValidationProvider {
  private cp2kPath: string;
  private timeout: number;
  private enabled: boolean;
  private activeProcesses: Map<string, ChildProcess> = new Map();
  
  constructor(options: CP2KValidationOptions = {}) {
    this.cp2kPath = options.cp2kPath || this.findCP2KExecutable();
    this.timeout = options.timeout || 30000; // 30 seconds default
    this.enabled = options.enabled !== false;
  }

  /**
   * Find CP2K executable in PATH
   */
  private findCP2KExecutable(): string {
    // Common CP2K executable names
    const executables = [
      'cp2k.psmp',    // MPI+OpenMP version
      'cp2k.popt',    // MPI version
      'cp2k.ssmp',    // OpenMP version
      'cp2k.sopt',    // Serial version
      'cp2k',         // Generic
    ];
    
    for (const exe of executables) {
      try {
        const result = require('child_process').execSync(`which ${exe}`, {
          encoding: 'utf-8',
          stdio: ['pipe', 'pipe', 'pipe']
        }).trim();
        if (result) {
          return result;
        }
      } catch {
        // Executable not found, try next
      }
    }
    
    return 'cp2k'; // Default fallback
  }

  /**
   * Update configuration
   */
  updateOptions(options: CP2KValidationOptions): void {
    if (options.cp2kPath !== undefined) {
      this.cp2kPath = options.cp2kPath;
    }
    if (options.timeout !== undefined) {
      this.timeout = options.timeout;
    }
    if (options.enabled !== undefined) {
      this.enabled = options.enabled;
    }
  }

  /**
   * Check if CP2K is available
   */
  async isCP2KAvailable(): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        const proc = spawn(this.cp2kPath, ['--version'], {
          timeout: 5000,
          stdio: 'pipe'
        });
        
        proc.on('error', () => resolve(false));
        proc.on('exit', (code) => resolve(code === 0 || code === 1));
        
        // Timeout fallback
        setTimeout(() => {
          proc.kill();
          resolve(false);
        }, 5000);
      } catch {
        resolve(false);
      }
    });
  }

  /**
   * Validate document using CP2K's -c flag
   */
  async validateWithCP2K(
    document: TextDocument,
    onDiagnostics?: (diagnostics: Diagnostic[]) => void
  ): Promise<Diagnostic[]> {
    if (!this.enabled) {
      return [];
    }

    // Cancel any previous validation for this document
    this.cancelValidation(document.uri);

    return new Promise((resolve) => {
      // Write document content to temporary file
      const tempFile = this.createTempFile(document);
      
      const diagnostics: Diagnostic[] = [];
      let stdout = '';
      let stderr = '';
      let resolved = false;
      
      const cleanup = () => {
        try {
          if (fs.existsSync(tempFile)) {
            fs.unlinkSync(tempFile);
          }
        } catch {
          // Ignore cleanup errors
        }
        this.activeProcesses.delete(document.uri);
      };

      const resolveOnce = (result: Diagnostic[]) => {
        if (!resolved) {
          resolved = true;
          cleanup();
          resolve(result);
        }
      };

      try {
        const proc = spawn(this.cp2kPath, [
          '-c',                    // Check syntax only
          '-i', tempFile,          // Input file
          '--no-license-warning',  // Skip license text
        ], {
          timeout: this.timeout,
          cwd: path.dirname(tempFile),
          env: { ...process.env, CP2K_DATA_PATH: process.env.CP2K_DATA_PATH || '' }
        });

        this.activeProcesses.set(document.uri, proc);

        proc.stdout?.on('data', (data) => {
          stdout += data.toString();
        });

        proc.stderr?.on('data', (data) => {
          stderr += data.toString();
        });

        proc.on('error', (err) => {
          console.error('CP2K validation error:', err);
          resolveOnce([]);
        });

        proc.on('close', (code) => {
          const combinedOutput = stdout + '\n' + stderr;
          const parsedDiagnostics = this.parseCP2KOutput(combinedOutput, document);
          
          diagnostics.push(...parsedDiagnostics);
          
          if (onDiagnostics) {
            onDiagnostics(diagnostics);
          }
          
          resolveOnce(diagnostics);
        });

        // Timeout handling
        setTimeout(() => {
          if (!resolved && proc.pid) {
            proc.kill('SIGTERM');
            resolveOnce([]);
          }
        }, this.timeout);

      } catch (error) {
        console.error('Failed to spawn CP2K:', error);
        resolveOnce([]);
      }
    });
  }

  /**
   * Cancel ongoing validation for a document
   */
  cancelValidation(uri: string): void {
    const proc = this.activeProcesses.get(uri);
    if (proc && proc.pid) {
      proc.kill('SIGTERM');
      this.activeProcesses.delete(uri);
    }
  }

  /**
   * Create temporary file for validation
   */
  private createTempFile(document: TextDocument): string {
    const tempDir = os.tmpdir();
    const baseName = path.basename(document.uri.replace(/^file:\/\//, '') || 'input.inp');
    const tempFile = path.join(tempDir, `cp2k-lsp-${Date.now()}-${baseName}`);
    
    fs.writeFileSync(tempFile, document.getText(), 'utf-8');
    
    return tempFile;
  }

  /**
   * Parse CP2K output for diagnostics
   */
  private parseCP2KOutput(output: string, document: TextDocument): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];
    const lines = output.split('\n');

    // CP2K error patterns
    const patterns = [
      // Error pattern: "CP2K| ERROR! ... in line X of file Y"
      {
        regex: /ERROR!?\s*(.+?)\s+in\s+line\s+(\d+)\s+of\s+(?:file\s+)?(.+?)(?:\s|$)/gi,
        severity: DiagnosticSeverity.Error
      },
      // Warning pattern: "CP2K| WARNING! ... in line X"
      {
        regex: /WARNING!?\s*(.+?)\s+in\s+line\s+(\d+)/gi,
        severity: DiagnosticSeverity.Warning
      },
      // Generic error with location
      {
        regex: /Error\s*:\s*(.+?)\s*\[line\s*(\d+)(?:,\s*col\s*(\d+))?\]/gi,
        severity: DiagnosticSeverity.Error
      },
      // Unknown keyword
      {
        regex: /Unknown\s+(?:keyword|section)\s+["']([^"']+)["']\s*(?:in\s+line\s+(\d+))?/gi,
        severity: DiagnosticSeverity.Error
      },
      // Missing required section/keyword
      {
        regex: /Missing\s+(?:required\s+)?(?:section|keyword)\s+["']([^"']+)["']/gi,
        severity: DiagnosticSeverity.Error
      },
      // Invalid value
      {
        regex: /Invalid\s+value\s+["']([^"']+)["']\s+for\s+(?:keyword\s+)?["']([^"']+)["']/gi,
        severity: DiagnosticSeverity.Error
      },
      // Syntax error
      {
        regex: /Syntax\s+error\s*(?::\s*(.+?))?\s*(?:in\s+line\s+(\d+))?/gi,
        severity: DiagnosticSeverity.Error
      },
      // File not found
      {
        regex: /File\s+["']([^"']+)["']\s+not\s+found/gi,
        severity: DiagnosticSeverity.Error
      },
      // Parse error
      {
        regex: /Parse\s+error\s*(?::\s*(.+?))?\s*(?:at\s+line\s+(\d+))?/gi,
        severity: DiagnosticSeverity.Error
      },
    ];

    for (const line of lines) {
      for (const pattern of patterns) {
        let match;
        const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
        
        while ((match = regex.exec(line)) !== null) {
          let message = '';
          let lineNum = 1;
          let column = 0;

          // Extract message and line number based on pattern
          if (match[1]) {
            if (match[1].match(/^\d+$/)) {
              // First capture is line number
              lineNum = parseInt(match[1]) || 1;
              message = match[2] || match[0];
            } else {
              // First capture is message
              message = match[1];
              lineNum = parseInt(match[2]) || 1;
              column = parseInt(match[3]) || 0;
            }
          }

          // Clean up message
          message = message.trim() || line.trim();

          // Calculate range
          const startLine = Math.max(0, lineNum - 1);
          const docLine = document.getText({
            start: { line: startLine, character: 0 },
            end: { line: startLine, character: Number.MAX_VALUE }
          });
          const endChar = column > 0 ? column : docLine.length;

          const diagnostic: Diagnostic = {
            severity: pattern.severity,
            range: Range.create(
              Position.create(startLine, column),
              Position.create(startLine, endChar)
            ),
            message: message,
            source: 'cp2k-cli',
          };

          // Avoid duplicate diagnostics
          const isDuplicate = diagnostics.some(d => 
            d.range.start.line === diagnostic.range.start.line &&
            d.message === diagnostic.message
          );

          if (!isDuplicate) {
            diagnostics.push(diagnostic);
          }
        }
      }
    }

    return diagnostics;
  }

  /**
   * Dispose provider
   */
  dispose(): void {
    // Kill all active processes
    for (const [uri, proc] of this.activeProcesses) {
      if (proc.pid) {
        proc.kill('SIGTERM');
      }
    }
    this.activeProcesses.clear();
  }
}

/**
 * Debounced validation helper
 */
export class DebouncedValidator {
  private pendingValidations: Map<string, NodeJS.Timeout> = new Map();
  private validator: DeepValidationProvider;
  private delay: number;

  constructor(validator: DeepValidationProvider, delay: number = 1000) {
    this.validator = validator;
    this.delay = delay;
  }

  async validate(
    document: TextDocument,
    callback: (diagnostics: Diagnostic[]) => void
  ): Promise<void> {
    // Cancel pending validation
    const existing = this.pendingValidations.get(document.uri);
    if (existing) {
      clearTimeout(existing);
    }

    // Schedule new validation
    const timeout = setTimeout(async () => {
      this.pendingValidations.delete(document.uri);
      const diagnostics = await this.validator.validateWithCP2K(document);
      callback(diagnostics);
    }, this.delay);

    this.pendingValidations.set(document.uri, timeout);
  }

  dispose(): void {
    for (const timeout of this.pendingValidations.values()) {
      clearTimeout(timeout);
    }
    this.pendingValidations.clear();
  }
}
