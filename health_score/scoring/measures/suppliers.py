"""Supplier tracking tiers, traceability index and the minimum purchase base"""

import pandas as pd

from health_score.scoring import registry
from health_score.scoring.measures.window import ratio


def purchases_by_supplier(w):
    """T12M purchase value per supplier: received PO lines plus bills not raised from a PO"""
    po_lines = w.last_12m(w.table("po_items"))
    bills = w.last_12m(w.table("bills"))
    unlinked_bills = bills[bills["po_id"].isna()] if not bills.empty else bills
    frames = [
        pd.DataFrame({"supplier_id": po_lines.get("supplier_id"), "value": _received_value(po_lines)}),
        pd.DataFrame({"supplier_id": unlinked_bills.get("supplier_id"), "value": unlinked_bills.get("amount")}),
    ]
    purchases = pd.concat(frames).dropna(subset=["supplier_id"])
    return purchases.groupby("supplier_id")["value"].sum() if not purchases.empty else pd.Series(dtype=float)


def purchase_documents(w):
    orders = w.last_12m(w.table("purchase_orders"))
    if not orders.empty:
        orders = orders[orders["status"].fillna("").str.lower() != "cancelled"]
    return len(orders) + len(w.last_12m(w.table("bills")))


def meets_purchase_base(documents, purchase_value, revenue_t12):
    return (
        documents >= registry.MIN_PURCHASE_DOCUMENTS
        and revenue_t12 > 0
        and purchase_value >= registry.MIN_PURCHASE_SHARE_OF_REVENUE * revenue_t12
    )


def supplier_tracking(w):
    purchase_value = purchases_by_supplier(w)
    inventory = w.table("inventory")
    tracked_inventory = inventory[inventory["supplier_id"].notna()] if not inventory.empty else inventory
    tiers = _tiers(w, purchase_value, tracked_inventory)
    total = float(purchase_value.sum())
    tracked = float(sum(v for s, v in purchase_value.items() if tiers.get(s, 0) >= 2))
    return {
        "tiers": tiers,
        "tier_counts": {k: sum(1 for t in tiers.values() if t == k) for k in registry.TIER_POINTS},
        "tracking_share": ratio(tracked, total) if total > 0 else None,
        "traceability_index": _traceability_index(inventory, purchase_value, tiers),
        "purchase_value_12m": total,
        "has_supplier_data": total > 0 or not tracked_inventory.empty,
    }


def _received_value(po_lines):
    if po_lines.empty:
        return pd.Series(dtype=float)
    return po_lines["received"] * po_lines["unit_price"]


def _tiers(w, purchase_value, tracked_inventory):
    po_lines = w.last_12m(w.table("po_items"))
    bills = w.last_12m(w.table("bills")).dropna(subset=["supplier_id"])
    items = w.table("order_items")
    sold = set(w.last_12m(items)["name_key"]) if not items.empty else set()
    received = set(po_lines.loc[po_lines["received"] > 0, "supplier_id"]) if not po_lines.empty else set()
    billed = set(bills["supplier_id"]) if not bills.empty else set()
    paid = (
        set(bills.loc[bills["paid_date"].notna() | (bills["balance"] <= 1), "supplier_id"])
        if not bills.empty
        else set()
    )
    suppliers = set(purchase_value.index) | (
        set(tracked_inventory["supplier_id"]) if not tracked_inventory.empty else set()
    )

    def tier(supplier):
        if purchase_value.get(supplier, 0) <= 0:
            return 0
        supplier_items = tracked_inventory[tracked_inventory["supplier_id"] == supplier]
        if supplier_items.empty:
            return 1
        full_chain = (
            supplier in received
            and supplier in billed
            and supplier in paid
            and bool(set(supplier_items["name_key"]) & sold)
        )
        return 3 if full_chain else 2

    return {supplier: tier(supplier) for supplier in suppliers}


def _traceability_index(inventory, purchase_value, tiers):
    if not inventory.empty:
        value = inventory["quantity"].clip(lower=0) * inventory["cost"]
        by_supplier = pd.Series(value.values, index=inventory["supplier_id"].fillna("")).groupby(level=0).sum()
        total = float(by_supplier.sum())
        if total > 0:
            return sum(v / total * registry.TIER_POINTS[tiers.get(s, 0) if s else 0] for s, v in by_supplier.items())
    total = float(purchase_value.sum())
    if total > 0:
        return sum(v / total * registry.TIER_POINTS[tiers.get(s, 0)] for s, v in purchase_value.items())
    return None
