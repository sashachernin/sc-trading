#!/usr/bin/env python3
"""Deterministic executable test double. Never represents actual model speech."""

import json, sys
from datetime import datetime, timedelta
from decimal import Decimal

p = json.load(sys.stdin)
role = p["role"]
purpose = p["purpose"]
c = p["packet"]
out = {}
if purpose == "RESEARCH":
    quotes = c["market"]["quotes"]
    symbols = list(quotes)
    symbols = symbols[:3] if role == "researcher_a" else list(reversed(symbols))[:3]
    out = {
        "role": role,
        "cutoff": c["market"]["cutoff"],
        "snapshot_id": c["market"]["id"],
        "candidates": [
            {
                "ticker": t,
                "company": quotes[t]["company"],
                "rank": i + 1,
                "max_allocation": "0.4",
                "expected_return": 0.025 - i * 0.005,
                "downside": -0.04,
                "probability_profit": 0.56,
                "confidence": 0.62,
                "thesis": (
                    "A synthetic catalyst test with missing fundamentals explicitly acknowledged."
                    if role == "researcher_a"
                    else "The supplied synthetic price series shows stable positive momentum."
                )
                + (
                    " Applying approved overlay guidance."
                    if c.get("lesson_ids")
                    else ""
                ),
                "catalysts": ["Synthetic fixture window"],
                "risks": ["Short horizon and simulated evidence"],
                "invalidation": "Unsupported or stale executable observation",
                "assumptions": ["No corporate actions in the synthetic fixture"],
                "evidence_ids": [quotes[t]["evidence_id"]],
            }
            for i, t in enumerate(symbols)
        ],
        "abstention_reason": None if symbols else "No eligible evidence",
    }
elif purpose == "DECISION":
    proposals = c["proposals"]
    cash = Decimal(c["cash"])
    picks = []
    seen = set()
    for x in proposals:
        if x["ticker"] not in seen and len(picks) < 2:
            picks.append(x)
            seen.add(x["ticker"])
    amount = (cash * min(Decimal(".35"), Decimal(c["limits"]["ticker"]))).quantize(
        Decimal(".01")
    )
    out = {
        "reviewed_ids": [x["id"] for x in proposals],
        "allocations": [
            {
                "proposal_id": x["id"],
                "amount": str(amount),
                "percent": str(amount / cash),
                "rationale": "Diversify the bounded synthetic test at 35% per ticker.",
            }
            for x in picks
        ],
        "rejections": [
            {
                "proposal_id": x["id"],
                "rationale": "Retain cash and avoid overlapping exposure.",
            }
            for x in proposals
            if x not in picks
        ],
        "retained_cash": str(cash - amount * len(picks)),
        "hold_cash": not picks,
        "summary": "Two distinct paper positions with a substantial cash reserve."
        if picks
        else "Hold cash: no proposals.",
        "risk_considerations": [
            "Combined ticker cap 40%",
            "Total deployment below 95%",
        ],
        "uncertainty": "Synthetic data proves workflow behavior, not investment skill.",
    }
elif purpose == "REVIEW":
    evidence = c["evidence_ids"]
    expiry = (
        (datetime.fromisoformat(c["cutoff"]) + timedelta(weeks=4)).date().isoformat()
    )
    out = {
        "summary": f"The reconciled synthetic week returned ${c['pnl']} net paper profit. Selection and forecasting need separate evaluation; this fixture is not evidence of market skill.",
        "scorecards": [
            {
                "role": r,
                "score": 0.6,
                "assessment": "Evidence was bounded; sample size remains one synthetic observation.",
            }
            for r in ("researcher_a", "researcher_b", "manager")
        ],
        "forecast_comparisons": [
            f"{x['ticker']}: forecast {x['expected_return']}, matched raw-price return {x['observed_return']}"
            for x in c["comparisons"]
        ],
        "selected_vs_rejected": "Matched windows include all eligible proposals; counterfactual returns exclude portfolio sizing.",
        "execution_effects": "Spread and slippage are charged by deterministic code.",
        "error_categories": ["Small sample uncertainty"],
        "successes": ["Cash and quantity reconciled"],
        "weaknesses": ["Fundamental/news data unavailable"],
        "limitations": "Synthetic fixture; exploratory associations only, with no demonstrated predictive advantage.",
        "evidence_ids": evidence,
        "patches": [
            {
                "target": "researcher_a",
                "operation": "hypothesis",
                "lesson_id": None,
                "text": "Explicitly distinguish catalyst evidence from price momentum and abstain when fundamental support is unavailable.",
                "parameter": None,
                "value": None,
                "evidence_ids": evidence[:1],
                "confidence": 0.55,
                "expected_effect": "Reduce unsupported catalyst claims",
                "duration_weeks": 4,
                "success_metric": "Share of theses with verified catalyst evidence",
                "rollback_condition": "No improvement after four observations",
                "expiry": expiry,
            }
        ],
    }
