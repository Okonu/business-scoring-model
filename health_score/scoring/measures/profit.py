"""Profitability and cost control measures (methodology table 7)"""

from health_score.scoring.measures.costs import gross_margin, item_sales
from health_score.scoring.measures.window import trend

POSTED_EXPENSE = ["approved", "paid", "posted"]
STOCK_NOT_SELLING = 10.0


def profit_measures(w, p):
    return {
        **_margins(w, p),
        **_staff_cost(w, p),
        **_cost_discipline(w, p),
        **_revenue_per_staff(w, p),
        **_property_costs(w, p),
        **_purchase_alignment(w, p),
    }


def _margins(w, p):
    values = {"gross_margin": gross_margin(w, p.profit_loss if p.books_reliable else [])}
    ledger_revenue = sum(float((r.get("revenue") or {}).get("total_revenue") or 0) for r in p.profit_loss)
    if p.books_reliable and ledger_revenue > 0:
        values["net_margin"] = sum(float(r.get("net_profit") or 0) for r in p.profit_loss) / ledger_revenue
    return values


def _staff_cost(w, p):
    payroll = w.last_3m(p.paid_payroll, "period_start")
    if payroll.empty or p.revenue_t3 <= 0:
        return {}
    return {"staff_cost_ratio": float(payroll["gross"].sum()) / p.revenue_t3}


def _cost_discipline(w, p):
    expenses = w.table("expenses")
    if expenses.empty:
        return {}
    expenses = expenses[expenses["status"].fillna("").str.lower().isin(POSTED_EXPENSE)]
    expense_growth = trend(float(w.last_3m(expenses)["amount"].sum()), float(w.prior_3m(expenses)["amount"].sum()))
    revenue_growth = trend(p.revenue_t3, p.revenue_p3)
    if expense_growth is None or revenue_growth is None:
        return {}
    return {"cost_discipline": expense_growth - revenue_growth}


def _revenue_per_staff(w, p):
    staff = staff_count(w)
    if not staff or p.revenue_t3 <= 0:
        return {}
    return {"revenue_per_staff": p.revenue_t3 / 3 / staff}


def staff_count(w):
    employees = w.table("employees")
    if not employees.empty:
        active = int((employees["terminated"].isna() | (employees["terminated"] > w.as_of)).sum())
        if active:
            return active
    shops = w.table("shops")
    return float(shops["staff_count"].sum()) if not shops.empty else 0


def _property_costs(w, p):
    values = {}
    maintenance = w.last_12m(w.table("maintenance"))
    rent_income = float(p.tx_t12.loc[p.tx_t12["source"] == "rent", "amount"].sum()) if not p.tx_t12.empty else 0.0
    if not maintenance.empty and rent_income > 0:
        cost = maintenance["cost"].where(maintenance["cost"] > 0, maintenance["estimate"]).fillna(0)
        values["maintenance_ratio"] = float(cost.sum()) / rent_income
    commissions = w.table("commissions")
    if not commissions.empty and commissions["sale_price"].sum() > 0:
        values["commission_ratio"] = float(commissions["amount"].sum() / commissions["sale_price"].sum())
    return values


def _purchase_alignment(w, p):
    if not p.purchase_base:
        return {}
    po_lines = w.last_3m(w.table("po_items"))
    purchased = float((po_lines["received"] * po_lines["unit_price"]).sum()) if not po_lines.empty else 0.0
    sold_cost = item_sales(w, w.t3, w.as_of, tracked_only=True).cogs
    if sold_cost > 0:
        return {"purchase_alignment": purchased / sold_cost}
    if purchased > 0:
        return {"purchase_alignment": STOCK_NOT_SELLING}
    return {}
