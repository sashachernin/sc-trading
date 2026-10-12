from datetime import date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select, func
from app.models import *
from app.services import scheduled
from app.market_data.providers import SyntheticProvider
from app.paper_trading.ledger import sell, reconcile
from app.paper_trading.actions import apply_action

MON = date(2026, 9, 14)


def test_partial_exit_commits_and_recovery(lab, monkeypatch):
    lab.open(MON)
    import app.services as services

    original = services.executable_packet

    def partial(cfg, tickers, kind, cutoff):
        p = original(cfg, tickers, kind, cutoff)
        for q in p["quotes"].values():
            q["available_quantity"] = "0.1"
        return p

    monkeypatch.setattr(services, "executable_packet", partial)
    with pytest.raises(ValueError, match="Partial"):
        lab.close(MON)
    with lab.sessions() as s:
        positions = list(s.scalars(select(Position).where(Position.status == "OPEN")))
        assert len(positions) == 2
        a = s.get(Account, lab.settings.experiment_id)
        reconcile(s, a)
        sold = s.scalar(
            select(func.count())
            .select_from(Fill)
            .join(Order)
            .where(Order.side == "SELL")
        )
        assert sold == 2
        assert s.scalar(select(Review)) is None
    monkeypatch.setattr(services, "executable_packet", original)
    lab.close(MON)
    with lab.sessions() as s:
        assert not list(s.scalars(select(Position).where(Position.status == "OPEN")))
        assert s.scalar(select(Cycle)).status == "COMPLETED"
        reconcile(s, s.get(Account, lab.settings.experiment_id))


def test_split_symbol_dividend_and_idempotency(lab):
    lab.open(MON)
    with lab.sessions.begin() as s:
        a = s.get(Account, lab.settings.experiment_id)
        p = s.scalar(select(Position))
        q = p.quantity
        basis = p.basis
        cash = a.cash
        apply_action(s, a, p, "split-1", "SPLIT", {"ratio": "2"})
        assert p.quantity == q * 2
        assert p.basis == basis
        apply_action(s, a, p, "split-1", "SPLIT", {"ratio": "2"})
        assert p.quantity == q * 2
        apply_action(s, a, p, "div-1", "DIVIDEND", {"amount_per_share": ".25"})
        assert a.cash == cash + (p.quantity * Decimal(".25")).quantize(
            Decimal(".00000001")
        )
        apply_action(s, a, p, "sym-1", "SYMBOL_CHANGE", {"ticker": "NEW"})
        assert p.ticker == "NEW"
        reconcile(s, a)
        with pytest.raises(ValueError):
            apply_action(s, a, p, "delist-1", "DELISTING", {})


def test_reconciliation_detects_corruption(lab):
    with lab.sessions.begin() as s:
        a = s.get(Account, lab.settings.experiment_id)
        a.cash += 1
        with pytest.raises(ValueError, match="Cash reconciliation"):
            reconcile(s, a)


def test_partial_purchase_supported(lab, monkeypatch):
    import app.services as services

    original = services.executable_packet

    def packet(cfg, tickers, kind, cutoff):
        p = original(cfg, tickers, kind, cutoff)
        if kind == "entry":
            for q in p["quotes"].values():
                q["available_quantity"] = ".1"
        return p

    monkeypatch.setattr(services, "executable_packet", packet)
    lab.open(MON)
    with lab.sessions() as s:
        assert all(p.quantity == Decimal(".1") for p in s.scalars(select(Position)))
        assert s.get(Account, lab.settings.experiment_id).cash > 900
        assert all(o.status == "PARTIALLY_FILLED" for o in s.scalars(select(Order)))
        reconcile(s, s.get(Account, lab.settings.experiment_id))


def test_supported_exit_fills_survive_missing_other_ticker(lab, monkeypatch):
    lab.open(MON)
    import app.services as services

    original = services.executable_packet

    def incomplete(cfg, tickers, kind, cutoff):
        p = original(cfg, tickers, kind, cutoff)
        p["quotes"].pop("AAPL")
        return p

    monkeypatch.setattr(services, "executable_packet", incomplete)
    with pytest.raises(ValueError):
        lab.close(MON)
    with lab.sessions() as s:
        assert (
            len(list(s.scalars(select(Position).where(Position.status == "CLOSED"))))
            == 1
        )
        assert (
            len(list(s.scalars(select(Position).where(Position.status == "OPEN")))) == 1
        )
        reconcile(s, s.get(Account, lab.settings.experiment_id))
    monkeypatch.setattr(services, "executable_packet", original)
    lab.close(MON)


def test_partial_exit_preserves_remaining_cost_basis(lab):
    lab.open(MON)
    with lab.sessions.begin() as s:
        c = s.scalar(select(Cycle))
        a = s.get(Account, lab.settings.experiment_id)
        ps = list(s.scalars(select(Position).where(Position.status == "OPEN")))
        old = {p.ticker: (p.quantity, p.basis) for p in ps}
        packet = SyntheticProvider(lab.settings).packet(
            [p.ticker for p in ps], scheduled(MON + timedelta(days=4), 15, 45), "exit"
        )
        for q in packet["quotes"].values():
            q["available_quantity"] = ".1"
        sell(s, a, c, packet, lab.settings)
        for p in ps:
            quantity, basis = old[p.ticker]
            assert abs(p.basis - basis * p.quantity / quantity) < Decimal(".00000002")
        sold = list(s.scalars(select(Fill).join(Order).where(Order.side == "SELL")))
        realized = sum(Decimal(f.data["realized_pnl"]) for f in sold)
        current_basis = sum(p.basis for p in ps)
        assert abs(realized - (a.cash + current_basis - 1000)) < Decimal(".00000002")


def test_public_action_blocks_unadjusted_exit(lab, monkeypatch):
    lab.open(MON)
    import app.services as services

    original = services.executable_packet

    def public(cfg, tickers, kind, cutoff):
        p = original(cfg, tickers, kind, cutoff)
        p["provider"] = "yahoo-public"
        p["quotes"]["AAPL"]["corporate_actions"] = [
            {
                "kind": "splits",
                "date": int(
                    __import__("datetime").datetime.fromisoformat(cutoff).timestamp()
                )
                - 3600,
            }
        ]
        return p

    monkeypatch.setattr(services, "executable_packet", public)
    with pytest.raises(ValueError, match="Partial"):
        lab.close(MON)
    with lab.sessions() as s:
        remaining = list(s.scalars(select(Position).where(Position.status == "OPEN")))
        assert [p.ticker for p in remaining] == ["AAPL"]
        reconcile(s, s.get(Account, lab.settings.experiment_id))
