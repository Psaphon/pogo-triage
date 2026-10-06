"""Command-line interface."""

import logging
from pathlib import Path

import click

from pogo_triage import __version__
from pogo_triage.pokegenie import (
    PokeGenieError,
    load_column_config,
    parse_file,
    summarize,
)


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


@main.command()
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--columns",
    "columns_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Column alias config (default: config/pokegenie_columns.toml).",
)
def parse(csv_path: Path, columns_path: Path | None) -> None:
    """Parse a Poke Genie CSV export and print summary counts."""
    try:
        records = parse_file(csv_path, load_column_config(columns_path))
    except PokeGenieError as exc:
        raise click.ClickException(str(exc)) from exc
    counts = summarize(records)
    click.echo(f"{counts.pop('total')} records")
    for name, count in counts.items():
        click.echo(f"{name}: {count}")
