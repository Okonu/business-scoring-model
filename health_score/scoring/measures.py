"""
Measure library for the business health score

`compute_measures(data)` returns the raw value of every measure that the
business's data supports, plus the context the engine needs (applicability
flags, supplier tracking, products in use, red-flag inputs). A measure whose
data doesn't exist is simply absent, never zero.
"""

import logging
import re
from datetime import timedelta

import numpy as np
import pandas as pd

from health_score.scoring import registry

logger = logging.getLogger(__name__)

DIGITAL_METHOD = re.compile(r"m-?pesa|card|visa|master|pesapal|till|paybill|bank|airtel|mobile|eft|cheque", re.I)
CASH_METHOD = re.compile(r"\bcash\b", re.I)
PAID_PAYROLL = {"processed", "approved", "paid", "completed"}


class Ctx:
    """Windows and helpers over one business (or one shop)"""

    def __init__(self, data):
        self.data = data
        self.t = data.table
        self.as_of = data.as_of
        self.t3 = self.as_of - timedelta(days=90)
        self.p3 = self.as_of - timedelta(days=180)
        self.t6 = self.as_of - timedelta(days=182)
        self.t12 = self.as_of - timedelta(days=365)
        tx = self.t("transactions")
        self.tx = tx[tx["date"] <= self.as_of] if not tx.empty else tx
        self.first_tx = self.tx["date"].min() if not self.tx.empty else None

    def between(self, df, start, end, col="date"):
        if df.empty or col not in df.columns:
            return df
        return df[(df[col] > start) & (df[col] <= end)]

    def rev(self, start, end):
        return float(self.between(self.tx, start, end)["amount"].sum())

    def history_days(self):
        return (self.as_of - self.first_tx).days if self.first_tx is not None else 0


def _ratio(a, b):
    if b is None or a is None or pd.isna(b) or b == 0:
        return None
    return float(a) / float(b)


def _trend(cur, prev):
    if prev is None or prev <= 0:
        return None
    return float(cur) / float(prev) - 1


# --------------------------------------------------------------------------
# Supplier tracking


def supplier_tracking(ctx):
    """
    Tier each supplier and compute the traceability index and tracking share

    Tier 1: purchases (PO or bill); tier 2: + inventory linked to the supplier;
    tier 3: + full chain (received delivery, bill, bill paid) and sales of its items.
    """
    t = ctx.t
    inv, po_items, bills, items = t("inventory"), t("po_items"), t("bills"), t("order_items")
    pos = ctx.between(po_items, ctx.t12, ctx.as_of)
    recent_bills = ctx.between(bills, ctx.t12, ctx.as_of)

    purchases = pd.concat(
        [
            pd.DataFrame({"supplier_id": pos["supplier_id"], "value": pos["received"] * pos["unit_price"]}),
            # Bills not raised from a purchase order (those are already counted above)
            pd.DataFrame(
                {
                    "supplier_id": recent_bills.loc[recent_bills["po_id"].isna(), "supplier_id"],
                    "value": recent_bills.loc[recent_bills["po_id"].isna(), "amount"],
                }
            ),
        ]
    ).dropna(subset=["supplier_id"])
    purchase_value = purchases.groupby("supplier_id")["value"].sum()

    tracked_inv = inv[inv["supplier_id"].notna()] if not inv.empty else inv
    inv_value = (inv["quantity"].clip(lower=0) * inv["cost"]) if not inv.empty else pd.Series(dtype=float)
    inv_value_by_supplier = (
        pd.Series(inv_value.values, index=inv["supplier_id"].fillna("__none__")).groupby(level=0).sum()
        if not inv.empty
        else pd.Series(dtype=float)
    )

    sold_names = set(ctx.between(items, ctx.t12, ctx.as_of)["name_key"]) if not items.empty else set()
    received_suppliers = set(pos.loc[pos["received"] > 0, "supplier_id"])
    billed = recent_bills.dropna(subset=["supplier_id"])
    paid_bill_suppliers = set(billed.loc[billed["paid_date"].notna() | (billed["balance"] <= 1), "supplier_id"])
    billed_suppliers = set(billed["supplier_id"])

    suppliers = (
        set(purchase_value.index) | set(tracked_inv["supplier_id"])
        if not tracked_inv.empty
        else set(purchase_value.index)
    )
    tiers = {}
    for s in suppliers:
        has_purchases = purchase_value.get(s, 0) > 0
        s_items = tracked_inv[tracked_inv["supplier_id"] == s] if not tracked_inv.empty else tracked_inv
        has_inventory = not s_items.empty
        if not has_purchases:
            tiers[s] = 0
        elif not has_inventory:
            tiers[s] = 1
        else:
            full_chain = (
                s in received_suppliers
                and s in billed_suppliers
                and s in paid_bill_suppliers
                and bool(set(s_items["name_key"]) & sold_names)
            )
            tiers[s] = 3 if full_chain else 2

    total_purchases = float(purchase_value.sum())
    tracked_purchases = float(sum(v for s, v in purchase_value.items() if tiers.get(s, 0) >= 2))
    tracking_share = _ratio(tracked_purchases, total_purchases) if total_purchases > 0 else None

    # Index weighted by inventory value; untracked inventory counts as tier 0
    index = None
    total_inv_value = float(inv_value_by_supplier.sum()) if not inv_value_by_supplier.empty else 0.0
    if total_inv_value > 0:
        index = sum(
            v / total_inv_value * registry.TIER_POINTS[tiers.get(s, 0) if s != "__none__" else 0]
            for s, v in inv_value_by_supplier.items()
        )
    elif total_purchases > 0:
        index = sum(v / total_purchases * registry.TIER_POINTS[tiers.get(s, 0)] for s, v in purchase_value.items())

    return {
        "tiers": tiers,
        "tier_counts": {k: sum(1 for v in tiers.values() if v == k) for k in (0, 1, 2, 3)},
        "tracking_share": tracking_share,
        "traceability_index": index,
        "purchase_value_12m": total_purchases,
        "has_supplier_data": total_purchases > 0 or not tracked_inv.empty,
    }


