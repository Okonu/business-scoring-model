# Business Health Score — Draft Methodology

- **Status:** Implemented (engine version 0.2.0). Weights and thresholds are starting proposals, not agreed values.
- **Date:** 2026-09-26
- **Data source:** BASEPOINT / FSS (schema: [`ERD.md`](ERD.md); API: `api.hospitality.reliatech.co.ke`)
- **Companion to:** [`credit-scoring-methodology.md`](credit-scoring-methodology.md)

---

## 1. Purpose and principles

The health score answers: *how healthy is this business overall?* The business scored is the **tenant** (a BASEPOINT business).

### 1.1 Principles

1. **Any one product is enough to score a business.** BASEPOINT sells standalone products: Duka (POS, inventory, customers, shops), Pesa (accounting), Bandu (HR and payroll), Mteja (CRM) and Dala (property). A business using only one of them must still get a full, comparable score.
2. **More products mean more evidence, plus a slight advantage.** The score is built from **six fixed dimensions with fixed weights**. Each product contributes *measures* to those same dimensions; no product adds a dimension or weight of its own. A business with five products and a business with one are scored on the same scale. Extra products make the estimate more precise, reported separately as **confidence** (§7). The only direct advantage is one deliberately small measure, **ecosystem depth** (§3.6), worth at most about 2 points.
3. **Fixed thresholds, not comparison with other businesses.** Each measure scores 0–100 against fixed Good/Poor thresholds, so one outlier business can't move anyone else's score. Sector benchmarks replace some thresholds once there's enough data (§6.3), and are then held fixed between quarterly refreshes.
4. **Supplier data where it exists, weighted more when tracked.** Businesses aren't required to record suppliers or link inventory to them. When they do (suppliers, purchase orders, deliveries, bills, supplier-linked inventory), that data feeds payables, procurement, sell-through and traceability measures. The more completely a supplier's goods are tracked from purchase to sale, the more those measures weigh (§3.9). When there's no supplier data, those measures don't apply and nothing is penalized.

### 1.2 Business and shops

A business operates one or more **shops**, and almost every record carries a `shop_id`. Scores are produced at two levels:

| Level | What it is |
|---|---|
| **Business** | The headline score, from consolidated data across all shops |
| **Shop** | The same dimensions calculated on each shop's own data, to show which shops lift or drag the business |

---

## 2. Dimensions

| # | Dimension | Weight | Question |
|---|---|---|---|
| 1 | **Sales performance** | 22% | Is the business selling steadily and growing? |
| 2 | **Cash, collections and payables** | 22% | Does the money it earns come in on time, and does it pay what it owes on time? |
| 3 | **Profitability and cost control** | 13% | Does it make money on what it sells? |
| 4 | **Customer and revenue base** | 13% | Is its income spread widely, and do customers come back? |
| 5 | **Operational stability** | 18% | Is it stable: staff, stock, capacity, shops, tenure? |
| 6 | **Formality and compliance** | 12% | Does it run like a formal business: digital payments, tax, books, statutory obligations? |

These weights never change with the products a business uses.

---

## 3. Data point register

**Every behavioural data point in BASEPOINT is weighted.** Each one feeds a measure, and each measure has a fixed weight inside one dimension. The "Sources" column lists which products can supply it. A business gets whichever measures its products allow. Within a dimension, the weights of the available measures are re-normalized to 100%; the dimension's own weight never changes. So a data point from an extra product sharpens a dimension without adding weight to it.

Each measure scores 0–100 on a **piecewise-linear scale**: at or better than Good = 100, at or worse than Poor = 0, linear in between. The thresholds are starting proposals.

### 3.1 Sales performance · 22%

**Revenue** is the union of these sources, **de-duplicated**:
- **Duka:** completed POS orders (`order_amount`).
- **Pesa invoices:** accounting invoices (`source = accounting`, `direction = customer`, status not `Draft` or `Voided`) that aren't linked to an order.
- **Pesa sales receipts:** receipts **not** linked to an invoice. These are cash sales recorded in accounting. A receipt linked to an invoice (`invoice_id`) is the payment for that invoice, not new revenue.
- **Dala:** rent invoices and property sale payments.

POS orders automatically create invoices (`source = pos`, with `order_id`). Those are the same sales and are **not counted again**.

A **transaction** is one completed order, unlinked sales receipt, accounting invoice or rent invoice.

