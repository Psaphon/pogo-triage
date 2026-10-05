"""Command-line interface."""

import logging

import click

from pogo_triage import __version__


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def main(verbose: bool) -> None:
    """Score a Poke Genie export and build a triage report."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


@main.command()
def version() -> None:
    """Print the installed version."""
    click.echo(__version__)
