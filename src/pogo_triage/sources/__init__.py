"""Shared fetch, cache and schema helpers for upstream public JSON sources."""

import logging
import os
import tomllib
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

SOURCES_ENV = "POGO_SOURCES_CONFIG"
CACHE_ENV = "POGO_CACHE_DIR"
DEFAULT_SOURCES_PATH = Path(__file__).resolve().parents[3] / "config" / "sources.toml"
DEFAULT_CACHE_DIR = Path(".cache") / "pogo-triage"
TIMEOUT_SECONDS = 30.0


class SourceError(Exception):
    """An upstream source could not be fetched or read from cache."""


class SchemaError(SourceError):
    """Upstream JSON does not have the expected shape."""


class CacheMissError(SourceError):
    """Offline mode was requested but the cache does not hold the file."""


def load_sources_config(path: Path | None = None) -> dict:
    """Load source defaults from `path`, else $POGO_SOURCES_CONFIG, else the bundled config."""
    if path is None:
        env = os.environ.get(SOURCES_ENV)
        path = Path(env) if env else DEFAULT_SOURCES_PATH
    with path.open("rb") as fh:
        return tomllib.load(fh)


def default_cache_dir() -> Path:
    env = os.environ.get(CACHE_ENV)
    return Path(env) if env else DEFAULT_CACHE_DIR


def make_client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True)


def fetch_text(client: httpx.Client, url: str) -> str:
    """GET `url` and return the body. Messages carry the status only, never the URL query."""
    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise SourceError(f"upstream returned HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise SourceError(f"upstream request failed: {type(exc).__name__}") from exc
    return response.text


def read_cache(cache_dir: Path, name: str) -> str:
    path = cache_dir / name
    if not path.is_file():
        raise CacheMissError(f"cache is empty ({name} missing); run without --offline first")
    return path.read_text(encoding="utf-8")


def write_cache(cache_dir: Path, name: str, text: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / name).write_text(text, encoding="utf-8")


def require_fields(entry: object, fields: dict[str, type | tuple[type, ...]], where: str) -> None:
    """Raise SchemaError naming the first missing or mistyped field in `entry`."""
    if not isinstance(entry, dict):
        raise SchemaError(f"{where}: entry is not an object")
    for name, expected in fields.items():
        if name not in entry:
            raise SchemaError(f"{where}: missing required field '{name}'")
        value = entry[name]
        if isinstance(value, bool) or not isinstance(value, expected):
            raise SchemaError(f"{where}: field '{name}' has the wrong type")