| Measure | Data points | Sources | Good | Poor | Weight |
|---|---|---|---|---|---|
| Daily transaction volume: average transactions per trading day, T3M | Orders, receipts, invoices | Duka, Pesa, Dala | ≥ 50 / day | ≤ 2 / day | 10% |
| Daily transaction value: average revenue per trading day, T3M | Same | Duka, Pesa, Dala | ≥ KES 50,000 / day | ≤ KES 1,000 / day | 10% |
| Revenue growth: T3M vs P3M | Same | Duka, Pesa, Dala | ≥ +10% | ≤ −30% | 14% |
| Year-on-year growth (needs 15+ months) | Same | Duka, Pesa, Dala | ≥ +10% | ≤ −30% | 8% |
| Revenue volatility: coefficient of variation of monthly revenue, T12M | Same | Duka, Pesa, Dala | ≤ 0.15 | ≥ 0.60 | 12% |
| Trading continuity: months with revenue in T12M | Same | Duka, Pesa, Dala | 12 | ≤ 6 | 6% |
| Trading days: days with sales ÷ days in T3M | Transaction dates | Duka, Pesa | ≥ 85% | ≤ 30% | 6% |
| Transaction count trend: T3M vs P3M | Transaction count | Duka, Pesa, Dala | ≥ +5% | ≤ −30% | 6% |
| Average transaction value trend: T3M vs P3M | Revenue ÷ transactions | Duka, Pesa | ≥ 0% | ≤ −25% | 4% |
| Revenue leakage: (discounts + voided items) ÷ gross sales | `discount_amount`, void reports, receipt `total_discount` | Duka, Pesa | ≤ 3% | ≥ 20% | 7% |
| Refunds and credit notes ÷ revenue | Refunds, notes | Pesa | ≤ 1% | ≥ 10% | 4% |
| Recurring revenue share: subscriptions, packages and leases ÷ revenue | Subscriptions, packages, leases | Duka, Dala | ≥ 30% | 0% | 5% |
| Forward bookings: bookings and consultations scheduled in the next 30 days vs the last 30 days | Schedules, consultations | Duka | ≥ 1.0× | ≤ 0.5× | 3% |
| Sales target attainment: actual ÷ target | Sales targets | Mteja | ≥ 100% | ≤ 60% | 3% |
| Lead conversion rate, T6M | Leads, lead stages | Mteja | ≥ 25% | ≤ 5% | 2% |

**Volume and value are scale measures.** Their fixed thresholds are starting points. Scale differs so much by business type that these two measures move to **sector percentiles** as soon as there are enough businesses per type (§6.3).

Recurring revenue has Poor = 0%. It only applies when the business offers subscriptions, packages or leases.

### 3.2 Cash, collections and payables · 22%

| Measure | Data points | Sources | Good | Poor | Weight |
|---|---|---|---|---|---|
| Cash realization: cash received ÷ revenue, T3M | Order payments, invoice payments, sales receipts, rent payments | Duka, Pesa, Dala | ≥ 95% | ≤ 60% | 19% |
| Severe overdue ratio (receivables): 60+ days past due ÷ total open | AR aging, rent aging | Pesa, Dala | ≤ 5% | ≥ 40% | 11% |
| DSO: receivables ÷ credit sales in T3M × 90 | Invoices; Duka proxy: Σ `Customer.current_balance` | Pesa, Dala, Duka | ≤ 30 | ≥ 120 | 11% |
| Weighted average days past due (receivables) | AR aging, rent aging | Pesa, Dala | ≤ 5 | ≥ 60 | 6% |
| Collection effectiveness index (CEI), T3M | Invoices, payments | Pesa, Dala | ≥ 90% | ≤ 50% | 6% |
| Aging drift: 3-month change in the receivables severe overdue ratio | AR aging with `as_of_date` | Pesa, Dala | ≤ 0 pts | ≥ +20 pts | 4% |
| Cash runway: bank balances ÷ average monthly outflow | Cash-flow report | Pesa | ≥ 3 months | ≤ 0.5 months | 10% |
| Customers over credit limit | `credit_limit`, `current_balance` | Duka, Pesa | ≤ 5% | ≥ 30% | 3% |
| Rent collection rate, T3M | Rent invoices, rent payments | Dala | ≥ 95% | ≤ 60% | 7% |
| Payment-plan collection: installments paid ÷ installments due | Payment plans, sale payments | Dala | ≥ 95% | ≤ 60% | 3% |
| Gift card liability: unredeemed balance ÷ monthly revenue | Gift cards | Duka | ≤ 5% | ≥ 50% | 2% |
| Severe overdue ratio (payables): bills 60+ days past due ÷ total open bills | AP aging, bills | Pesa | ≤ 5% | ≥ 40% | 7% ◆ |
| Bills paid on time: bills paid by `due_date` ÷ bills due, T6M | Bills (`due_date`, `paid_date`) | Pesa | ≥ 90% | ≤ 40% | 7% ◆ |
| DPO ÷ agreed supplier terms | Bills, `Supplier.payment_terms` | Pesa, Duka | ≤ 1.1× | ≥ 2.5× | 4% ◆ |

