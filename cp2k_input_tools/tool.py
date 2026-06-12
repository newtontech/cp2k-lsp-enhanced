"""Agent-facing CLI for Diagnostic Engine v1 operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .agent_operations import OPERATIONS
from .rich_diagnostics import agent_check_payload

SOFTWARE = "cp2k"


def _capabilities_payload() -> dict[str, Any]:
    return {
        "software": SOFTWARE,
        "status": "available",
        "capabilities": {
            "operations": list(OPERATIONS),
            "operation": "capabilities",
            "status": "available",
            "source": "cp2k-lsp-tool",
        },
    }


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
    from .version_policy import lint_version_policy_from_env

    diagnostics.extend(lint_version_policy_from_env(text))

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


def _empty_operation(path: Path, operation: str) -> dict[str, Any]:
    payload = agent_check_payload(
        software=SOFTWARE,
        uri=path.resolve().as_uri(),
        operation=operation,
        diagnostics=[],
        path=str(path),
        file_type=_file_type(path),
    )
    payload["summary"]["note"] = f"{operation} is reserved by the Diagnostic Engine v1 CLI contract"
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cp2k-lsp-tool")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    capabilities = subparsers.add_parser("capabilities")
    capabilities.add_argument("--format", choices=["json"], default="json")
    for operation in ("check", "context", "complete", "hover", "symbols", "fix"):
        sub = subparsers.add_parser(operation)
        sub.add_argument("path", type=Path)
        sub.add_argument("--format", choices=["json"], default="json")
        if operation == "check":
            sub.add_argument("--fail-on-blocking", action="store_true")
    args = parser.parse_args(argv)
    if args.operation == "capabilities":
        print(json.dumps(_capabilities_payload(), indent=2, sort_keys=True))
        return 0
    if args.operation == "check":
        payload = check_path(args.path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if getattr(args, "fail_on_blocking", False) and not payload["ok"] else 0
    print(json.dumps(_empty_operation(args.path, args.operation), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
