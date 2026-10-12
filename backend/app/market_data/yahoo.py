"""Personal research adapter to Yahoo's public, unofficial chart endpoint.

Prices are timestamped observations, never guaranteed executable broker quotes.
Missing/stale metadata fails closed. No account, API key or broker orders.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
import re
import httpx
from app.context.compiler import digest
from app.market_data.providers import iso, parse

NY = ZoneInfo("America/New_York")


class YahooProvider:
    name = "yahoo-public"

    def __init__(self, settings):
        self.settings = settings

    def _chart(self, client, ticker, interval, period):
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", ticker):
            raise ValueError("Invalid market symbol")
        response = client.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            params={
                "interval": interval,
                "range": period,
                "includePrePost": "false",
                "events": "div,splits",
                "includeAdjustedClose": "false",
            },
        )
        response.raise_for_status()
        data = response.json()["chart"]
        if data.get("error") or not data.get("result"):
            raise ValueError("Public chart unavailable")
        return data["result"][0]

    def _observation(self, client, ticker, cutoff, benchmark=False):
        intraday = self._chart(client, ticker, "1m", "1d")
        meta = intraday["meta"]
        expected = "ETF" if benchmark else "EQUITY"
        name = meta.get("longName") or meta.get("shortName") or ticker
        if (
            meta.get("symbol") != ticker
            or meta.get("currency") != "USD"
            or meta.get("instrumentType") != expected
            or meta.get("exchangeName")
            not in ("NMS", "NGM", "NCM", "NYQ", "ASE", "PCX")
            or any(
                x in name.upper()
                for x in ("PREFERRED", "WARRANT", "DEPOSITARY", " UNIT")
            )
        ):
            raise ValueError("Unsupported security metadata")
        observed = datetime.fromtimestamp(meta["regularMarketTime"], timezone.utc)
        age = (parse(cutoff) - observed).total_seconds()
        price = Decimal(str(meta["regularMarketPrice"]))
        if (
            not price.is_finite()
            or price <= 0
            or not 0 <= age <= self.settings.quote_max_age_seconds
        ):
            raise ValueError("Missing, stale or future public observation")
        # Explicitly exclude extended-hours observations.
        session = meta.get("currentTradingPeriod", {}).get("regular", {})
        if not session.get("start", 0) <= observed.timestamp() <= session.get("end", 0):
            raise ValueError("Observation outside regular session")
        if benchmark:
            return {
                "ticker": ticker,
                "comparison_only": True,
                "price": str(price),
                "observed_at": iso(observed),
                "retrieved_at": iso(datetime.now(timezone.utc)),
            }
        daily = self._chart(client, ticker, "1d", "3mo")
        bars = daily["indicators"]["quote"][0]
        cutoff_day = parse(cutoff).astimezone(NY).date()
        history, volumes = [], []
        for stamp, close, volume in zip(
            daily.get("timestamp", []), bars["close"], bars["volume"]
        ):
            if (
                datetime.fromtimestamp(stamp, timezone.utc).astimezone(NY).date()
                >= cutoff_day
            ):
                continue  # Never use a partial current-session daily close.
            if close is not None and volume is not None:
                value = Decimal(str(close))
                if value.is_finite() and value > 0:
                    history.append(str(value))
                    volumes.append(int(volume))
        actions = []
        for action_kind, records in daily.get("events", {}).items():
            for record in records.values():
                stamp = record.get("date")
                if stamp is not None and stamp <= parse(cutoff).timestamp():
                    actions.append({"kind": action_kind, **record})
        return {
            "ticker": ticker,
            "company": name,
            "security_type": "common_stock",
            "exchange": meta["exchangeName"],
            "tradable": True,
            "price": str(price),
            "observed_at": iso(observed),
            "published_at": None,
            "retrieved_at": iso(datetime.now(timezone.utc)),
            "volume": sum(volumes[-5:]) // max(1, len(volumes[-5:])),
            "history": history[-20:],
            "fundamentals": None,
            "news": [],
            "events": [],
            "delay_seconds": int(age),
            "corporate_actions": actions,
            "corporate_action_coverage": "reported chart events only; not exhaustive",
            "evidence_id": f"yahoo:{ticker}:{iso(observed)}",
            "price_semantics": "regularMarketPrice observation; simulated fill with configured costs",
            "history_semantics": "Yahoo close series may be split-restated; research only",
        }

    def packet(self, tickers, cutoff, kind):
        now = datetime.now(timezone.utc)
        if abs((now - parse(cutoff)).total_seconds()) > 120:
            raise ValueError("Public provider supports forward snapshots only")
        symbols = sorted(set(tickers) | {"SPY"})
        quotes, errors, benchmark = (
            {},
            [],
            {"ticker": "SPY", "comparison_only": True, "price": None},
        )
        with httpx.Client(
            timeout=10, headers={"User-Agent": "Mozilla/5.0 AIInvestmentLab/0.1"}
        ) as client:

            def fetch(ticker):
                try:
                    return (
                        ticker,
                        self._observation(client, ticker, cutoff, ticker == "SPY"),
                        None,
                    )
                except (
                    httpx.HTTPError,
                    KeyError,
                    ValueError,
                    TypeError,
                    InvalidOperation,
                ) as exc:
                    return ticker, None, type(exc).__name__

            with ThreadPoolExecutor(max_workers=4) as pool:
                for ticker, quote, error in pool.map(fetch, symbols):
                    if error:
                        errors.append(
                            f"{ticker}: public observation unavailable ({error})"
                        )
                    elif ticker == "SPY":
                        benchmark = quote
                    else:
                        quotes[ticker] = quote
        packet = {
            "provider": self.name,
            "cutoff": cutoff,
            "synthetic": False,
            "quotes": quotes,
            "benchmark": benchmark,
            "unavailable": errors
            + [
                "Unofficial public endpoint: variable delay, rate limits and no uptime guarantee.",
                "No verified fundamentals, news, earnings, security halts or comprehensive corporate actions.",
                "Personal research use; private dashboard. Prices are observations, not executable quotes.",
            ],
        }
        packet["id"] = digest(packet)[:24]
        return packet
