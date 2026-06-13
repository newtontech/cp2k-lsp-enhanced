"""Validation backend registry for CP2K LSP/OpenQC consumers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationBackend:
    """Machine-readable validation backend descriptor."""

    id: str
    kind: str
    mode: str
    status: str
    operations: tuple[str, ...]
    command: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["operations"] = list(self.operations)
        payload["command"] = list(self.command)
        return payload


VALIDATION_BACKENDS: tuple[ValidationBackend, ...] = (
    ValidationBackend(
        id="cp2k-lsp-tool-static",
        kind="open_source",
        mode="static",
        status="available",
        operations=("check", "context", "complete", "hover", "symbols", "fix"),
        command=("cp2k-lsp-tool", "check"),
        notes="Local CP2K parser, linter, typecheck, and DiagnosticEnvelope/v1 checks.",
    ),
    ValidationBackend(
        id="cp2k-log-parser",
        kind="open_source",
        mode="log",
        status="available",
        operations=("check",),
        command=("cp2k-lsp-tool", "check"),
        notes="Local CP2K output-log diagnostics are exposed through the same check envelope when log fixtures are supplied.",
    ),
    ValidationBackend(
        id="cp2k-commercial-static-parser",
        kind="commercial_placeholder",
        mode="static",
        status="unavailable",
        operations=(),
        notes="Reserved backend slot for commercial static validators; no paid or remote job is launched by this repo.",
    ),
    ValidationBackend(
        id="cp2k-commercial-log-parser",
        kind="commercial_placeholder",
        mode="log",
        status="unavailable",
        operations=(),
        notes="Reserved backend slot for commercial runtime-log parsers; no credentials or remote service are required.",
    ),
)


def validation_backends_payload() -> list[dict[str, Any]]:
    """Return the stable validation backend registry payload."""
    return [backend.to_dict() for backend in VALIDATION_BACKENDS]
