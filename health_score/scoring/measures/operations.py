"""Operational stability measures (methodology table 9)"""

from datetime import timedelta

import pandas as pd

from health_score.scoring.measures.costs import item_sales, tracked_items
from health_score.scoring.measures.suppliers import purchases_by_supplier
from health_score.scoring.measures.window import trend

DAYS_PER_MONTH = 30.44
WORKING_DAYS_PER_YEAR = 260
CLOSED_TICKETS = ["closed", "resolved", "completed", "cancelled"]
OCCUPIED_UNITS = ["occupied", "leased", "sold"]
MIN_ITEMS_WITH_MINIMUM = 3
MIN_CATALOGUE = 5
BACKLOG_DAYS = 30
FILL_RATE_GRACE_DAYS = 7
STOCK_WITHOUT_SALES_DAYS = 999.0


def operations_measures(w, p):
    return {
        **_tenure(w, p),
        **_staff(w),
        **_payroll(w, p),
        **_key_person(w, p),
        **_inventory(w),
        **_catalogue(w),
        **_capacity(w, p),
        **_property(w),
        **_suppliers(w, p),
    }


def _tenure(w, p):
    started = w.first_transaction
    created = pd.to_datetime(w.tenant.get("createdAt"), errors="coerce", utc=True)
    if p.business_level and pd.notna(created):
        created = created.tz_localize(None)
        started = min(started, created) if started is not None else created
    return {"tenure": (w.as_of - started).days / DAYS_PER_MONTH} if started is not None else {}


def _staff(w):
    employees = w.table("employees")
    if employees.empty:
        return {}

    def active_at(day):
        hired = employees["hired"].isna() | (employees["hired"] <= day)
        staying = employees["terminated"].isna() | (employees["terminated"] > day)
        return int((hired & staying).sum())

    values = {}
    now, half_year_ago, year_ago = active_at(w.as_of), active_at(w.t6), active_at(w.t12)
    if half_year_ago >= 1:
        values["staff_trend"] = trend(now, half_year_ago)
    average = (now + year_ago) / 2
    if average >= 1:
        values["staff_turnover"] = len(w.last_12m(employees, "terminated")) / average
    leave = w.last_12m(w.table("leave"), "start")
    if not leave.empty and now:
        approved = leave[leave["status"].fillna("").str.lower() == "approved"]
        unplanned = approved[~approved["type"].fillna("").str.lower().str.contains("annual")]
        values["unplanned_leave"] = float(unplanned["days"].fillna(0).sum()) / (now * WORKING_DAYS_PER_YEAR)
    return values


def _payroll(w, p):
    runs = p.paid_payroll
    if runs.empty:
        return {}
    months_run = set(w.last_6m(runs, "period_start")["period_start"].dt.to_period("M"))
    months_expected = min(6, max(1, (w.as_of.to_period("M") - runs["period_start"].min().to_period("M")).n + 1))
    values = {"payroll_regularity": min(len(months_run) / months_expected, 1.0)}
    year_runs = w.last_12m(runs, "period_start")
    if not year_runs.empty:
        statutory = (year_runs["paye"].fillna(0) > 0) | (year_runs["nssf"].fillna(0) > 0)
        values["statutory_compliance"] = float(statutory.mean())
    return values


def _key_person(w, p):
    earners = w.table("top_earners")
    if not p.business_level or earners.empty or earners["earnings"].sum() <= 0:
        return {}
    return {"key_person": float(earners["earnings"].max() / earners["earnings"].sum())}


def _selling_stock(w):
    inventory = w.table("inventory")
    return inventory[inventory["selling"] & inventory["active"]] if not inventory.empty else inventory