else:
    seq = c["sequence"]
    transcript = c["transcript"]
    evidence = c["evidence_ids"]
    prior = transcript[-1]["message_markdown"] if transcript else ""
    pnl = c["source"].get("pnl", "0.00")
    status = c["source"].get("status", "KICKOFF")
    names = {
        "researcher_a": "Avery",
        "researcher_b": "Morgan",
        "analyst": "Riley",
        "manager": "Casey",
    }
    messages = {
        1: f"Welcome, team. Our source record is {status}, with ${pnl} in recorded net paper profit. This is a synthetic demonstration, so let's separate successful plumbing from successful investing. I'd like each of you to explain your evidence, what remains uncertain, and one question for next week. We will discuss the actual record rather than inventing a market story. Avery, let's begin with the fundamentals perspective.",
        2: "I reviewed the bounded candidate packet. My fundamentals perspective has a real limitation here: the fixture does not supply company fundamentals or verified news, and I should say that plainly. I can test proposal structure, but cannot claim a catalyst edge. Morgan, how much does the supplied trend really tell us over this short holding period? Next week I want clearer evidence behind each catalyst claim.",
        3: "Avery, I agree about separating evidence from storytelling. The supplied price series lets me discuss momentum, but it does not establish that momentum predicts next week's returns. The manager kept a cash reserve, which made the sizing easy to audit. Riley, can we distinguish forecast quality from the outcome of the selected basket? My question is how often rejected candidates outperform our selections over matched windows.",
        4: f"Morgan, the matched-window comparison is the right starting point. The recorded paper result is ${pnl}; that number comes from the ledger, not my narrative. My review treats research, selection, sizing, and execution separately. A single synthetic week cannot establish calibration or a profitable strategy. I proposed a bounded hypothesis for Avery, and activation belongs to the learning gate. Casey, what evidence would justify greater conviction next week?",
        5: "Let's follow Avery's evidence question first. We have a completed record or an explicitly unavailable result; neither gives us permission to fill the gaps with a plausible story. Avery, what would make your catalyst claim falsifiable, and how would the approved hypothesis change your next proposal? Please connect that answer to the records we already discussed. We should keep Monday's research independent of this conversation.",
        7: "Thanks. Let's bring the price perspective into that discussion. Morgan, how would you separate a stable trend from a noisy move over our short holding window? The cash reserve and ticker caps remain application rules regardless of our enthusiasm. Please explain what the supplied packet supports and what it leaves unanswered. I would rather carry an honest question into Monday than turn today's discussion into a recommendation.",
        9: "Riley, let's close the substantive discussion with evaluation. We have heard about missing catalyst evidence and uncertainty around short-window momentum. How should we assess the bounded lesson without mistaking one favorable result for proof? Please connect forecast comparisons, selected and rejected candidates, and execution costs. Our account and overlays will remain unchanged by this meeting; any formal update goes through Friday's review and validation.",
        11: f"We agree that the recorded status is {status} and the verified net paper result is ${pnl}. We also agree that missing evidence needs an explicit label. Avery will look for supported catalysts, Morgan will keep trend claims cautious, and Riley will separate forecasts from realized outcomes. Those are focus areas, not completed recommendations. Our open question is whether the next observations support the bounded hypothesis. Thanks, everyone; the ledger gets the final word on the arithmetic.",
    }
    if not c["source"].get("proposals"):
        messages[2] = (
            "There are no recorded proposals in this frozen source packet, so I will not pretend to have completed a catalyst study. From the fundamentals perspective, our useful preparation is to identify what evidence would support a short holding-period thesis. Verified events and company information would matter; missing inputs should remain explicitly unavailable. Morgan, what price history would you want before making a recommendation? That is a question for a future independent run."
        )
        messages[3] = (
            "Avery, I agree that preparation should stay separate from a completed recommendation. There are no recorded momentum proposals in this source packet. I can describe the questions I would investigate, but cannot claim to have measured a trend we were not supplied. I would want bounded price and volume history and an honest account of missing observations. Riley, how should we evaluate this week when no supported trading comparison exists?"
        )
    if (
        c["source"].get("status") != "COMPLETED"
        or c["source"].get("summary") == "Review unavailable"
    ):
        messages[4] = (
            f"No completed Friday review is supplied for this {status} record, so there is no analyst conclusion or new learning patch for me to claim. The account facts still come from the verified source packet; they should not be padded with hypothetical trading outcomes. My focus is to preserve that distinction and identify the information we need next. Casey, can we make next week's readiness depend on actual evidence and reconciled account state?"
        )
        messages[5] = (
            "Let's develop Avery's preparation question. The source record does not give us a completed recommendation or review to analyze, and that absence should remain visible. Avery, what would make a future catalyst thesis falsifiable, and what evidence would you need before proposing any hypothesis? Please connect your answer to the limitations already discussed. Monday's proposals will still come from a fresh independent research run."
        )
        messages[11] = (
            f"Our source status is {status}, and no completed review is supplied. We will not invent trading lessons to make the conversation feel fuller. Avery's focus is supported catalyst evidence, Morgan's is adequate price history, and Riley's is a fair evaluation of whatever observations actually become available. These are tentative preparation questions rather than completed recommendations or activated lessons. Thanks, everyone; our next step depends on evidence and account readiness."
        )
    message = messages.get(
        seq,
        f"Casey, your question about '{prior[:70].rstrip()}' gets to the central uncertainty. From my {role.replace('_', ' ')} perspective, the supplied record supports a bounded comparison, while the missing information should stay missing. I will use the approved evidence and exact overlay version in the next applicable run. We should check the measured outcome before strengthening this hypothesis. Avery and Morgan's earlier points both suggest keeping claims proportional to the available observations.",
    )
    remaining = c.get("remaining", [])
    out = {
        "meeting_id": c["meeting_id"],
        "sequence": seq,
        "speaker": role,
        "phase": c["phase"],
        "message_markdown": message,
        "reply_to_turn_ids": [transcript[-1]["id"]] if transcript else [],
        "evidence_ids": evidence[:2],
        "next_speaker": remaining[0] if seq in (5, 7, 9) and remaining else None,
        "closing": {
            "title": "Evidence before conviction: our weekly lab meeting",
            "standfirst": f"A synthetic team discussion of {status}, paper outcomes, and the questions ahead.",
            "recap": f"The team discussed the verified paper result ${pnl}, missing fundamental evidence, matched comparisons and bounded learning.",
            "takeaways": [
                "Keep claims proportional to evidence",
                "Separate portfolio results from forecasting skill",
            ],
            "focus_areas": [
                "Verify catalyst evidence",
                "Evaluate matched-window comparisons",
            ],
            "open_questions": [
                "Will future observations support the bounded hypothesis?"
            ],
        }
        if seq == 11
        else None,
    }
path = sys.argv[sys.argv.index("--output-last-message") + 1]
with open(path, "w") as f:
    json.dump(out, f)
print(json.dumps({"type": "fixture.completed"}))