**Cash businesses:** if credit sales are under 5% of revenue, the receivables measures don't apply. **Businesses without supplier bills:** the payables measures don't apply. Neither case is penalized.

### 3.3 Profitability and cost control · 13%

| Measure | Data points | Sources | Good | Poor | Weight |
|---|---|---|---|---|---|
| Gross margin: (revenue − cost of goods sold) ÷ revenue | Best available cost, in order: actual purchase cost of supplier-tracked stock (PO and bill unit prices); P&L; sold quantity × `supplier_price` (only if ≥ 80% of items sold have a cost price); recipes for restaurants | Pesa, Duka | ≥ 35% | ≤ 5% | 24% |
| Net margin: (revenue − expenses) ÷ revenue | P&L | Pesa | ≥ 10% | ≤ −10% | 23% |
| Staff cost ÷ revenue | Payroll `total_gross`; wages | Bandu, Duka | ≤ 25% | ≥ 60% | 14% |
| Cost discipline: expense growth − revenue growth, T3M vs P3M | Expenses | Pesa | ≤ 0 pts | ≥ +25 pts | 9% |
| Revenue per staff member, monthly | Revenue ÷ staff (`staff_count`, active employees) | Duka, Bandu | ≥ sector 75th pct | ≤ sector 10th pct | 9% |
| Maintenance cost ÷ rent income | Maintenance tickets and costs, rent | Dala | ≤ 5% | ≥ 25% | 9% |
| Commission cost ÷ property sales | Commissions, sales | Dala | ≤ 3% | ≥ 10% | 4% |
| Purchase-to-sales alignment: purchases of supplier-tracked stock ÷ cost of that stock sold, T3M | POs, bills, order items of supplier-tracked products | Duka, Pesa | 0.8–1.2× | ≤ 0.3× or ≥ 2.5× | 8% ◆ |

Revenue per staff member uses sector percentiles from the start, since it varies too much by business type for fixed thresholds.

### 3.4 Customer and revenue base · 13%

| Measure | Data points | Sources | Good | Poor | Weight |
|---|---|---|---|---|---|
| Top customer's share of T12M revenue | Identified customers; tenants | Duka, Pesa, Dala | ≤ 15% | ≥ 60% | 16% |
| Customer retention: share of P3M customers who bought again in T3M | Customers, orders; lease renewals | Duka, Pesa, Dala | ≥ 70% | ≤ 20% | 16% |
| Active-customer trend: T3M vs P3M | Customers, orders | Duka, Pesa, Dala | ≥ +5% | ≤ −30% | 10% |
| Revenue concentration (HHI across customers) | Customers, orders | Duka, Pesa, Dala | ≤ 0.10 | ≥ 0.40 | 7% |
| Transaction breadth: largest single sale's share of T12M revenue | Orders, invoices | Duka, Pesa | ≤ 5% | ≥ 40% | 10% |
| Product concentration: top product's share of revenue | Best sellers, order items | Duka | ≤ 20% | ≥ 70% | 8% |
| New customers per month, T3M vs P3M | Customer `createdAt` | Duka, Mteja | ≥ 0% | ≤ −50% | 8% |
| Customer visit trend: T3M vs P3M | Customer visits | Duka, Mteja | ≥ 0% | ≤ −30% | 6% |
| Customer satisfaction: average feedback rating | Customer feedback | Duka | ≥ 4.3 / 5 | ≤ 3.0 / 5 | 7% |
| Loyalty engagement: revenue from loyalty, gift card and subscription customers ÷ revenue | Loyalty points, gift cards, subscriptions | Duka | ≥ 20% | 0% | 5% |
| At-risk revenue: share of revenue from `at_risk` or `churned` customers | Lifecycle stages | Mteja | ≤ 5% | ≥ 30% | 7% |

**Walk-in businesses:** if identified customers account for under 20% of revenue, the customer-level measures don't apply. The dimension then rests on transaction breadth, product concentration and the transaction trend.

### 3.5 Operational stability · 18%