# --------------------------------------------------------------------------
# Cost of goods sold for items that can be matched to inventory


def _item_costs(ctx):
    """Latest purchase unit price per item, falling back to the inventory cost price"""
    inv, po_items = ctx.t("inventory"), ctx.t("po_items")
    cost = {}
    if not inv.empty:
        for _, r in inv.iterrows():
            if r["cost"] > 0 and r["name_key"]:
                cost[r["name_key"]] = (r["cost"], "cost_price", r["supplier_id"])
    if not po_items.empty:
        latest = po_items[po_items["unit_price"] > 0].sort_values("date").groupby("name_key").tail(1)
        for _, r in latest.iterrows():
            if r["name_key"]:
                cost[r["name_key"]] = (r["unit_price"], "purchase_price", r["supplier_id"])
    return cost


def _cogs(ctx, start, end, tracked_only=False):
    """Revenue, matched revenue, COGS and units for items sold in a window"""
    items = ctx.between(ctx.t("order_items"), start, end)
    costs = _item_costs(ctx)
    inv = ctx.t("inventory")
    tracked = set(inv.loc[inv["supplier_id"].notna(), "name_key"]) if not inv.empty else set()
    if items.empty:
        return 0.0, 0.0, 0.0, 0.0
    if tracked_only:
        items = items[items["name_key"].isin(tracked)]
    matched = items[items["name_key"].isin(costs.keys())]
    # Mapping a string column keeps its dtype under pandas 3 with pyarrow, so force numbers
    unit_cost = pd.to_numeric(
        matched["name_key"].map({k: c[0] for k, c in costs.items()}).astype(object), errors="coerce"
    ).fillna(0.0)
    cogs = float((matched["quantity"] * unit_cost).sum())
    return float(items["amount"].sum()), float(matched["amount"].sum()), cogs, float(items["quantity"].sum())


# --------------------------------------------------------------------------
# Products in use


def products_in_use(ctx):
    """BASE products with activity in the last 3 months"""
    t, s, e = ctx.t, ctx.t3, ctx.as_of
    active = {
        "duka": not ctx.between(t("orders"), s, e).empty,
        "pesa": any(not ctx.between(t(n), s, e).empty for n in ("receipts", "expenses", "bills"))
        or not ctx.between(
            t("invoices")[t("invoices")["source"] == "accounting"] if not t("invoices").empty else t("invoices"), s, e
        ).empty,
        "bandu": not ctx.between(t("payroll"), s, e, "period_start").empty
        or not ctx.between(t("leave"), s, e, "start").empty,
        "mteja": not ctx.between(t("leads"), s, e).empty or not ctx.between(t("sales_targets"), s, e, "end").empty,
        "dala": any(
            not ctx.between(t(n), s, e).empty
            for n in ("rent_invoices", "rent_payments", "property_sale_payments", "maintenance")
        ),
    }
    return [p for p, on in active.items() if on]


# --------------------------------------------------------------------------
# Receivables from Pesa aging reports and Dala rent


def _ar_items(ctx, report="ar_aging", as_of=None):
    """(amount_due, days_overdue) for every open receivable"""
    as_of = as_of or ctx.as_of
    rows = []
    for rep in (ctx.data.reports.get(report) or {}).values():
        for cust in (rep or {}).get("customers") or []:
            for inv in cust.get("invoices") or []:
                rows.append((float(inv.get("amount_due") or 0), float(inv.get("days_overdue") or 0)))
    rent = ctx.t("rent_invoices")
    if not rent.empty:
        open_rent = rent[(rent["balance"].fillna(0) > 0) & (rent["date"] <= as_of)]
        for _, r in open_rent.iterrows():
            days = (as_of - r["due_date"]).days if pd.notna(r["due_date"]) else 0
            rows.append((float(r["balance"]), float(max(days, 0))))
    return [(a, d) for a, d in rows if a > 0]


def _severe_share(items, days=60):
    total = sum(a for a, _ in items)
    return _ratio(sum(a for a, d in items if d > days), total) if total > 0 else None


