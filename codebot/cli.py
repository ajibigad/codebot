"""CLI interface for codebot."""

import click
from dotenv import load_dotenv

from codebot.cli_runner.runner import run
from codebot.server.app import serve


@click.group()
def cli():
    """Codebot CLI - AI-assisted development task automation."""
    load_dotenv()


# Register commands
cli.add_command(run)
cli.add_command(serve)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
