"""Customer and revenue base measures (methodology table 8)"""

from health_score.scoring import registry
from health_score.scoring.measures.window import trend

AT_RISK_STAGES = ["at_risk", "churned"]
MIN_NAMED_CUSTOMERS = 2
MIN_PRIOR_CUSTOMERS = 3
MIN_TRANSACTIONS_FOR_BREADTH = 10
MIN_PRODUCTS = 3
MIN_RATINGS = 3


def customer_measures(w, p):
    return {
        **_named_customers(p),
        **_breadth(w, p),
        **_acquisition(w),
        **_visits(w),
        **_loyalty(w, p),
    }


def _named_customers(p):
    if p.walk_in:
        if p.history_days >= registry.TREND_MIN_HISTORY_DAYS:
            return {"active_customer_trend": trend(len(p.tx_t3), len(p.tx_p3))}
        return {}
    if p.revenue_t12 <= 0 or p.identified_share is None:
        return {}
    values = {}
    by_customer = p.tx_t12.dropna(subset=["customer_key"]).groupby("customer_key")["amount"].sum()
    if len(by_customer) >= MIN_NAMED_CUSTOMERS:
        values["top_customer_share"] = float(by_customer.max() / p.revenue_t12)
        values["customer_hhi"] = float(((by_customer / by_customer.sum()) ** 2).sum())
    current, previous = set(p.tx_t3["customer_key"].dropna()), set(p.tx_p3["customer_key"].dropna())
    if len(previous) >= MIN_PRIOR_CUSTOMERS:
        values["customer_retention"] = len(previous & current) / len(previous)
        values["active_customer_trend"] = trend(len(current), len(previous))
    return values


def _breadth(w, p):
    values = {}
    if len(p.tx_t12) >= MIN_TRANSACTIONS_FOR_BREADTH and p.revenue_t12 > 0:
        values["txn_breadth"] = float(p.tx_t12["amount"].max() / p.revenue_t12)
    items = w.last_12m(w.table("order_items"))
    if not items.empty and items["amount"].sum() > 0:
        by_product = items.groupby("name_key")["amount"].sum()
        if len(by_product) >= MIN_PRODUCTS:
            values["product_concentration"] = float(by_product.max() / by_product.sum())
    return values


def _acquisition(w):
    customers = w.table("customers")
    if customers.empty:
        return {}
    first_seen = customers.groupby("key")["created"].min()
    new_t3 = int(((first_seen > w.t3) & (first_seen <= w.as_of)).sum())
    new_p3 = int(((first_seen > w.p3) & (first_seen <= w.t3)).sum())
    return {"new_customer_trend": trend(new_t3, new_p3)}


def _visits(w):
    visits = w.table("visits")
    if visits.empty:
        return {}
    values = {"visit_trend": trend(len(w.last_3m(visits)), len(w.prior_3m(visits)))}
    ratings = visits["rating"].dropna()
    if len(ratings) >= MIN_RATINGS:
        values["satisfaction"] = float(ratings.mean())
    return values


def _loyalty(w, p):
    customers = w.table("customers")
    if customers.empty or p.revenue_t12 <= 0:
        return {}
    values = {}
    if (customers["loyalty"] > 0).any() or not w.table("packages").empty:
        loyal = set(customers.loc[customers["loyalty"] > 0, "key"])
        orders = w.last_12m(w.table("orders"))
        loyal_revenue = p.tx_t12.loc[p.tx_t12["customer_key"].isin(loyal), "amount"].sum()
        subscription_revenue = orders.loc[orders["recurring"], "amount"].sum() if not orders.empty else 0.0
        values["loyalty_engagement"] = float(loyal_revenue + subscription_revenue) / p.revenue_t12
    if customers["stage"].notna().any() and not p.walk_in:
        at_risk = set(customers.loc[customers["stage"].fillna("").isin(AT_RISK_STAGES), "key"])
        values["at_risk_share"] = (
            float(p.tx_t12.loc[p.tx_t12["customer_key"].isin(at_risk), "amount"].sum()) / p.revenue_t12
        )
    return values