# --------------------------------------------------------------------------
# All measures


def compute_measures(data, business_level=True):
    """
    Raw values for every measure the data supports

    Returns:
        tuple: (values: {measure_id: float}, context: dict)
    """
    ctx = Ctx(data)
    t, v = ctx.t, {}
    tx = ctx.tx
    as_of, t3, p3, t6, t12 = ctx.as_of, ctx.t3, ctx.p3, ctx.t6, ctx.t12
    history = ctx.history_days()

    tx_t3 = ctx.between(tx, t3, as_of)
    tx_p3 = ctx.between(tx, p3, t3)
    tx_t12 = ctx.between(tx, t12, as_of)
    rev_t3, rev_p3, rev_t12 = float(tx_t3["amount"].sum()), float(tx_p3["amount"].sum()), float(tx_t12["amount"].sum())
    credit_share = _ratio(tx_t12.loc[tx_t12["credit"] == True, "amount"].sum(), rev_t12) if rev_t12 > 0 else None
    cash_business = credit_share is not None and credit_share < registry.CASH_BUSINESS_CREDIT_SHARE
    identified_share = (
        _ratio(tx_t12.loc[tx_t12["customer_key"].notna(), "amount"].sum(), rev_t12) if rev_t12 > 0 else None
    )
    walk_in = identified_share is not None and identified_share < registry.WALK_IN_IDENTIFIED_SHARE

    # ---------------------------------------------------------------- sales
    trading_days = tx_t3["date"].dt.normalize().nunique() if not tx_t3.empty else 0
    if trading_days:
        v["daily_txn_volume"] = len(tx_t3) / trading_days
        v["daily_txn_value"] = rev_t3 / trading_days
        window_days = min(90, max((as_of - ctx.first_tx).days, 1))
        v["trading_days"] = min(trading_days / window_days, 1.0)
    if history >= 180:
        v["revenue_growth"] = _trend(rev_t3, rev_p3)
        v["txn_count_trend"] = _trend(len(tx_t3), len(tx_p3))
        if len(tx_t3) and len(tx_p3):
            v["avg_txn_value_trend"] = _trend(rev_t3 / len(tx_t3), rev_p3 / len(tx_p3))
    if history >= 455:
        v["yoy_growth"] = _trend(rev_t3, ctx.rev(as_of - timedelta(days=455), t12))
    if ctx.first_tx is not None:
        start_month = max(ctx.first_tx.to_period("M"), (as_of - pd.DateOffset(months=11)).to_period("M"))
        months = pd.period_range(start_month, as_of.to_period("M"), freq="M")
        if len(months) >= 3:
            monthly = tx_t12.groupby(tx_t12["date"].dt.to_period("M"))["amount"].sum().reindex(months, fill_value=0)
            v["trading_continuity"] = float((monthly > 0).sum()) / len(months) * 12
            if len(months) >= 6 and monthly.mean() > 0:
                v["revenue_volatility"] = float(monthly.std(ddof=0) / monthly.mean())
    discounts = float(tx_t3["discount"].sum())
    if rev_t3 > 0:
        v["revenue_leakage"] = discounts / (rev_t3 + discounts)
    refunds = data.reports.get("refunds_summary")
    if refunds and business_level and "pesa" in products_in_use(ctx):
        total_refunds = sum(
            float(r.get("total_amount") or 0)
            for r in (refunds.get("summary") or [])
            if str(r.get("_id", "")).lower() not in ("rejected", "cancelled")
        )
        v["refund_rate"] = _ratio(total_refunds, float(tx["amount"].sum()))
    orders_t12 = ctx.between(t("orders"), t12, as_of)
    offers_recurring = not t("packages").empty or not t("leases").empty or orders_t12["recurring"].any()
    if offers_recurring and rev_t12 > 0:
        recurring = float(orders_t12.loc[orders_t12["recurring"], "amount"].sum()) + float(
            tx_t12.loc[tx_t12["source"] == "rent", "amount"].sum()
        )
        v["recurring_share"] = recurring / rev_t12
    sched = t("schedules")
    if not ctx.between(sched, t12, as_of + timedelta(days=30)).empty:
        nxt = len(ctx.between(sched, as_of, as_of + timedelta(days=30)))
        last = len(ctx.between(sched, as_of - timedelta(days=30), as_of))
        v["forward_bookings"] = nxt / last if last else (2.0 if nxt else None)
    targets = t("sales_targets")
    targets = (
        targets[(targets["type"].fillna("revenue") == "revenue") & (targets["target"] > 0)]
        if not targets.empty
        else targets
    )
    targets = ctx.between(targets, t6, as_of, "end")
    if not targets.empty:
        actual = sum(ctx.rev(r["start"], r["end"]) for _, r in targets.iterrows() if pd.notna(r["start"]))
        v["target_attainment"] = _ratio(actual, targets["target"].sum())
    leads = ctx.between(t("leads"), t6, as_of)
    if len(leads) >= 3:
        won = (
            leads["stage"].fillna("").str.lower().isin(["won", "converted", "closed_won"])
            | leads["customer_id"].notna()
        )
        v["lead_conversion"] = float(won.mean())

    # ------------------------------------------------------ cash & payables
    cash_in = ctx.between(t("cash_in"), t3, as_of)
    if rev_t3 > 0:
        v["cash_realization"] = float(cash_in["amount"].sum()) / rev_t3
    if not cash_business and credit_share is not None:
        ar = _ar_items(ctx)
        ar_total = sum(a for a, _ in ar)
        credit_t3 = float(tx_t3.loc[tx_t3["credit"] == True, "amount"].sum())
        uses_ar = bool(data.reports.get("ar_aging")) or not t("rent_invoices").empty
        if uses_ar:
            v["ar_severe_overdue"] = _severe_share(ar) if ar_total > 0 else 0.0
            if ar_total > 0:
                v["ar_wadpd"] = sum(a * max(d, 0) for a, d in ar) / ar_total
            if credit_t3 > 0:
                v["dso"] = ar_total / credit_t3 * 90
            prev = _severe_share(_ar_items(ctx, "ar_aging_prev", t3))
            now = _severe_share(ar)
            if prev is not None and now is not None:
                v["aging_drift"] = now - prev
            v["cei"] = _cei(ctx)
        elif credit_t3 > 0:
            balances = float(t("customers")["balance"].clip(lower=0).sum()) if not t("customers").empty else 0
            if balances > 0:
                v["dso"] = balances / credit_t3 * 90
        cust = t("customers")
        limited = cust[cust["credit_limit"] > 0] if not cust.empty else cust
        if len(limited) >= 3:
            v["credit_limit_breach"] = float((limited["balance"] > limited["credit_limit"]).mean())

    rent = ctx.between(t("rent_invoices"), t3, as_of, "due_date")
    if not rent.empty and rent["amount"].sum() > 0:
        v["rent_collection"] = float(rent["paid"].fillna(0).sum() / rent["amount"].sum())
    v["plan_collection"] = _plan_collection(ctx)
    cards = t("gift_cards")
    if not cards.empty and rev_t3 > 0:
        live = cards[(cards["active"] == True) & ((cards["expiry"].isna()) | (cards["expiry"] > as_of))]
        v["gift_card_liability"] = float(live["amount"].sum()) / (rev_t3 / 3)
    bills = t("bills")
    if not bills.empty:
        open_bills = bills[bills["balance"] > 1]
        if not ctx.between(bills, t12, as_of).empty or not open_bills.empty:
            open_total = float(open_bills["balance"].sum())
            days = (as_of - open_bills["due_date"]).dt.days.fillna(0)
            v["ap_severe_overdue"] = (
                float(open_bills.loc[days > 60, "balance"].sum()) / open_total if open_total > 0 else 0.0
            )
            due = bills[(bills["due_date"] > t6) & (bills["due_date"] <= as_of)]
            if not due.empty:
                on_time = due["paid_date"].notna() & (due["paid_date"] <= due["due_date"] + timedelta(days=1))
                v["bills_on_time"] = float(on_time.mean())
            purchases_t3 = float(ctx.between(bills, t3, as_of)["amount"].sum())
            terms = t("suppliers")["payment_terms"] if not t("suppliers").empty else pd.Series(dtype=float)
            avg_terms = float(terms[terms > 0].mean()) if (terms > 0).any() else 30.0
            if purchases_t3 > 0:
                v["dpo_vs_terms"] = (open_total / purchases_t3 * 90) / avg_terms

    # --------------------------------------------------------- profitability
    # Ledger figures count only when the books reflect at least 80% of observed sales
    pl = [r for r in (data.reports.get("profit_loss") or {}).values() if r]
    pl_rev = sum(float((r.get("revenue") or {}).get("total_revenue") or 0) for r in pl)
    books_coverage = _ratio(pl_rev, rev_t12) if rev_t12 > 0 else None
    books_reliable = books_coverage is not None and books_coverage >= 0.8
    gm = _gross_margin(ctx, pl if books_reliable else [])
    if gm is not None:
        v["gross_margin"] = gm
    if books_reliable and pl_rev > 0:
        v["net_margin"] = sum(float(r.get("net_profit") or 0) for r in pl) / pl_rev
    if business_level and books_reliable:
        v["cash_runway"] = _cash_runway(data)
    payroll = t("payroll")
    paid_payroll = (
        payroll[payroll["status"].fillna("").str.lower().isin(PAID_PAYROLL)] if not payroll.empty else payroll
    )
    payroll_t3 = ctx.between(paid_payroll, t3, as_of, "period_start")
    if not payroll_t3.empty and rev_t3 > 0:
        v["staff_cost_ratio"] = float(payroll_t3["gross"].sum()) / rev_t3
    exp = t("expenses")
    if not exp.empty:
        exp = exp[exp["status"].fillna("").str.lower().isin(["approved", "paid", "posted"])]
        e_t3, e_p3 = float(ctx.between(exp, t3, as_of)["amount"].sum()), float(ctx.between(exp, p3, t3)["amount"].sum())
        eg, rg = _trend(e_t3, e_p3), _trend(rev_t3, rev_p3)
        if eg is not None and rg is not None:
            v["cost_discipline"] = eg - rg
    staff = _staff_count(ctx)
    if staff and rev_t3 > 0:
        v["revenue_per_staff"] = rev_t3 / 3 / staff
    maint = ctx.between(t("maintenance"), t12, as_of)
    rent_t12 = float(tx_t12.loc[tx_t12["source"] == "rent", "amount"].sum())
    if not maint.empty and rent_t12 > 0:
        cost = maint["cost"].where(maint["cost"] > 0, maint["estimate"]).fillna(0)
        v["maintenance_ratio"] = float(cost.sum()) / rent_t12
    comm = t("commissions")
    if not comm.empty and comm["sale_price"].sum() > 0:
        v["commission_ratio"] = float(comm["amount"].sum() / comm["sale_price"].sum())
    # Purchase-pattern measures need a minimum number of purchase documents
    purchase_docs = ctx.between(t("purchase_orders"), t12, as_of)
    purchase_docs = (
        purchase_docs[purchase_docs["status"].fillna("").str.lower() != "cancelled"]
        if not purchase_docs.empty
        else purchase_docs
    )
    enough_purchases = len(purchase_docs) + len(ctx.between(bills, t12, as_of)) >= registry.MIN_PURCHASE_DOCUMENTS
    po_t3 = ctx.between(t("po_items"), t3, as_of)
    _, _, tracked_cogs_t3, _ = _cogs(ctx, t3, as_of, tracked_only=True)
    purchases_tracked_t3 = float((po_t3["received"] * po_t3["unit_price"]).sum()) if not po_t3.empty else 0.0
    if enough_purchases and tracked_cogs_t3 > 0:
        v["purchase_alignment"] = purchases_tracked_t3 / tracked_cogs_t3
    elif enough_purchases and purchases_tracked_t3 > 0:
        v["purchase_alignment"] = 10.0  # buying stock that isn't selling

    # ----------------------------------------------------- customers & revenue
    if rev_t12 > 0 and not walk_in and identified_share is not None:
        by_cust = tx_t12.dropna(subset=["customer_key"]).groupby("customer_key")["amount"].sum()
        if len(by_cust) >= 2:
            v["top_customer_share"] = float(by_cust.max() / rev_t12)
            shares = by_cust / by_cust.sum()
            v["customer_hhi"] = float((shares**2).sum())
        c_t3 = set(tx_t3["customer_key"].dropna())
        c_p3 = set(tx_p3["customer_key"].dropna())
        if len(c_p3) >= 3:
            v["customer_retention"] = len(c_p3 & c_t3) / len(c_p3)
            v["active_customer_trend"] = _trend(len(c_t3), len(c_p3))
    elif walk_in and history >= 180:
        v["active_customer_trend"] = _trend(len(tx_t3), len(tx_p3))
    if len(tx_t12) >= 10 and rev_t12 > 0:
        v["txn_breadth"] = float(tx_t12["amount"].max() / rev_t12)
    items_t12 = ctx.between(t("order_items"), t12, as_of)
    if not items_t12.empty and items_t12["amount"].sum() > 0:
        by_product = items_t12.groupby("name_key")["amount"].sum()
        if len(by_product) >= 3:
            v["product_concentration"] = float(by_product.max() / by_product.sum())
    cust = t("customers")
    if not cust.empty:
        first_seen = cust.groupby("key")["created"].min()
        v["new_customer_trend"] = _trend(
            int(((first_seen > t3) & (first_seen <= as_of)).sum()), int(((first_seen > p3) & (first_seen <= t3)).sum())
        )
    visits = t("visits")
    if not visits.empty:
        v["visit_trend"] = _trend(len(ctx.between(visits, t3, as_of)), len(ctx.between(visits, p3, t3)))
        ratings = visits["rating"].dropna()
        if len(ratings) >= 3:
            v["satisfaction"] = float(ratings.mean())
    if rev_t12 > 0 and not cust.empty and ((cust["loyalty"] > 0).any() or not t("packages").empty):
        loyal = set(cust.loc[cust["loyalty"] > 0, "key"])
        loyal_rev = tx_t12.loc[tx_t12["customer_key"].isin(loyal), "amount"].sum()
        v["loyalty_engagement"] = float(loyal_rev + orders_t12.loc[orders_t12["recurring"], "amount"].sum()) / rev_t12
    if not cust.empty and cust["stage"].notna().any() and rev_t12 > 0 and not walk_in:
        risky = set(cust.loc[cust["stage"].fillna("").isin(["at_risk", "churned"]), "key"])
        v["at_risk_share"] = float(tx_t12.loc[tx_t12["customer_key"].isin(risky), "amount"].sum()) / rev_t12

    # ------------------------------------------------------------ operations
    started = ctx.first_tx
    created = pd.to_datetime(data.tenant.get("createdAt"), errors="coerce", utc=True)
    if business_level and pd.notna(created):
        created = created.tz_localize(None)
        started = min(started, created) if started is not None else created
    if started is not None:
        v["tenure"] = (as_of - started).days / 30.44
    emp = t("employees")
    if not emp.empty:

        def active_at(d):
            return int(
                (
                    (emp["hired"].isna() | (emp["hired"] <= d)) & (emp["terminated"].isna() | (emp["terminated"] > d))
                ).sum()
            )

        now_n, prev_n, year_n = active_at(as_of), active_at(as_of - timedelta(days=182)), active_at(t12)
        if prev_n >= 1:
            v["staff_trend"] = _trend(now_n, prev_n)
        avg_n = (now_n + year_n) / 2
        if avg_n >= 1:
            v["staff_turnover"] = int(ctx.between(emp, t12, as_of, "terminated").shape[0]) / avg_n
        leave = ctx.between(t("leave"), t12, as_of, "start")
        if not leave.empty and now_n:
            leave = leave[leave["status"].fillna("").str.lower() == "approved"]
            unplanned = leave[~leave["type"].fillna("").str.lower().str.contains("annual")]
            v["unplanned_leave"] = float(unplanned["days"].fillna(0).sum()) / (now_n * 260)
    if not paid_payroll.empty:
        past = paid_payroll[paid_payroll["period_start"] <= as_of]
        if not past.empty:
            months_run = set(ctx.between(past, t6, as_of, "period_start")["period_start"].dt.to_period("M"))
            expected = min(6, max(1, (as_of.to_period("M") - past["period_start"].min().to_period("M")).n + 1))
            v["payroll_regularity"] = min(len(months_run) / expected, 1.0)
            year_runs = ctx.between(past, t12, as_of, "period_start")
            if not year_runs.empty:
                v["statutory_compliance"] = float(
                    ((year_runs["paye"].fillna(0) > 0) | (year_runs["nssf"].fillna(0) > 0)).mean()
                )
    earners = t("top_earners")
    if business_level and not earners.empty and earners["earnings"].sum() > 0:
        v["key_person"] = float(earners["earnings"].max() / earners["earnings"].sum())
    inv = t("inventory")
    selling = inv[inv["selling"] & inv["active"]] if not inv.empty else inv
    if not selling.empty:
        with_min = selling[selling["min_qty"] > 0]
        if len(with_min) >= 3:
            v["stockout_rate"] = float((with_min["quantity"] < with_min["min_qty"]).mean())
        value = selling["quantity"].clip(lower=0) * selling["cost"]
        if value.sum() > 0:
            sold_90 = set(ctx.between(t("order_items"), t3, as_of)["name_key"])
            v["dead_stock"] = float(value[~selling["name_key"].isin(sold_90)].sum() / value.sum())
            _, _, cogs_t12, _ = _cogs(ctx, t12, as_of)
            if cogs_t12 > 0:
                v["inventory_turnover"] = cogs_t12 / float(value.sum())
    catalogue = set(
        pd.concat(
            [
                t("products")["name"],
                t("services")["name"],
                selling["name"] if not selling.empty else pd.Series(dtype=str),
            ]
        )
        .dropna()
        .str.strip()
        .str.lower()
    )
    if len(catalogue) >= 5:
        sold = set(ctx.between(t("order_items"), t3, as_of)["name_key"])
        v["catalogue_activity"] = len(catalogue & sold) / len(catalogue)
    tables = t("tables")
    table_orders = ctx.between(t("orders"), t3, as_of)
    table_orders = table_orders[table_orders["table_id"].notna()] if not table_orders.empty else table_orders
    if not tables.empty and not table_orders.empty and trading_days:
        v["capacity_utilization"] = len(table_orders) / (len(tables) * trading_days)
    units = t("units")
    if not units.empty:
        v["occupancy"] = float(units["status"].fillna("").str.lower().isin(["occupied", "leased", "sold"]).mean())
    maint_all = t("maintenance")
    if not maint_all.empty:
        open_t = maint_all[
            ~maint_all["status"].fillna("").str.lower().isin(["closed", "resolved", "completed", "cancelled"])
        ]
        if not open_t.empty:
            v["maintenance_backlog"] = float((open_t["date"] < as_of - timedelta(days=30)).mean())
    tracking = supplier_tracking(ctx)
    po_t12 = ctx.between(t("po_items"), t12, as_of)
    purchase_by_supplier = (
        pd.concat(
            [
                pd.DataFrame({"s": po_t12["supplier_id"], "v": po_t12["received"] * po_t12["unit_price"]}),
                pd.DataFrame(
                    {
                        "s": ctx.between(bills, t12, as_of)["supplier_id"] if not bills.empty else pd.Series(dtype=str),
                        "v": ctx.between(bills, t12, as_of)["amount"] if not bills.empty else pd.Series(dtype=float),
                    }
                ),
            ]
        )
        .dropna(subset=["s"])
        .groupby("s")["v"]
        .sum()
    )
    if enough_purchases and purchase_by_supplier.sum() > 0:
        v["supplier_concentration"] = float(purchase_by_supplier.max() / purchase_by_supplier.sum())
        months = set(po_t12.loc[po_t12["date"] > t6, "date"].dt.to_period("M"))
        if not bills.empty:
            months |= set(ctx.between(bills, t6, as_of)["date"].dt.to_period("M"))
        v["procurement_regularity"] = len(months) / 6
    po_t6 = ctx.between(t("po_items"), t6, as_of - timedelta(days=7))
    if enough_purchases and not po_t6.empty and po_t6["ordered"].sum() > 0:
        v["fill_rate"] = float(po_t6["received"].sum() / po_t6["ordered"].sum())
    received_t6 = float(ctx.between(t("po_items"), t6, as_of)["received"].sum())
    if enough_purchases and received_t6 > 0:
        inv_tracked = set(inv.loc[inv["supplier_id"].notna(), "name_key"]) if not inv.empty else set()
        sold_t6 = ctx.between(t("order_items"), t6, as_of)
        v["sell_through"] = float(sold_t6.loc[sold_t6["name_key"].isin(inv_tracked), "quantity"].sum()) / received_t6
    if enough_purchases and not inv.empty and inv["supplier_id"].notna().any():
        tracked_items = inv[inv["supplier_id"].notna()]
        _, _, _, units_t3 = _cogs(ctx, t3, as_of, tracked_only=True)
        qty = float(tracked_items["quantity"].clip(lower=0).sum())
        if units_t3 > 0:
            v["stock_cover"] = qty / (units_t3 / 90)
        elif qty > 0:
            v["stock_cover"] = 999.0

    # ------------------------------------------------------------- formality
    methods = ctx.between(t("cash_in"), t12, as_of)["method"].dropna().astype(str)
    methods = methods[methods.str.strip() != ""]
    if len(methods) >= 5:
        digital = methods.str.contains(DIGITAL_METHOD)
        v["digital_payment_share"] = float(digital.mean())
    if business_level:
        v["tax_compliance"] = _tax_compliance(ctx)
    # Receipt numbers only exist since a BASEPOINT update, so count from the first receipted order
    all_orders = t("orders")
    first_receipt = all_orders.loc[all_orders["receipted"], "date"].min() if not all_orders.empty else None
    if first_receipt is not None and pd.notna(first_receipt):
        since = max(t12, first_receipt.to_period("M").start_time - timedelta(seconds=1))
        pos_window = ctx.between(all_orders, since, as_of)
        receipts_window = ctx.between(t("receipts"), since, as_of)
        if len(pos_window) + len(receipts_window) >= 10:
            v["receipting"] = float(pos_window["receipted"].sum() + len(receipts_window)) / (
                len(pos_window) + len(receipts_window)
            )
    je = t("journal_entries")
    if not je.empty:
        dates = je["date"].fillna(je["created"])
        if (dates <= as_of).any():
            v["bookkeeping_regularity"] = len(set(dates[(dates > t6) & (dates <= as_of)].dt.to_period("M"))) / 6
    recs = t("bank_reconciliations")
    if not recs.empty:
        done = recs[recs["status"].fillna("").str.lower().isin(["completed", "complete", "reconciled"])]
        last = done["completed"].fillna(done["updated"]).max() if not done.empty else None
        if last is not None and pd.notna(last):
            v["reconciliation_recency"] = (as_of - last).days
    if business_level:
        v["platform_standing"] = _platform_standing(data.tenant)
        in_use = products_in_use(ctx)
        if in_use:
            v["ecosystem_depth"] = registry.ECOSYSTEM_SCORES[min(len(in_use), 4)]
    if tracking["traceability_index"] is not None:
        v["traceability"] = tracking["traceability_index"]

    values = {k: float(x) for k, x in v.items() if x is not None and np.isfinite(x)}
    context = {
        "credit_share": credit_share,
        "cash_business": cash_business,
        "identified_customer_share": identified_share,
        "walk_in": walk_in,
        "history_days": history,
        "first_transaction": ctx.first_tx.isoformat() if ctx.first_tx is not None else None,
        "revenue_t3m": rev_t3,
        "revenue_p3m": rev_p3,
        "revenue_t12m": rev_t12,
        "books_coverage": books_coverage,
        "books_reliable": books_reliable,
        "transactions_t3m": int(len(tx_t3)),
        "supplier_tracking": tracking,
        "purchase_documents_12m": int(len(purchase_docs) + len(ctx.between(bills, t12, as_of))),
        "products_in_use": products_in_use(ctx) if business_level else None,
        "red_flag_inputs": {
            "ar_120_share": _severe_share(_ar_items(ctx), 120),
            "ap_90_share": _ap_share(ctx, 90),
            "missed_payroll": _missed_payroll(ctx, paid_payroll),
        },
    }
    return values, context


