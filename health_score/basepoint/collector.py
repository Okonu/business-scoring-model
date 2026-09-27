"""
Collects one business's data from the FSS API into standard tables

Every table is a pandas DataFrame. Tables with a `shop_id` column can be
filtered to a single shop. Nothing here scores anything.
"""

import concurrent.futures as cf
import logging
from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Months of orders to fetch: 15 are needed for year-on-year growth
ORDER_HISTORY_MONTHS = 16

# POS order statuses that are not sales
EXCLUDED_ORDER_STATUSES = ("cancel", "void", "refund", "reject")


@dataclass
class BusinessData:
    """Everything collected for one business, as at `as_of`"""

    as_of: pd.Timestamp
    tenant: dict
    user: dict
    tables: dict = field(default_factory=dict)
    reports: dict = field(default_factory=dict)

    def table(self, name):
        return self.tables.get(name, pd.DataFrame())

    def for_shop(self, shop_id):
        """Copy with every shop-level table filtered to one shop"""
        tables = {}
        for name, df in self.tables.items():
            if "shop_id" in df.columns and name != "shops":
                tables[name] = df[df["shop_id"] == shop_id]
            else:
                tables[name] = df
        reports = {
            name: ({shop_id: per_shop.get(shop_id)} if isinstance(per_shop, dict) else per_shop)
            for name, per_shop in self.reports.items()
        }
        return BusinessData(self.as_of, self.tenant, self.user, tables, reports)


