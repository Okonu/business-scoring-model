"""Facts about a business that decide which measures apply"""

from dataclasses import dataclass

import pandas as pd

from health_score.scoring import registry
from health_score.scoring.measures.products import products_in_use
from health_score.scoring.measures.suppliers import meets_purchase_base, purchase_documents, supplier_tracking
from health_score.scoring.measures.window import ratio

PAID_PAYROLL = {"processed", "approved", "paid", "completed"}


@dataclass(frozen=True)
class Profile:
    business_level: bool
    history_days: int
    tx_t3: pd.DataFrame
    tx_p3: pd.DataFrame
    tx_t12: pd.DataFrame
    revenue_t3: float
    revenue_p3: float
    revenue_t12: float
    trading_days: int
    credit_share: float | None
    cash_business: bool
    identified_share: float | None
    walk_in: bool
    profit_loss: list
    books_coverage: float | None
    books_reliable: bool
    paid_payroll: pd.DataFrame
    purchase_documents: int
    supplier_tracking: dict
    purchase_base: bool
    sector: str
    products: list | None


def build_profile(w, business_level=True):
    tx = w.transactions
    tx_t3, tx_p3, tx_t12 = w.last_3m(tx), w.prior_3m(tx), w.last_12m(tx)
    revenue_t12 = float(tx_t12["amount"].sum())
    credit_share = _share(tx_t12, tx_t12["credit"].eq(True), revenue_t12) if not tx_t12.empty else None
    identified_share = _share(tx_t12, tx_t12["customer_key"].notna(), revenue_t12) if not tx_t12.empty else None
    profit_loss = [r for r in (w.reports.get("profit_loss") or {}).values() if r]
    ledger_revenue = sum(float((r.get("revenue") or {}).get("total_revenue") or 0) for r in profit_loss)
    books_coverage = ratio(ledger_revenue, revenue_t12) if revenue_t12 > 0 else None
    tracking = supplier_tracking(w)
    documents = purchase_documents(w)
    return Profile(
        business_level=business_level,
        history_days=w.history_days(),
        tx_t3=tx_t3,
        tx_p3=tx_p3,
        tx_t12=tx_t12,
        revenue_t3=float(tx_t3["amount"].sum()),
        revenue_p3=float(tx_p3["amount"].sum()),
        revenue_t12=revenue_t12,
        trading_days=int(tx_t3["date"].dt.normalize().nunique()) if not tx_t3.empty else 0,
        credit_share=credit_share,
        cash_business=credit_share is not None and credit_share < registry.CASH_BUSINESS_CREDIT_SHARE,
        identified_share=identified_share,
        walk_in=identified_share is not None and identified_share < registry.WALK_IN_IDENTIFIED_SHARE,
        profit_loss=profit_loss,
        books_coverage=books_coverage,
        books_reliable=books_coverage is not None and books_coverage >= registry.BOOKS_COVERAGE_MIN,
        paid_payroll=_paid_payroll(w),
        purchase_documents=documents,
        supplier_tracking=tracking,
        purchase_base=meets_purchase_base(documents, tracking["purchase_value_12m"], revenue_t12),
        sector=registry.sector_of(w.tenant.get("business_type_name")),
        products=products_in_use(w) if business_level else None,
    )


def _share(tx, mask, total):
    return ratio(tx.loc[mask, "amount"].sum(), total) if total > 0 else None


def _paid_payroll(w):
    payroll = w.table("payroll")
    if payroll.empty:
        return payroll
    paid = payroll[payroll["status"].fillna("").str.lower().isin(PAID_PAYROLL)]
    return paid[paid["period_start"] <= w.as_of]