# ------------------------------------------------------------------ helpers


def _cei(ctx):
    """Collection effectiveness over the last 3 months, from invoices and rent"""
    s, e = ctx.t3, ctx.as_of
    frames = []
    inv = ctx.t("invoices")
    if not inv.empty:
        acc = inv[(inv["source"] == "accounting") & ~inv["status"].fillna("").isin(["Draft", "Voided"])]
        frames.append(acc[["date", "due_date", "paid_date", "amount", "balance"]])
    rent = ctx.t("rent_invoices")
    if not rent.empty:
        frames.append(rent[["date", "due_date", "paid_date", "amount", "balance"]])
    if not frames:
        return None
    df = pd.concat(frames)
    opening = df[(df["date"] <= s) & (df["paid_date"].isna() | (df["paid_date"] > s))]["amount"].sum()
    sales = df[(df["date"] > s) & (df["date"] <= e)]["amount"].sum()
    closing = df[df["date"] <= e]["balance"].fillna(0).sum()
    closing_current = df[(df["date"] <= e) & (df["due_date"] > e)]["balance"].fillna(0).sum()
    denominator = opening + sales - closing_current
    return _ratio(opening + sales - closing, denominator) if denominator > 0 else None


def _cash_runway(data):
    accounts = data.table("bank_accounts")
    flows = [r for r in (data.reports.get("cash_flow") or {}).values() if r]
    outflow = 0.0
    for rep in flows:
        for acc in rep.get("accounts") or []:
            outflow += float(acc.get("outflows") or 0)
    if accounts.empty or outflow <= 0:
        return None
    balance = float(accounts["balance"].fillna(0).sum())
    return max(balance, 0.0) / (outflow / 3)


