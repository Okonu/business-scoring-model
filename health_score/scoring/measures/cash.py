"""Cash, collections and payables measures (methodology table 6)"""

from datetime import timedelta

import pandas as pd

from health_score.scoring.measures.receivables import (
    collection_effectiveness,
    open_bills,
    open_receivables,
    severe_payables_share,
    severe_share,
)

DEFAULT_SUPPLIER_TERMS_DAYS = 30.0
MIN_CUSTOMERS_WITH_LIMIT = 3
PLAN_COLLECTION_CEILING = 1.5


def cash_measures(w, p):
    return {
        **_realization(w, p),
        **_receivables(w, p),
        **_runway(w, p),
        **_property_and_plans(w),
        **_gift_cards(w, p),
        **_payables(w),
    }


def _realization(w, p):
    if p.revenue_t3 <= 0:
        return {}
    return {"cash_realization": float(w.last_3m(w.table("cash_in"))["amount"].sum()) / p.revenue_t3}


def _receivables(w, p):
    if p.cash_business or p.credit_share is None:
        return {}
    values = {}
    credit_t3 = float(p.tx_t3.loc[p.tx_t3["credit"].eq(True), "amount"].sum())
    items = open_receivables(w)
    total = sum(amount for amount, _ in items)
    if w.reports.get("ar_aging") or not w.table("rent_invoices").empty:
        values["ar_severe_overdue"] = severe_share(items) if total > 0 else 0.0
        if total > 0:
            values["ar_wadpd"] = sum(amount * max(days, 0) for amount, days in items) / total
        if credit_t3 > 0:
            values["dso"] = total / credit_t3 * 90
        previous = severe_share(open_receivables(w, "ar_aging_prev", w.t3))
        current = severe_share(items)
        if previous is not None and current is not None:
            values["aging_drift"] = current - previous
        values["cei"] = collection_effectiveness(w)
    elif credit_t3 > 0:
        customers = w.table("customers")
        balances = float(customers["balance"].clip(lower=0).sum()) if not customers.empty else 0.0
        if balances > 0:
            values["dso"] = balances / credit_t3 * 90
    values.update(_credit_limits(w))
    return values


def _credit_limits(w):
    customers = w.table("customers")
    limited = customers[customers["credit_limit"] > 0] if not customers.empty else customers
    if len(limited) < MIN_CUSTOMERS_WITH_LIMIT:
        return {}
    return {"credit_limit_breach": float((limited["balance"] > limited["credit_limit"]).mean())}


def _runway(w, p):
    if not (p.business_level and p.books_reliable):
        return {}
    accounts = w.table("bank_accounts")
    outflow = sum(
        float(account.get("outflows") or 0)
        for report in (w.reports.get("cash_flow") or {}).values()
        if report
        for account in report.get("accounts") or []
    )
    if accounts.empty or outflow <= 0:
        return {}
    balance = max(float(accounts["balance"].fillna(0).sum()), 0.0)
    return {"cash_runway": balance / (outflow / 3)}


def _property_and_plans(w):
    values = {}
    rent = w.last_3m(w.table("rent_invoices"), "due_date")
    if not rent.empty and rent["amount"].sum() > 0:
        values["rent_collection"] = float(rent["paid"].fillna(0).sum() / rent["amount"].sum())
    values["plan_collection"] = _plan_collection(w)
    return values


def _plan_collection(w):
    plans = w.table("payment_plans")
    if plans.empty:
        return None
    plans = plans[plans["start"] <= w.as_of]
    expected = paid = 0.0
    for _, plan in plans.iterrows():
        elapsed = (w.as_of.to_period("M") - plan["start"].to_period("M")).n + 1
        installments = int(plan["installments"] or 0)
        due = (plan["deposit"] or 0) + (plan["installment"] or 0) * min(max(elapsed, 0), installments)
        expected += min(due, plan["total"] or due)
        paid += (plan["total"] or 0) - (plan["outstanding"] or 0)
    return min(paid / expected, PLAN_COLLECTION_CEILING) if expected > 0 else None


def _gift_cards(w, p):
    cards = w.table("gift_cards")
    if cards.empty or p.revenue_t3 <= 0:
        return {}
    live = cards[cards["active"].eq(True) & (cards["expiry"].isna() | (cards["expiry"] > w.as_of))]
    return {"gift_card_liability": float(live["amount"].sum()) / (p.revenue_t3 / 3)}


def _payables(w):
    bills = w.table("bills")
    unpaid = open_bills(w)
    if bills.empty or (w.last_12m(bills).empty and unpaid.empty):
        return {}
    values = {"ap_severe_overdue": severe_payables_share(w) or 0.0}
    due = bills[(bills["due_date"] > w.t6) & (bills["due_date"] <= w.as_of)]
    if not due.empty:
        on_time = due["paid_date"].notna() & (due["paid_date"] <= due["due_date"] + timedelta(days=1))
        values["bills_on_time"] = float(on_time.mean())
    purchases_t3 = float(w.last_3m(bills)["amount"].sum())
    if purchases_t3 > 0:
        days_payable = float(unpaid["balance"].sum()) / purchases_t3 * 90
        values["dpo_vs_terms"] = days_payable / _supplier_terms(w)
    return values


def _supplier_terms(w):
    suppliers = w.table("suppliers")
    terms = suppliers["payment_terms"] if not suppliers.empty else pd.Series(dtype=float)
    agreed = terms[terms > 0]
    return float(agreed.mean()) if not agreed.empty else DEFAULT_SUPPLIER_TERMS_DAYS