def collect(client, tenant, user, as_of=None, max_workers=8):
    """
    Fetch and normalize all available data for the logged-in business

    Args:
        client (FSSClient): logged-in client
        tenant (dict): business record from login
        user (dict): user record from login
        as_of (date-like, optional): reference date; defaults to now

    Returns:
        BusinessData
    """
    as_of = pd.Timestamp(as_of or pd.Timestamp.now(tz="UTC")).tz_localize(None).normalize()
    t3_start = as_of - timedelta(days=90)
    t12_start = as_of - timedelta(days=365)

    shops = client.get_list("/shops", label="/shops")
    shop_ids = [s["_id"] for s in shops if s.get("_id")]

    # (name, path, params, key)
    business_jobs = [
        ("invoices", "/accounting/invoices", None, "invoices"),
        ("receipts", "/accounting/sales-receipts", None, "receipts"),
        ("feedback", "/api/customers/feedback", None, "feedback"),
        ("gift_cards", "/api/customers/all-cards", None, None),
        ("schedules", "/api/customers/all-schedules", None, None),
        ("inventory", "/product-inventory", None, None),
        ("products", "/product/products", None, None),
        ("suppliers", "/suppliers", None, None),
        ("purchase_orders", "/purchase-orders", None, None),
        ("bills", "/accounting/bills", None, "bills"),
        ("expenses", "/accounting/expenses", None, "expenses"),
        ("transfers", "/transfers", None, None),
        ("tables", "/tables", None, None),
        ("bank_accounts", "/accounting/chart-of-accounts/bank", None, "accounts"),
        ("employees", "/bandu/employees", None, None),
        ("payroll", "/bandu/payroll", None, None),
        ("leave", "/bandu/leave", None, "leaves"),
        ("units", "/api/dala/units", None, None),
        ("leases", "/api/dala/leases", None, None),
        ("rent_invoices", "/api/dala/rent-invoices", None, None),
        ("rent_payments", "/api/dala/rent-payments", None, None),
        ("maintenance", "/api/dala/maintenance", None, None),
        ("payment_plans", "/api/dala/payment-plans", None, None),
        ("commissions", "/api/dala/commissions", None, None),
        ("sale_payments", "/api/dala/sale-payments", None, None),
        ("sales_targets", "/api/crm/sales-targets", None, "targets"),
        ("leads", "/api/crm/leads", None, "leads"),
    ]
    single_jobs = [
        ("top_earners", "/orders/top-earners"),
        ("refunds_summary", "/accounting/refunds/summary"),
        ("digitax", "/accounting/digi-tax/config"),
    ]
    period = {"from": day(t12_start), "to": day(as_of)}
    period_t3 = {"from": day(t3_start), "to": day(as_of)}
    shop_jobs = [
        ("customers", "/api/customers", {}, None),
        ("packages", "/packages", {}, "packages"),
        ("services", "/services", {}, "services"),
        ("journal_entries", "/accounting/journal-entries", {}, "entries"),
        ("bank_reconciliations", "/accounting/bank-reconciliations", {}, "reconciliations"),
    ]
    shop_reports = [
        ("ar_aging", "/accounting/reports/ar-aging", {"as_of_date": day(as_of)}),
        ("ar_aging_prev", "/accounting/reports/ar-aging", {"as_of_date": day(t3_start)}),
        ("ap_aging", "/accounting/reports/ap-aging", {"as_of_date": day(as_of)}),
        ("profit_loss", "/accounting/reports/profit-loss", period),
        ("cash_flow", "/accounting/reports/cash-flow", period_t3),
    ]

    # Orders are fetched month by month: the full list times out for large businesses
    order_months = _month_windows(as_of, ORDER_HISTORY_MONTHS)

    raw, reports = {}, {name: {} for name, _, _ in shop_reports}
    order_chunks = []
    per_shop_raw = {name: [] for name, *_ in shop_jobs}
    reports.update({name: None for name, _ in single_jobs})

    with cf.ThreadPoolExecutor(max_workers) as ex:
        futures = {}
        for name, path, params, key in business_jobs:
            futures[ex.submit(client.get_list, path, params, key, path)] = ("biz", name, None)
        for start, end in order_months:
            fut = ex.submit(client.get_list, "/orders", {"startDate": start, "endDate": end}, None, "/orders [monthly]")
            futures[fut] = ("orders", "orders", None)
        for name, path in single_jobs:
            futures[ex.submit(client.get, path, None, path)] = ("single", name, None)
        for sid in shop_ids:
            for name, path, params, key in shop_jobs:
                fut = ex.submit(client.get_list, path, {**params, "shop_id": sid}, key, path)
                futures[fut] = ("shop_list", name, sid)
            for name, path, params in shop_reports:
                fut = ex.submit(client.get, path, {**params, "shop_id": sid}, f"{path} [{name}]")
                futures[fut] = ("shop_report", name, sid)

        for fut in cf.as_completed(futures):
            kind, name, sid = futures[fut]
            try:
                result = fut.result()
            except Exception as e:  # a failed endpoint must not stop the others
                logger.warning(f"{name} failed: {e}")
                result = None
            if kind == "orders":
                order_chunks.append(result or [])
            elif kind == "biz":
                raw[name] = result or []
            elif kind == "single":
                reports[name] = result
            elif kind == "shop_list":
                for rec in result or []:
                    rec.setdefault("shop_id", sid)
                per_shop_raw[name].extend(result or [])
            else:
                reports[name][sid] = result

    raw["orders"] = list({o["_id"]: o for chunk in order_chunks for o in chunk if o.get("_id")}.values())
    raw.update(per_shop_raw)
    raw["shops"] = shops

    tables = {
        "shops": _shops(shops),
        "orders": _orders(raw["orders"]),
        "order_items": _order_items(raw["orders"]),
        "payments": _payments(raw["orders"]),
        "invoices": _invoices(raw["invoices"]),
        "receipts": _receipts(raw["receipts"]),
        "customers": _customers(raw["customers"]),
        "visits": _frame(
            raw["feedback"],
            {"shop_id": "shop_id", "customer_id": "customer_id", "date": "visit_date", "rating": "rating"},
        ),
        "gift_cards": _frame(
            raw["gift_cards"],
            {
                "shop_id": "shop_id",
                "amount": "amount",
                "active": "status",
                "expiry": "expiry_date",
                "date": "createdAt",
            },
        ),
        "schedules": _frame(raw["schedules"], {"shop_id": "shop_id", "date": "appointment_date"}),
        "packages": _frame(raw["packages"], {"shop_id": "shop_id", "price": "price", "active": "is_active"}),
        "services": _frame(raw["services"], {"id": "_id", "shop_id": "shop_id", "name": "name"}),
        "products": _frame(raw["products"], {"id": "_id", "shop_id": "shop_id", "name": "name"}),
        "inventory": _inventory(raw["inventory"]),
        "suppliers": _frame(raw["suppliers"], {"id": "_id", "name": "name", "payment_terms": "payment_terms"}),
        "purchase_orders": _purchase_orders(raw["purchase_orders"]),
        "po_items": _po_items(raw["purchase_orders"]),
        "bills": _bills(raw["bills"]),
        "expenses": _frame(
            raw["expenses"], {"shop_id": "shop_id", "date": "expense_date", "amount": "grand_total", "status": "status"}
        ),
        "transfers": _frame(raw["transfers"], {"shop_id": "shop_id", "date": "transfer_date", "status": "status"}),
        "bank_accounts": _frame(
            raw["bank_accounts"], {"id": "_id", "name": "account_name", "balance": "current_balance"}
        ),
        "employees": _employees(raw["employees"]),
        "payroll": _frame(
            raw["payroll"],
            {
                "shop_id": "shop_id",
                "period_start": "period_start",
                "status": "status",
                "gross": "total_gross",
                "paye": "total_paye",
                "nssf": "total_nssf",
            },
        ),
        "leave": _frame(
            raw["leave"],
            {
                "shop_id": "shop_id",
                "type": "leave_type",
                "start": "start_date",
                "days": "days_requested",
                "status": "status",
            },
        ),
        "units": _frame(
            raw["units"],
            {"shop_id": "shop_id", "status": "status", "units": "totalUnits", "available": "availableUnits"},
        ),
        "leases": _frame(
            raw["leases"],
            {
                "shop_id": "shop_id",
                "start": "startDate",
                "end": "endDate",
                "rent": "rentAmount",
                "status": "status",
                "occupant_id": "occupantId",
            },
        ),
        "rent_invoices": _frame(
            raw["rent_invoices"],
            {
                "id": "_id",
                "shop_id": "shop_id",
                "occupant_id": "occupantId",
                "date": "periodStart",
                "due_date": "dueDate",
                "amount": "totalAmount",
                "paid": "paidAmount",
                "balance": "balance",
                "status": "status",
                "paid_date": "paidDate",
            },
        ),
        "rent_payments": _frame(
            raw["rent_payments"],
            {"shop_id": "shop_id", "date": "paymentDate", "amount": "amount", "method": "paymentMethod"},
        ),
        "maintenance": _frame(
            raw["maintenance"],
            {
                "shop_id": "shop_id",
                "status": "status",
                "date": "createdAt",
                "cost": "actualCost",
                "estimate": "estimatedCost",
            },
        ),
        "payment_plans": _frame(
            raw["payment_plans"],
            {
                "shop_id": "shop_id",
                "total": "totalAmount",
                "deposit": "initialDeposit",
                "outstanding": "outstandingBalance",
                "installment": "installmentAmount",
                "installments": "numberOfInstallments",
                "start": "startDate",
                "status": "status",
            },
        ),
        "commissions": _commissions(raw["commissions"]),
        "property_sale_payments": _property_sale_payments(raw["sale_payments"]),
        "sales_targets": _frame(
            raw["sales_targets"],
            {
                "shop_id": "shop_id",
                "type": "type",
                "start": "period_start",
                "end": "period_end",
                "target": "target_value",
                "actual": "actual_value",
            },
        ),
        "tables": _frame(raw["tables"], {"id": "_id", "shop_id": "shop_id"}),
        "leads": _frame(
            raw["leads"], {"shop_id": "shop_id", "stage": "stage", "customer_id": "customer_id", "date": "createdAt"}
        ),
        "journal_entries": _frame(
            raw["journal_entries"],
            {"shop_id": "shop_id", "date": "entry_date", "status": "status", "created": "createdAt"},
        ),
        "bank_reconciliations": _frame(
            raw["bank_reconciliations"],
            {
                "shop_id": "shop_id",
                "status": "status",
                "date": "statement_date",
                "completed": "completed_at",
                "updated": "updatedAt",
            },
        ),
        "top_earners": _top_earners(reports.pop("top_earners")),
    }
    tables["transactions"] = _transactions(tables)
    tables["cash_in"] = _cash_in(tables)
    return BusinessData(as_of=as_of, tenant=tenant, user=user, tables=tables, reports=reports)


