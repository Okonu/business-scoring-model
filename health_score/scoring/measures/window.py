"""Time windows over one business or one shop, and the arithmetic shared by every measure"""

from datetime import timedelta

import pandas as pd


class Window:
    def __init__(self, data):
        self.data = data
        self.table = data.table
        self.reports = data.reports
        self.tenant = data.tenant
        self.as_of = data.as_of
        self.t3 = self.as_of - timedelta(days=90)
        self.p3 = self.as_of - timedelta(days=180)
        self.t6 = self.as_of - timedelta(days=182)
        self.t12 = self.as_of - timedelta(days=365)
        tx = data.table("transactions")
        self.transactions = tx[tx["date"] <= self.as_of] if not tx.empty else tx
        self.first_transaction = self.transactions["date"].min() if not self.transactions.empty else None

    def between(self, df, start, end, column="date"):
        if df.empty or column not in df.columns:
            return df
        return df[(df[column] > start) & (df[column] <= end)]

    def last_3m(self, df, column="date"):
        return self.between(df, self.t3, self.as_of, column)

    def prior_3m(self, df, column="date"):
        return self.between(df, self.p3, self.t3, column)

    def last_6m(self, df, column="date"):
        return self.between(df, self.t6, self.as_of, column)

    def last_12m(self, df, column="date"):
        return self.between(df, self.t12, self.as_of, column)

    def revenue(self, start, end):
        return float(self.between(self.transactions, start, end)["amount"].sum())

    def history_days(self):
        return (self.as_of - self.first_transaction).days if self.first_transaction is not None else 0


def ratio(numerator, denominator):
    if numerator is None or denominator is None or pd.isna(denominator) or denominator == 0:
        return None
    return float(numerator) / float(denominator)


def trend(current, previous):
    if previous is None or previous <= 0:
        return None
    return float(current) / float(previous) - 1
