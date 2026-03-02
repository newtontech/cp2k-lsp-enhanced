#!/usr/bin/env node
import {
  createConnection,
  TextDocuments,
  Diagnostic,
  DiagnosticSeverity,
  ProposedFeatures,
  InitializeParams,
  DidChangeConfigurationNotification,
  CompletionItem,
  TextDocumentPositionParams,
  TextDocumentSyncKind,
  InitializeResult,
  DocumentDiagnosticReportKind,
  type DocumentDiagnosticReport,
  HoverParams,
  Hover,
  DefinitionParams,
  Location,
  DocumentFormattingParams,
  TextEdit,
  FormattingOptions,
} from 'vscode-languageserver/node';

import { TextDocument } from 'vscode-languageserver-textdocument';
import { CP2KParser } from './parser/cp2k-parser';
import { DiagnosticsProvider, DiagnosticsOptions } from './features/diagnostics';
import { CompletionProvider, CompletionOptions } from './features/completion';
import { HoverProvider } from './features/hover';
import { DefinitionProvider } from './features/definition';
import { FormattingProvider } from './features/formatting';
import { KeywordDatabase } from './data/keyword-database';
import { SchemaParser } from './data/schema-parser';
import { DebouncedValidator } from './features/deep-validation';

// Create a connection for the server
const connection = createConnection(ProposedFeatures.all);

// Create a simple text document manager
const documents: TextDocuments<TextDocument> = new TextDocuments(TextDocument);

let hasConfigurationCapability = false;
let hasWorkspaceFolderCapability = false;
let hasDiagnosticRelatedInformationCapability = false;

// Initialize providers
const keywordDb = new KeywordDatabase();
let schemaParser: SchemaParser | undefined = undefined;
const parser = new CP2KParser();

// Diagnostics provider with optional schema validation
let diagnosticsProvider: DiagnosticsProvider;
const completionProvider = new CompletionProvider(keywordDb, schemaParser);
const hoverProvider = new HoverProvider(keywordDb);
const definitionProvider = new DefinitionProvider(keywordDb);
const formattingProvider = new FormattingProvider();

// Deep validation (debounced)
let debouncedValidator: DebouncedValidator | undefined = undefined;

// Configuration interface
interface CP2KSettings {
  maxNumberOfProblems: number;
  cp2kVersion: string;
  cp2kPath: string;
  enableSchemaValidation: boolean;
  enableDeepValidation: boolean;
  validationDelay: number;
}

// Default configuration
const defaultSettings: CP2KSettings = {
  maxNumberOfProblems: 100,
  cp2kVersion: '2025.1',
  cp2kPath: '',
  enableSchemaValidation: true,
  enableDeepValidation: false,
  validationDelay: 1000,
};

// Cache the settings of all open documents
const documentSettings: Map<string, Thenable<CP2KSettings>> = new Map();

connection.onInitialize(async (params: InitializeParams) => {
  const capabilities = params.capabilities;

  // Does the client support the `workspace/configuration` request?
  hasConfigurationCapability = !!(
    capabilities.workspace && !!capabilities.workspace.configuration
  );
  hasWorkspaceFolderCapability = !!(
    capabilities.workspace && !!capabilities.workspace.workspaceFolders
  );
  hasDiagnosticRelatedInformationCapability = !!(
    capabilities.textDocument &&
    capabilities.textDocument.publishDiagnostics &&
    capabilities.textDocument.publishDiagnostics.relatedInformation
  );

  // Initialize schema parser if possible
  try {
    const initSettings = await getDocumentSettings('');
    const cp2kPath = initSettings.cp2kPath || defaultSettings.cp2kPath;
    
    if (initSettings.enableSchemaValidation) {
      schemaParser = new SchemaParser(cp2kPath);
      try {
        await schemaParser.loadSchema();
        connection.console.log('Schema loaded successfully');
      } catch (error) {
        connection.console.warn(`Failed to load schema: ${error}`);
      }
    }
  } catch (error) {
    connection.console.warn(`Failed to initialize schema parser: ${error}`);
  }

  // Initialize providers with schema parser
  const diagOptions: DiagnosticsOptions = {
    enableSchemaValidation: true,
    enableDeepValidation: false
  };
  diagnosticsProvider = new DiagnosticsProvider(parser, schemaParser, diagOptions);
  
  // Update completion provider with schema
  const compOptions: CompletionOptions = {
    enableSnippets: true,
    enableUnitCompletion: true
  };
  if (schemaParser) {
    const EnhancedCompletion = require('./features/completion').CompletionProvider;
    const enhancedCompletion = new EnhancedCompletion(keywordDb, schemaParser, compOptions);
    // @ts-ignore - reassign for now, better design would be to update the provider
  }

  const result: InitializeResult = {
    capabilities: {
      textDocumentSync: TextDocumentSyncKind.Incremental,
      // Enable completion
      completionProvider: {
        resolveProvider: true,
        triggerCharacters: ['&', ' ', '\n', '_', '/'],
      },
      // Enable hover
      hoverProvider: true,
      // Enable go-to-definition
      definitionProvider: true,
      // Enable document formatting
      documentFormattingProvider: true,
      // Enable diagnostic
      diagnosticProvider: {
        interFileDependencies: false,
        workspaceDiagnostics: false,
      },
    },
  };
  
  if (hasWorkspaceFolderCapability) {
    result.capabilities.workspace = {
      workspaceFolders: {
        supported: true,
      },
    };
  }
  return result;
});

