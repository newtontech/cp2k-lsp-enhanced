import { TextDocument } from 'vscode-languageserver-textdocument';

describe('LSP Server', () => {
  describe('Document handling', () => {
    it('should create text documents', () => {
      const doc = TextDocument.create('test://test.inp', 'cp2k', 1, '&GLOBAL\n&END GLOBAL');
      expect(doc.uri).toBe('test://test.inp');
      expect(doc.languageId).toBe('cp2k');
      expect(doc.version).toBe(1);
    });

    it('should get document text', () => {
      const content = '&GLOBAL\n&END GLOBAL';
      const doc = TextDocument.create('test://test.inp', 'cp2k', 1, content);
      expect(doc.getText()).toBe(content);
    });

    it('should get document line count', () => {
      const doc = TextDocument.create('test://test.inp', 'cp2k', 1, '&GLOBAL\n&END GLOBAL');
      expect(doc.lineCount).toBe(2);
    });

    it('should handle empty document', () => {
      const doc = TextDocument.create('test://test.inp', 'cp2k', 1, '');
      expect(doc.getText()).toBe('');
      expect(doc.lineCount).toBe(1);
    });

    it('should convert position to offset', () => {
      const doc = TextDocument.create('test://test.inp', 'cp2k', 1, '&GLOBAL\n&END GLOBAL');
      const offset = doc.offsetAt({ line: 1, character: 0 });
      expect(offset).toBe(8);
    });

    it('should convert offset to position', () => {
      const doc = TextDocument.create('test://test.inp', 'cp2k', 1, '&GLOBAL\n&END GLOBAL');
      const position = doc.positionAt(8);
      expect(position.line).toBe(1);
      expect(position.character).toBe(0);
    });

    it('should get text in range', () => {
      const doc = TextDocument.create('test://test.inp', 'cp2k', 1, '&GLOBAL\n&END GLOBAL');
      const text = doc.getText({
        start: { line: 0, character: 0 },
        end: { line: 0, character: 7 }
      });
      expect(text).toBe('&GLOBAL');
    });

    it('should update document content', () => {
      const doc = TextDocument.create('test://test.inp', 'cp2k', 1, '&GLOBAL');
      TextDocument.update(doc, [{ text: '&GLOBAL\n&END GLOBAL' }], 2);
      expect(doc.version).toBe(2);
    });
  });
});
