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
import { DiagnosticsProvider } from './features/diagnostics';
import { CompletionProvider } from './features/completion';
import { HoverProvider } from './features/hover';
import { DefinitionProvider } from './features/definition';
import { FormattingProvider } from './features/formatting';
import { KeywordDatabase } from './data/keyword-database';

// Create a connection for the server
const connection = createConnection(ProposedFeatures.all);

// Create a simple text document manager
const documents: TextDocuments<TextDocument> = new TextDocuments(TextDocument);

let hasConfigurationCapability = false;
let hasWorkspaceFolderCapability = false;
let hasDiagnosticRelatedInformationCapability = false;

// Initialize providers
const keywordDb = new KeywordDatabase();
const parser = new CP2KParser();
const diagnosticsProvider = new DiagnosticsProvider(parser);
const completionProvider = new CompletionProvider(keywordDb);
const hoverProvider = new HoverProvider(keywordDb);
const definitionProvider = new DefinitionProvider(keywordDb);
const formattingProvider = new FormattingProvider();

connection.onInitialize((params: InitializeParams) => {
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

connection.onInitialized(() => {
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

// The global settings, used when the `workspace/configuration` approach is not supported
interface CP2KSettings {
  maxNumberOfProblems: number;
  cp2kVersion: string;
  enableValidation: boolean;
}

// Cache the settings of all open documents
const documentSettings: Map<string, Thenable<CP2KSettings>> = new Map();

connection.onDidChangeConfiguration((change) => {
  if (hasConfigurationCapability) {
    // Reset all cached document settings
    documentSettings.clear();
  }
  // Revalidate all open text documents
  documents.all().forEach(validateTextDocument);
});

function getDocumentSettings(resource: string): Thenable<CP2KSettings> {
  if (!hasConfigurationCapability) {
    return Promise.resolve({
      maxNumberOfProblems: 100,
      cp2kVersion: '2025.1',
      enableValidation: true,
    });
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
  
  if (!settings.enableValidation) {
    return;
  }

  const diagnostics = diagnosticsProvider.provideDiagnostics(textDocument, settings.maxNumberOfProblems);
  
  // Send the computed diagnostics to VSCode
  connection.sendDiagnostics({ uri: textDocument.uri, diagnostics });
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