def _inventory(w):
    selling = _selling_stock(w)
    if selling.empty:
        return {}
    values = {}
    with_minimum = selling[selling["min_qty"] > 0]
    if len(with_minimum) >= MIN_ITEMS_WITH_MINIMUM:
        values["stockout_rate"] = float((with_minimum["quantity"] < with_minimum["min_qty"]).mean())
    stock_value = selling["quantity"].clip(lower=0) * selling["cost"]
    if stock_value.sum() > 0:
        sold_recently = set(w.last_3m(w.table("order_items"))["name_key"])
        values["dead_stock"] = float(stock_value[~selling["name_key"].isin(sold_recently)].sum() / stock_value.sum())
        cogs = item_sales(w, w.t12, w.as_of).cogs
        if cogs > 0:
            values["inventory_turnover"] = cogs / float(stock_value.sum())
    return values


def _catalogue(w):
    selling = _selling_stock(w)
    names = [w.table("products")["name"], w.table("services")["name"]]
    if not selling.empty:
        names.append(selling["name"])
    catalogue = set(pd.concat(names).dropna().str.strip().str.lower())
    if len(catalogue) < MIN_CATALOGUE:
        return {}
    sold = set(w.last_3m(w.table("order_items"))["name_key"])
    return {"catalogue_activity": len(catalogue & sold) / len(catalogue)}


def _capacity(w, p):
    tables = w.table("tables")
    orders = w.last_3m(w.table("orders"))
    table_orders = orders[orders["table_id"].notna()] if not orders.empty else orders
    if tables.empty or table_orders.empty or not p.trading_days:
        return {}
    return {"capacity_utilization": len(table_orders) / (len(tables) * p.trading_days)}


def _property(w):
    values = {}
    units = w.table("units")
    if not units.empty:
        values["occupancy"] = float(units["status"].fillna("").str.lower().isin(OCCUPIED_UNITS).mean())
    tickets = w.table("maintenance")
    if not tickets.empty:
        open_tickets = tickets[~tickets["status"].fillna("").str.lower().isin(CLOSED_TICKETS)]
        if not open_tickets.empty:
            old = open_tickets["date"] < w.as_of - timedelta(days=BACKLOG_DAYS)
            values["maintenance_backlog"] = float(old.mean())
    return values


def _suppliers(w, p):
    if not p.purchase_base:
        return {}
    values = {}
    by_supplier = purchases_by_supplier(w)
    if by_supplier.sum() > 0:
        values["supplier_concentration"] = float(by_supplier.max() / by_supplier.sum())
    values["procurement_regularity"] = _procurement_months(w) / 6
    ordered = w.between(w.table("po_items"), w.t6, w.as_of - timedelta(days=FILL_RATE_GRACE_DAYS))
    if not ordered.empty and ordered["ordered"].sum() > 0:
        values["fill_rate"] = float(ordered["received"].sum() / ordered["ordered"].sum())
    values.update(_tracked_stock(w))
    return values


def _procurement_months(w):
    po_lines = w.last_6m(w.table("po_items"))
    months = set(po_lines["date"].dt.to_period("M")) if not po_lines.empty else set()
    bills = w.last_6m(w.table("bills"))
    if not bills.empty:
        months |= set(bills["date"].dt.to_period("M"))
    return len(months)


def _tracked_stock(w):
    values = {}
    tracked = tracked_items(w)
    received = float(w.last_6m(w.table("po_items"))["received"].sum())
    if received > 0:
        sold = w.last_6m(w.table("order_items"))
        values["sell_through"] = float(sold.loc[sold["name_key"].isin(tracked), "quantity"].sum()) / received
    inventory = w.table("inventory")
    if tracked and not inventory.empty:
        on_hand = float(inventory.loc[inventory["supplier_id"].notna(), "quantity"].clip(lower=0).sum())
        units_t3 = item_sales(w, w.t3, w.as_of, tracked_only=True).units
        if units_t3 > 0:
            values["stock_cover"] = on_hand / (units_t3 / 90)
        elif on_hand > 0:
            values["stock_cover"] = STOCK_WITHOUT_SALES_DAYS
    return values
