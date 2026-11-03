"""Sales performance measures (methodology table 5)"""

from datetime import timedelta

import pandas as pd

from health_score.scoring import registry
from health_score.scoring.measures.window import ratio, trend

WON_LEAD_STAGES = ["won", "converted", "closed_won"]
MIN_LEADS = 3


def sales_measures(w, p):
    return {
        **_scale(w, p),
        **_growth(w, p),
        **_continuity(w, p),
        **_leakage(w, p),
        **_recurring(w, p),
        **_pipeline(w),
    }


def _scale(w, p):
    if not p.trading_days:
        return {}
    window_days = min(90, max((w.as_of - w.first_transaction).days, 1))
    return {
        "daily_txn_volume": len(p.tx_t3) / p.trading_days,
        "daily_txn_value": p.revenue_t3 / p.trading_days,
        "trading_days": min(p.trading_days / window_days, 1.0),
    }


def _growth(w, p):
    values = {}
    if p.history_days >= registry.TREND_MIN_HISTORY_DAYS:
        values["revenue_growth"] = trend(p.revenue_t3, p.revenue_p3)
        values["txn_count_trend"] = trend(len(p.tx_t3), len(p.tx_p3))
        if len(p.tx_t3) and len(p.tx_p3):
            values["avg_txn_value_trend"] = trend(p.revenue_t3 / len(p.tx_t3), p.revenue_p3 / len(p.tx_p3))
    if p.history_days >= registry.YOY_MIN_HISTORY_DAYS:
        values["yoy_growth"] = trend(p.revenue_t3, same_quarter_last_year(w))
    return values


def same_quarter_last_year(w):
    return w.revenue(w.as_of - timedelta(days=455), w.t12)


def _continuity(w, p):
    if w.first_transaction is None:
        return {}
    start = max(w.first_transaction.to_period("M"), (w.as_of - pd.DateOffset(months=11)).to_period("M"))
    months = pd.period_range(start, w.as_of.to_period("M"), freq="M")
    if len(months) < 3:
        return {}
    monthly = p.tx_t12.groupby(p.tx_t12["date"].dt.to_period("M"))["amount"].sum().reindex(months, fill_value=0)
    values = {"trading_continuity": float((monthly > 0).sum()) / len(months) * 12}
    if len(months) >= 6 and monthly.mean() > 0:
        values["revenue_volatility"] = float(monthly.std(ddof=0) / monthly.mean())
    return values


def _leakage(w, p):
    values = {}
    discounts = float(p.tx_t3["discount"].sum()) if not p.tx_t3.empty else 0.0
    if p.revenue_t3 > 0:
        values["revenue_leakage"] = discounts / (p.revenue_t3 + discounts)
    refunds = w.reports.get("refunds_summary")
    if refunds and p.business_level and "pesa" in (p.products or []):
        total = sum(
            float(row.get("total_amount") or 0)
            for row in refunds.get("summary") or []
            if str(row.get("_id", "")).lower() not in ("rejected", "cancelled")
        )
        values["refund_rate"] = ratio(total, float(w.transactions["amount"].sum()))
    return values


def _recurring(w, p):
    orders = w.last_12m(w.table("orders"))
    offered = not w.table("packages").empty or not w.table("leases").empty or orders["recurring"].any()
    if not offered or p.revenue_t12 <= 0:
        return {}
    recurring = float(orders.loc[orders["recurring"], "amount"].sum())
    rent = float(p.tx_t12.loc[p.tx_t12["source"] == "rent", "amount"].sum())
    return {"recurring_share": (recurring + rent) / p.revenue_t12}


def _pipeline(w):
    values = {}
    schedules = w.table("schedules")
    if not w.between(schedules, w.t12, w.as_of + timedelta(days=30)).empty:
        upcoming = len(w.between(schedules, w.as_of, w.as_of + timedelta(days=30)))
        recent = len(w.between(schedules, w.as_of - timedelta(days=30), w.as_of))
        values["forward_bookings"] = upcoming / recent if recent else (2.0 if upcoming else None)
    targets = w.table("sales_targets")
    if not targets.empty:
        targets = targets[(targets["type"].fillna("revenue") == "revenue") & (targets["target"] > 0)]
    targets = w.last_6m(targets, "end")
    if not targets.empty:
        actual = sum(w.revenue(row["start"], row["end"]) for _, row in targets.iterrows() if pd.notna(row["start"]))
        values["target_attainment"] = ratio(actual, targets["target"].sum())
    leads = w.last_6m(w.table("leads"))
    if len(leads) >= MIN_LEADS:
        won = leads["stage"].fillna("").str.lower().isin(WON_LEAD_STAGES) | leads["customer_id"].notna()
        values["lead_conversion"] = float(won.mean())
    return values