| Measure | Data points | Sources | Good | Poor | Weight |
|---|---|---|---|---|---|
| Business tenure: months since the first transaction or `Tenant.createdAt` | Tenant, orders | Any | ≥ 36 | ≤ 6 | 8% |
| Staff count trend: now vs 6 months ago | `Shop.staff_count`; active employees | Duka, Bandu | ≥ 0% | ≤ −40% | 6% |
| Staff turnover: exits ÷ average headcount, T12M | Employees (`employment_status`, dates) | Bandu | ≤ 15% | ≥ 60% | 6% |
| Payroll regularity: months with completed payroll in T6M ÷ 6 | Payroll; wages | Bandu, Duka | 100% | ≤ 50% | 8% |
| Shift regularity: trading days with an opened shift ÷ trading days | Shifts | Duka | ≥ 90% | ≤ 40% | 5% |
| Key-person dependence: top staff member's share of sales | `served_by`, top earners | Duka | ≤ 40% | ≥ 90% | 5% |
| Stock-out rate: selling items below `min_viable_quantity` | Inventory | Duka | ≤ 5% | ≥ 30% | 6% |
| Inventory turnover: COGS T12M ÷ average inventory value at cost | Inventory, cost prices | Duka | ≥ 6× | ≤ 1× | 6% |
| Dead stock: value of items unsold in 90 days ÷ inventory value | Inventory, order items | Duka | ≤ 10% | ≥ 50% | 3% |
| Catalogue activity: share of active products sold in T3M | Products, services, order items | Duka | ≥ 60% | ≤ 15% | 3% |
| Capacity utilization: orders per table per trading day (restaurants); room nights ÷ available rooms (hotels) | Tables, orders; hotel bookings | Duka | ≥ sector 75th pct | ≤ sector 10th pct | 3% |
| Occupancy: occupied units ÷ total units | Units | Dala | ≥ 90% | ≤ 50% | 6% |
| Maintenance backlog: open tickets older than 30 days ÷ open tickets | Maintenance tickets | Dala | ≤ 10% | ≥ 50% | 3% |
| Shop network (2+ shops only): see §3.7 | Shops, orders | Duka | ≥ 75 | ≤ 40 | 8% |
| Unplanned leave: unplanned leave days ÷ working days | Leave | Bandu | ≤ 2% | ≥ 10% | 2% |
| Asset base trend: net book value now vs 12 months ago | Assets | Pesa | ≥ 0% | ≤ −30% | 2% |
| Supplier concentration: top supplier's share of purchases, T12M | Purchase orders, bills | Duka, Pesa | ≤ 30% | ≥ 80% | 5% ◆ |
| Delivery fill rate: quantity received ÷ quantity ordered on purchase orders, T6M | Purchase orders (`delivery_percentage`, status), deliveries | Duka | ≥ 95% | ≤ 60% | 4% ◆ |
| Procurement regularity: months with purchases in T6M ÷ 6 | Purchase orders, bills | Duka, Pesa | 100% | ≤ 33% | 2% ◆ |
| Sell-through of supplier-tracked stock: units sold ÷ units received, per supplier, weighted by purchase value, T6M | Deliveries, order items of supplier-tracked products | Duka | ≥ 80% | ≤ 30% | 5% ◆ |
| Stock cover of supplier-tracked stock: days of sales the stock on hand covers | Inventory, order items | Duka | 14–60 days | ≤ 3 or ≥ 180 days | 4% ◆ |

Supplier measures (◆) apply only when the business records suppliers and purchases; sell-through and stock cover also need inventory tracked to suppliers. Their weights scale with tracking completeness (§3.9).

### 3.6 Formality and compliance · 12%

| Measure | Data points | Sources | Good | Poor | Weight |
|---|---|---|---|---|---|
| Digital payment share: M-Pesa, card and Pesapal ÷ all payments | Payment methods, order payments, receipt `payment_method` | Duka, Pesa | ≥ 70% | ≤ 10% | 18% |
| Tax registration and eTIMS: VAT enabled; share of invoices verified with KRA eTIMS | `is_vat_enabled`, eTIMS/DigiTax status | Duka, Pesa | eTIMS on, ≥ 90% verified | neither | 15% |
| Receipting: share of sales with a receipt issued | `receiptNumber`, sales receipts, printed documents | Duka, Pesa | ≥ 95% | ≤ 50% | 8% |
| Bookkeeping regularity: months with posted journal entries in T6M ÷ 6 | Journal entries | Pesa | 100% | ≤ 33% | 11% |
| Bank reconciliation recency: days since the last completed reconciliation | Bank reconciliations | Pesa | ≤ 35 | ≥ 120 | 7% |
| Statutory payroll compliance: payroll runs with statutory deductions processed; P9 forms generated | Deductions, P9 forms | Bandu | 100% | ≤ 50% | 8% |
| Platform standing: BASEPOINT subscription active and paid on time | `subscription_status`, `next_billing_date` | Any | Active, current | Lapsed | 8% |
| **Ecosystem depth:** BASE products actively used (with activity in T3M) | Activity per product | Any | 4+ products = 100; 3 = 80; 2 = 60 | 1 product = 40 | 15% |
| Supply-chain traceability index (§3.9): inventory value weighted by supplier tracking tier | Suppliers, POs, deliveries, bills, inventory, order items | Duka, Pesa | ≥ 80 | ≤ 10 | 10% ◆ |

