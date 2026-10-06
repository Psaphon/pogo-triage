import logging
from pathlib import Path

from click.testing import CliRunner

from pogo_triage.cli import main
from pogo_triage.pokegenie import load_column_config, parse_file

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "pokegenie_sample.csv"
MALFORMED = FIXTURES / "pokegenie_malformed.csv"
REORDERED = FIXTURES / "pokegenie_reordered.csv"


def test_cli_summary_counts():
    result = CliRunner().invoke(main, ["parse", str(SAMPLE)])
    assert result.exit_code == 0
    assert result.output.splitlines() == [
        "10 records",
        "shiny: 2",
        "lucky: 2",
        "shadow: 1",
        "purified: 1",
        "costume: 1",
        "100% IV: 4",
    ]


def test_summary_never_prints_species():
    result = CliRunner().invoke(main, ["parse", str(SAMPLE)])
    assert "mon" not in result.output.replace("records", "")


def test_record_fields():
    records = parse_file(SAMPLE)
    shiny = records[1]
    assert (shiny.species, shiny.nickname, shiny.cp, shiny.level) == (
        "Shinymon",
        "Sparkle",
        800,
        20.5,
    )
    assert (shiny.atk_iv, shiny.def_iv, shiny.sta_iv) == (10, 11, 12)
    assert shiny.shiny and not shiny.lucky
    assert shiny.catch_date.isoformat() == "2024-02-10"
    assert records[4].form == "Alolan"


def test_column_order_does_not_matter():
    assert parse_file(REORDERED) == parse_file(SAMPLE)


def test_malformed_rows_warn_and_are_skipped(caplog):
    with caplog.at_level(logging.WARNING, logger="pogo_triage"):
        result = CliRunner().invoke(main, ["parse", str(MALFORMED)])
    assert result.exit_code == 0
    assert result.output.splitlines()[0] == "2 records"
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 3
    for row, message in zip((3, 4, 5), warnings, strict=True):
        assert f"row {row}" in message
    joined = " ".join(warnings)
    assert "Nocpmon" not in joined and "Noivmon" not in joined


def test_empty_file(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    result = CliRunner().invoke(main, ["parse", str(empty)])
    assert result.exit_code == 0
    assert result.output.splitlines()[0] == "0 records"


def test_missing_required_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Name,CP,Atk IV,Def IV\nTestmon,100,1,2\n")
    result = CliRunner().invoke(main, ["parse", str(bad)])
    assert result.exit_code != 0
    assert "sta_iv" in result.stderr


def test_alias_from_temp_config(tmp_path):
    renamed = tmp_path / "renamed.csv"
    renamed.write_text("Mon,CP,Atk IV,Def IV,Sta IV\nTestmon,100,1,2,3\n")
    assert CliRunner().invoke(main, ["parse", str(renamed)]).exit_code != 0

    config = tmp_path / "columns.toml"
    config.write_text(
        '[required]\nspecies = ["Mon"]\ncp = ["CP"]\natk_iv = ["Atk IV"]\n'
        'def_iv = ["Def IV"]\nsta_iv = ["Sta IV"]\n'
    )
    result = CliRunner().invoke(main, ["parse", str(renamed), "--columns", str(config)])
    assert result.exit_code == 0
    assert result.output.splitlines()[0] == "1 records"


def test_env_override_for_columns(tmp_path, monkeypatch):
    config = tmp_path / "columns.toml"
    config.write_text('[required]\nspecies = ["Mon"]\n')
    monkeypatch.setenv("POGO_COLUMNS_CONFIG", str(config))
    assert list(load_column_config().required) == ["species"]
