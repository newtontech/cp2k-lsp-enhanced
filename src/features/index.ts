/**
 * Features module exports
 * 
 * LSP Features for CP2K input files:
 * - Completion: Auto-completion for sections, keywords, values, and units
 * - Diagnostics: Real-time validation of syntax, types, and schema constraints
 * - Hover: Documentation on hover for sections, keywords, and values
 * - Definition: Go-to-definition for sections and variables
 * - Formatting: Document formatting with proper indentation
 * - DeepValidation: CP2K CLI integration for deep validation
 */

export { DiagnosticsProvider, DiagnosticsOptions } from './diagnostics';
export { CompletionProvider, CompletionOptions } from './completion';
export { HoverProvider, HoverOptions } from './hover';
export { DefinitionProvider } from './definition';
export { FormattingProvider } from './formatting';
export { DeepValidationProvider, DebouncedValidator, CP2KValidationOptions } from './deep-validation';
