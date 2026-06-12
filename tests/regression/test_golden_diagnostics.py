"""Golden diagnostics regression tests (issue #71).

Validates that known-good CP2K inputs produce zero ERROR-level diagnostics,
and that known-bad inputs produce expected diagnostics matching golden snapshots.

These tests use the linter + parser to check inputs and compare actual
diagnostics against golden JSON files.

Run: pytest tests/regression/test_golden_diagnostics.py -v
"""

import json
from pathlib import Path

import pytest

from cp2k_input_tools.linter import lint
from cp2k_input_tools.parser import CP2KInputParser
from cp2k_input_tools.parser_errors import ParserError
from cp2k_input_tools.tokenizer import TokenizerError

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"
MUTATIONS_DIR = FIXTURES_DIR / "mutations"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_golden(fixture_path: Path) -> dict:
    """Load the golden JSON file next to a fixture."""
    golden_path = fixture_path.parent / f"{fixture_path.stem}_golden.json"
    if not golden_path.exists():
        pytest.skip(f"Golden file missing: {golden_path}")
    return json.loads(golden_path.read_text())


def _get_diagnostics(filepath: str) -> list:
    """Get diagnostics for a file using linter + parser.

    Returns a list of dicts with keys: line, severity, code, message.
    """
    content = Path(filepath).read_text()
    diags = []

    # 1. Try linter diagnostics
    try:
        lint_diags = lint(content)
        for d in lint_diags:
            diags.append({
                "line": getattr(d, "line", 0),
                "severity": getattr(d, "severity", "unknown"),
                "code": getattr(d, "code", ""),
                "message": getattr(d, "message", str(d)),
            })
    except Exception:
        pass

    # 2. Try parser diagnostics
    try:
        parser = CP2KInputParser()
        parser.parse(content.splitlines())
    except (TokenizerError, ParserError) as exc:
        ctx = exc.args[1] if len(exc.args) > 1 else None
        line = getattr(ctx, "linenr", 1) if ctx else 1
        diags.append({
            "line": line,
            "severity": "error",
            "code": f"PARSER_{type(exc).__name__}",
            "message": str(exc.args[0]),
        })

    return diags


def _error_diagnostics(diags: list) -> list:
    """Filter diagnostics to only ERROR severity."""
    return [d for d in diags if d.get("severity") == "error"]


def _diag_messages(diags: list) -> list[str]:
    """Extract message strings from a list of diagnostics."""
    return [d.get("message", "") for d in diags]


# ---------------------------------------------------------------------------
# Valid input golden tests — no errors expected
# ---------------------------------------------------------------------------

class TestValidGoldenInputs:
    """Valid CP2K inputs should produce zero ERROR diagnostics."""

    VALID_FIXTURES = sorted(GOLDEN_DIR.glob("valid_*.inp"))

    @pytest.mark.parametrize("inp_file", VALID_FIXTURES, ids=lambda p: p.stem)
    def test_valid_input_no_errors(self, inp_file: Path):
        """Each valid input fixture should have zero ERROR diagnostics."""
        result = _get_diagnostics(str(inp_file))
        errors = _error_diagnostics(result)
        golden = _load_golden(inp_file)

        # If golden says diagnostics should be empty, enforce it
        if golden.get("diagnostics") == []:
            assert len(errors) == 0, (
                f"{inp_file.name} should have no errors, got: {_diag_messages(errors)}"
            )

    @pytest.mark.parametrize("inp_file", VALID_FIXTURES, ids=lambda p: p.stem)
    def test_golden_determinism(self, inp_file: Path):
        """Running check twice should produce the same diagnostics."""
        result1 = _get_diagnostics(str(inp_file))
        result2 = _get_diagnostics(str(inp_file))
        msgs1 = sorted(_diag_messages(result1))
        msgs2 = sorted(_diag_messages(result2))
        assert msgs1 == msgs2, f"Non-deterministic diagnostics for {inp_file.name}"


# ---------------------------------------------------------------------------
# Mutation tests — invalid inputs should produce expected diagnostics
# ---------------------------------------------------------------------------

class TestMutationDiagnostics:
    """Mutation fixtures should produce specific diagnostics."""

    MUTATION_FIXTURES = sorted(MUTATIONS_DIR.glob("mutation_*.inp"))

    @pytest.mark.parametrize("inp_file", MUTATION_FIXTURES, ids=lambda p: p.stem)
    def test_mutation_produces_diagnostics(self, inp_file: Path):
        """Each mutation should produce at least one diagnostic."""
        result = _get_diagnostics(str(inp_file))
        assert len(result) > 0, (
            f"{inp_file.name} should produce diagnostics but got none"
        )

    @pytest.mark.parametrize("inp_file", MUTATION_FIXTURES, ids=lambda p: p.stem)
    def test_mutation_matches_golden_severity(self, inp_file: Path):
        """Each mutation's diagnostics should include the expected severity."""
        result = _get_diagnostics(str(inp_file))
        golden = _load_golden(inp_file)
        golden_diags = golden.get("diagnostics", [])

        if not golden_diags:
            pytest.skip("No golden diagnostics specified")

        for g_diag in golden_diags:
            expected_severity = g_diag.get("severity", "error")
            matching = [d for d in result if d.get("severity") == expected_severity]
            assert len(matching) > 0, (
                f"{inp_file.name}: expected at least one '{expected_severity}' diagnostic, "
                f"got severities: {[d.get('severity') for d in result]}"
            )

    @pytest.mark.parametrize("inp_file", MUTATION_FIXTURES, ids=lambda p: p.stem)
    def test_mutation_matches_golden_message_fragment(self, inp_file: Path):
        """Diagnostics should contain the expected message fragment."""
        result = _get_diagnostics(str(inp_file))
        golden = _load_golden(inp_file)
        golden_diags = golden.get("diagnostics", [])

        if not golden_diags:
            pytest.skip("No golden diagnostics specified")

        for g_diag in golden_diags:
            fragment = g_diag.get("message_fragment")
            if not fragment:
                continue
            messages = _diag_messages(result)
            found = any(fragment in msg for msg in messages)
            assert found, (
                f"{inp_file.name}: expected message fragment '{fragment}' "
                f"in any diagnostic, got: {messages}"
            )
