"""VS Code protocol smoke tests for CP2K LSP.

This module provides end-to-end smoke tests that verify the LSP server
handles VS Code protocol messages correctly, including:
- Initialize/shutdown lifecycle
- Document sync (didOpen, didChange, didClose)
- Diagnostics publishing
- Hover, completion, formatting, code actions
- Document symbols
- Semantic tokens (when implemented)

Tests exercise the server directly via pygls, without requiring a real VS Code instance.
"""
