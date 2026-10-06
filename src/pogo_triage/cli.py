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
from pogo_triage.sources import SourceError
from pogo_triage.sources.pvpoke import fetch_rankings


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


@main.command()
@click.option("--offline", is_flag=True, help="Read only the cache; make no requests.")
@click.option(
    "--cache-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Cache directory (default: $POGO_CACHE_DIR or .cache/pogo-triage).",
)
def fetch(offline: bool, cache_dir: Path | None) -> None:
    """Fetch upstream data into the cache and print summary counts."""
    try:
        rankings = fetch_rankings(cache_dir=cache_dir, offline=offline)
    except SourceError as exc:
        raise click.ClickException(str(exc)) from exc
    for league, entries in rankings.items():
        click.echo(f"pvpoke {league}: {len(entries)} entries")
