"""Golden file comparison utilities for CP2K LSP regression testing."""

import json
import pathlib
from typing import Any, Dict, List, Optional

FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"


def load_golden(name: str) -> Dict[str, Any]:
    """Load a golden fixture JSON file."""
    path = FIXTURES_DIR / f"{name}.json"
    with open(path) as f:
        return json.load(f)


def save_golden(name: str, data: Dict[str, Any]) -> None:
    """Save data as a golden fixture JSON file."""
    path = FIXTURES_DIR / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def normalize_diagnostics(diagnostics: List[Any]) -> List[Dict[str, Any]]:
    """Normalize diagnostic objects for golden comparison.

    Strips non-deterministic fields and keeps:
    - range (start/end line/character)
    - message (trimmed)
    - severity
    - source
    - code (if present)
    """
    result = []
    for d in diagnostics:
        entry = {}
        if hasattr(d, "range"):
            entry["range"] = {
                "start": {"line": d.range.start.line, "character": d.range.start.character},
                "end": {"line": d.range.end.line, "character": d.range.end.character},
            }
        if hasattr(d, "message"):
            # Trim to first 200 chars for stability
            entry["message"] = d.message[:200]
        if hasattr(d, "severity") and d.severity is not None:
            entry["severity"] = int(d.severity)
        if hasattr(d, "source") and d.source:
            entry["source"] = d.source
        if hasattr(d, "code") and d.code:
            entry["code"] = str(d.code)
        result.append(entry)
    return result


def normalize_text_edits(edits: List[Any]) -> List[Dict[str, Any]]:
    """Normalize TextEdit objects for golden comparison."""
    result = []
    for e in edits:
        entry = {}
        if hasattr(e, "range"):
            entry["range"] = {
                "start": {"line": e.range.start.line, "character": e.range.start.character},
                "end": {"line": e.range.end.line, "character": e.range.end.character},
            }
        if hasattr(e, "new_text"):
            entry["new_text"] = e.new_text
        result.append(entry)
    return result


def assert_golden(name: str, actual: List[Any], *, update: bool = False) -> None:
    """Compare actual diagnostics/edits against golden file.

    If update=True, the golden file is rewritten with current actual data.
    """
    normalized = normalize_diagnostics(actual) if actual else []
    if update:
        save_golden(name, {"items": normalized})
        return

    golden = load_golden(name)
    golden_items = golden.get("items", [])
    if normalized != golden_items:
        import json
        import difflib
        actual_str = json.dumps(normalized, indent=2, sort_keys=True)
        golden_str = json.dumps(golden_items, indent=2, sort_keys=True)
        diff = '\n'.join(difflib.unified_diff(
            golden_str.splitlines(), actual_str.splitlines(),
            fromfile='golden', tofile='actual', lineterm=''
        ))
        raise AssertionError(
            f"Golden mismatch for {name}.json.\n"
            f"Expected {len(golden_items)} items, got {len(normalized)} items.\n"
            f"Diff:\n{diff}"
        )
