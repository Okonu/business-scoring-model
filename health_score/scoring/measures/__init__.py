"""Raw measure values for one business or one shop, and the context the engine needs"""

import numpy as np

from health_score.scoring.measures.cash import cash_measures
from health_score.scoring.measures.customers import customer_measures
from health_score.scoring.measures.formality import formality_measures
from health_score.scoring.measures.operations import operations_measures
from health_score.scoring.measures.profile import Profile, build_profile
from health_score.scoring.measures.profit import profit_measures
from health_score.scoring.measures.sales import sales_measures
from health_score.scoring.measures.signals import red_flag_inputs
from health_score.scoring.measures.window import Window

DIMENSION_MEASURES = (
    sales_measures,
    cash_measures,
    profit_measures,
    customer_measures,
    operations_measures,
    formality_measures,
)


def compute_measures(data, business_level=True):
    """
    Every measure the data supports; a measure without data is absent, never zero

    Returns:
        tuple: (values: {measure_id: float}, context: dict)
    """
    w = Window(data)
    p = build_profile(w, business_level)
    raw = {}
    for measure in DIMENSION_MEASURES:
        raw.update(measure(w, p))
    values = {k: float(v) for k, v in raw.items() if v is not None and np.isfinite(v)}
    return values, _context(w, p)


def _context(w, p: Profile):
    return {
        "credit_share": p.credit_share,
        "cash_business": p.cash_business,
        "identified_customer_share": p.identified_share,
        "walk_in": p.walk_in,
        "history_days": p.history_days,
        "first_transaction": w.first_transaction.isoformat() if w.first_transaction is not None else None,
        "revenue_t3m": p.revenue_t3,
        "revenue_p3m": p.revenue_p3,
        "revenue_t12m": p.revenue_t12,
        "books_coverage": p.books_coverage,
        "books_reliable": p.books_reliable,
        "transactions_t3m": int(len(p.tx_t3)),
        "sector": p.sector,
        "supplier_tracking": p.supplier_tracking,
        "purchase_documents_12m": p.purchase_documents,
        "purchase_base_met": p.purchase_base,
        "products_in_use": p.products,
        "red_flag_inputs": red_flag_inputs(w, p),
    }


__all__ = ["compute_measures"]
