"""Cache invalidation for VS Code file events.

Provides cache invalidation handlers for file system events:
- File created/deleted/renamed
- File content changed
- Workspace folder changes
"""

import logging
import os

from cp2k_input_tools.workspace_index import WorkspaceResourceIndex

logger = logging.getLogger(__name__)


class CacheInvalidator:
    """Handles cache invalidation for file system events."""
    
    def __init__(self, workspace_index: WorkspaceResourceIndex):
        """Initialize the cache invalidator.
        
        Args:
            workspace_index: The workspace resource index to invalidate
        """
        self.workspace_index = workspace_index
    
    def on_file_created(self, file_path: str) -> None:
        """Handle file creation event.
        
        Args:
            file_path: Path of the created file
        """
        logger.debug(f"File created: {file_path}")
        # No cache invalidation needed for new files
        # They will be picked up when referenced
    
    def on_file_deleted(self, file_path: str) -> None:
        """Handle file deletion event.
        
        Args:
            file_path: Path of the deleted file
        """
        logger.debug(f"File deleted: {file_path}")
        # Invalidate the file from data files cache
        self.workspace_index.invalidate_file(file_path)
        
        # Also invalidate any documents that reference this file
        self._invalidate_references_to_file(file_path)
    
    def on_file_renamed(self, old_path: str, new_path: str) -> None:
        """Handle file rename event.
        
        Args:
            old_path: Old file path
            new_path: New file path
        """
        logger.debug(f"File renamed: {old_path} -> {new_path}")
        # Invalidate the old path
        self.workspace_index.invalidate_file(old_path)
        
        # Update references if needed
        self._update_references_for_rename(old_path, new_path)
    
    def on_file_changed(self, file_path: str) -> None:
        """Handle file content change event.
        
        Args:
            file_path: Path of the changed file
        """
        logger.debug(f"File changed: {file_path}")
        # Invalidate the file from data files cache
        self.workspace_index.invalidate_file(file_path)
    
    def on_workspace_folder_changed(self, added: list, removed: list) -> None:
        """Handle workspace folder change event.
        
        Args:
            added: List of added folder paths
            removed: List of removed folder paths
        """
        logger.debug(f"Workspace folders changed: added={added}, removed={removed}")
        # Clear all caches when workspace structure changes
        self.workspace_index._cache.clear()
        self.workspace_index.data_files.clear()
    
    def _invalidate_references_to_file(self, file_path: str) -> None:
        """Invalidate all references to a specific file.
        
        Args:
            file_path: The file path that was deleted
        """
        normalized_path = os.path.normpath(file_path)
        
        for doc_uri in list(self.workspace_index.file_references.keys()):
            refs = self.workspace_index.file_references[doc_uri]
            for ref in refs:
                resolved = self.workspace_index.resolve_file_path(ref, doc_uri)
                if resolved and os.path.normpath(resolved) == normalized_path:
                    # Mark this reference as invalid by removing it
                    refs.remove(ref)
                    logger.debug(f"Removed invalid reference to {file_path} in {doc_uri}")
    
    def _update_references_for_rename(self, old_path: str, new_path: str) -> None:
        """Update references when a file is renamed.
        
        Args:
            old_path: Old file path
            new_path: New file path
        """
        # For now, just invalidate the old path
        # References will be re-resolved when needed
        pass
