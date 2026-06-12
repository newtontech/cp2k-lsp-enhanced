"""Machine-readable code-intelligence CLI API for agent workflows.

Provides JSON output for diagnostics, hover, references, formatting preview,
and code actions — consumable by Claude Code, OpenCode, Codex, and other agents.
"""

import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import click

from cp2k_input_tools.parser import CP2KInputParser, Section
from cp2k_input_tools.parser_errors import ParserError
from cp2k_input_tools.tokenizer import TokenizerError


@dataclass
class DiagRange:
    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass
class Diagnostic:
    severity: str  # "error" | "warning" | "info"
    source: str  # "cp2k-parser" | "cp2k-schema" | "cp2k-lint"
    code: str
    message: str
    range: DiagRange


@dataclass
class DiagnosticsResult:
    file: str
    diagnostics: List[Diagnostic] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "warning")


@dataclass
class DeltaResult:
    before_file: str
    after_file: str
    before_count: int
    after_count: int
    fixed_count: int
    new_count: int
    unchanged_count: int


def parse_file_to_diagnostics(file_path: str, base_dir: str = ".") -> DiagnosticsResult:
    """Parse a CP2K input file and return structured diagnostics."""
    parser = CP2KInputParser(base_dir=base_dir)
    diagnostics: List[Diagnostic] = []

    try:
        with open(file_path, "r") as fhandle:
            parser.parse(fhandle)
    except (TokenizerError, ParserError) as exc:
        ctx = exc.args[1]
        colnr = ctx.colnr or 0
        diagnostics.append(
            Diagnostic(
                severity="error",
                source="cp2k-parser",
                code=f"E{type(exc).__name__}",
                message=str(exc.args[0]),
                range=DiagRange(
                    start_line=ctx.linenr - 1,
                    start_col=colnr,
                    end_line=ctx.linenr - 1,
                    end_col=colnr + 1,
                ),
            )
        )

    return DiagnosticsResult(file=file_path, diagnostics=diagnostics)


def compute_delta(before_path: str, after_path: str) -> DeltaResult:
    """Compute diagnostics delta between two JSON diagnostic snapshots."""
    with open(before_path, "r") as f:
        before = json.load(f)
    with open(after_path, "r") as f:
        after = json.load(f)

    before_msgs = {d["message"] for d in before.get("diagnostics", [])}
    after_msgs = {d["message"] for d in after.get("diagnostics", [])}

    fixed = before_msgs - after_msgs
    new_msgs = after_msgs - before_msgs
    unchanged = before_msgs & after_msgs

    return DeltaResult(
        before_file=before_path,
        after_file=after_path,
        before_count=len(before_msgs),
        after_count=len(after_msgs),
        fixed_count=len(fixed),
        new_count=len(new_msgs),
        unchanged_count=len(unchanged),
    )


def get_hover_info(file_path: str, line: int, character: int) -> Optional[Dict[str, Any]]:
    """Return hover information for the token at the given position."""
    parser = CP2KInputParser()

    try:
        with open(file_path, "r") as fhandle:
            parser.parse(fhandle)
    except (TokenizerError, ParserError):
        return None

    # Walk the section tree to find the section containing the line
    def find_section_at_line(section: Section, target_line: int, lines: List[str]) -> Optional[Section]:
        # Approximate: find deepest section whose start is before the line
        for sub in section.subsections:
            candidate = find_section_at_line(sub, target_line, lines)
            if candidate:
                return candidate
        return section

    # Try to get line content for basic keyword detection
    try:
        with open(file_path, "r") as fhandle:
            lines = fhandle.readlines()
    except (IOError, OSError):
        return None

    if 0 < line <= len(lines):
        target_line = lines[line - 1].strip()
        # Check if line looks like a keyword
        import re

        kw_match = re.match(r"&?(\w+)", target_line)
        if kw_match:
            name = kw_match.group(1).upper()
            # Look up in schema
            return {"name": name, "line": line, "position": character, "contents": f"Keyword/Section: {name}"}

    return None


def get_references(file_path: str, line: int, character: int) -> List[Dict[str, Any]]:
    """Find all references to the variable at the given position."""
    try:
        with open(file_path, "r") as fhandle:
            content = fhandle.read()
    except (IOError, OSError):
        return []

    lines = content.split("\n")
    if 0 < line <= len(lines):
        target_line = lines[line - 1].strip()
        import re

        # Check for @SET or $VAR
        set_match = re.match(r"@SET\s+(\w+)", target_line)
        if set_match:
            var_name = set_match.group(1)
            refs = []
            for i, line_text in enumerate(lines, 1):
                if f"${var_name}" in line_text or f"@SET {var_name}" in line_text:
                    refs.append({"file": file_path, "line": i, "text": line_text.strip()})
            return refs

        # Check if cursor is on a $VAR usage
        var_match = re.findall(r"\$(\w+)", target_line)
        if var_match:
            # Find the variable at the cursor position
            for var_name in var_match:
                refs = []
                for i, line_text in enumerate(lines, 1):
                    if f"${var_name}" in line_text or f"@SET {var_name}" in line_text:
                        refs.append({"file": file_path, "line": i, "text": line_text.strip()})
                return refs

    return []