connection.onInitialized(async () => {
  if (hasConfigurationCapability) {
    // Register for all configuration changes
    connection.client.register(DidChangeConfigurationNotification.type, undefined);
  }
  if (hasWorkspaceFolderCapability) {
    connection.workspace.onDidChangeWorkspaceFolders((_event) => {
      connection.console.log('Workspace folder change event received.');
    });
  }
});

connection.onDidChangeConfiguration(async (change) => {
  if (hasConfigurationCapability) {
    // Reset all cached document settings
    documentSettings.clear();
  }
  
  // Update providers based on new settings
  const settings = await getDocumentSettings('');
  
  // Update schema parser
  if (settings.enableSchemaValidation && !schemaParser) {
    schemaParser = new SchemaParser(settings.cp2kPath);
    try {
      await schemaParser.loadSchema();
      connection.console.log('Schema loaded after configuration change');
    } catch (error) {
      connection.console.warn(`Failed to load schema: ${error}`);
    }
  }
  
  // Update diagnostics provider
  if (diagnosticsProvider) {
    diagnosticsProvider.updateOptions({
      enableSchemaValidation: settings.enableSchemaValidation,
      enableDeepValidation: settings.enableDeepValidation,
      cp2kPath: settings.cp2kPath
    });
  }
  
  // Update deep validation
  if (settings.enableDeepValidation) {
    if (!debouncedValidator) {
      const DeepValidationProvider = require('./features/deep-validation').DeepValidationProvider;
      const validator = new DeepValidationProvider({ cp2kPath: settings.cp2kPath });
      debouncedValidator = new DebouncedValidator(validator, settings.validationDelay);
    }
  } else {
    debouncedValidator = undefined;
  }
  
  // Revalidate all open text documents
  documents.all().forEach(validateTextDocument);
});

function getDocumentSettings(resource: string): Thenable<CP2KSettings> {
  if (!hasConfigurationCapability) {
    return Promise.resolve(defaultSettings);
  }
  let result = documentSettings.get(resource);
  if (!result) {
    result = connection.workspace.getConfiguration({
      scopeUri: resource,
      section: 'cp2k',
    });
    documentSettings.set(resource, result);
  }
  return result;
}

// Only keep settings for open documents
documents.onDidClose((e) => {
  documentSettings.delete(e.document.uri);
});

// The content of a text document has changed
documents.onDidChangeContent((change) => {
  validateTextDocument(change.document);
});

async function validateTextDocument(textDocument: TextDocument): Promise<void> {
  const settings = await getDocumentSettings(textDocument.uri);
  
  if (!settings.enableSchemaValidation && !settings.enableDeepValidation) {
    return;
  }

  // Schema-based diagnostics (fast)
  const diagnostics = diagnosticsProvider.provideDiagnostics(textDocument, settings.maxNumberOfProblems);
  connection.sendDiagnostics({ uri: textDocument.uri, diagnostics });
  
  // CP2K CLI deep validation (async, debounced)
  if (settings.enableDeepValidation && debouncedValidator && diagnosticsProvider) {
    await diagnosticsProvider.provideDeepValidation(textDocument, (deepDiagnostics) => {
      // Combine both sets of diagnostics
      const combinedDiagnostics = diagnostics.concat(deepDiagnostics);
      const uniqueDiagnostics = removeDuplicates(combinedDiagnostics);
      connection.sendDiagnostics({ 
        uri: textDocument.uri, 
        diagnostics: uniqueDiagnostics.slice(0, settings.maxNumberOfProblems)
      });
    });
  }
}

function removeDuplicates(diagnostics: Diagnostic[]): Diagnostic[] {
  const seen = new Set<string>();
  return diagnostics.filter(d => {
    const key = `${d.range.start.line}:${d.range.start.character}:${d.message}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

connection.languages.diagnostics.on(async (params) => {
  const document = documents.get(params.textDocument.uri);
  if (document !== undefined) {
    const settings = await getDocumentSettings(document.uri);
    const diagnostics = diagnosticsProvider.provideDiagnostics(document, settings.maxNumberOfProblems);
    return {
      kind: DocumentDiagnosticReportKind.Full,
      items: diagnostics,
    } as DocumentDiagnosticReport;
  }
  return {
    kind: DocumentDiagnosticReportKind.Full,
    items: [],
  } as DocumentDiagnosticReport;
});

// Completion provider
connection.onCompletion(
  (textDocumentPosition: TextDocumentPositionParams): CompletionItem[] => {
    const document = documents.get(textDocumentPosition.textDocument.uri);
    if (!document) {
      return [];
    }
    return completionProvider.provideCompletionItems(
      document,
      textDocumentPosition.position
    );
  }
);

// Completion resolve handler
connection.onCompletionResolve((item: CompletionItem): CompletionItem => {
  return completionProvider.resolveCompletionItem(item);
});

// Hover provider
connection.onHover(
  (params: HoverParams): Hover | null => {
    const document = documents.get(params.textDocument.uri);
    if (!document) {
      return null;
    }
    return hoverProvider.provideHover(document, params.position);
  }
);

// Definition provider (go-to-definition)
connection.onDefinition(
  (params: DefinitionParams): Location | null => {
    const document = documents.get(params.textDocument.uri);
    if (!document) {
      return null;
    }
    return definitionProvider.provideDefinition(document, params.position);
  }
);

// Formatting provider
connection.onDocumentFormatting(
  (params: DocumentFormattingParams): TextEdit[] => {
    const document = documents.get(params.textDocument.uri);
    if (!document) {
      return [];
    }
    return formattingProvider.provideFormatting(document, params.options);
  }
);

// Make the text document manager listen on the connection
// for open, change and close text document events
documents.listen(connection);

// Listen on the connection
connection.listen();