**Ecosystem depth gives a slight, capped advantage for using more BASE products.** A business running more of its operations on BASE is more transparent and its data is more verifiable. The advantage is deliberately small. Formality is 12% of the score, and even a single-product business scores 40 on this measure. So using all products instead of one adds at most about **2 points** to the overall score. Only products with actual activity in the last 3 months count, not products merely enabled.

The traceability index applies only when the business tracks inventory. Unlike ecosystem depth, it rewards how completely the business records its supply chain, whichever products it uses.

### 3.7 Shop network measure (2+ shops)

A single measure inside Operational stability, not a dimension of its own, so having several shops doesn't add weight. It is the average of four sub-scores:

| Sub-measure | Good | Poor |
|---|---|---|
| Share of revenue from shops scoring below 50 | ≤ 10% | ≥ 50% |
| Top shop's share of T12M revenue | ≤ 40% | ≥ 85% |
| Share of established shops with declining revenue (T3M vs P3M ≤ −10%) | ≤ 20% | ≥ 60% |
| Dormant shops: established shops with no sales in the last 30 days | 0% | ≥ 40% |

A shop's first 3 months are its **ramp-up**. Ramp-up shops count towards revenue and balances, but are excluded from growth, trend, retention and shop-network comparisons. Stock transfers between shops (`Transfer`) are internal movements, not sales.

### 3.8 Data points not weighted

These are configuration or presentation settings, not business behaviour, so they carry no weight: printers and print settings, units of measure, modifiers and add-ons, colour schemes and branding, tips settings, hotel settings, gallery, FAQs, roles and permissions, notifications, document templates and signing, Biashara AI. If any of them turns out to carry signal, it can be given a weight like any other data point.

WhatsApp/omnichannel responsiveness (`Customer.unreplied_texts`, `conversation_count`) is a candidate measure for the customer dimension, once we know how widely it's used.

### 3.9 Supplier-tracked data: tiers and heavier weights

Each supplier relationship is placed in a **tracking tier**, according to how much of the chain from purchase to sale the business records:

| Tier | What's recorded for the supplier | Index points |
|---|---|---|
| 0 | Nothing, or supplier name only | 0 |
| 1 | Purchases: purchase orders or bills | 40 |
| 2 | Purchases **and** inventory tracked to the supplier (`ProductInventory.supplier_id`) | 75 |
| 3 | The full chain: purchase order → delivery → bill → payment, **and** sales of that supplier's items (orders, invoices, receipts) | 100 |