def _plan_collection(ctx):
    plans = ctx.t("payment_plans")
    if plans.empty:
        return None
    plans = plans[plans["start"] <= ctx.as_of]
    expected = paid = 0.0
    for _, p in plans.iterrows():
        elapsed = (ctx.as_of.to_period("M") - p["start"].to_period("M")).n + 1
        n = int(p["installments"] or 0)
        due = (p["deposit"] or 0) + (p["installment"] or 0) * min(max(elapsed, 0), n)
        expected += min(due, p["total"] or due)
        paid += (p["total"] or 0) - (p["outstanding"] or 0)
    return min(paid / expected, 1.5) if expected > 0 else None


def _gross_margin(ctx, pl):
    """
    Prefer the P&L's cost of sales (if the books are reliable); otherwise
    item-level costs covering 80%+ of item sales
    """
    rev = sum(float((r.get("revenue") or {}).get("total_revenue") or 0) for r in pl)
    cogs = sum(
        float(a.get("amount") or 0)
        for r in pl
        for a in (r.get("expenses") or {}).get("accounts") or []
        if re.search(
            r"cost of (goods|sales)|cogs|purchases", f"{a.get('account_subtype')} {a.get('account_name')}", re.I
        )
    )
    if rev > 0 and cogs > 0:
        return (rev - cogs) / rev
    item_rev, matched_rev, item_cogs, _ = _cogs(ctx, ctx.t12, ctx.as_of)
    if item_rev > 0 and matched_rev / item_rev >= 0.8 and matched_rev > 0:
        return (matched_rev - item_cogs) / matched_rev
    return None


