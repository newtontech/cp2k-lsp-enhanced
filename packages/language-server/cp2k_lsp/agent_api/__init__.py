"""Agent-facing JSON/domain APIs for CP2K input authoring.

This module exposes three groups of functionality:

* **Description API** (#36) – structured descriptions of CP2K sections,
  keywords, their types, defaults, and human-readable docs.
* **Schema Lookup API** (#37) – query section/keyword hierarchies,
  valid subsections, keyword types, enum values, and path-based lookups.
* **Guidance API** (#38) – minimal examples for common calculation types
  and context-aware next-token suggestions given a partial CP2K input.

All public functions return JSON-serialisable dicts (or lists of dicts)
so they can be consumed directly by LLM agents, REST endpoints, or CLI
tools.
"""

from cp2k_lsp.agent_api.description import (
    describe_keyword,
    describe_section,
    describe_section_tree,
    list_all_keywords,
    list_all_sections,
)
from cp2k_lsp.agent_api.guidance import (
    get_minimal_example,
    get_next_token_guidance,
    list_available_examples,
)
from cp2k_lsp.agent_api.schema import (
    lookup_keyword_schema,
    lookup_section_path,
    lookup_section_schema,
    resolve_section_children,
)

__all__ = [
    # #36 – domain language description
    "describe_section",
    "describe_keyword",
    "describe_section_tree",
    "list_all_sections",
    "list_all_keywords",
    # #37 – schema lookup
    "lookup_section_schema",
    "lookup_keyword_schema",
    "lookup_section_path",
    "resolve_section_children",
    # #38 – examples & guidance
    "get_minimal_example",
    "get_next_token_guidance",
    "list_available_examples",
]