**Traceability index** = Σ over inventory value (or purchase value where there's no inventory) of each supplier's share × its tier points. A business whose stock mostly comes from tier-3 suppliers scores near 100.

**Heavier weights for better-tracked supplier data.** Every supplier measure (◆) has its base weight multiplied by a tracking factor before the dimension's weights are re-normalized:

> tracking factor = 0.75 + 0.5 × (share of purchase value from tier 2–3 suppliers)

So supplier measures weigh 0.75× their base when nothing is tracked to inventory, 1.0× at half, and **1.25×** when all purchases come from tier 2–3 suppliers. The dimension weights (§2) never change; only the supplier measures' share *within* a dimension grows. Well-tracked supplier data therefore counts slightly more than other evidence in the same dimension.

**Why tracking earns weight:** when a supplier's goods can be followed from purchase to sale, the measures are computed from verified transactions (actual purchase costs, received quantities, units sold) rather than estimates. It also makes the stock usable as a basis for inventory-backed financing.

**In the demo account:** 20 of 34 inventory items are linked to a supplier, and there are 13 purchase orders and 3 bills. Most of its suppliers would sit at tiers 1–2.

---

## 4. Time frame and aging

- **Reference date (`t`):** normally today.
- **Windows:** T3M (trailing 3 months), P3M (the 3 months before that), T12M (trailing 12 months).
- **Monthly snapshots:** the score is computed at each month-end, so the output shows a trend.
- **Aging buckets:** not yet due, 1–30, 31–60, 61–90, 91–120, 121+ days past due. These are the same buckets as Pesa's AR aging report (`GET /accounting/reports/ar-aging`, which takes `as_of_date` for past snapshots). Rent aging uses the same buckets on `RentInvoice`.
- **Point-in-time reconstruction:** an invoice is open at date `d` if `issue_date ≤ d` and it wasn't fully paid by `d`. The amount open = `grand_total − Σ payments dated ≤ d`.

---

## 5. From measures to the score

1. **Measure → dimension:** a weighted average of the dimension's available measures, re-normalized within the dimension.
2. **Dimension → score:** a weighted average of the six dimensions at their **fixed** weights (§2).
3. **A dimension with no available measure at all** is filled with the **peer median** for that dimension. Peers are businesses of the same `business_type`, or all businesses until there are enough per type. The dimension is flagged as imputed, and confidence is lowered. This keeps the weights fixed: a missing dimension pulls the business neither up nor down relative to its peers.
4. **Minimum to publish:** at least 3 months of activity in a sales product (Duka, Pesa or Dala), and at most one imputed dimension. Otherwise the result is "Insufficient data".
5. **Red-flag caps** (§6) are applied last.

### 5.1 Business vs shop scores

- **Shop score:** the dimensions on the shop's own records. Shops in ramp-up get no score.
- **Business score:** the dimensions on **consolidated** data, not an average of shop scores. When consolidating:
  - Stock transfers between the business's own shops are not revenue or cost.
  - Customers are recorded per shop in BASEPOINT. At business level they're de-duplicated by phone or KRA PIN, the keys the API's cross-branch lookup uses (`/api/customers/other-branches`).
  - Accounting is per shop. Business-level ledger figures are the sum of the shops' reports.
  - Records without a `shop_id` (e.g. older orders; shown as "Unknown Shop" in BASEPOINT) count at business level only, and their share is reported.

---

## 6. Red flags, bands and benchmarks

### 6.1 Red flags (caps)

Red flags **cap** the score rather than subtracting from it, so a serious problem can't be averaged away. They're checked only when the relevant data exists, so a flag can never fire because a product is missing.

| Red flag | Condition | Cap | Needs |
|---|---|---|---|
| Revenue collapse | T3M revenue ≤ 50% of P3M | 40 | Any sales product |
| Missed payroll | No completed payroll in the last 2 months, for a business that normally runs one | 40 | Bandu or Duka wages |
| Cash exhaustion | Cash runway < 1 month | 45 | Pesa |
| Flagship shop collapse | A shop with ≥ 50% of revenue has T3M revenue ≤ 50% of P3M | 45 | 2+ shops |
| Receivables write-off risk | ≥ 40% of receivables 120+ days past due | 50 | Pesa or Dala |
| Single-customer dependence | Top customer ≥ 70% of T12M revenue | 55 | Identified customers |
| Severe supplier arrears | ≥ 50% of open bills 90+ days past due | 40 | Supplier bills |
| Widespread shop decline | ≥ 60% of established shops (at least 2) declining | 55 | 2+ shops |

### 6.2 Bands

| Score | Band |
|---|---|
| 80–100 | Strong |
| 65–79 | Healthy |
| 50–64 | Watch |
| 35–49 | Weak |
| 0–34 | Distressed |

### 6.3 Sector benchmarks

Once there are ≥ 20 businesses per `business_type`, the Good/Poor thresholds of sector-sensitive measures (margins, DSO, staff cost ÷ revenue, inventory turnover, stock-out rate) move to sector percentiles: Good = 75th, Poor = 10th. Refresh quarterly, and keep thresholds fixed between refreshes.

---

## 7. Confidence and product neutrality

### 7.1 Confidence

Reported alongside the score, never added to it:

| Level | Condition |
|---|---|
| High | No imputed dimension, ≥ 12 months of activity, and ≥ 60% of all measure weight available |
| Medium | At most one imputed dimension and ≥ 6 months of activity |
| Low | Otherwise (still published if §5 point 4 is met) |

The output also lists the **products used** (e.g. "Duka only", "Duka + Pesa + Bandu").

### 7.2 Keeping products neutral

- Dimension weights are fixed (§2); products only add measures inside dimensions.
- The one intended advantage for using more products is ecosystem depth (§3.6), capped at about 2 points.
- Every behavioural data point has a weight (§3), so no data is silently ignored, and no product's data counts for more than its measures' weights.
- The same quantity measured by two products is a single measure with alternative sources, never two measures. Examples: revenue from POS orders and from POS-generated invoices; payroll from Bandu and from Duka wages. Where both exist, the richer source is used: Pesa over the Duka proxy for DSO, Bandu over Duka wages.
- No measure rewards product usage, data volume or coverage.
- **Neutrality check (ongoing calibration):** for every business with more than one product, also compute its score using only one product's measures. Across the portfolio, the average gap between the full score and the single-product score should equal the designed ecosystem-depth advantage (at most about 2 points), and no more. A larger or negative gap means a proxy measure's thresholds need recalibrating.

---

## 8. Output per business

- **Headline:** score (0–100), band, confidence, products used, trend (Δ vs 3 months ago).
- **Dimensions:** each dimension's score, whether it was imputed, and its measures (raw value, score, source product).
- **Shops:** each shop's score, band, trend, share of revenue and status (established / new / dormant), ranked. Plus the share of revenue not linked to any shop.
- **Aging tables:** receivables and rent, where applicable.
- **Red flags:** active flags and the cap applied.
- **Drivers:** the three strongest positive and three strongest negative measures, as plain-language reasons.
- **History:** monthly snapshots.

---

## 9. What real data shows (a BASEPOINT demo business, 2026-09-26)

A read-only look at a live BASEPOINT account shows what the pipeline must handle:

| Observation | Consequence |
|---|---|
| 242 orders from Dec 2024 to Sep 2026, but months with no orders (e.g. Aug–Sep 2025, Nov 2025, Aug 2026) | Trading continuity and volatility must handle zero months; low-volume businesses need the minimum-activity rule |
| About half the records predate the current schema: 119 of 225 invoices and 125 of 242 orders have no `status`, `direction` or `payment_status` | The source adapter needs rules for legacy records. For example, a legacy POS invoice with payments is treated as paid |
| 25 orders have no `shop_id` | Counted at business level only (§5.1) |
| Invoice values actually used: `status` = `Paid`, `Pending`, `Partially_Paid`, `Voided`, `Draft`; `direction` = `customer`; `source` = `pos`, `accounting` | Filters in §3.1 are based on these |
| 92 of the invoices are POS-generated (`source = pos`), duplicates of orders; only 14 are accounting invoices with due dates | Confirms the de-duplication rule; credit sales are a small share for POS-heavy businesses |
| Only 27 of 242 orders are linked to a customer; customers mostly lack `type`, `lifecycle_stage` and `credit_limit` | Most POS businesses will be "walk-in" for the customer dimension (§3.4) |
| The business record has a `modules` block (`pos`, `accounting`, `inventory`, `crm`, `payroll`, `dala`, `etims`) with `enabled_at` dates | Use it to detect which products a business uses |
| Pesa's AR aging report uses exactly the buckets in §4 | Aging can come straight from the report |
| 10 sales receipts, only 1 linked to an invoice | Unlinked receipts are extra cash sales and count as revenue (§3.1) |
| 14 suppliers, 13 purchase orders (`partially_delivered`, `fully_delivered`, `approved`, `cancelled`), 3 bills with due and paid dates; 20 of 34 inventory items linked to a supplier | Supplier measures (§3.2, §3.5, §3.6) are usable where businesses record suppliers |

---

## 10. Limitations

| # | Limitation | Mitigation |
|---|---|---|
| L1 | Legacy records lack status fields | Source-adapter rules (§9) |
| L2 | Cost prices are optional and reflect today's price, not the price at the time of sale | Gross margin from Duka only when ≥ 80% of items sold have a cost price; Pesa P&L preferred |
| L3 | Customers are recorded per shop | De-duplicate by phone or KRA PIN (§5.1) |
| L4 | Seasonality penalizes T3M vs P3M growth | Year-on-year growth offsets this once 15 months exist |
| L5 | Multi-currency | Convert to the business's base currency (`accounting_settings.base_currency`) at the document date |
| L6 | Shop types differ (`pos_mode`: retail, restaurant, hotel, …) | Sector benchmarks per shop type, eventually |
| L7 | Supplier data is optional and often partial (in the demo account, 20 of 34 inventory items are linked to a supplier) | Supplier measures apply only when data exists; traceability is measured, not assumed |
| L8 | The API authenticates as a user of one business (company code + PIN or username) | Scoring many businesses needs a service integration agreed with BASEPOINT (§11) |

---

## 11. Data access (API)

The API authenticates with a `companycode` header plus a bearer token from `POST /users/login`. The spec's path prefixes aren't always accurate; the actual routes are below:

| Need | Route |
|---|---|
| Products enabled | `POST /tenants/verify` → `modules`, `*_settings.enabled_at` |
| Shops | `GET /shops` |
| Orders, with items and payments embedded | `GET /orders` |
| Invoices | `GET /accounting/invoices?page=&limit=` (not `/invoices` as the spec says) |
| Sales receipts | `GET /accounting/sales-receipts` |
| Suppliers | `GET /suppliers` |
| Purchase orders | `GET /purchase-orders` |
| Bills | `GET /accounting/bills` |
| Payables aging | `GET /accounting/reports/ap-aging?shop_id=&as_of_date=` |
| Inventory | `GET /product-inventory` |
| Receivables aging | `GET /accounting/reports/ar-aging?shop_id=&as_of_date=` |
| Ledger | `GET /accounting/reports/profit-loss`, `balance-sheet`, `cash-flow` (per `shop_id`) |
| Sales receipts | `GET /accounting/sales-receipts` |
| Customers | `GET /api/customers?shop_id=`, `GET /api/customers/other-branches` |
| Inventory and low stock | `Duka · Product Inventory` routes; `GET /orders/admin-dashboard/summary` → `lowStockItems` |
| Payroll | `Bandu · Payroll`, `GET /bandu/reports/payroll-summary` |
| Property | `GET /dala/reports/property-occupancy`, `rent-collection`; `Dala · Rent Invoices` |

---

## 12. Pipeline (design only)

| Component | Role |
|---|---|
| Source adapter | Reads each business's data via the API; applies legacy-record rules; de-duplicates POS invoices |
| Product detection | Reads enabled modules and which ones actually hold data |
| Snapshot builder | Reconstructs revenue, receivables and balances at each month-end |
| Measure library | One function per measure, per source product, each returning "not available" when its data is missing |
| Aggregator | Measures → dimensions → score; imputation; confidence; red-flag caps; per shop and consolidated |
| Neutrality check | The single-product comparison in §7.2, run across the portfolio |

Build order: source adapter and product detection → Duka measures (every business has at least one sales product, and Duka is the most common) → aggregator and output → Pesa measures → Dala, Bandu and Mteja measures → neutrality check → sector benchmarks.

---

## 13. Decisions needed

1. Dimension weights (§2), measure weights and Good/Poor thresholds (§3), including whether Formality and compliance (§3.6) belongs in the health score.
2. Scale thresholds for daily transaction volume and value (§3.1), until sector benchmarks exist.
3. The size of the ecosystem-depth advantage (§3.6): its weight and its 1-to-4+ product scale.
4. Supplier tracking tiers and the tracking factor range (0.75×–1.25×) (§3.9).
5. Red-flag conditions and caps (§6.1).
6. The publication rule and imputation approach (§5).
7. Shop ramp-up length (3 months proposed).
8. How the scoring service accesses many businesses' data (L8).

---

## 14. Implementation

The application is in the `health_score` package. The scoring rules (dimensions, measures, weights and thresholds) are in `health_score/scoring/registry.py`. For the structure of the application, refer to [Architecture](../architecture.md). For the API, refer to [API reference](../api.md).

| Task | Command |
|---|---|
| Start the API | `uvicorn health_score.api.app:app --port 8100` |
| Score a business | `POST /v1/scores` with `company_code`, `pin`, and optional `username` and `as_of_date` |
| Start the web page | `streamlit run streamlit_app.py` |
| Run the tests | `pytest` |

The API and the web page use the same service. The service logs in to BASEPOINT as the business, collects every dataset its products hold (approximately 40 endpoints, in parallel), calculates the score and returns the full result. The application does not store data. It uses the credentials for one request only and does not write them to the log. It reads only whitelisted business fields from `/tenants/verify`.

Decisions made while implementing:

- **Books-coverage guard.** Ledger-based measures (P&L gross margin, net margin, cash runway) are used only when P&L revenue covers ≥ 80% of the sales seen in transactions. In the demo business the books cover 30% of sales. Without the guard, it showed a 99.7% gross margin (almost no cost of sales posted) and 555 months of cash runway (bank outflows barely recorded).
- **Payables come from the bills themselves**, not the AP aging report. In the demo business the AP aging report showed 0 outstanding, while two bills were 120+ days overdue.
- **Not yet measurable from the API:** shift regularity (`/shifts` returns the weekly rota, not shifts actually opened) and asset trend (no asset data). They stay in the register and apply once data exists.
- **Imputed dimensions** use 50 until enough businesses have been scored to compute peer medians.
- **Sales targets** are measured against revenue computed from transactions for the target period, because BASEPOINT's `actual_value` was 0 even where sales existed.
- **Orders are fetched month by month** (16 months, in parallel). The full order list times out (HTTP 502) for large businesses; one BASEPOINT business with ~1,000 orders a month returned "insufficient data" until this change.
- **A failed sales endpoint is reported, never scored as missing data.** If BASEPOINT doesn't return sales, the result is "Data unavailable" with the failing endpoint listed, not "Insufficient data".
- **Purchase-pattern measures need at least 3 purchase documents** (purchase orders or bills) in 12 months: supplier concentration, fill rate, procurement regularity, sell-through, stock cover and purchase alignment. One purchase order automatically makes "top supplier = 100% of purchases", which isn't a signal. Payables measures still apply to any bill, since an overdue bill is a real debt.
- **Receipting is measured from the first order with a receipt number.** Receipt numbers only appear on BASEPOINT orders from mid-2026, so earlier orders can't have them.
