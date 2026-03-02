import * as featuresIndex from '../src/features/index';
import { DiagnosticsProvider } from '../src/features/diagnostics';
import { CompletionProvider } from '../src/features/completion';
import { HoverProvider } from '../src/features/hover';
import { DefinitionProvider } from '../src/features/definition';
import { FormattingProvider } from '../src/features/formatting';
import { KeywordDatabase } from '../src/data/keyword-database';
import { CP2KParser } from '../src/parser/cp2k-parser';

describe('Features Index', () => {
  it('should export DiagnosticsProvider', () => {
    expect(featuresIndex.DiagnosticsProvider).toBe(DiagnosticsProvider);
  });

  it('should export CompletionProvider', () => {
    expect(featuresIndex.CompletionProvider).toBe(CompletionProvider);
  });

  it('should export HoverProvider', () => {
    expect(featuresIndex.HoverProvider).toBe(HoverProvider);
  });

  it('should export DefinitionProvider', () => {
    expect(featuresIndex.DefinitionProvider).toBe(DefinitionProvider);
  });

  it('should export FormattingProvider', () => {
    expect(featuresIndex.FormattingProvider).toBe(FormattingProvider);
  });

  it('should be able to create all provider instances', () => {
    const keywordDb = new KeywordDatabase();
    const parser = new CP2KParser();

    const diagnosticsProvider = new featuresIndex.DiagnosticsProvider(parser);
    expect(diagnosticsProvider).toBeInstanceOf(DiagnosticsProvider);

    const completionProvider = new featuresIndex.CompletionProvider(keywordDb);
    expect(completionProvider).toBeInstanceOf(CompletionProvider);

    const hoverProvider = new featuresIndex.HoverProvider(keywordDb);
    expect(hoverProvider).toBeInstanceOf(HoverProvider);

    const definitionProvider = new featuresIndex.DefinitionProvider(keywordDb);
    expect(definitionProvider).toBeInstanceOf(DefinitionProvider);

    const formattingProvider = new featuresIndex.FormattingProvider();
    expect(formattingProvider).toBeInstanceOf(FormattingProvider);
  });
});
