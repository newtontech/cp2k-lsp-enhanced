"""Main CLI entry point for the CP2K LSP enhanced tool.

Provides the `cp2k-lsp` command with subcommands for agent workflows.
"""

import click

from .agent_inspect import cli as inspect_cli
from .context import context
from .diagnostics import cp2k_check


@click.group()
def cp2k_lsp():
    """CP2K LSP enhanced CLI — language server tools and agent workflows."""
    pass


cp2k_lsp.add_command(inspect_cli, name="inspect")
cp2k_lsp.add_command(context, name="context")
cp2k_lsp.add_command(cp2k_check, name="check")


if __name__ == "__main__":
    cp2k_lsp()
