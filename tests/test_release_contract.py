from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_newtontech_distribution_identity_and_compatibility_command() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    poetry = metadata["tool"]["poetry"]

    assert poetry["name"] == "cp2k-lsp-enhanced"
    assert poetry["version"] == "0.1.1"
    assert poetry["repository"] == "https://github.com/newtontech/cp2k-lsp-enhanced"
    assert poetry["scripts"]["cp2k-language-server"] == ("cp2k_input_tools.cli.lsp:cp2k_language_server")
    assert poetry["scripts"]["cp2k-lsp-tool"] == "cp2k_input_tools.tool:main"


def test_pypi_release_uses_oidc_and_protected_environment() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")

    assert "name: pypi" in workflow
    assert "id-token: write" in workflow
    assert "PYPI_TOKEN" not in workflow
    assert "pypa/gh-action-pypi-publish@" in workflow
