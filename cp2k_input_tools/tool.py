"""Agent-facing CLI for Diagnostic Engine v1 operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .agent_operations import OPERATIONS
from .rich_diagnostics import agent_check_payload
from .validation_backends import validation_backends_payload

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
        "validationBackends": validation_backends_payload(),
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


def _completion_payload(path: Path, line: int, character: int) -> dict[str, Any]:
    from cp2k_input_tools.cli.tool import _get_completions

    payload = _empty_operation(path, "complete")
    payload["summary"].pop("note", None)
    payload["items"] = _get_completions(str(path), line, character)["items"]
    payload["is_incomplete"] = False
    return payload


def _hover_payload(path: Path, line: int, character: int) -> dict[str, Any]:
    from cp2k_lsp.agent_api.schema import (  # type: ignore[import-untyped]
        lookup_keyword_at_path,
        lookup_keyword_schema,
        lookup_section_schema,
    )
    from cp2k_lsp.features.hover import HoverProvider  # type: ignore[import-untyped]

    from cp2k_input_tools.cursor_context import resolve_cursor_context

    payload = _empty_operation(path, "hover")
    payload["summary"].pop("note", None)
    text = path.read_text(encoding="utf-8")
    ctx = resolve_cursor_context(text=text, line=line, character=character, uri=path.resolve().as_uri())
    word = (ctx.current_keyword or ctx.current_section or "").upper()
    section_path = ".".join(ctx.section_path) if ctx.section_path else None

    provider = HoverProvider(server=object())
    content = None
    if word:
        keyword_schema = lookup_keyword_at_path(section_path, word) if section_path else None
        if keyword_schema is None:
            keyword_schema = lookup_keyword_schema(word)
        if keyword_schema:
            content = provider._format_keyword_hover(keyword_schema)
        else:
            section_schema = lookup_section_schema(word)
            if section_schema:
                content = provider._format_section_hover(section_schema)

    payload["hover"] = {
        "contents": content or "No documentation available",
        "keyword": ctx.current_keyword,
        "section_path": list(ctx.section_path),
    }
    return payload


def _explain_payload(name: str) -> dict[str, Any]:
    from cp2k_lsp.agent_api.schema import lookup_keyword_schema, lookup_section_schema  # type: ignore[import-untyped]
    from cp2k_lsp.features.hover import HoverProvider  # type: ignore[import-untyped]

    query = name.upper()
    provider = HoverProvider(server=object())
    content = None
    kind = None

    keyword_schema = lookup_keyword_schema(query)
    if keyword_schema:
        content = provider._format_keyword_hover(keyword_schema)
        kind = "keyword"
    else:
        section_schema = lookup_section_schema(query)
        if section_schema:
            content = provider._format_section_hover(section_schema)
            kind = "section"

    return {
        "software": SOFTWARE,
        "status": "available" if content else "not_found",
        "operation": "explain",
        "query": query,
        "kind": kind,
        "contents": content or f"No CP2K schema documentation found for {query}.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cp2k-lsp-tool")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    capabilities = subparsers.add_parser("capabilities")
    capabilities.add_argument("--format", choices=["json"], default="json")
    index_regenerate = subparsers.add_parser("index-regenerate")
    index_regenerate.add_argument("--release-version", default=None)
    index_regenerate.add_argument("--format", choices=["json"], default="json")
    for operation in ("check", "context", "complete", "hover", "symbols", "fix"):
        sub = subparsers.add_parser(operation)
        sub.add_argument("path", type=Path)
        sub.add_argument("--format", choices=["json"], default="json")
        if operation == "check":
            sub.add_argument("--fail-on-blocking", action="store_true")
        if operation in {"context", "complete", "hover", "fix"}:
            sub.add_argument("--line", type=int, default=0)
            sub.add_argument("--character", type=int, default=0)
    explain = subparsers.add_parser("explain")
    explain.add_argument("name")
    explain.add_argument("--format", choices=["json"], default="json")
    args = parser.parse_args(argv)
    if args.operation == "capabilities":
        print(json.dumps(_capabilities_payload(), indent=2, sort_keys=True))
        return 0
    if args.operation == "index-regenerate":
        from .precomputed_index import regenerate_indexes

        payload = regenerate_indexes(release_version=args.release_version)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.operation == "check":
        payload = check_path(args.path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if getattr(args, "fail_on_blocking", False) and not payload["ok"] else 0
    if args.operation == "context":
        from cp2k_lsp.agent_commands import run_context  # type: ignore[import-untyped]

        payload = run_context(arguments=[{"path": str(args.path), "line": args.line, "character": args.character}])
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.operation == "symbols":
        from cp2k_lsp.agent_commands import run_symbols  # type: ignore[import-untyped]

        payload = run_symbols(arguments=[{"path": str(args.path)}])
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.operation == "fix":
        from cp2k_lsp.agent_commands import run_fix_preview  # type: ignore[import-untyped]

        payload = run_fix_preview(arguments=[{"path": str(args.path), "line": args.line, "character": args.character}])
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.operation == "complete":
        print(json.dumps(_completion_payload(args.path, args.line, args.character), indent=2, sort_keys=True))
        return 0
    if args.operation == "hover":
        print(json.dumps(_hover_payload(args.path, args.line, args.character), indent=2, sort_keys=True))
        return 0
    if args.operation == "explain":
        print(json.dumps(_explain_payload(args.name), indent=2, sort_keys=True))
        return 0
    print(json.dumps(_empty_operation(args.path, args.operation), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
