"""Red flags that cap the overall score (methodology table 13)"""

from health_score.scoring import registry
from health_score.scoring.shops import mature_shops


def red_flags(values, context, shops):
    checks = (
        _revenue_collapse(context),
        _missed_payroll(context),
        _severe_supplier_arrears(context),
        _cash_exhaustion(values),
        *_flagship_collapse(shops),
        _receivables_write_off(context),
        _single_customer(values),
        _widespread_shop_decline(shops),
    )
    return [flag for flag in checks if flag]


def overall_cap(flags):
    return min((flag["cap"] for flag in flags), default=100)


def _flag(key, name, detail):
    return {"flag": name, "detail": detail, "cap": registry.CAPS[key]}


def _halved(current, previous):
    return previous is not None and previous > 0 and current <= registry.COLLAPSE_RATIO * previous


def _revenue_collapse(context):
    if context["history_days"] < registry.TREND_MIN_HISTORY_DAYS:
        return None
    quarter = _halved(context["revenue_t3m"], context["revenue_p3m"])
    last_year = context["red_flag_inputs"].get("revenue_same_quarter_last_year")
    year_on_year = last_year is None or _halved(context["revenue_t3m"], last_year)
    if quarter and year_on_year:
        return _flag(
            "revenue_collapse", "Revenue collapse", "Last 3 months' revenue is at most half of the previous 3 months"
        )
    return None


def _missed_payroll(context):
    if context["red_flag_inputs"].get("missed_payroll"):
        return _flag("missed_payroll", "Missed payroll", "No completed payroll in the last 2 months")
    return None


def _severe_supplier_arrears(context):
    share = context["red_flag_inputs"].get("ap_severe_share")
    if share is not None and share >= registry.SUPPLIER_ARREARS_SHARE:
        return _flag(
            "severe_supplier_arrears", "Severe supplier arrears", "Half or more of open bills are 90+ days past due"
        )
    return None


def _cash_exhaustion(values):
    runway = values.get("cash_runway")
    if runway is not None and runway < registry.CASH_EXHAUSTION_MONTHS:
        return _flag("cash_exhaustion", "Cash exhaustion", "Cash runway under 20 days")
    return None


def _flagship_collapse(shops):
    return [
        _flag("flagship_collapse", "Flagship shop collapse", f"{shop['name']} halved its revenue")
        for shop in shops
        if shop["revenue_share"] >= registry.FLAGSHIP_SHARE and _halved(shop["revenue_t3m"], shop["revenue_p3m"])
    ]


def _receivables_write_off(context):
    share = context["red_flag_inputs"].get("ar_severe_share")
    if share is not None and share >= registry.WRITE_OFF_SHARE:
        return _flag("receivables_write_off", "Receivables write-off risk", "40%+ of receivables are 90+ days past due")
    return None


def _single_customer(values):
    share = values.get("top_customer_share")
    if share is not None and share >= registry.SINGLE_CUSTOMER_SHARE:
        return _flag("single_customer", "Single-customer dependence", "One customer is 70%+ of revenue")
    return None


def _widespread_shop_decline(shops):
    mature = mature_shops(shops)
    if len(mature) < registry.MIN_SHOPS_FOR_NETWORK:
        return None
    if sum(s["declining"] for s in mature) / len(mature) >= registry.WIDESPREAD_DECLINE_SHARE:
        return _flag("widespread_shop_decline", "Widespread shop decline", "60%+ of established shops are declining")
    return None
