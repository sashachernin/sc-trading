from datetime import datetime, timezone
import pytest
from app.config import Settings
from app.market_data.yahoo import YahooProvider
from app.market_data.providers import screen

STAMP = int(datetime(2026, 10, 12, 13, 34, tzinfo=timezone.utc).timestamp())
CUTOFF = "2026-10-12T13:35:00+00:00"


def chart(ticker="AAPL"):
    return {
        "meta": {
            "symbol": ticker,
            "currency": "USD",
            "instrumentType": "EQUITY",
            "longName": "Apple Inc.",
            "exchangeName": "NMS",
            "regularMarketTime": STAMP,
            "regularMarketPrice": 200,
            "currentTradingPeriod": {
                "regular": {"start": STAMP - 240, "end": STAMP + 23000}
            },
        },
        "timestamp": [STAMP - 86400 * i for i in range(25, -1, -1)],
        "indicators": {
            "quote": [{"close": [190] * 25 + [999], "volume": [2000000] * 26}]
        },
    }


def test_excludes_partial_daily_close_and_preserves_timestamp(monkeypatch):
    p = YahooProvider(Settings())
    monkeypatch.setattr(p, "_chart", lambda *a: chart())
    quote = p._observation(None, "AAPL", CUTOFF)
    assert len(quote["history"]) == 20
    assert "999" not in quote["history"]
    assert quote["delay_seconds"] == 60
    assert quote["published_at"] is None
    packet = {"quotes": {"AAPL": quote}, "cutoff": CUTOFF}
    assert "AAPL" in screen(packet, Settings())["quotes"]


@pytest.mark.parametrize(
    "change",
    [
        {"regularMarketTime": STAMP - 900},
        {"regularMarketTime": STAMP + 120},
        {"instrumentType": "ETF"},
        {"currency": "EUR"},
        {"regularMarketPrice": "NaN"},
        {"longName": "Apple Preferred"},
        {"symbol": "OTHER"},
    ],
)
def test_rejects_stale_future_and_ineligible(monkeypatch, change):
    p = YahooProvider(Settings())
    data = chart()
    data["meta"].update(change)
    monkeypatch.setattr(p, "_chart", lambda *a: data)
    with pytest.raises(ValueError):
        p._observation(None, "AAPL", CUTOFF)


def test_benchmark_retains_observation_time(monkeypatch):
    p = YahooProvider(Settings())
    data = chart("SPY")
    data["meta"]["instrumentType"] = "ETF"
    monkeypatch.setattr(p, "_chart", lambda *a: data)
    q = p._observation(None, "SPY", CUTOFF, benchmark=True)
    assert q["comparison_only"] and q["observed_at"]


def test_public_adapter_refuses_historical_reconstruction():
    with pytest.raises(ValueError, match="forward"):
        YahooProvider(Settings()).packet(["AAPL"], CUTOFF, "entry")
