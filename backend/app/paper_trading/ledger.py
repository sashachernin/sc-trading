from decimal import Decimal, ROUND_DOWN, ROUND_HALF_EVEN
from datetime import datetime
from sqlalchemy import select, func
from app.models import Account, Position, Ledger, Order, Fill, CorporateAction
from app.market_data.providers import parse

D = Decimal
Q = D(".00000001")
CENT = D(".01")


def money(x):
    return D(x).quantize(CENT, rounding=ROUND_HALF_EVEN)


def precise(x):
    return D(x).quantize(Q, rounding=ROUND_HALF_EVEN)


def validate_quote(q, now, settings, order_time=None):
    if D(q["price"]) <= 0:
        raise ValueError("Unsupported execution price")
    age = (parse(now) - parse(q["observed_at"])).total_seconds()
    if age < 0 or age > settings.quote_max_age_seconds:
        raise ValueError("Stale or future execution observation")
    if order_time and parse(q["observed_at"]) < parse(order_time):
        raise ValueError("Execution observation predates order")
    if not q.get("tradable"):
        raise ValueError("Security halted or unsupported")


def reconcile(session, account):
    total = session.scalar(
        select(func.sum(Ledger.amount)).where(Ledger.account_id == account.id)
    ) or D(0)
    if precise(total) != precise(account.cash) or account.cash < 0:
        raise ValueError("Cash reconciliation failed")
    positions = session.scalars(
        select(Position).where(Position.account_id == account.id)
    ).all()
    for p in positions:
        fills = session.execute(
            select(Order.side, Fill.quantity)
            .join(Fill, Fill.order_id == Order.id)
            .where(Order.position_id == p.id)
        ).all()
        quantity = sum((q if side == "BUY" else -q for side, q in fills), D(0))
        quantity += session.scalar(
            select(func.sum(CorporateAction.quantity_delta)).where(
                CorporateAction.position_id == p.id
            )
        ) or D(0)
        if precise(quantity) != precise(p.quantity):
            raise ValueError("Quantity reconciliation failed")


def validate_decision(decision, proposals, cash, settings):
    ids = {p["id"]: p for p in proposals}
    allocations = decision["allocations"]
    rejected = decision["rejections"]
    reviewed = decision["reviewed_ids"]
    if set(reviewed) != set(ids) or len(reviewed) != len(ids):
        raise ValueError("Manager must review all proposals exactly once")
    acted = [x["proposal_id"] for x in allocations + rejected]
    if len(acted) != len(set(acted)) or set(acted) != set(ids):
        raise ValueError("Decision must accept or reject every proposal once")
    if decision["hold_cash"] != (not allocations):
        raise ValueError("Hold-cash mismatch")
    deployed = sum((D(x["amount"]) for x in allocations), D(0))
    grouped = {}
    for x in allocations:
        if x["proposal_id"] not in ids:
            raise ValueError("Unsubmitted proposal")
        p = ids[x["proposal_id"]]
        ticker = p["ticker"]
        amount = D(x["amount"])
        if amount > cash * D(p["max_allocation"]):
            raise ValueError("Researcher allocation limit")
        if abs(D(x["percent"]) - amount / cash) > D(".000001"):
            raise ValueError("Allocation percentage mismatch")
        grouped[ticker] = grouped.get(ticker, D(0)) + amount
    if any(x > cash * D(settings.max_stock_allocation) for x in grouped.values()):
        raise ValueError("Combined ticker allocation exceeds limit")
    if deployed > cash * D(settings.max_deployed):
        raise ValueError("Deployment exceeds limit")
    if abs(cash - deployed - D(decision["retained_cash"])) > Q:
        raise ValueError("Cash arithmetic mismatch")
    return grouped


