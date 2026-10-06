"""Typed records produced by the parsers."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PokemonRecord:
    """One Pokémon from a Poke Genie export."""

    species: str
    cp: int
    atk_iv: int
    def_iv: int
    sta_iv: int
    form: str = ""
    nickname: str = ""
    level: float | None = None
    quick_move: str = ""
    charge_move: str = ""
    charge_move_2: str = ""
    catch_date: date | None = None
    shiny: bool = False
    lucky: bool = False
    shadow: bool = False
    purified: bool = False
    costume: bool = False

    @property
    def is_hundo(self) -> bool:
        return self.atk_iv == self.def_iv == self.sta_iv == 15
