"""Agent-facing CLI for Diagnostic Engine v1 operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .agent_operations import operation_path, with_capabilities
from .rich_diagnostics import agent_check_payload

SOFTWARE = "cp2k"


def _file_type(path: Path) -> str:
    name = path.name.upper()
    if name in {"INCAR", "POSCAR", "KPOINTS", "POTCAR", "CONTCAR"}:
        return name
    if "." in path.name:
        return path.suffix.lstrip(".").lower()
    return name.lower()


def _collect_diagnostics(path: Path) -> list[Any]:
    text = path.read_text(encoding="utf-8")
    diagnostics: list[Any] = []
    from .linter import lint as static_lint
    from .parser import CP2KInputParser
    from .typecheck import validate_text

    try:
        with path.open("r", encoding="utf-8") as fhandle:
            CP2KInputParser().parse(fhandle)
    except Exception as exc:
        diagnostics.append(
            {
                "code": f"E{type(exc).__name__}",
                "severity": "error",
                "source": "cp2k-parser",
                "message": str(exc),
                "line": 1,
                "column": 1,
                "category": "syntax",
                "confidence": 1.0,
                "blocking": True,
            }
        )
    diagnostics.extend(static_lint(text))
    diagnostics.extend(validate_text(text))
    return diagnostics


def check_path(path: Path) -> dict[str, Any]:
    uri = path.resolve().as_uri()
    diagnostics = _collect_diagnostics(path)
    return agent_check_payload(
        software=SOFTWARE,
        uri=uri,
        operation="check",
        diagnostics=diagnostics,
        path=str(path),
        file_type=_file_type(path),
    )



def _operation_payload(path: Path, operation: str, line: int = 0, character: int = 0) -> dict[str, Any]:
    return operation_path(
        path,
        operation,
        software=SOFTWARE,
        file_type_func=_file_type,
        collect_diagnostics=_collect_diagnostics,
        line=line,
        character=character,
    )

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cp2k-lsp-tool")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("check", "context", "complete", "hover", "symbols", "fix"):
        sub = subparsers.add_parser(operation)
        sub.add_argument("path", type=Path)
        sub.add_argument("--format", choices=["json"], default="json")
        sub.add_argument("--line", type=int, default=0, help="0-based line for position-aware operations.")
        sub.add_argument("--character", type=int, default=0, help="0-based character for position-aware operations.")
        if operation == "check":
            sub.add_argument("--fail-on-blocking", action="store_true")
    caps_sub = subparsers.add_parser("capabilities")
    caps_sub.add_argument("--format", choices=["json"], default="json")
    args = parser.parse_args(argv)
    if args.operation == "capabilities":
        from .agent_operations import OPERATIONS
        payload = {
            "software": SOFTWARE,
            "status": "available",
            "capabilities": {
                "operations": list(OPERATIONS),
                "operation": "capabilities",
                "status": "available",
                "source": "cp2k-lsp-tool",
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.operation == "check":
        payload = with_capabilities(check_path(args.path), "check")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if getattr(args, "fail_on_blocking", False) and not payload["ok"] else 0
    payload = _operation_payload(args.path, args.operation, args.line, args.character)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