def buy(session, account, cycle, grouped, packet, settings):
    for ticker, budget in sorted(grouped.items()):
        key = f"{cycle.id}:BUY:{ticker}"
        if session.get(Ledger, key):
            continue
        q = packet["quotes"].get(ticker)
        if not q:
            raise ValueError("Missing executable quote")
        validate_quote(
            q, packet["cutoff"], settings, packet.get("order_time", packet["cutoff"])
        )
        rate = (D(settings.spread_bps) + D(settings.slippage_bps)) / 10000
        price = precise(D(q["price"]) * (1 + rate))
        fee = D(settings.fee_usd)
        quantity = ((budget - fee) / price).quantize(Q, rounding=ROUND_DOWN)
        if q.get("available_quantity") is not None:
            quantity = min(
                quantity, D(q["available_quantity"]).quantize(Q, rounding=ROUND_DOWN)
            )
        if quantity <= 0:
            raise ValueError("Insufficient allocation for fees")
        cost = precise(quantity * price + fee)
        if cost > account.cash:
            raise ValueError("Insufficient cash")
        p = Position(
            id=f"{cycle.id}:{ticker}",
            account_id=account.id,
            cycle_id=cycle.id,
            ticker=ticker,
            quantity=quantity,
            basis=cost,
            status="OPEN",
        )
        session.add(p)
        session.flush()
        order = Order(
            id=key,
            position_id=p.id,
            side="BUY",
            status="PARTIALLY_FILLED"
            if precise(quantity * price + fee) < budget - Q
            else "FILLED",
            created_at=parse(packet.get("order_time", packet["cutoff"])),
        )
        session.add(order)
        session.flush()
        session.add(
            Fill(
                id=key,
                order_id=key,
                ticker=ticker,
                quantity=quantity,
                price=price,
                fee=fee,
                data={
                    "label": "PAPER / SIMULATED",
                    "provider": packet["provider"],
                    "observation_time": q["observed_at"],
                    "fill_time": q["observed_at"],
                    "fill_model": "spread-slippage-v1",
                    "raw_price": q["price"],
                },
            )
        )
        session.add(
            Ledger(
                id=key,
                account_id=account.id,
                cycle_id=cycle.id,
                amount=-cost,
                kind="PAPER_BUY",
            )
        )
        account.cash -= cost
    session.flush()
    reconcile(session, account)


def sell(session, account, cycle, packet, settings):
    for p in session.scalars(
        select(Position).where(Position.cycle_id == cycle.id, Position.status == "OPEN")
    ).all():
        prior = session.scalar(
            select(func.count())
            .select_from(Order)
            .where(Order.position_id == p.id, Order.side == "SELL")
        )
        key = f"{cycle.id}:SELL:{p.ticker}" + (f":{prior}" if prior else "")
        if session.get(Ledger, key):
            continue
        q = packet["quotes"].get(p.ticker)
        if not q:
            continue  # Preserve unavailable positions and fill the supported ones.
        # Public chart events are evidence, not authority to adjust the ledger.
        # Preserve affected positions until an operator verifies and records the action.
        unresolved = False
        if packet.get("provider") == "yahoo-public":
            entry = parse(cycle.data["entry_cutoff"]).timestamp()
            for action in q.get("corporate_actions") or []:
                if entry < action["date"] <= parse(packet["cutoff"]).timestamp():
                    action_id = f"{cycle.experiment_id}:yahoo:{p.ticker}:{action['kind']}:{action['date']}"
                    if not session.get(CorporateAction, action_id):
                        unresolved = True
            if unresolved:
                continue
        try:
            validate_quote(
                q,
                packet["cutoff"],
                settings,
                packet.get("order_time", packet["cutoff"]),
            )
        except ValueError:
            continue
        rate = (D(settings.spread_bps) + D(settings.slippage_bps)) / 10000
        price = precise(D(q["price"]) * (1 - rate))
        fee = D(settings.fee_usd)
        quantity = p.quantity
        if q.get("available_quantity") is not None:
            quantity = min(
                quantity, D(q["available_quantity"]).quantize(Q, rounding=ROUND_DOWN)
            )
        if quantity <= 0:
            continue
        proceeds = precise(quantity * price - fee)
        if proceeds < 0:
            continue
        sold_basis = (
            p.basis
            if quantity == p.quantity
            else precise(p.basis * quantity / p.quantity)
        )
        order = Order(
            id=key,
            position_id=p.id,
            side="SELL",
            status="PARTIALLY_FILLED" if quantity < p.quantity else "FILLED",
            created_at=parse(packet.get("order_time", packet["cutoff"])),
        )
        session.add(order)
        session.flush()
        session.add(
            Fill(
                id=key,
                order_id=key,
                ticker=p.ticker,
                quantity=quantity,
                price=price,
                fee=fee,
                data={
                    "label": "PAPER / SIMULATED",
                    "provider": packet["provider"],
                    "observation_time": q["observed_at"],
                    "fill_time": q["observed_at"],
                    "fill_model": "spread-slippage-v1",
                    "raw_price": q["price"],
                    "cost_basis_sold": str(sold_basis),
                    "realized_pnl": str(precise(proceeds - sold_basis)),
                },
            )
        )
        session.add(
            Ledger(
                id=key,
                account_id=account.id,
                cycle_id=cycle.id,
                amount=proceeds,
                kind="PAPER_SELL",
            )
        )
        account.cash += proceeds
        p.quantity -= quantity
        p.basis -= sold_basis
        p.status = "CLOSED" if p.quantity == 0 else "OPEN"
    session.flush()
    reconcile(session, account)
