"""BASEPOINT products a business actively uses"""


def products_in_use(w):
    table = w.table
    accounting_invoices = table("invoices")
    if not accounting_invoices.empty:
        accounting_invoices = accounting_invoices[accounting_invoices["source"] == "accounting"]
    active = {
        "duka": not w.last_3m(table("orders")).empty,
        "pesa": any(not w.last_3m(table(name)).empty for name in ("receipts", "expenses", "bills"))
        or not w.last_3m(accounting_invoices).empty,
        "bandu": not w.last_3m(table("payroll"), "period_start").empty or not w.last_3m(table("leave"), "start").empty,
        "mteja": not w.last_3m(table("leads")).empty or not w.last_3m(table("sales_targets"), "end").empty,
        "dala": any(
            not w.last_3m(table(name)).empty
            for name in ("rent_invoices", "rent_payments", "property_sale_payments", "maintenance")
        ),
    }
    return [product for product, on in active.items() if on]