def _staff_count(ctx):
    emp = ctx.t("employees")
    if not emp.empty:
        n = int((emp["terminated"].isna() | (emp["terminated"] > ctx.as_of)).sum())
        if n:
            return n
    shops = ctx.t("shops")
    return float(shops["staff_count"].sum()) if not shops.empty else 0


def _tax_compliance(ctx):
    tenant = ctx.data.tenant
    digitax = ctx.data.reports.get("digitax") or {}
    registered = bool(
        tenant.get("is_vat_enabled") or (tenant.get("modules") or {}).get("etims") or digitax.get("enabled")
    )
    inv = ctx.between(ctx.t("invoices"), ctx.t12, ctx.as_of)
    acc = inv[inv["source"] == "accounting"] if not inv.empty else inv
    verified = float(acc["etims"].mean()) if not acc.empty else 0.0
    return (50.0 if registered else 0.0) + 50.0 * verified


def _platform_standing(tenant):
    status = str(tenant.get("subscription_status") or "").lower()
    current = str(tenant.get("current_subscription_status") or "").lower()
    if status == "active" and tenant.get("is_subscription_active") and current not in ("past_due", "unpaid"):
        return 100.0 if current in ("", "active") else 70.0
    if current in ("past_due",):
        return 30.0
    return 0.0


def _ap_share(ctx, days):
    bills = ctx.t("bills")
    if bills.empty:
        return None
    open_bills = bills[bills["balance"] > 1]
    total = float(open_bills["balance"].sum())
    if total <= 0:
        return None
    late = (ctx.as_of - open_bills["due_date"]).dt.days.fillna(0) > days
    return float(open_bills.loc[late, "balance"].sum()) / total


def _missed_payroll(ctx, paid_payroll):
    """True if a business that runs payroll has none in the last 2 months"""
    if paid_payroll.empty:
        return False
    past = paid_payroll[paid_payroll["period_start"] <= ctx.as_of]
    prior = ctx.between(past, ctx.as_of - timedelta(days=182), ctx.as_of - timedelta(days=61), "period_start")
    recent = ctx.between(past, ctx.as_of - timedelta(days=61), ctx.as_of, "period_start")
    return len(set(prior["period_start"].dt.to_period("M"))) >= 3 and recent.empty