def format_preview(file_path: str) -> str:
    """Return formatted version of the file without modifying it."""
    try:
        with open(file_path, "r") as fhandle:
            lines = fhandle.readlines()
    except (IOError, OSError) as e:
        return f"Error reading file: {e}"

    formatted = []
    depth = 0
    indent = "  "

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("!"):
            formatted.append(stripped)
            continue

        upper = stripped.upper()
        if upper.startswith("&END") or upper.startswith("&_END"):
            depth = max(0, depth - 1)

        formatted.append(f"{indent * depth}{stripped}")

        if upper.startswith("&") and not upper.startswith("&END") and not upper.startswith("&_END"):
            depth += 1

    return "\n".join(formatted) + "\n"


def get_code_actions(file_path: str, line: int, character: int) -> List[Dict[str, Any]]:
    """Return suggested code actions for the given position."""
    actions: List[Dict[str, Any]] = []
    try:
        with open(file_path, "r") as fhandle:
            lines = fhandle.readlines()
    except (IOError, OSError):
        return actions

    if 0 < line <= len(lines):
        target_line = lines[line - 1].strip().upper()

        if target_line.startswith("&END"):
            actions.append(
                {
                    "title": "Verify &END section name matches opening section",
                    "kind": "quickfix",
                    "description": "Ensure the section name after &END matches the corresponding &SECTION name",
                }
            )

    return actions


# CLI commands


@click.group()
def cli():
    """Machine-readable code-intelligence API for agent workflows."""
    pass


@cli.group()
def inspect():
    """Inspect CP2K input files and return JSON results."""
    pass


@inspect.command("diagnostics")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--base-dir", default=".", help="Base directory for @INCLUDE resolution")
@click.option("--fail-on-error", is_flag=True, help="Exit non-zero if any errors found")
def inspect_diagnostics(file_path, base_dir, fail_on_error):
    """Return diagnostics for a CP2K input file as JSON."""
    result = parse_file_to_diagnostics(file_path, base_dir)
    output = {
        "file": result.file,
        "diagnostics": [asdict(d) for d in result.diagnostics],
        "error_count": result.error_count,
        "warning_count": result.warning_count,
    }
    click.echo(json.dumps(output, indent=2))
    if fail_on_error and result.error_count > 0:
        sys.exit(1)


@inspect.command("diagnostics-delta")
@click.argument("before_path", type=click.Path(exists=True))
@click.argument("after_path", type=click.Path(exists=True))
def inspect_diagnostics_delta(before_path, after_path):
    """Compare two diagnostic snapshots and return delta as JSON."""
    result = compute_delta(before_path, after_path)
    click.echo(json.dumps(asdict(result), indent=2))


@inspect.command("hover")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--line", "-l", type=int, required=True, help="1-based line number")
@click.option("--character", "-c", type=int, required=True, help="0-based character position")
def inspect_hover(file_path, line, character):
    """Return hover information for the token at position as JSON."""
    info = get_hover_info(file_path, line, character)
    if info:
        click.echo(json.dumps(info, indent=2))
    else:
        click.echo(json.dumps({"message": "No hover information available at this position"}))


@inspect.command("references")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--line", "-l", type=int, required=True, help="1-based line number")
@click.option("--character", "-c", type=int, required=True, help="0-based character position")
def inspect_references(file_path, line, character):
    """Find all references to the symbol at position as JSON."""
    refs = get_references(file_path, line, character)
    click.echo(json.dumps({"references": refs, "count": len(refs)}, indent=2))


@inspect.command("format-preview")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--apply", is_flag=True, help="Apply formatting to the file (default: preview only)")
def inspect_format_preview(file_path, apply):
    """Preview formatting for a CP2K input file without modifying it."""
    formatted = format_preview(file_path)
    if apply:
        with open(file_path, "w") as fhandle:
            fhandle.write(formatted)
        click.echo(json.dumps({"status": "applied", "file": file_path}))
    else:
        click.echo(json.dumps({"formatted": formatted, "file": file_path}))


@inspect.command("code-actions")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--line", "-l", type=int, required=True, help="1-based line number")
@click.option("--character", "-c", type=int, required=True, help="0-based character position")
def inspect_code_actions(file_path, line, character):
    """Return suggested code actions for the position as JSON."""
    actions = get_code_actions(file_path, line, character)
    click.echo(json.dumps({"actions": actions, "count": len(actions)}, indent=2))


if __name__ == "__main__":
    cli()