def _month_windows(as_of, months):
    """(start, end) date strings per calendar month; each end overlaps the next start by a day"""
    first = (as_of - pd.DateOffset(months=months - 1)).to_period("M")
    windows = []
    for period in pd.period_range(first, as_of.to_period("M"), freq="M"):
        start = period.start_time
        end = min((period + 1).start_time, as_of + timedelta(days=1))
        windows.append((start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
    return windows


def day(d):
    return d.strftime("%Y-%m-%d")


# ------------------------------------------------------------- normalizers


def _id(v):
    if isinstance(v, dict):
        return v.get("_id") or v.get("id")
    return v


def _dt(series):
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)


def _num(series):
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _frame(records, mapping):
    """Build a DataFrame from records, picking and renaming fields"""
    rows = []
    for r in records or []:
        rows.append(
            {out: _id(r.get(src)) if out.endswith("_id") or out == "id" else r.get(src) for out, src in mapping.items()}
        )
    df = pd.DataFrame(rows, columns=list(mapping))
    for col in df.columns:
        if col in (
            "date",
            "due_date",
            "paid_date",
            "expiry",
            "start",
            "end",
            "period_start",
            "completed",
            "updated",
            "created",
        ):
            df[col] = _dt(df[col])
        elif col in (
            "amount",
            "price",
            "paid",
            "balance",
            "total",
            "deposit",
            "outstanding",
            "installment",
            "installments",
            "target",
            "actual",
            "gross",
            "paye",
            "nssf",
            "cost",
            "estimate",
            "rent",
            "days",
            "units",
            "available",
            "payment_terms",
            "rating",
        ):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _shops(shops):
    df = _frame(shops, {"shop_id": "_id", "name": "name", "pos_mode": "pos_mode", "staff_count": "staff_count"})
    df["staff_count"] = _num(df["staff_count"])
    return df


def _orders(orders):
    rows = []
    for o in orders:
        status = str(o.get("order_status") or "").lower()
        if any(s in status for s in EXCLUDED_ORDER_STATUSES):
            continue
        rows.append(
            {
                "id": o.get("_id"),
                "shop_id": _id(o.get("shop_id")),
                "date": o.get("createdAt"),
                # Older orders may lack order_amount
                "amount": next(
                    (o.get(k) for k in ("order_amount", "total_cart_amount", "subtotal") if o.get(k) is not None), 0
                ),
                "discount": o.get("discount_amount"),
                "status": o.get("order_status"),
                "customer_id": _id(o.get("customer_id")),
                "customer_phone": o.get("customer_phone"),
                "table_id": _id(o.get("table_id")),
                "recurring": bool(
                    o.get("subscription_id")
                    or o.get("package_id")
                    or any(i.get("is_subscription_item") for i in o.get("order_items") or [])
                ),
                "receipted": any(p.get("receiptNumber") for p in o.get("order_payments") or []),
            }
        )
    df = pd.DataFrame(
        rows,
        columns=[
            "id",
            "shop_id",
            "date",
            "amount",
            "discount",
            "status",
            "customer_id",
            "customer_phone",
            "table_id",
            "recurring",
            "receipted",
        ],
    )
    df["date"] = _dt(df["date"])
    df["amount"] = _num(df["amount"])
    df["discount"] = _num(df["discount"])
    return df


def _order_items(orders):
    rows = []
    for o in orders:
        status = str(o.get("order_status") or "").lower()
        if any(s in status for s in EXCLUDED_ORDER_STATUSES):
            continue
        for i in o.get("order_items") or []:
            product = i.get("product_id")
            rows.append(
                {
                    "order_id": o.get("_id"),
                    "shop_id": _id(i.get("shop_id") or o.get("shop_id")),
                    "date": o.get("createdAt"),
                    "product_id": _id(product),
                    "product_name": (product or {}).get("name")
                    if isinstance(product, dict)
                    else i.get("miscellaneous_name"),
                    "quantity": i.get("quantity"),
                    "price": i.get("price"),
                }
            )
    df = pd.DataFrame(rows, columns=["order_id", "shop_id", "date", "product_id", "product_name", "quantity", "price"])
    df["date"] = _dt(df["date"])
    df["quantity"] = _num(df["quantity"])
    df["price"] = _num(df["price"])
    df["amount"] = df["quantity"] * df["price"]
    df["name_key"] = df["product_name"].fillna("").str.strip().str.lower()
    return df


def _payments(orders):
    """Completed inbound POS payments embedded in orders"""
    rows = []
    for o in orders:
        for p in o.get("order_payments") or []:
            status = str(p.get("payment_status") or "COMPLETED").upper()
            if p.get("is_trash") or p.get("reversed_at") or status not in ("COMPLETED", "PAID"):
                continue
            if str(p.get("direction") or "inbound").lower() != "inbound":
                continue
            rows.append(
                {
                    "shop_id": _id(p.get("shop_id") or o.get("shop_id")),
                    "date": p.get("payment_date") or p.get("createdAt"),
                    "amount": p.get("amount"),
                    "method": p.get("name"),
                    "source": "pos",
                }
            )
    df = pd.DataFrame(rows, columns=["shop_id", "date", "amount", "method", "source"])
    df["date"] = _dt(df["date"])
    df["amount"] = _num(df["amount"])
    return df


def _invoices(invoices):
    df = _frame(
        invoices,
        {
            "id": "_id",
            "shop_id": "shop_id",
            "source": "source",
            "direction": "direction",
            "status": "status",
            "customer_id": "customer_id",
            "order_id": "order_id",
            "date": "issue_date",
            "due_date": "due_date",
            "paid_date": "paid_date",
            "amount": "grand_total",
            "paid": "amount_paid",
            "balance": "amount_due",
        },
    )
    df["created"] = _dt(pd.Series([i.get("createdAt") for i in invoices], dtype=object))
    df["date"] = df["date"].fillna(df["created"])
    df["etims"] = [
        bool((i.get("digitax") or {}).get("status") in ("verified", "success", "VERIFIED"))
        if isinstance(i.get("digitax"), dict)
        else False
        for i in invoices
    ]
    df["amount"] = _num(df["amount"])
    df["paid"] = _num(df["paid"])
    df["balance"] = _num(df["balance"])
    return df


def _receipts(receipts):
    df = _frame(
        receipts,
        {
            "id": "_id",
            "shop_id": "shop_id",
            "date": "receipt_date",
            "amount": "grand_total",
            "discount": "total_discount",
            "status": "status",
            "invoice_id": "invoice_id",
            "customer_id": "customer_id",
            "method": "payment_method",
        },
    )
    df = df[~df["status"].fillna("").str.lower().isin(["voided", "void", "cancelled"])]
    df["amount"] = _num(df["amount"])
    df["discount"] = _num(df["discount"])
    return df


def _customers(customers):
    df = _frame(
        customers,
        {
            "id": "_id",
            "shop_id": "shop_id",
            "phone": "phone",
            "kra_pin": "kra_pin",
            "credit_limit": "credit_limit",
            "balance": "current_balance",
            "stage": "lifecycle_stage",
            "loyalty": "loyalty_points",
            "created": "createdAt",
        },
    )
    df["credit_limit"] = _num(df["credit_limit"])
    df["balance"] = _num(df["balance"])
    df["loyalty"] = _num(df["loyalty"])
    phone = df["phone"].astype(str).str.replace(r"\D", "", regex=True).str[-9:]
    kra = df["kra_pin"].fillna("").astype(str).str.upper().str.strip()
    # One customer across shops: match by KRA PIN, then phone, else the record id
    df["key"] = np.where(
        kra.str.len() >= 10, "kra:" + kra, np.where(phone.str.len() == 9, "tel:" + phone, "id:" + df["id"].astype(str))
    )
    return df


def _inventory(items):
    df = _frame(
        items,
        {
            "id": "_id",
            "shop_id": "shop_id",
            "name": "name",
            "quantity": "quantity",
            "price": "price",
            "cost": "supplier_price",
            "min_qty": "min_viable_quantity",
            "usage_type": "usage_type",
            "status": "status",
            "supplier_id": "supplier_id",
        },
    )
    for col in ("quantity", "price", "cost", "min_qty"):
        df[col] = _num(df[col])
    df["name_key"] = df["name"].fillna("").str.strip().str.lower()
    df["selling"] = df["usage_type"].fillna("selling").isin(["selling", "both"])
    df["active"] = df["status"].fillna("active").str.lower() == "active"
    return df


def _purchase_orders(pos):
    df = _frame(
        pos,
        {
            "id": "_id",
            "shop_id": "shop_id",
            "supplier_id": "supplier_id",
            "status": "status",
            "date": "createdAt",
            "total": "total_amount",
        },
    )
    df["total"] = _num(df["total"])
    return df


def _po_items(pos):
    rows = []
    for po in pos:
        if str(po.get("status") or "").lower() == "cancelled":
            continue
        for i in po.get("po_items") or []:
            inv = i.get("inventory_id")
            rows.append(
                {
                    "po_id": po.get("_id"),
                    "shop_id": _id(po.get("shop_id")),
                    "date": po.get("createdAt"),
                    "supplier_id": _id(po.get("supplier_id")),
                    "inventory_id": _id(inv),
                    "name_key": str((inv or {}).get("name") or "").strip().lower() if isinstance(inv, dict) else "",
                    "ordered": i.get("quantity_ordered"),
                    "received": i.get("quantity_received"),
                    "unit_price": i.get("unit_price"),
                }
            )
    df = pd.DataFrame(
        rows,
        columns=[
            "po_id",
            "shop_id",
            "date",
            "supplier_id",
            "inventory_id",
            "name_key",
            "ordered",
            "received",
            "unit_price",
        ],
    )
    df["date"] = _dt(df["date"])
    for col in ("ordered", "received", "unit_price"):
        df[col] = _num(df[col])
    return df


def _bills(bills):
    df = _frame(
        bills,
        {
            "id": "_id",
            "shop_id": "shop_id",
            "supplier_id": "supplier_id",
            "date": "bill_date",
            "due_date": "due_date",
            "paid_date": "paid_date",
            "amount": "grand_total",
            "balance": "amount_due",
            "status": "status",
            "po_id": "purchase_order_id",
        },
    )
    df = df[~df["status"].fillna("").str.lower().isin(["voided", "void", "draft"])]
    df["amount"] = _num(df["amount"])
    df["balance"] = _num(df["balance"])
    return df


def _employees(emps):
    df = _frame(
        emps,
        {
            "id": "_id",
            "shop_id": "shop_id",
            "hired": "hire_date",
            "terminated": "termination_date",
            "status": "employment_status",
        },
    )
    df["hired"] = _dt(df["hired"])
    df["terminated"] = _dt(df["terminated"])
    return df


def _commissions(records):
    rows = [
        {
            "shop_id": r.get("shop_id"),
            "amount": r.get("amount"),
            "sale_price": (r.get("sale") or {}).get("salePrice"),
            "date": r.get("createdAt"),
        }
        for r in records
    ]
    df = pd.DataFrame(rows, columns=["shop_id", "amount", "sale_price", "date"])
    df["date"] = _dt(df["date"])
    df["amount"] = _num(df["amount"])
    df["sale_price"] = _num(df["sale_price"])
    return df


def _property_sale_payments(records):
    """/api/dala/sale-payments also returns POS invoice payments; keep property sales only"""
    rows = [
        {
            "shop_id": r.get("shop_id"),
            "date": r.get("paymentDate"),
            "amount": r.get("amount"),
            "method": r.get("paymentMethod"),
        }
        for r in records
        if r.get("saleId") or r.get("paymentPlanId")
    ]
    df = pd.DataFrame(rows, columns=["shop_id", "date", "amount", "method"])
    df["date"] = _dt(df["date"])
    df["amount"] = _num(df["amount"])
    return df


def _top_earners(body):
    earners = ((body or {}).get("data") or {}).get("top_earners") or []
    return pd.DataFrame(
        [{"staff_id": e.get("staff_id"), "earnings": e.get("total_earnings")} for e in earners],
        columns=["staff_id", "earnings"],
    )


def _transactions(t):
    """
    One row per sale, de-duplicated across products

    POS orders; accounting invoices not linked to an order; sales receipts not
    linked to an invoice; rent invoices; property sale payments.
    """
    customers = t["customers"].set_index("id")["key"] if not t["customers"].empty else pd.Series(dtype=str)

    def key(ids):
        return ids.map(lambda c: customers.get(c, f"id:{c}") if pd.notna(c) and c else None)

    orders = t["orders"]
    parts = [
        pd.DataFrame(
            {
                "shop_id": orders["shop_id"],
                "date": orders["date"],
                "amount": orders["amount"],
                "discount": orders["discount"],
                "source": "pos",
                "credit": False,
                "customer_key": key(orders["customer_id"]),
            }
        )
    ]

    inv = t["invoices"]
    acc = inv[
        (inv["source"] == "accounting")
        & inv["direction"].fillna("customer").eq("customer")
        & ~inv["status"].fillna("").isin(["Draft", "Voided"])
        & inv["order_id"].isna()
    ]
    parts.append(
        pd.DataFrame(
            {
                "shop_id": acc["shop_id"],
                "date": acc["date"],
                "amount": acc["amount"],
                "discount": 0.0,
                "source": "invoice",
                "credit": True,
                "customer_key": key(acc["customer_id"]),
            }
        )
    )

    rc = t["receipts"]
    rc = rc[rc["invoice_id"].isna()]
    parts.append(
        pd.DataFrame(
            {
                "shop_id": rc["shop_id"],
                "date": rc["date"],
                "amount": rc["amount"],
                "discount": rc["discount"],
                "source": "receipt",
                "credit": False,
                "customer_key": key(rc["customer_id"]),
            }
        )
    )

    ri = t["rent_invoices"]
    ri = ri[~ri["status"].fillna("").str.lower().isin(["cancelled", "void", "voided"])]
    parts.append(
        pd.DataFrame(
            {
                "shop_id": ri["shop_id"],
                "date": ri["date"],
                "amount": ri["amount"],
                "discount": 0.0,
                "source": "rent",
                "credit": True,
                "customer_key": ri["occupant_id"].map(lambda c: f"occ:{c}" if c else None),
            }
        )
    )

    sp = t["property_sale_payments"]
    parts.append(
        pd.DataFrame(
            {
                "shop_id": sp["shop_id"],
                "date": sp["date"],
                "amount": sp["amount"],
                "discount": 0.0,
                "source": "property_sale",
                "credit": False,
                "customer_key": None,
            }
        )
    )

    df = (
        pd.concat([p for p in parts if not p.empty], ignore_index=True)
        if any(not p.empty for p in parts)
        else pd.DataFrame(columns=["shop_id", "date", "amount", "discount", "source", "credit", "customer_key"])
    )
    df = df.dropna(subset=["date"])
    df["amount"] = _num(df["amount"])
    df["discount"] = _num(df["discount"])
    return df[df["amount"] > 0]


def _cash_in(t):
    """Money received: POS payments, receipts, invoice payments, rent, property sales"""
    parts = [t["payments"][["shop_id", "date", "amount", "method", "source"]]]
    rc = t["receipts"]
    parts.append(
        pd.DataFrame(
            {
                "shop_id": rc["shop_id"],
                "date": rc["date"],
                "amount": rc["amount"],
                "method": rc["method"],
                "source": "receipt",
            }
        )
    )
    inv = t["invoices"]
    paid = inv[(inv["source"] == "accounting") & (inv["paid"] > 0)]
    parts.append(
        pd.DataFrame(
            {
                "shop_id": paid["shop_id"],
                "date": paid["paid_date"].fillna(paid["date"]),
                "amount": paid["paid"],
                "method": None,
                "source": "invoice",
            }
        )
    )
    rp = t["rent_payments"]
    parts.append(
        pd.DataFrame(
            {
                "shop_id": rp["shop_id"],
                "date": rp["date"],
                "amount": rp["amount"],
                "method": rp["method"],
                "source": "rent",
            }
        )
    )
    sp = t["property_sale_payments"]
    parts.append(
        pd.DataFrame(
            {
                "shop_id": sp["shop_id"],
                "date": sp["date"],
                "amount": sp["amount"],
                "method": sp["method"],
                "source": "property_sale",
            }
        )
    )
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame(columns=["shop_id", "date", "amount", "method", "source"])
    df = pd.concat(parts, ignore_index=True).dropna(subset=["date"])
    df["amount"] = _num(df["amount"])
    return df[df["amount"] > 0]
