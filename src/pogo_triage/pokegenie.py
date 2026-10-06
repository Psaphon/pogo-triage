"""Header-mapped parsing and validation of Poke Genie CSV exports."""

import csv
import logging
import os
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pogo_triage.models import PokemonRecord

logger = logging.getLogger(__name__)

COLUMNS_ENV = "POGO_COLUMNS_CONFIG"
DEFAULT_COLUMNS_PATH = Path(__file__).resolve().parents[2] / "config" / "pokegenie_columns.toml"

_TRUE = {"1", "true", "yes", "y", "x"}
_FALSE = {"", "0", "false", "no", "n"}
_MAX_IV = 15
_MAX_LEVEL = 55


class PokeGenieError(Exception):
    """The export cannot be parsed at all (as opposed to one bad row)."""


class MissingColumnError(PokeGenieError):
    def __init__(self, column: str, aliases: list[str]) -> None:
        self.column = column
        super().__init__(f"missing required column '{column}' (accepted headers: {aliases})")


class RowError(ValueError):
    """One row is invalid. The message never contains row values (public logs)."""


@dataclass(frozen=True)
class ColumnConfig:
    required: dict[str, list[str]]
    optional: dict[str, list[str]] = field(default_factory=dict)


def load_column_config(path: Path | None = None) -> ColumnConfig:
    """Load aliases from `path`, else $POGO_COLUMNS_CONFIG, else the bundled config."""
    if path is None:
        env = os.environ.get(COLUMNS_ENV)
        path = Path(env) if env else DEFAULT_COLUMNS_PATH
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return ColumnConfig(required=data["required"], optional=data.get("optional", {}))


def _norm(header: str) -> str:
    return header.strip().casefold()


def _map_columns(headers: list[str], config: ColumnConfig) -> dict[str, int]:
    """Map canonical field -> column index. Raises MissingColumnError for required gaps."""
    index = {}
    for i, header in enumerate(headers):
        index.setdefault(_norm(header), i)
    mapping: dict[str, int] = {}
    for name, aliases in config.required.items():
        found = next((index[_norm(a)] for a in aliases if _norm(a) in index), None)
        if found is None:
            raise MissingColumnError(name, aliases)
        mapping[name] = found
    for name, aliases in config.optional.items():
        found = next((index[_norm(a)] for a in aliases if _norm(a) in index), None)
        if found is not None:
            mapping[name] = found
    return mapping


def _int(value: str, name: str, low: int, high: int | None = None) -> int:
    try:
        number = int(value.strip())
    except ValueError:
        raise RowError(f"{name} is not an integer") from None
    if number < low or (high is not None and number > high):
        raise RowError(f"{name} is out of range")
    return number


def _flag(value: str, name: str) -> bool:
    text = value.strip().casefold()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise RowError(f"{name} is not a boolean flag")


def _build(get: "dict[str, str]") -> PokemonRecord:
    species = get["species"].strip()
    if not species:
        raise RowError("species is blank")
    level = None
    if get.get("level", "").strip():
        try:
            level = float(get["level"])
        except ValueError:
            raise RowError("level is not a number") from None
        if not 1 <= level <= _MAX_LEVEL:
            raise RowError("level is out of range")
    catch_date = None
    if get.get("catch_date", "").strip():
        try:
            catch_date = date.fromisoformat(get["catch_date"].strip()[:10])
        except ValueError:
            raise RowError("catch_date is not an ISO date") from None
    return PokemonRecord(
        species=species,
        cp=_int(get["cp"], "cp", 0),
        atk_iv=_int(get["atk_iv"], "atk_iv", 0, _MAX_IV),
        def_iv=_int(get["def_iv"], "def_iv", 0, _MAX_IV),
        sta_iv=_int(get["sta_iv"], "sta_iv", 0, _MAX_IV),
        form=get.get("form", "").strip(),
        nickname=get.get("nickname", "").strip(),
        level=level,
        quick_move=get.get("quick_move", "").strip(),
        charge_move=get.get("charge_move", "").strip(),
        charge_move_2=get.get("charge_move_2", "").strip(),
        catch_date=catch_date,
        shiny=_flag(get.get("shiny", ""), "shiny"),
        lucky=_flag(get.get("lucky", ""), "lucky"),
        shadow=_flag(get.get("shadow", ""), "shadow"),
        purified=_flag(get.get("purified", ""), "purified"),
        costume=_flag(get.get("costume", ""), "costume"),
    )


def parse_rows(lines: Iterable[str], config: ColumnConfig) -> list[PokemonRecord]:
    """Parse CSV text lines. Bad rows are skipped with one warning naming the row number.

    Row numbers are 1-based file rows, so the first data row is row 2.
    """
    reader = csv.reader(lines)
    try:
        headers = next(reader)
    except StopIteration:
        return []
    mapping = _map_columns(headers, config)
    records = []
    for row in reader:
        row_number = reader.line_num
        if not any(cell.strip() for cell in row):
            continue
        cells = {name: (row[i] if i < len(row) else "") for name, i in mapping.items()}
        try:
            records.append(_build(cells))
        except RowError as exc:
            logger.warning("skipping row %d: %s", row_number, exc)
    return records


def parse_file(path: Path, config: ColumnConfig | None = None) -> list[PokemonRecord]:
    config = config or load_column_config()
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return parse_rows(fh, config)


def summarize(records: list[PokemonRecord]) -> dict[str, int]:
    """Counts only, never species, nicknames or IVs."""
    return {
        "total": len(records),
        "shiny": sum(r.shiny for r in records),
        "lucky": sum(r.lucky for r in records),
        "shadow": sum(r.shadow for r in records),
        "purified": sum(r.purified for r in records),
        "costume": sum(r.costume for r in records),
        "100% IV": sum(r.is_hundo for r in records),
    }
