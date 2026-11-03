"""Formality and compliance measures (methodology table 11)"""

import re
from datetime import timedelta

import pandas as pd

DIGITAL_METHOD = re.compile(r"m-?pesa|card|visa|master|pesapal|till|paybill|bank|airtel|mobile|eft|cheque", re.I)
COMPLETED_RECONCILIATION = ["completed", "complete", "reconciled"]
LAPSED_SUBSCRIPTION = ("past_due", "unpaid")
MIN_PAYMENTS = 5
MIN_RECEIPTABLE_SALES = 10
ETIMS_GOOD_SHARE = 0.90
REGISTERED_SCORE = 50.0


def formality_measures(w, p):
    values = {**_digital_payments(w), **_receipting(w), **_books(w)}
    if p.business_level:
        values["tax_compliance"] = tax_compliance(w)
        values["platform_standing"] = platform_standing(w.tenant)
    if p.purchase_base and p.supplier_tracking["traceability_index"] is not None:
        values["traceability"] = p.supplier_tracking["traceability_index"]
    return values


def _digital_payments(w):
    methods = w.last_12m(w.table("cash_in"))["method"].dropna().astype(str)
    methods = methods[methods.str.strip() != ""]
    if len(methods) < MIN_PAYMENTS:
        return {}
    return {"digital_payment_share": float(methods.str.contains(DIGITAL_METHOD).mean())}


def _receipting(w):
    orders = w.table("orders")
    first_receipt = orders.loc[orders["receipted"], "date"].min() if not orders.empty else None
    if first_receipt is None or pd.isna(first_receipt):
        return {}
    since = max(w.t12, first_receipt.to_period("M").start_time - timedelta(seconds=1))
    sales = w.between(orders, since, w.as_of)
    receipts = w.between(w.table("receipts"), since, w.as_of)
    total = len(sales) + len(receipts)
    if total < MIN_RECEIPTABLE_SALES:
        return {}
    return {"receipting": float(sales["receipted"].sum() + len(receipts)) / total}


def _books(w):
    values = {}
    entries = w.table("journal_entries")
    if not entries.empty:
        dates = entries["date"].fillna(entries["created"])
        if (dates <= w.as_of).any():
            values["bookkeeping_regularity"] = (
                len(set(dates[(dates > w.t6) & (dates <= w.as_of)].dt.to_period("M"))) / 6
            )
    reconciliations = w.table("bank_reconciliations")
    if not reconciliations.empty:
        done = reconciliations[reconciliations["status"].fillna("").str.lower().isin(COMPLETED_RECONCILIATION)]
        last = done["completed"].fillna(done["updated"]).max() if not done.empty else None
        if last is not None and pd.notna(last):
            values["reconciliation_recency"] = (w.as_of - last).days
    return values


def tax_compliance(w):
    """0 with neither VAT nor eTIMS; 50 once registered, rising to 100 at 90% of invoices eTIMS-verified"""
    tenant = w.tenant
    digitax = w.reports.get("digitax") or {}
    registered = bool(
        tenant.get("is_vat_enabled") or (tenant.get("modules") or {}).get("etims") or digitax.get("enabled")
    )
    if not registered:
        return 0.0
    invoices = w.last_12m(w.table("invoices"))
    accounting = invoices[invoices["source"] == "accounting"] if not invoices.empty else invoices
    verified = float(accounting["etims"].mean()) if not accounting.empty else 0.0
    return REGISTERED_SCORE + (100.0 - REGISTERED_SCORE) * min(verified / ETIMS_GOOD_SHARE, 1.0)


def platform_standing(tenant):
    status = str(tenant.get("subscription_status") or "").lower()
    current = str(tenant.get("current_subscription_status") or "").lower()
    if status == "active" and tenant.get("is_subscription_active") and current not in LAPSED_SUBSCRIPTION:
        return 100.0 if current in ("", "active") else 70.0
    if current == "past_due":
        return 30.0
    return 0.0
