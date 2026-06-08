"""Main CLI entry point for the CP2K LSP enhanced tool.

Provides the `cp2k-lsp` command with subcommands for agent workflows.
"""

import click

from .agent_inspect import cli as inspect_cli


@click.group()
def cp2k_lsp():
    """CP2K LSP enhanced CLI — language server tools and agent workflows."""
    pass


cp2k_lsp.add_command(inspect_cli, name="inspect")


if __name__ == "__main__":
    cp2k_lsp()
