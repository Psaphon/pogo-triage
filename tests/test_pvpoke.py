import json
import logging
from pathlib import Path

import httpx
import pytest
from click.testing import CliRunner

from pogo_triage.cli import main
from pogo_triage.sources import SchemaError, SourceError
from pogo_triage.sources.pvpoke import fetch_rankings, load_sources_config

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "pvpoke_rankings_sample.json").read_text(encoding="utf-8")
)
CONFIG = load_sources_config()["pvpoke"]


def _serve(data=FIXTURE):
    by_url = {CONFIG[league]: data[league] for league in data}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=by_url[str(request.url)])

    return httpx.Client(transport=httpx.MockTransport(handler))


def _failing_client():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network used")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_three_leagues_keyed_by_species(tmp_path):
    rankings = fetch_rankings(client=_serve(), cache_dir=tmp_path)
    assert set(rankings) == {"great", "ultra", "master"}
    for league, entries in FIXTURE.items():
        assert len(rankings[league]) == len(entries)
    assert rankings["master"]["mewtwo"]["speciesName"] == "Mewtwo"


def test_missing_field_names_field_and_league(tmp_path):
    broken = json.loads(json.dumps(FIXTURE))
    del broken["ultra"][1]["score"]
    with pytest.raises(SchemaError, match=r"ultra league.*'score'"):
        fetch_rankings(client=_serve(broken), cache_dir=tmp_path)
    assert not (tmp_path / "pvpoke_ultra.json").exists()


def test_cache_written_and_offline_returns_identical(tmp_path):
    online = fetch_rankings(client=_serve(), cache_dir=tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "pvpoke_great.json",
        "pvpoke_master.json",
        "pvpoke_ultra.json",
    ]
    offline = fetch_rankings(client=_failing_client(), cache_dir=tmp_path, offline=True)
    assert offline == online


def test_env_overrides_url(tmp_path, monkeypatch):
    monkeypatch.setenv("POGO_PVPOKE_GREAT_URL", "https://example.test/great.json")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        league = {v: k for k, v in CONFIG.items()}.get(str(request.url), "great")
        return httpx.Response(200, json=FIXTURE[league])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetch_rankings(client=client, cache_dir=tmp_path)
    assert seen[0] == "https://example.test/great.json"


def test_http_error_is_source_error(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(SourceError, match="503"):
        fetch_rankings(client=client, cache_dir=tmp_path)


def test_logs_contain_counts_only(tmp_path, caplog):
    with caplog.at_level(logging.DEBUG):
        fetch_rankings(client=_serve(), cache_dir=tmp_path)
    assert "great league: 3 entries" in caplog.text
    assert "Bulbasaur" not in caplog.text and "bulbasaur" not in caplog.text


def test_cli_offline_with_empty_cache_fails(tmp_path):
    result = CliRunner().invoke(main, ["fetch", "--offline", "--cache-dir", str(tmp_path)])
    assert result.exit_code != 0
    assert "without --offline" in result.output
