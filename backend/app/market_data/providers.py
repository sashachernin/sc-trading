from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import httpx
import exchange_calendars as xcals
from app.context.compiler import digest

D = Decimal


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def parse(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def eligible_week(monday):
    cal = xcals.get_calendar("XNYS")
    friday = monday + timedelta(days=4)
    for day in (monday, friday):
        key = day.isoformat()
        if not cal.is_session(key):
            return False, f"{key} is not an exchange session"
        opening = cal.session_open(key).to_pydatetime()
        closing = cal.session_close(key).to_pydatetime()
        if (closing - opening).total_seconds() < 6.5 * 3600:
            return False, f"{key} has an early close"
    return True, ""


class SyntheticProvider:
    name = "synthetic"

    def __init__(self, settings):
        self.settings = settings

    def packet(self, tickers, cutoff, kind):
        quotes = {}
        for ticker in sorted(set(tickers)):
            seed = int(
                hashlib.sha256((ticker + cutoff[:10]).encode()).hexdigest()[:8], 16
            )
            base = D(
                80 + int(hashlib.sha256(ticker.encode()).hexdigest()[:4], 16) % 250
            )
            week = datetime.fromisoformat(cutoff).date()
            monday = week - timedelta(days=week.weekday())
            drift = D(
                int(
                    hashlib.sha256((ticker + monday.isoformat()).encode()).hexdigest()[
                        :4
                    ],
                    16,
                )
                % 901
                - 350
            ) / D(10000)
            price = base if kind == "entry" else base * (1 + drift)
            quotes[ticker] = {
                "ticker": ticker,
                "company": ticker + " Synthetic Common Stock",
                "security_type": "common_stock",
                "exchange": "NASDAQ",
                "tradable": True,
                "price": str(price.quantize(D(".000001"))),
                "observed_at": cutoff,
                "retrieved_at": cutoff,
                "published_at": cutoff,
                "volume": 2000000 + seed % 3000000,
                "history": [
                    str((base * (1 + D(i - 19) / 1000)).quantize(D(".000001")))
                    for i in range(20)
                ],
                "fundamentals": None,
                "news": [],
                "events": [],
                "delay_seconds": 0,
                "corporate_actions": [],
                "evidence_id": f"{kind}:{ticker}:{monday.isoformat()}",
            }
        packet = {
            "id": digest({"cutoff": cutoff, "kind": kind, "quotes": quotes})[:24],
            "provider": self.name,
            "cutoff": cutoff,
            "synthetic": True,
            "quotes": quotes,
            "benchmark": {
                "ticker": "SPY",
                "comparison_only": True,
                "price": "500" if kind == "entry" else "505",
            },
            "unavailable": [
                "Real fundamentals and news; synthetic data is a deterministic test fixture"
            ],
        }
        return packet


class AlpacaProvider:
    """Read-only adapter. No broker orders. IEX is explicitly a partial-market feed."""

    name = "alpaca"

    def __init__(self, settings):
        self.settings = settings
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise ValueError("Alpaca credentials required")
        self.client = httpx.Client(
            headers={
                "APCA-API-KEY-ID": settings.alpaca_api_key,
                "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
            },
            timeout=20,
        )

    def packet(self, tickers, cutoff, kind):
        # Forward runs only. Latest quote is never substituted for historical evidence.
        now = datetime.now(timezone.utc)
        if abs((now - parse(cutoff)).total_seconds()) > 120:
            raise ValueError(
                "Real provider only supports forward point-in-time snapshots"
            )
        symbols = sorted(set(tickers) | {"SPY"})
        response = self.client.get(
            "https://data.alpaca.markets/v2/stocks/snapshots",
            params={"symbols": ",".join(symbols), "feed": self.settings.alpaca_feed},
        )
        response.raise_for_status()
        raw = response.json()
        quotes = {}
        for ticker in sorted(set(tickers)):
            asset = self.client.get(
                f"{self.settings.alpaca_asset_base_url}/v2/assets/{ticker}"
            )
            asset.raise_for_status()
            meta = asset.json()
            # Conservative denylist for ambiguous security classification. Configured common-stock universe is operator-reviewed.
            name = meta["name"].upper()
            if (
                not meta.get("tradable")
                or meta.get("status") != "active"
                or meta.get("class") != "us_equity"
                or any(
                    x in name
                    for x in (
                        "ETF",
                        "FUND",
                        "PREFERRED",
                        "WARRANT",
                        "DEPOSITARY",
                        " UNIT",
                        "TRUST",
                    )
                )
            ):
                continue
            # Historical end cutoff prevents a later latest snapshot from leaking into a decision.
            trades = self.client.get(
                f"https://data.alpaca.markets/v2/stocks/{ticker}/trades",
                params={
                    "start": iso(
                        parse(cutoff)
                        - timedelta(seconds=self.settings.quote_max_age_seconds)
                    ),
                    "end": cutoff,
                    "sort": "desc",
                    "limit": 1,
                    "feed": self.settings.alpaca_feed,
                },
            )
            trades.raise_for_status()
            observations = trades.json().get("trades", [])
            trade = observations[0] if observations else None
            if not trade or parse(trade["t"]) > parse(cutoff):
                continue
            if (
                parse(cutoff) - parse(trade["t"])
            ).total_seconds() > self.settings.quote_max_age_seconds:
                continue
            start = (parse(cutoff) - timedelta(days=45)).isoformat()
            bars = self.client.get(
                f"https://data.alpaca.markets/v2/stocks/{ticker}/bars",
                params={
                    "timeframe": "1Day",
                    "start": start,
                    "end": cutoff,
                    "adjustment": "raw",
                    "feed": self.settings.alpaca_feed,
                    "limit": 50,
                },
            )
            bars.raise_for_status()
            history = [
                b for b in bars.json().get("bars", []) if parse(b["t"]) <= parse(cutoff)
            ]
            quotes[ticker] = {
                "ticker": ticker,
                "company": meta["name"],
                "security_type": "common_stock",
                "exchange": meta["exchange"],
                "tradable": True,
                "price": str(trade["p"]),
                "observed_at": trade["t"],
                "published_at": trade["t"],
                "retrieved_at": iso(now),
                "volume": sum(b["v"] for b in history[-5:])
                // max(1, len(history[-5:])),
                "history": [str(b["c"]) for b in history[-20:]],
                "fundamentals": None,
                "news": [],
                "events": [],
                "delay_seconds": max(
                    0, int((parse(cutoff) - parse(trade["t"])).total_seconds())
                ),
                "corporate_actions": None,
                "evidence_id": f"{kind}:{ticker}:{cutoff}",
            }
        bench = raw.get("SPY", {}).get("latestTrade")
        packet = {
            "provider": f"alpaca-{self.settings.alpaca_feed}",
            "cutoff": cutoff,
            "synthetic": False,
            "quotes": quotes,
            "benchmark": {
                "ticker": "SPY",
                "comparison_only": True,
                "price": str(bench["p"])
                if bench and parse(bench["t"]) <= parse(cutoff)
                else None,
            },
            "unavailable": [
                "Fundamentals, earnings, news, corporate actions; operator must resolve corporate actions before recovery",
                "IEX feed is partial-market data; verify redistribution rights",
            ],
        }
        packet["id"] = digest(packet)[:24]
        return packet


def provider(settings):
    if settings.market_provider == "synthetic":
        return SyntheticProvider(settings)
    if settings.market_provider == "yahoo":
        from app.market_data.yahoo import YahooProvider

        return YahooProvider(settings)
    return AlpacaProvider(settings)


def screen(packet, settings):
    valid = {}
    for ticker, q in packet["quotes"].items():
        age = (parse(packet["cutoff"]) - parse(q["observed_at"])).total_seconds()
        if (
            q["security_type"] == "common_stock"
            and q["tradable"]
            and D(q["price"]) >= 5
            and q["volume"] >= 1000000
            and len(q["history"]) >= 20
            and 0 <= age <= settings.quote_max_age_seconds
        ):
            valid[ticker] = q
    return dict(
        packet,
        quotes=dict(sorted(valid.items())[:20]),
        screen_version="v1-price5-volume1m-history20",
    )


def executable_packet(settings, tickers, kind, order_time):
    """Bounded polling for the first supported post-order observation."""
    if settings.market_provider == "synthetic":
        packet = provider(settings).packet(tickers, order_time, kind)
        return dict(packet, order_time=order_time)
    import time

    deadline = time.monotonic() + settings.execution_wait_seconds
    while True:
        cutoff = iso(datetime.now(timezone.utc))
        packet = provider(settings).packet(tickers, cutoff, kind)
        if all(
            t in packet["quotes"]
            and parse(packet["quotes"][t]["observed_at"]) >= parse(order_time)
            for t in set(tickers)
        ):
            return dict(packet, order_time=order_time)
        if time.monotonic() >= deadline:
            raise ValueError(
                "No supported fresh post-order observation within execution window"
            )
        time.sleep(5 if settings.market_provider == "yahoo" else 1)
