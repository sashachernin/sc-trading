from decimal import Decimal
from app.models import CorporateAction, Ledger
from app.paper_trading.ledger import precise, reconcile


def apply_action(session, account, position, id, kind, data):
    """Explicit operator/provider-verified adjustments, never inferred from model prose."""
    if session.get(CorporateAction, id):
        return
    delta = Decimal(0)
    if kind == "SPLIT":
        ratio = Decimal(data["ratio"])
        if ratio <= 0:
            raise ValueError("Split ratio must be positive")
        quantity = precise(position.quantity * ratio)
        delta = quantity - position.quantity
        position.quantity = quantity
    elif kind == "SYMBOL_CHANGE":
        ticker = data["ticker"]
        import re

        if not re.fullmatch("[A-Z][A-Z0-9.]{0,9}", ticker):
            raise ValueError("Unsupported ticker")
        position.ticker = ticker
    elif kind == "DIVIDEND":
        value = precise(position.quantity * Decimal(data["amount_per_share"]))
        if value < 0:
            raise ValueError("Negative dividend")
        session.add(
            Ledger(
                id=id,
                account_id=account.id,
                cycle_id=position.cycle_id,
                amount=value,
                kind="PAPER_DIVIDEND",
            )
        )
        account.cash += value
    else:
        raise ValueError("Unsupported corporate action requires operator recovery")
    session.add(
        CorporateAction(
            id=id, position_id=position.id, kind=kind, quantity_delta=delta, data=data
        )
    )
    session.flush()
    reconcile(session, account)
