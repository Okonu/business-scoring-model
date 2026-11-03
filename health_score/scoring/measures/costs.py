"""Cost of goods sold for items that can be matched to a purchase or cost price"""

import re
from dataclasses import dataclass

import pandas as pd

from health_score.scoring import registry

COST_OF_SALES = re.compile(r"cost of (goods|sales)|cogs|purchases", re.I)


@dataclass(frozen=True)
class ItemSales:
    revenue: float
    matched_revenue: float
    cogs: float
    units: float


def item_costs(w):
    """Latest purchase unit price per item, falling back to the inventory cost price"""
    costs = {}
    inventory = w.table("inventory")
    for _, row in inventory.iterrows():
        if row["cost"] > 0 and row["name_key"]:
            costs[row["name_key"]] = row["cost"]
    po_lines = w.table("po_items")
    if not po_lines.empty:
        latest = po_lines[po_lines["unit_price"] > 0].sort_values("date").groupby("name_key").tail(1)
        for _, row in latest.iterrows():
            if row["name_key"]:
                costs[row["name_key"]] = row["unit_price"]
    return costs


def tracked_items(w):
    inventory = w.table("inventory")
    return set(inventory.loc[inventory["supplier_id"].notna(), "name_key"]) if not inventory.empty else set()


def item_sales(w, start, end, tracked_only=False):
    items = w.between(w.table("order_items"), start, end)
    if items.empty:
        return ItemSales(0.0, 0.0, 0.0, 0.0)
    if tracked_only:
        items = items[items["name_key"].isin(tracked_items(w))]
    costs = item_costs(w)
    matched = items[items["name_key"].isin(costs.keys())]
    unit_cost = pd.to_numeric(matched["name_key"].map(costs).astype(object), errors="coerce").fillna(0.0)
    return ItemSales(
        revenue=float(items["amount"].sum()),
        matched_revenue=float(matched["amount"].sum()),
        cogs=float((matched["quantity"] * unit_cost).sum()),
        units=float(items["quantity"].sum()),
    )


def gross_margin(w, profit_loss):
    """Ledger cost of sales when the books are reliable, else item costs covering 80%+ of item sales"""
    revenue = sum(float((r.get("revenue") or {}).get("total_revenue") or 0) for r in profit_loss)
    cogs = sum(
        float(account.get("amount") or 0)
        for report in profit_loss
        for account in (report.get("expenses") or {}).get("accounts") or []
        if COST_OF_SALES.search(f"{account.get('account_subtype')} {account.get('account_name')}")
    )
    if revenue > 0 and cogs > 0:
        return (revenue - cogs) / revenue
    sales = item_sales(w, w.t12, w.as_of)
    if sales.matched_revenue > 0 and sales.matched_revenue / sales.revenue >= registry.ITEM_COST_COVERAGE_MIN:
        return (sales.matched_revenue - sales.cogs) / sales.matched_revenue
    return None
