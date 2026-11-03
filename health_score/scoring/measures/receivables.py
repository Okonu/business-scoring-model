"""Open receivables and payables with their days past due"""

import pandas as pd

from health_score.scoring import registry
from health_score.scoring.measures.window import ratio


def open_receivables(w, report="ar_aging", as_of=None):
    """(amount due, days past due) for every open invoice and rent invoice"""
    as_of = as_of or w.as_of
    items = [
        (float(invoice.get("amount_due") or 0), float(invoice.get("days_overdue") or 0))
        for aging in (w.reports.get(report) or {}).values()
        for customer in (aging or {}).get("customers") or []
        for invoice in customer.get("invoices") or []
    ]
    rent = w.table("rent_invoices")
    if not rent.empty:
        open_rent = rent[(rent["balance"].fillna(0) > 0) & (rent["date"] <= as_of)]
        for _, row in open_rent.iterrows():
            days = (as_of - row["due_date"]).days if pd.notna(row["due_date"]) else 0
            items.append((float(row["balance"]), float(max(days, 0))))
    return [(amount, days) for amount, days in items if amount > 0]


def severe_share(items, days=registry.SEVERE_OVERDUE_DAYS):
    total = sum(amount for amount, _ in items)
    return ratio(sum(amount for amount, d in items if d > days), total) if total > 0 else None


def open_bills(w):
    bills = w.table("bills")
    return bills[bills["balance"] > 1] if not bills.empty else bills


def severe_payables_share(w, days=registry.SEVERE_OVERDUE_DAYS):
    bills = open_bills(w)
    total = float(bills["balance"].sum()) if not bills.empty else 0.0
    if total <= 0:
        return None
    late = (w.as_of - bills["due_date"]).dt.days.fillna(0) > days
    return float(bills.loc[late, "balance"].sum()) / total


def collection_effectiveness(w):
    frames = []
    invoices = w.table("invoices")
    if not invoices.empty:
        accounting = invoices[
            (invoices["source"] == "accounting") & ~invoices["status"].fillna("").isin(["Draft", "Voided"])
        ]
        frames.append(accounting[["date", "due_date", "paid_date", "amount", "balance"]])
    rent = w.table("rent_invoices")
    if not rent.empty:
        frames.append(rent[["date", "due_date", "paid_date", "amount", "balance"]])
    if not frames:
        return None
    df = pd.concat(frames)
    start, end = w.t3, w.as_of
    opening = df[(df["date"] <= start) & (df["paid_date"].isna() | (df["paid_date"] > start))]["amount"].sum()
    sales = df[(df["date"] > start) & (df["date"] <= end)]["amount"].sum()
    closing = df[df["date"] <= end]["balance"].fillna(0).sum()
    closing_current = df[(df["date"] <= end) & (df["due_date"] > end)]["balance"].fillna(0).sum()
    denominator = opening + sales - closing_current
    return ratio(opening + sales - closing, denominator) if denominator > 0 else None
