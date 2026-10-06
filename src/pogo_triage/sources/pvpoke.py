"""PvPoke Great, Ultra and Master League rankings: fetch, validate, cache."""

import json
import logging
import os
from pathlib import Path

import httpx

from pogo_triage.sources import (
    SchemaError,
    default_cache_dir,
    fetch_text,
    load_sources_config,
    make_client,
    read_cache,
    require_fields,
    write_cache,
)

logger = logging.getLogger(__name__)

LEAGUES = ("great", "ultra", "master")
_REQUIRED = {"speciesId": str, "speciesName": str, "score": (int, float), "moveset": list}

Rankings = dict[str, dict[str, dict]]


def _url(league: str, config: dict) -> str:
    override = os.environ.get(f"POGO_PVPOKE_{league.upper()}_URL")
    return override or config["pvpoke"][league]


def parse_league(text: str, league: str) -> dict[str, dict]:
    """Validate one league's JSON and key its entries by species ID."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"{league} league: invalid JSON") from exc
    if not isinstance(data, list):
        raise SchemaError(f"{league} league: expected a list of rankings")
    ranked: dict[str, dict] = {}
    for position, entry in enumerate(data):
        require_fields(entry, _REQUIRED, f"{league} league entry {position}")
        ranked[entry["speciesId"]] = entry
    return ranked


def fetch_rankings(
    client: httpx.Client | None = None,
    cache_dir: Path | None = None,
    offline: bool = False,
    config: dict | None = None,
) -> Rankings:
    """Return all three leagues keyed by species ID.

    Online, each file is validated and then written to the cache. Offline, only the cache is read
    and no request is made.
    """
    cache_dir = cache_dir or default_cache_dir()
    config = config or load_sources_config()
    owns_client = client is None and not offline
    if owns_client:
        client = make_client()
    try:
        rankings: Rankings = {}
        for league in LEAGUES:
            name = f"pvpoke_{league}.json"
            if offline:
                text = read_cache(cache_dir, name)
            else:
                text = fetch_text(client, _url(league, config))
            rankings[league] = parse_league(text, league)
            if not offline:
                write_cache(cache_dir, name, text)
            logger.info("%s league: %d entries", league, len(rankings[league]))
        return rankings
    finally:
        if owns_client:
            client.close()
