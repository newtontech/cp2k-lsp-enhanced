"""Snapshot checks for the CP2K TextMate grammar.

These tests keep the offline VS Code grammar useful without requiring a Node
TextMate runtime in the Python gate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
GRAMMAR_PATH = ROOT_DIR / "syntaxes" / "cp2k.tmLanguage.json"


def _load_patterns() -> list[tuple[str, re.Pattern[str]]]:
    grammar = json.loads(GRAMMAR_PATH.read_text(encoding="utf-8"))
    patterns: list[tuple[str, re.Pattern[str]]] = []

    for repo_entry in grammar["repository"].values():
        for pattern in repo_entry["patterns"]:
            patterns.append((pattern["name"], re.compile(pattern["match"])))

    return patterns


def _scopes_for(line: str) -> list[str]:
    return [scope for scope, pattern in _load_patterns() if pattern.search(line)]


def test_grammar_declares_cp2k_language_metadata():
    grammar = json.loads(GRAMMAR_PATH.read_text(encoding="utf-8"))

    assert grammar["scopeName"] == "source.cp2k"
    assert "inp" in grammar["fileTypes"]
    assert "cp2k" in grammar["fileTypes"]


def test_grammar_snapshot_for_core_cp2k_constructs():
    samples = {
        "&GLOBAL": ["entity.name.section.begin.cp2k"],
        "  RUN_TYPE ENERGY": ["support.type.property-name.cp2k"],
        "  EPS_SCF [hartree] 1.0E-7": [
            "support.type.property-name.cp2k",
            "storage.modifier.unit.cp2k",
            "constant.numeric.cp2k",
        ],
        "  BASIS_SET_FILE_NAME ./BASIS_MOLOPT": [
            "support.type.property-name.cp2k",
        ],
        "@INCLUDE './fragments/common.inc'": [
            "keyword.control.preprocessor.cp2k",
            "string.quoted.include.cp2k",
            "string.quoted.single.cp2k",
        ],
        "  PROJECT ${PROJECT_NAME}": [
            "support.type.property-name.cp2k",
            "variable.other.cp2k",
        ],
        "  ! editable inline comment": ["comment.line.inline.cp2k"],
        "# full-line hash comment": ["comment.line.number-sign.cp2k"],
        "&END GLOBAL": ["entity.name.section.end.cp2k"],
    }

    for line, expected_scopes in samples.items():
        scopes = _scopes_for(line)
        for expected_scope in expected_scopes:
            assert expected_scope in scopes, line


def test_grammar_handles_malformed_but_editable_input():
    partial_samples = {
        "&END": ["entity.name.section.end.cp2k"],
        "@IF ${COND": ["keyword.control.preprocessor.cp2k"],
        "  COORD_FILE_NAME ./coords.xyz ! trailing": [
            "support.type.property-name.cp2k",
            "string.unquoted.path.cp2k",
            "comment.line.inline.cp2k",
        ],
    }

    for line, expected_scopes in partial_samples.items():
        scopes = _scopes_for(line)
        for expected_scope in expected_scopes:
            assert expected_scope in scopes, line
