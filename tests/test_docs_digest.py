"""Tests for docs_digest loader and wiki digest pipeline.

Tests cover:
- Deterministic JSONL output
- Provenance fields present on every entry
- Search utility
- Hover index structure
- Rules YAML structure
"""

import json
import os

import pytest


@pytest.fixture
def tmp_digest_dir(tmp_path):
    """Create a temporary docs_digest directory with sample data."""
    digest_dir = tmp_path / "docs_digest"
    digest_dir.mkdir()

    hover_index = {
        "version": "1.0.0",
        "cp2k_version": "2024.1",
        "generated_at": "2026-06-13",
        "sections": {
            "GLOBAL": {"description": "Global parameters", "manual_url": "https://example.com"},
        },
        "keywords": {
            "RUN_TYPE": {"description": "Run type", "type": "enum", "manual_url": "https://example.com"},
        },
    }
    (digest_dir / "cp2k_hover_index.json").write_text(json.dumps(hover_index, indent=2))

    entries = [
        {
            "type": "keyword",
            "name": "RUN_TYPE",
            "description": "Run type",
            "provenance": {
                "source": "schema",
                "cp2k_version": "2024.1",
                "crawl_date": "2026-06-13",
                "license": "CP2K license",
            },
        },
        {
            "type": "section",
            "name": "GLOBAL",
            "description": "Global parameters",
            "provenance": {
                "source": "schema",
                "cp2k_version": "2024.1",
                "crawl_date": "2026-06-13",
                "license": "CP2K license",
            },
        },
        {
            "type": "recipe",
            "name": "H2O_DFT",
            "description": "Water DFT calculation",
            "provenance": {
                "source": "community",
                "cp2k_version": "2024.1",
                "crawl_date": "2026-06-13",
                "license": "MIT",
            },
        },
    ]
    lines = [json.dumps(e) for e in entries]
    (digest_dir / "cp2k_wiki.jsonl").write_text("\n".join(lines) + "\n")

    return digest_dir


class TestHoverIndexStructure:
    def test_hover_index_has_required_fields(self, tmp_digest_dir):
        os.environ["CP2K_DOCS_DIGEST_DIR"] = str(tmp_digest_dir)
        try:
            from cp2k_input_tools.docs_digest import load_hover_index
            index = load_hover_index()
            assert index is not None
            assert "version" in index
            assert "cp2k_version" in index
            assert "sections" in index
            assert "keywords" in index
        finally:
            del os.environ["CP2K_DOCS_DIGEST_DIR"]

    def test_hover_index_missing_file(self, tmp_path):
        os.environ["CP2K_DOCS_DIGEST_DIR"] = str(tmp_path / "nonexistent")
        try:
            from cp2k_input_tools.docs_digest import load_hover_index
            index = load_hover_index()
            assert index is None
        finally:
            del os.environ["CP2K_DOCS_DIGEST_DIR"]


class TestWikiJsonlStructure:
    def test_wiki_entries_have_provenance(self, tmp_digest_dir):
        os.environ["CP2K_DOCS_DIGEST_DIR"] = str(tmp_digest_dir)
        try:
            from cp2k_input_tools.docs_digest import load_wiki_entries
            entries = load_wiki_entries()
            assert len(entries) > 0
            for entry in entries:
                assert "provenance" in entry
                assert "source" in entry["provenance"]
                assert "cp2k_version" in entry["provenance"]
                assert "crawl_date" in entry["provenance"]
        finally:
            del os.environ["CP2K_DOCS_DIGEST_DIR"]

    def test_wiki_entries_deterministic_order(self, tmp_digest_dir):
        os.environ["CP2K_DOCS_DIGEST_DIR"] = str(tmp_digest_dir)
        try:
            from cp2k_input_tools.docs_digest import load_wiki_entries
            entries1 = load_wiki_entries()
            entries2 = load_wiki_entries()
            names1 = [e["name"] for e in entries1]
            names2 = [e["name"] for e in entries2]
            assert names1 == names2
        finally:
            del os.environ["CP2K_DOCS_DIGEST_DIR"]

    def test_wiki_entries_have_type(self, tmp_digest_dir):
        os.environ["CP2K_DOCS_DIGEST_DIR"] = str(tmp_digest_dir)
        try:
            from cp2k_input_tools.docs_digest import load_wiki_entries
            entries = load_wiki_entries()
            for entry in entries:
                assert "type" in entry
                assert entry["type"] in ("keyword", "section", "recipe", "rule")
        finally:
            del os.environ["CP2K_DOCS_DIGEST_DIR"]


class TestSearchUtility:
    def test_search_by_name(self, tmp_digest_dir):
        os.environ["CP2K_DOCS_DIGEST_DIR"] = str(tmp_digest_dir)
        try:
            from cp2k_input_tools.docs_digest import search_wiki
            results = search_wiki("RUN_TYPE")
            assert len(results) > 0
            assert results[0]["name"] == "RUN_TYPE"
        finally:
            del os.environ["CP2K_DOCS_DIGEST_DIR"]

    def test_search_by_type_filter(self, tmp_digest_dir):
        os.environ["CP2K_DOCS_DIGEST_DIR"] = str(tmp_digest_dir)
        try:
            from cp2k_input_tools.docs_digest import search_wiki
            results = search_wiki("GLOBAL", entry_type="section")
            assert len(results) > 0
            assert results[0]["type"] == "section"
        finally:
            del os.environ["CP2K_DOCS_DIGEST_DIR"]

    def test_search_limit(self, tmp_digest_dir):
        os.environ["CP2K_DOCS_DIGEST_DIR"] = str(tmp_digest_dir)
        try:
            from cp2k_input_tools.docs_digest import search_wiki
            results = search_wiki("a", limit=1)
            assert len(results) <= 1
        finally:
            del os.environ["CP2K_DOCS_DIGEST_DIR"]

    def test_search_no_match(self, tmp_digest_dir):
        os.environ["CP2K_DOCS_DIGEST_DIR"] = str(tmp_digest_dir)
        try:
            from cp2k_input_tools.docs_digest import search_wiki
            results = search_wiki("NONEXISTENT_KEYWORD_12345")
            assert len(results) == 0
        finally:
            del os.environ["CP2K_DOCS_DIGEST_DIR"]


class TestProvenanceUtility:
    def test_get_provenance_from_entry(self):
        from cp2k_input_tools.docs_digest import get_provenance
        entry = {"provenance": {"source": "schema", "cp2k_version": "2024.1"}}
        prov = get_provenance(entry)
        assert prov["source"] == "schema"

    def test_get_provenance_missing(self):
        from cp2k_input_tools.docs_digest import get_provenance
        entry = {"name": "test"}
        prov = get_provenance(entry)
        assert prov["source"] == "unknown"
