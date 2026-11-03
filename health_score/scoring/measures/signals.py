"""Inputs to the red flags that are not measures themselves"""

from datetime import timedelta

from health_score.scoring import registry
from health_score.scoring.measures.receivables import open_receivables, severe_payables_share, severe_share
from health_score.scoring.measures.sales import same_quarter_last_year

PRIOR_PAYROLL_MONTHS = 3


def red_flag_inputs(w, p):
    return {
        "ar_severe_share": severe_share(open_receivables(w)),
        "ap_severe_share": severe_payables_share(w),
        "missed_payroll": missed_payroll(w, p.paid_payroll),
        "revenue_same_quarter_last_year": (
            same_quarter_last_year(w) if p.history_days >= registry.YOY_MIN_HISTORY_DAYS else None
        ),
    }


def missed_payroll(w, runs):
    """A business that ran payroll in 3+ of the prior months has none in the last 2"""
    if runs.empty:
        return False
    gap_start = w.as_of - timedelta(days=registry.PAYROLL_GAP_DAYS)
    prior = w.between(runs, w.t6, gap_start, "period_start")
    recent = w.between(runs, gap_start, w.as_of, "period_start")
    return len(set(prior["period_start"].dt.to_period("M"))) >= PRIOR_PAYROLL_MONTHS and recent.empty
