"""Shared fixtures: a fake BASEPOINT client serving synthetic business data"""

from datetime import datetime, timedelta

import pytest

from health_score.basepoint import AuthenticationError, collect

AS_OF = datetime(2026, 9, 26)
SHOPS = ["shopA", "shopB"]

TENANT = {
    "_id": "t1",
    "name": "Test Business",
    "tenant_code": "TEST-000001",
    "business_type_name": "Retail",
    "createdAt": (AS_OF - timedelta(days=600)).isoformat(),
    "subscription_status": "active",
    "is_subscription_active": True,
    "modules": {"pos": True},
}
ADMIN = {"name": "admin", "role": "admin", "is_admin": True}

SHOP_SCOPED = {
    "/api/customers",
    "/packages",
    "/services",
    "/accounting/journal-entries",
    "/accounting/bank-reconciliations",
}


class FakeClient:
    """Serves canned BASEPOINT responses by path; mirrors FSSClient's interface"""

    def __init__(self, lists=None, reports=None, pin="1234", base_url=None, timeout=None):
        self.lists = lists or {}
        self.reports = reports or {}
        self.pin = pin
        self.coverage = []

    def login(self, company_code, pin, username=None):
        if pin != self.pin:
            raise AuthenticationError("Login failed for this company code")
        return dict(TENANT), dict(ADMIN)

    def get_list(self, path, params=None, key=None, label=None, **_):
        self.coverage.append({"endpoint": label or path, "status": 200, "records": 0, "error": None, "ms": 1})
        records = [dict(r) for r in self.lists.get(path, [])]
        shop = (params or {}).get("shop_id")
        if shop and path in SHOP_SCOPED:
            records = [r for r in records if r.get("shop_id") == shop]
        return records

    def get(self, path, params=None, label=None):
        return self.reports.get(path)


def make_order(i, shop, day, amount, customer=None, method="Mpesa"):
    date = (AS_OF - timedelta(days=day)).isoformat()
    return {
        "_id": f"o{i}",
        "shop_id": shop,
        "createdAt": date,
        "order_amount": amount,
        "discount_amount": 0,
        "order_status": "COMPLETED",
        "customer_id": customer,
        "order_items": [{"product_id": {"_id": "p1", "name": "Flour"}, "quantity": 1, "price": amount}],
        "order_payments": [
            {
                "amount": amount,
                "payment_date": date,
                "name": method,
                "payment_status": "COMPLETED",
                "direction": "inbound",
                "receiptNumber": f"R{i}",
            }
        ],
    }


def make_business(days=540, daily=4, amount=1000, decline_last_90=False):
    """A steady two-shop Duka business with named customers"""
    orders, i = [], 0
    for day in range(1, days):
        n = daily if not (decline_last_90 and day <= 90) else max(daily // 4, 1)
        for k in range(n):
            orders.append(make_order(i, SHOPS[k % 2], day, amount, customer=f"c{i % 40}"))
            i += 1
    customers = [
        {
            "_id": f"c{j}",
            "shop_id": SHOPS[j % 2],
            "phone": f"07{j:08d}",
            "createdAt": (AS_OF - timedelta(days=500 - j)).isoformat(),
        }
        for j in range(40)
    ]
    inventory = [
        {
            "_id": f"i{j}",
            "shop_id": "shopA",
            "name": "Flour" if j == 0 else f"Item {j}",
            "quantity": 30,
            "price": 1000,
            "supplier_price": 600,
            "min_viable_quantity": 10,
            "usage_type": "selling",
            "status": "active",
        }
        for j in range(5)
    ]
    return {
        "/shops": [{"_id": s, "name": s, "pos_mode": "retail", "staff_count": 3} for s in SHOPS],
        "/orders": orders,
        "/api/customers": customers,
        "/product-inventory": inventory,
        # POS orders create invoices automatically; these must not be counted again
        "/accounting/invoices": [
            {
                "_id": f"inv{o['_id']}",
                "shop_id": o["shop_id"],
                "source": "pos",
                "order_id": o["_id"],
                "grand_total": o["order_amount"],
                "issue_date": o["createdAt"],
                "status": "Paid",
            }
            for o in orders[:50]
        ],
    }


def make_purchase_order(n, days_ago, supplier="s1"):
    return {
        "_id": f"po{n}",
        "shop_id": "shopA",
        "supplier_id": supplier,
        "status": "fully_delivered",
        "createdAt": (AS_OF - timedelta(days=days_ago)).isoformat(),
        "po_items": [
            {
                "inventory_id": {"_id": "i0", "name": "Flour"},
                "quantity_ordered": 50,
                "quantity_received": 50,
                "unit_price": 600,
            }
        ],
    }


def collect_data(lists, reports=None):
    """Collected BusinessData for synthetic lists"""
    return collect(FakeClient(lists, reports), dict(TENANT), dict(ADMIN), AS_OF)


@pytest.fixture
def business_lists():
    return make_business()
