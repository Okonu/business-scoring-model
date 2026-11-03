# Business Health Score

- **Status:** Implemented in engine version 0.3.0.
- **Source:** the "Business Health Score" methodology document (October 2026): [PDF](Business%20Health%20Score%20Methodology.pdf).
- **Data source:** BASEPOINT / FSS (schema: [`ERD.md`](ERD.md)).
- **Code:** `health_score/scoring/registry.py` holds every number in this document.

## 1 Introduction

### 1.1 What the score measures

The health score answers one question: how healthy is this business overall? It is a number from 0 to 100. A higher number means a healthier business. It is built only from what the business records in BASEPOINT: its sales, payments, invoices, stock, staff and suppliers. Nobody fills in a form.

The score looks at six things, which we call dimensions:

1. **Sales:** does the business sell steadily, and are sales growing or shrinking?
2. **Cash:** does the money it earns actually come in, on time, and does it pay its own bills on time?
3. **Profit:** is there money left after paying for goods, staff and other costs?
4. **Customers:** does income come from many customers who come back, or from a few?
5. **Stability:** how long has it traded, and are staff, stock and shops steady?
6. **Formality:** does it keep books, issue receipts, pay taxes and take digital payments?

Each dimension is measured by several measures. A measure is one number from the records, such as the share of sales that was actually paid. Each measure is scored from 0 to 100. Measures are averaged into a dimension score, and the six dimension scores are averaged into the overall score.

Each score is reported with three companions:

- a **band**, from Strong to Distressed, so the number has a plain meaning;
- a **confidence** level, High, Medium or Low, which says how much data the score rests on;
- the list of **products used**, for example "Duka only" or "Duka + Pesa + Bandu".

**Table 1: The six dimensions**

| Dimension | What it looks at (example measures) | Weight |
|---|---|---|
| 1. Sales performance | Sales per day, growth, how steady sales are month to month | 20% |
| 2. Cash, collections and payables | Share of sales actually paid, overdue invoices, cash in the bank, paying suppliers on time | 25% |
| 3. Profitability and cost control | Gross and net margin, staff cost as a share of sales | 15% |
| 4. Customer and revenue base | Dependence on the biggest customer, repeat customers | 12% |
| 5. Operational stability | Age of the business, staff turnover, stock-outs, shop performance | 18% |
| 6. Formality and compliance | eTIMS and VAT, receipts, bookkeeping, statutory payroll, digital payments | 10% |
| **Total** | | **100%** |

### 1.2 How each number is justified

No single study gives the right weight for a small Kenyan business's cash runway. So we use a ladder of evidence and say, for every number, which rung it stands on.

**Table 2: The evidence ladder**

| Tag | Basis | What it means and examples |
|---|---|---|
| S | Standard or regulation | A rule set by a regulator or standard setter. Examples: 90 days past due as default (Basel, IFRS 9, CBK); eTIMS invoicing (Finance Act 2023); the 10% major-customer rule (ASC 280). |
| E | Empirical evidence | A published study or official statistic. Examples: median cash buffer of 27 days (JPMorgan Chase Institute, 2016); why Kenyan small firms close (KNBS, 2016); business survival rates (BLS, 2024). |
| B | Industry benchmark | A rule of thumb widely used in a sector. Examples: restaurant labour at 25–35% of sales; collection effectiveness of 80% or more. |
| C | Convention | A value we set because no external source exists. It is a placeholder. It should be checked against data as more businesses are scored. |

## 2 How the score is built

### 2.1 Five steps from data to score

1. **Score each measure from 0 to 100.** At or better than the Good threshold scores 100. At or worse than Poor scores 0. In between, the score rises in a straight line. For "lower is better" measures, such as days sales outstanding, the line runs the other way.
2. **Average measures into a dimension score.** Use the measure weights. If some measures have no data, the weights of the ones that do are scaled back up to 100%.
3. **Apply the credibility rule.** If the measures with data carry less than half of a dimension's weight, pull the dimension score toward the peer median (Section 2.2).
4. **Average the six dimensions** at their fixed weights (Table 4).
5. **Apply red-flag caps,** then assign the band and confidence (Section 5).

### 2.2 Missing data

**Within a dimension.** A measure with no data is skipped. The other measures' weights are scaled up. The dimension's own weight never changes.

**Credibility rule.** Scaling up has a weak point. A dimension can end up resting on one measure. For example, a Duka-only business may have no ledger, so profitability can rest on revenue per staff member alone, a measure that carries under 10% of the dimension's weight. The dimension score is therefore blended with the peer median:

```
dimension score = c × measured score + (1 − c) × peer median
c = min(1, weight of measures with data ÷ 50%)
```

This is the logic of credibility weighting in insurance pricing (Bühlmann, 1967). The less evidence there is, the closer the estimate stays to the group average. The 50% point is a convention (C). A dimension with half its weight measured counts in full.

**A whole dimension missing.** It is filled with the peer median for that dimension and flagged as imputed. Peers are businesses of the same business type, or all businesses until there are enough. Until enough businesses are scored, the engine uses 50. Imputation lowers confidence.

**Minimum to publish.** At least 3 months of activity in a sales product (Duka, Pesa or Dala), and at most one imputed dimension. Otherwise the result is "Insufficient data". If a sales endpoint fails, the result is "Data unavailable", never "Insufficient data".

### 2.3 Time windows

The reference date is normally today. The score is also computed at each month-end, so a trend can be shown.

**Table 3: Time windows and receivable aging**

| Term | Meaning |
|---|---|
| T3M, P3M | Trailing 3 months; the 3 months before that. Used for short-term trends. |
| T12M | Trailing 12 months. Used for levels, concentration and volatility. |
| Aging buckets | Not yet due; 1–30; 31–60; 61–90; 91–120; 121+ days past due. Same buckets as Pesa's receivables aging report. |
| Open invoice at date d | Issued on or before d and not fully paid by d. Amount open = total minus payments dated on or before d. |

## 3 Dimension weights

Dimension weights are fixed. They do not change with the products a business uses.

**Table 4: Dimension weights and justification**

| Dimension | Weight (%) | Basis | Why |
|---|---|---|---|
| Sales performance | 20 | E | Revenue level and trend are core inputs in cash-flow underwriting (FinRegLab, 2019). It sits below cash because several sales measures are noisy over 3 months and overlap with cash. |
| Cash, collections and payables | 25 | E | Largest single risk. 30% of closed Kenyan small firms cite a shortage of operating funds (KNBS, 2016). Half of small firms hold under 27 days of cash (JPMorgan Chase Institute, 2016). Liquidity is a leading predictor of small-firm default (Altman and Sabato, 2007). |
| Profitability and cost control | 15 | E | Profitability is among the strongest predictors of small-firm failure (Altman, 1968; Altman and Sabato, 2007). The credibility rule (Section 2.2) guards against thin ledger data. |
| Customer and revenue base | 12 | C | Concentration and retention matter, but most point-of-sale businesses record few named customers. The dimension often rests on few measures. |
| Operational stability | 18 | E | Business age is one of the strongest survival predictors (BLS, 2024; KNBS, 2016). Staff and stock stability carry the rest. |
| Formality and compliance | 10 | E | Formal firms are more productive and better at accessing credit (La Porta and Shleifer, 2014). The weight inside the dimension sits mainly on legal duties: tax, receipts, books and statutory payroll. |
| **Total** | **100** | | |

## 4 Measures, thresholds and weights

Every behavioural data point in BASEPOINT feeds one measure. Each measure sits in one dimension and has a weight inside it. A business gets whichever measures its products allow. Exact definitions and source products are in Appendix A.

Reading the tables: Good scores 100 and Poor scores 0. Basis: S standard or regulation, E empirical evidence, B industry benchmark, C convention. ♦ marks a supplier measure. It applies only when the business records suppliers and purchases (Section 4.7).

### 4.1 Sales performance (20%)

Revenue is the union of completed point-of-sale orders, accounting invoices not linked to an order, sales receipts not linked to an invoice, and rent invoices and property sale payments. Invoices created automatically from orders are the same sales and are not counted twice.

**Table 5: Sales performance**

| Measure | Good | Poor | Weight (%) | Basis | Why |
|---|---|---|---|---|---|
| Daily transaction volume | ≥ 50 | ≤ 2 | 8 | C | It measures scale, not health, and overlaps with daily value. Moves to sector percentiles at 30+ firms per type. |
| Daily transaction value (KES) | ≥ 50k | ≤ 1k | 10 | C | Scale measure. Interim values; sector percentiles replace them. |
| Revenue growth, T3M vs P3M | ≥ +5% | ≤ −25% | 10 | S | +5% a quarter compounds to about 22% a year. A 25% fall is the "substantial decline" test used for small-firm relief (SBA, 2021). Quarterly figures are noisy and seasonal, so the weight is moderate. |
| Year-on-year growth (15+ months) | ≥ +10% | ≤ −25% | 12 | S | Removes seasonality, so it gets more weight than the quarterly comparison. Same decline test. |
| Revenue volatility (CV, T12M) | ≤ 0.15 | ≥ 0.60 | 12 | C | No external standard. Use seasonally adjusted series once 24 months exist. |
| Trading continuity (months with sales) | 12 | ≤ 6 | 8 | C | Continuous trading is the most basic sign of survival. |
| Trading days share, T3M | ≥ 85% | ≤ 30% | 6 | C | 85% equals trading 6 days a week; 30% about 2 days a week. |
| Transaction count trend | ≥ +5% | ≤ −25% | 6 | S | Aligned with the revenue decline test. |
| Average transaction value trend | ≥ 0% | ≤ −25% | 4 | C | A falling average sale suggests customers are spending less per visit. |
| Revenue leakage (discounts, voids) | ≤ 3% | ≥ 20% | 7 | C | Discounts and voids cut the revenue a business keeps. Good allows 3% because some discounting is deliberate pricing. |
| Refunds and credit notes | ≤ 1% | ≥ 10% | 4 | C | Frequent refunds reverse earned revenue and point to quality or service problems. |
| Recurring revenue share | ≥ 30% | 0% | 5 | C | Contracted repeat income makes revenue more predictable. Only where subscriptions, packages or leases are offered. |
| Forward bookings ratio | ≥ 1.0× | ≤ 0.5× | 3 | C | 1.0× means bookings hold steady. |
| Sales target attainment | ≥ 100% | ≤ 60% | 3 | C | 100% is the target by definition. |
| Lead conversion rate, T6M | ≥ 25% | ≤ 5% | 2 | C | Varies widely by sector. Calibrate. |
| **Total** | | | **100** | | |

CV = coefficient of variation of monthly revenue (standard deviation divided by mean). The growth decline thresholds mirror the US Paycheck Protection Program second-draw test of a 25% fall in gross receipts. The red-flag cap (Table 13) uses the stricter 50% fall test.

### 4.2 Cash, collections and payables (25%)

**Cash businesses:** if credit sales are under 5% of revenue, the receivables measures do not apply. **Businesses without supplier bills:** the payables measures do not apply. Neither case is penalized.

**Table 6: Cash, collections and payables**

| Measure | Good | Poor | Weight (%) | Basis | Why |
|---|---|---|---|---|---|
| Cash realization (cash received ÷ revenue) | ≥ 95% | ≤ 60% | 19 | E | Cash received is the core of cash-flow underwriting (FinRegLab, 2019), so it carries the largest weight. |
| Severe overdue receivables: share of open receivables 90+ days past due | ≤ 5% | ≥ 40% | 11 | S | Overdue means 90+ days past due, the default definition in Basel, IFRS 9 and CBK guidelines. The share thresholds are a convention (C). |
| Days sales outstanding (DSO) | ≤ 45 | ≥ 90 | 9 | B | 30-day terms plus 15 days' grace, the edge of "pays on time" in trade credit scores (Dun & Bradstreet). 90 days is default. It overlaps with the two aging measures, so the weight is moderate. |
| Weighted average days past due | ≤ 5 | ≥ 30 | 6 | S | 30 days past due signals a significant rise in credit risk under IFRS 9. |
| Collection effectiveness index (CEI) | ≥ 80% | ≤ 50% | 6 | B | 80% or more is the usual benchmark for good collection (Versapay). |
| Aging drift (3-month change) | ≤ 0 pt | ≥ +20 pt | 4 | C | A rising overdue share is an early warning before debts reach default. |
| Cash runway (months) | ≥ 2 | ≤ 0.5 | 12 | E | The median small firm holds 27 days of cash; a quarter hold under 13 (JPMorgan Chase Institute, 2016). 2 months is about twice the median; 0.5 is the bottom quartile. |
| Customers over credit limit | ≤ 5% | ≥ 30% | 3 | C | Customers above their limit show that credit control is slipping. |
| Rent collection rate, T3M | ≥ 95% | ≤ 60% | 7 | B | Matches the cash realization standard. |
| Payment-plan collection | ≥ 95% | ≤ 60% | 3 | B | Matches the cash realization standard. |
| Gift-card liability ÷ monthly revenue | ≤ 5% | ≥ 50% | 2 | C | Unredeemed gift cards are a debt to customers, owed in future goods or service time. |
| Severe overdue payables: share of open bills 90+ days past due ♦ | ≤ 5% | ≥ 40% | 7 | S | Same 90-day default line as receivables, for consistency. The share thresholds are a convention (C). |
| Bills paid on time, T6M ♦ | ≥ 90% | ≤ 40% | 7 | B | "Pays within terms" is the low-risk band in trade credit scores (Dun & Bradstreet). |
| DPO ÷ agreed supplier terms ♦ | ≤ 1.1× | ≥ 2.5× | 4 | B | Days beyond terms is the standard trade-credit yardstick (Dun & Bradstreet). |
| **Total** | | | **100** | | |

Default definitions: Basel framework CRE36.69; IFRS 9 paragraphs 5.5.11 (30 days) and B5.5.37 (90 days); CBK Prudential Guideline on risk classification of assets (watch 31–90 days, substandard 91–180 days). DPO = days payables outstanding. Customer and supplier payment terms come from `Customer.payment_terms` and `Supplier.payment_terms`.

### 4.3 Profitability and cost control (15%)

Ledger measures (gross margin from the profit and loss, net margin, cash runway) are used only when ledger revenue covers at least 80% of the sales seen in transactions. Without this guard, incomplete books produce absurd values.

**Table 7: Profitability and cost control**

| Measure | Good | Poor | Weight (%) | Basis | Why |
|---|---|---|---|---|---|
| Gross margin | By sector | By sector | 24 | B | One threshold cannot fit all. Restaurants run food cost at 25–35% of sales, so their margins sit far above a retailer's (Complete Controller, 2025). |
| Net margin | ≥ 10% | ≤ −10% | 23 | B | Typical restaurants earn 3–5%; well-run ones 10% or more. Break-even scores 50. |
| Staff cost ÷ revenue | ≤ 30% | ≥ 50% | 17 | B | Restaurant labour runs 25–35% of sales; salon and spa payroll 30–35%. Above 50% leaves little for goods and rent. |
| Cost discipline (expense vs revenue growth) | ≤ 0 pt | ≥ +25 pt | 9 | C | Costs that grow faster than revenue squeeze margins over time. |
| Revenue per staff member | 75th pct | 10th pct | 6 | C | A productivity measure, not profit. Should not score until sector data exist. |
| Maintenance cost ÷ rent income | ≤ 5% | ≥ 25% | 9 | C | High upkeep relative to rent erodes a property's net income. |
| Commission cost ÷ property sales | ≤ 3% | ≥ 10% | 4 | C | Commissions above usual agent rates cut the margin on each sale. Confirm against local agent rates. |
| Purchase-to-sales alignment ♦ | 0.8–1.2× | < 0.3 or > 2.5× | 8 | C | Buying roughly what is sold avoids both overstocking and running stock down. |
| **Total** | | | **100** | | |

Interim gross margin thresholds until sector percentiles exist (Good / Poor): food service ≥ 60% / ≤ 40%; retail and wholesale ≥ 25% / ≤ 5%; personal and professional services ≥ 50% / ≤ 20%; other ≥ 35% / ≤ 5%. Business type comes from the tenant record, not the shop's point-of-sale mode.

### 4.4 Customer and revenue base (12%)

**Walk-in businesses:** if named customers account for under 20% of revenue, the customer-level measures do not apply. The dimension then rests on transaction breadth, product concentration and transaction trends.

**Table 8: Customer and revenue base**

| Measure | Good | Poor | Weight (%) | Basis | Why |
|---|---|---|---|---|---|
| Top customer's share of revenue | ≤ 10% | ≥ 50% | 16 | S | 10% is the "major customer" line in financial reporting (FASB, ASC 280). Half of revenue from one customer is a severe dependence. |
| Customer retention, T3M | ≥ 70% | ≤ 20% | 18 | E | Small gains in retention raise profits sharply (Reichheld and Sasser, 1990). Thresholds vary by sector; calibrate. |
| Active-customer trend | ≥ +5% | ≤ −25% | 10 | S | Aligned with the revenue decline test. |
| Revenue concentration (HHI) | ≤ 0.10 | ≥ 0.25 | 5 | S | Competition authorities treat 0.18 as "highly concentrated" (0.25 before 2023) (DOJ and FTC, 2023). It largely repeats top-customer share, so its weight is small. |
| Transaction breadth (largest sale's share) | ≤ 5% | ≥ 40% | 10 | C | Revenue that rests on one large sale is less dependable than many smaller ones. |
| Product concentration (top product) | ≤ 20% | ≥ 70% | 8 | C | Relying on one product leaves the business exposed if demand or supply for it falls. |
| New customers per month, trend | ≥ 0% | ≤ −50% | 8 | C | A steady inflow of new customers replaces those who leave. |
| Customer visit trend | ≥ 0% | ≤ −30% | 6 | C | Falling visits usually come before falling sales. |
| Customer satisfaction (1–5) | ≥ 4.3 | ≤ 3.0 | 7 | C | Satisfied customers are more likely to return. 3.0 is the neutral mid-point of the scale. |
| Loyalty engagement share | ≥ 20% | 0% | 5 | C | Customers in loyalty, gift-card or subscription schemes are more likely to come back. |
| At-risk revenue share | ≤ 5% | ≥ 30% | 7 | C | Revenue from customers who are already drifting away is likely to be lost. |
| **Total** | | | **100** | | |

HHI = Herfindahl–Hirschman index, the sum of squared revenue shares across customers (0 to 1). We use 0.25 as Poor so a score of zero means clearly concentrated. The red flag for single-customer dependence is set at 70% (Table 13).

### 4.5 Operational stability (18%)

**Table 9: Operational stability**

| Measure | Good | Poor | Weight (%) | Basis | Why |
|---|---|---|---|---|---|
| Business tenure (months) | ≥ 48 | ≤ 12 | 10 | E | Kenyan small firms close at 3.8 years on average; 61% of closures are firms under 2 years old (KNBS, 2016). One US firm in five fails in year 1 (BLS, 2024). |
| Staff count trend (6 months) | ≥ 0% | ≤ −40% | 6 | C | A shrinking team often signals that the business is cutting back. |
| Staff turnover, T12M | ≤ 30% | ≥ 80% | 6 | E | Hospitality loses about 5% of staff a month, over 60% a year (BLS, 2025). Sector percentiles later. |
| Payroll regularity, T6M | 100% | ≤ 50% | 8 | S | Payroll taxes are due monthly, by the 9th of the next month. |
| Shift regularity | ≥ 90% | ≤ 40% | 5 | C | Opening a shift on each trading day shows the business runs to a routine. Not yet measurable from the API. |
| Key-person dependence | ≤ 40% | ≥ 90% | 5 | C | A business where one person makes most sales is at risk if that person leaves. |
| Stock-out rate | ≤ 5% | ≥ 20% | 6 | E | Retail stock-outs average about 8% worldwide (Gruen et al., 2002). The average firm should score above half. |
| Inventory turnover (× per year) | By sector | By sector | 6 | B | Perishable stock turns far faster than durable goods. Sector percentiles apply; non-food retail uses 6 (Good) and 1 (Poor). |
| Dead stock (unsold 90 days) | ≤ 10% | ≥ 50% | 3 | C | Stock unsold for 90 days ties up cash and may never sell. |
| Catalogue activity | ≥ 60% | ≤ 15% | 3 | C | A catalogue full of items that never sell points to weak range and stock control. |
| Capacity utilization | 75th pct | 10th pct | 3 | C | Use of tables or rooms differs by type of venue, so it is sector-relative from the start. |
| Occupancy (units) | ≥ 90% | ≤ 50% | 6 | B | 5–10% vacancy is a normal letting margin. |
| Maintenance backlog | ≤ 10% | ≥ 50% | 3 | C | Repair tickets left open for over a month point to weak property management. |
| Shop network (2+ shops) | ≥ 75 | ≤ 40 | 6 | C | It partly repeats sales trends, so its weight is moderate. Sub-measures in Table 10. |
| Unplanned leave | ≤ 2% | ≥ 10% | 2 | C | High unplanned absence disrupts service and can signal low morale. |
| Asset base trend | ≥ 0% | ≤ −30% | 2 | C | A shrinking asset base can mean assets are sold to cover costs. Not yet measurable from the API. |
| Supplier concentration ♦ | ≤ 30% | ≥ 80% | 5 | C | Depending on one supplier leaves the business exposed if that supplier fails. |
| Delivery fill rate ♦ | ≥ 95% | ≤ 60% | 4 | B | 95% is a common supply-chain service target. |
| Procurement regularity ♦ | 100% | ≤ 33% | 2 | C | Buying every month shows steady restocking. |
| Sell-through of tracked stock ♦ | ≥ 80% | ≤ 30% | 5 | B | Common retail sell-through target. |
| Stock cover of tracked stock (days) ♦ | 14–60 | < 3 or > 180 | 4 | C | Too little stock risks stock-outs, and too much ties up cash. |
| **Total** | | | **100** | | |

Tenure is counted from the first transaction or tenant creation date. It understates age for firms that joined BASEPOINT late. Use a self-reported founding date when one is captured. Kenyan statutory payroll (PAYE, NSSF, SHIF, Housing Levy) is remitted monthly.

**Shop network sub-measures.** For businesses with two or more shops, one measure in this dimension. It is the average of four sub-scores.

**Table 10: Shop network sub-measures**

| Sub-measure | Good | Poor | Basis | Why |
|---|---|---|---|---|
| Revenue share from shops scoring under 50 | ≤ 10% | ≥ 50% | C | Weak shops that carry much of the revenue drag on the whole business. |
| Top shop's share of T12M revenue | ≤ 50% | ≥ 90% | C | A flagship plus smaller branches is a normal structure. |
| Established shops declining (≤ −10%) | ≤ 20% | ≥ 60% | C | Several established shops shrinking at once points to a business-wide problem. |
| Dormant established shops (no sales 30 days) | 0% | ≥ 40% | C | A shop with no sales for 30 days is likely closed or failing. |

A shop's first 3 months are its ramp-up. Ramp-up shops count toward revenue and balances, but not toward growth, trend, retention or network comparisons.

### 4.6 Formality and compliance (10%)

**Table 11: Formality and compliance**

| Measure | Good | Poor | Weight (%) | Basis | Why |
|---|---|---|---|---|---|
| Digital payment share | ≥ 70% | ≤ 10% | 20 | C | Digital payments leave a verifiable trail. Thresholds are ours; check against FinAccess data. |
| Tax registration and eTIMS | eTIMS, ≥ 90% | neither | 20 | S | Since January 2024, expenses without an eTIMS invoice are not tax-deductible (Finance Act, 2023). VAT registration is compulsory above KES 5 million turnover. |
| Receipting (sales with a receipt) | ≥ 95% | ≤ 50% | 10 | S | The law expects a tax invoice for every sale by a registered business. |
| Bookkeeping regularity, T6M | 100% | ≤ 33% | 14 | S | Records must be kept for 5 years (Tax Procedures Act, 2015). VAT and turnover tax returns are monthly. |
| Bank reconciliation recency (days) | ≤ 35 | ≥ 90 | 9 | B | Monthly reconciliation is standard month-end practice. 90 days means a full quarter missed. |
| Statutory payroll compliance | 100% | ≤ 50% | 12 | S | PAYE, NSSF, SHIF and Housing Levy are legal duties, remitted monthly. |
| Platform standing (subscription paid) | Active | Lapsed | 5 | C | Reflects the relationship with BASEPOINT more than the firm's health, so its weight is small. |
| Supply-chain traceability index ♦ | ≥ 80 | ≤ 10 | 10 | C | Tracing goods from supplier to sale shows the stock records can be trusted. Applies only above a minimum purchase base (Section 4.7). |
| **Total** | | | **100** | | |

The tax registration measure scores 100 for eTIMS active with ≥ 90% of invoices verified, and 0 when neither VAT nor eTIMS is set up. Small firms on turnover tax (KES 1–25 million) may face a simpler record-keeping route under KRA guidance; score them on records kept, not on eTIMS alone.

### 4.7 Supplier-tracked data

Each supplier relationship is placed in a tracking tier. The tier says how much of the chain from purchase to sale the business records.

**Table 12: Supplier tracking tiers**

| Tier | What is recorded for the supplier | Index points |
|---|---|---|
| 0 | Nothing, or supplier name only | 0 |
| 1 | Purchases: purchase orders or bills | 40 |
| 2 | Purchases and inventory linked to the supplier | 75 |
| 3 | Full chain: order, delivery, bill, payment, and sales of the supplier's items | 100 |

- **Traceability index** = inventory value (or purchase value) share of each supplier × its tier points, summed.
- **Tracking factor** on each ♦ measure's weight = 0.75 + 0.5 × share of purchases from tier 2–3 suppliers (0.75× to 1.25×).
- **Minimum to apply:** 3 purchase documents and T12M purchases ≥ 5% of T12M revenue.

**Why tracked data weighs more.** Tracked data are computed from verified transactions (actual costs, received quantities, units sold), not estimates. Giving more weight to more precise evidence is the logic of inverse-variance weighting. The 0.75–1.25 range is a convention (C).

**Why a minimum base.** Service businesses (spas, salons, consultancies) buy few goods. A handful of small purchases says nothing about their supply chain, yet can produce a traceability score of 0. The 5% floor is a convention (C). Payables measures still apply to any bill, since an overdue bill is a real debt.

**Data points not weighted.** Configuration and presentation settings carry no weight: printers and print settings, units of measure, modifiers and add-ons, colours and branding, tip settings, hotel settings, gallery, FAQs, roles and permissions, notifications, document templates and signing, and Biashara AI. WhatsApp responsiveness is a candidate customer measure once usage is known.

## 5 Red flags, bands and benchmarks

### 5.1 Red flags

A red flag caps the score. It does not subtract from it. A serious problem cannot be averaged away by good results elsewhere. This limits the "compensation" that plain weighted averages allow (Nardo et al., 2008). A flag is checked only when its data exist, so a missing product can never trigger one.

**Table 13: Red flags and caps**

| Red flag | Condition | Cap | Basis | Why |
|---|---|---|---|---|
| Revenue collapse | T3M ≤ 50% of P3M and, with 15+ months, also ≤ 50% year on year | 40 | S | A fall below half is the "significant decline" test in US small-firm relief (IRS, 2021). The year-on-year check avoids firing on seasonal dips. |
| Missed payroll | No payroll in 2 months, for a firm that normally runs one | 40 | S | Unpaid staff and payroll taxes are legal breaches. |
| Cash exhaustion | Runway < 0.67 month (20 days) | 45 | E | Half of small firms hold under 27 days of cash (JPMorgan Chase Institute, 2016). A 20-day line sits below that median, so the flag does not fire for most healthy firms. |
| Flagship shop collapse | Shop with ≥ 50% of revenue falls to ≤ 50% | 45 | S | Same 50% decline test. |
| Receivables write-off risk | ≥ 40% of receivables 90+ days past due | 50 | S | 90 days past due is default (BCBS, 2019; IASB, IFRS 9). |
| Single-customer dependence | Top customer ≥ 70% of revenue | 55 | C | Set well above the 10% major-customer line, so it catches only extreme dependence. |
| Severe supplier arrears | ≥ 50% of open bills 90+ days past due | 40 | S | Uses the 90-day default line. |
| Widespread shop decline | ≥ 60% of established shops (min. 2) declining | 55 | C | When most established shops shrink together, the problem is the business, not one location. |

The cap levels are conventions (C). Each places the business in the Weak band (cap 40 or 45) or at the top of Watch (50, 55).

### 5.2 Bands

**Table 14: Score bands**

| Score | Band | Plain meaning |
|---|---|---|
| 80–100 | Strong | At or near Good on most measures. |
| 65–79 | Healthy | Better than halfway on most measures; no serious red flag. |
| 50–64 | Watch | Around halfway between Good and Poor; some weak areas. |
| 35–49 | Weak | Below halfway, or capped by a red flag. |
| 0–34 | Distressed | Poor on most measures. |

Basis C. Bands are equal 15-point steps around 50, the point where measures sit on average halfway between Good and Poor. Credit scorecards set cut-offs from observed failure rates (Siddiqi, 2017). Once 12 months of outcomes exist, we will set each cut-off where the failure rate changes clearly.

### 5.3 Sector benchmarks

Some measures differ too much by sector for one threshold: margins, DSO, staff cost, inventory turnover, stock-outs, staff turnover, transaction volume and value. For these, Good becomes the sector's 75th percentile and Poor its 10th.

**Table 15: Sector benchmark rules**

| Rule | Value | Basis | Why |
|---|---|---|---|
| Minimum firms per business type | 30 | C | With fewer firms the 10th percentile rests on one or two businesses, which is unstable. |
| Good / Poor percentiles | 75th / 10th | C | Good means better than three in four peers. |
| Refresh | Quarterly, fixed between | C | Keeps scores comparable within a quarter. |
| Sector key | Tenant business type, checked against shop mode | C | Shop point-of-sale modes are often left at defaults (e.g. a spa's shops typed "restaurant"), which would compare it with the wrong peers. |

## 6 Explaining a score to a business

This section is for staff who walk a business through its score. It uses an illustrative business. The numbers are made up to show the method.

### 6.1 What to say first

- Your score is a number from 0 to 100. Higher is healthier.
- It comes only from what you record in BASEPOINT. Nobody fills in a form.
- It looks at six areas: sales, cash, profit, customers, stability and formality.
- Each area is scored from 0 to 100. The six are then combined with fixed weights. Cash counts most, at 25%.
- A serious problem, such as missed payroll, caps the score. Good results elsewhere cannot hide it.
- Using more BASEPOINT products gives more evidence, not more points.

### 6.2 Worked example

The illustrative business is a two-shop hardware retailer that uses Duka and Pesa. It sells partly on credit.

**Step 1. One measure becomes a score.** Each measure is placed on a line between its Poor value (score 0) and its Good value (score 100). The score is the share of that distance the business has covered.

- **Cash realization (higher is better).** The business received KES 88 for every KES 100 it sold, so the value is 88%. Poor is 60% and Good is 95%. The distance from Poor to Good is 35 points. The business has covered 28 of them. 28 ÷ 35 = 0.80, so the measure scores 80.
- **Days sales outstanding (lower is better).** Customers take 63 days on average to pay. Poor is 90 days and Good is 45 days. The distance is 45 days. The business is 27 days better than Poor. 27 ÷ 45 = 0.60, so the measure scores 60.

**Step 2. Measures become a dimension score.** Suppose the business has data for five cash measures. Their weights add up to 57. They are scaled up to 100, so each keeps its share. Measures with no data, such as rent collection, do not add or remove points.

**Table 16: Illustrative business: cash, collections and payables**

| Measure | Value | Good | Poor | Score | Weight | Weight used (%) |
|---|---|---|---|---|---|---|
| Cash realization | 88% | ≥ 95% | ≤ 60% | 80 | 19 | 33.3 |
| Severe overdue receivables | 12% | ≤ 5% | ≥ 40% | 80 | 11 | 19.3 |
| Days sales outstanding | 63 days | ≤ 45 | ≥ 90 | 60 | 9 | 15.8 |
| Collection effectiveness index | 62% | ≥ 80% | ≤ 50% | 40 | 6 | 10.5 |
| Cash runway | 0.8 months | ≥ 2 | ≤ 0.5 | 20 | 12 | 21.1 |
| **Cash dimension** | | | | **60.0** | **57** | **100.0** |

Dimension score = (19 × 80 + 11 × 80 + 9 × 60 + 6 × 40 + 12 × 20) ÷ 57 = 3,420 ÷ 57 = 60.0. The five measures carry more than half of the dimension's weight (57%), so the credibility rule does not change the result. The test `test_worked_example_cash_dimension` checks this example against the engine.

## 7 Implementation notes

These notes say how the engine applies rules that the methodology leaves open.

- **Peer medians and sector percentiles.** No peer data exists yet. The engine uses 50 as the peer median. Revenue per staff member and capacity utilization have sector-percentile thresholds only, so they do not get a score yet. The response shows their values in `measures_pending_benchmark`. The other sector-relative measures use the interim values in the tables until 30 businesses of a type have a score.
- **Sector.** The engine reads the sector from the tenant business type (for example `massage_parlour` is personal services). An unknown type uses "other".
- **Tax registration and eTIMS.** Neither VAT nor eTIMS scores 0. Registration scores 50. The score rises in a straight line to 100 at 90% of accounting invoices verified with eTIMS.
- **Inventory turnover.** Until sector percentiles exist, every sector uses 6 (Good) and 1 (Poor).
- **Days past due.** "90+ days past due" means more than 90 days after the due date, the 91–120 and 121+ aging buckets.
- **Confidence.** High: no imputed dimension, 12+ months of history and 60%+ of the measure weight with data. Medium: at most one imputed dimension and 6+ months of history. Otherwise Low.

## Appendix A: Measure definitions and data sources

Products: D = Duka, P = Pesa, B = Bandu, M = Mteja, L = Dala (property). The same quantity from two products is one measure with alternative sources, never two measures. Where both exist, the richer source is used: Pesa over the Duka proxy for DSO, Bandu over Duka wages.

**Table 17: Measure definitions**

| Measure | Definition and data points | Products |
|---|---|---|
| **Sales performance** | | |
| Daily transaction volume | Average transactions per trading day, T3M. A transaction is one completed order, unlinked sales receipt, accounting invoice or rent invoice. | D, P, L |
| Daily transaction value | Average revenue per trading day, T3M. | D, P, L |
| Revenue growth | Revenue T3M vs P3M. | D, P, L |
| Year-on-year growth | Revenue T3M vs the same 3 months a year earlier. Needs 15+ months. | D, P, L |
| Revenue volatility | Coefficient of variation of monthly revenue, T12M. Zero months included. | D, P, L |
| Trading continuity | Months with revenue in T12M. | D, P, L |
| Trading days share | Days with sales ÷ days in T3M. | D, P |
| Transaction count trend | Transaction count T3M vs P3M. | D, P, L |
| Average transaction value trend | Revenue ÷ transactions, T3M vs P3M. | D, P |
| Revenue leakage | (Discounts + voided items) ÷ gross sales. | D, P |
| Refunds and credit notes | Refunds and credit notes ÷ revenue. | P |
| Recurring revenue share | Subscriptions, packages and leases ÷ revenue. | D, L |
| Forward bookings ratio | Bookings scheduled in the next 30 days ÷ the last 30 days. | D |
| Sales target attainment | Actual ÷ target, using revenue computed from transactions. | M |
| Lead conversion rate | Won leads ÷ closed leads, T6M. | M |
| **Cash, collections and payables** | | |
| Cash realization | Cash received (order payments, invoice payments, receipts, rent payments) ÷ revenue, T3M. | D, P, L |
| Severe overdue receivables | Receivables 90+ days past due ÷ total open receivables. From AR and rent aging. | P, L |
| Days sales outstanding | Receivables ÷ credit sales in T3M × 90. Duka proxy: sum of customer balances. | P, L, D |
| Weighted average days past due | Days past due weighted by open amount. | P, L |
| Collection effectiveness index | (Opening receivables + credit sales − closing receivables) ÷ (opening receivables + credit sales − current receivables), T3M. | P, L |
| Aging drift | 3-month change in the severe overdue ratio. | P, L |
| Cash runway | Bank balances ÷ average monthly outflow, from the cash-flow report. Needs the books-coverage guard. | P |
| Customers over credit limit | Customers with balance above credit limit ÷ customers with a limit. | D, P |
| Rent collection rate | Rent paid ÷ rent invoiced, T3M. | L |
| Payment-plan collection | Instalments paid ÷ instalments due. | L |
| Gift-card liability | Unredeemed gift-card balance ÷ monthly revenue. | D |
| Severe overdue payables | Bills 90+ days past due ÷ open bills. From the bills themselves, not the AP aging report. | P |
| Bills paid on time | Bills paid by due date ÷ bills due, T6M. | P |
| DPO ÷ supplier terms | Days payables outstanding ÷ agreed supplier payment terms. | P, D |
| **Profitability and cost control** | | |
| Gross margin | (Revenue − cost of goods sold) ÷ revenue. Cost source in order of preference: actual purchase cost of tracked stock; ledger; sold quantity × supplier price (if ≥ 80% of items sold have a cost); recipes. | P, D |
| Net margin | (Revenue − expenses) ÷ revenue, from the profit and loss. | P |
| Staff cost ÷ revenue | Payroll gross pay or Duka wages ÷ revenue. | B, D |
| Cost discipline | Expense growth minus revenue growth, T3M vs P3M. | P |
| Revenue per staff member | Monthly revenue ÷ staff count or active employees. | D, B |
| Maintenance cost ÷ rent income | Maintenance costs ÷ rent income. | L |
| Commission cost ÷ property sales | Commissions ÷ property sales. | L |
| Purchase-to-sales alignment | Purchases of tracked stock ÷ cost of that stock sold, T3M. | D, P |
| **Customer and revenue base** | | |
| Top customer's share | Largest customer's share of T12M revenue (tenants count as customers). | D, P, L |
| Customer retention | Share of P3M customers who bought again in T3M; lease renewals for property. | D, P, L |
| Active-customer trend | Active customers T3M vs P3M. | D, P, L |
| Revenue concentration (HHI) | Sum of squared customer revenue shares, T12M. | D, P, L |
| Transaction breadth | Largest single sale's share of T12M revenue. | D, P |
| Product concentration | Top product's share of revenue. | D |
| New customers per month | New customers T3M vs P3M. | D, M |
| Customer visit trend | Visits T3M vs P3M. | D, M |
| Customer satisfaction | Average feedback rating (1–5). | D |
| Loyalty engagement | Revenue from loyalty, gift-card and subscription customers ÷ revenue. | D |
| At-risk revenue | Revenue from customers in at-risk or churned stages ÷ revenue. | M |
| **Operational stability** | | |
| Business tenure | Months since the first transaction or tenant creation. | Any |
| Staff count trend | Staff now vs 6 months ago. | D, B |
| Staff turnover | Exits ÷ average headcount, T12M. | B |
| Payroll regularity | Months with completed payroll in T6M ÷ 6. | B, D |
| Shift regularity | Trading days with an opened shift ÷ trading days. | D |
| Key-person dependence | Top staff member's share of sales. | D |
| Stock-out rate | Selling items below minimum quantity ÷ selling items. | D |
| Inventory turnover | Cost of goods sold T12M ÷ average inventory at cost. | D |
| Dead stock | Value of items unsold in 90 days ÷ inventory value. | D |
| Catalogue activity | Active products sold in T3M ÷ active products. | D |
| Capacity utilization | Orders per table per trading day (restaurants); room nights ÷ available rooms (hotels). | D |
| Occupancy | Occupied units ÷ total units. | L |
| Maintenance backlog | Open tickets older than 30 days ÷ open tickets. | L |
| Shop network | Average of the four sub-measures in Table 10. | D |
| Unplanned leave | Unplanned leave days ÷ working days. | B |
| Asset base trend | Net book value now vs 12 months ago. | P |
| Supplier concentration | Top supplier's share of purchases, T12M. | D, P |
| Delivery fill rate | Quantity received ÷ quantity ordered on purchase orders, T6M. | D |
| Procurement regularity | Months with purchases in T6M ÷ 6. | D, P |
| Sell-through | Units sold ÷ units received per supplier, weighted by purchase value, T6M. | D |
| Stock cover | Days of sales the tracked stock on hand covers. | D |
| **Formality and compliance** | | |
| Digital payment share | M-Pesa, card and Pesapal payments ÷ all payments. | D, P |
| Tax registration and eTIMS | VAT enabled; share of invoices verified with KRA eTIMS. | D, P |
| Receipting | Sales with a receipt issued ÷ sales, from the first receipted order. | D, P |
| Bookkeeping regularity | Months with posted journal entries in T6M ÷ 6. | P |
| Bank reconciliation recency | Days since the last completed reconciliation. | P |
| Statutory payroll compliance | Payroll runs with statutory deductions processed; P9 forms generated. | B |
| Platform standing | BASEPOINT subscription active and paid on time. | Any |
| Supply-chain traceability index | Inventory value weighted by supplier tracking tier (Table 12). | D, P |

## References

- Altman, E. I. (1968). Financial ratios, discriminant analysis and the prediction of corporate bankruptcy. *Journal of Finance*, 23(4), 589–609.
- Altman, E. I., & Sabato, G. (2007). Modelling credit risk for SMEs: Evidence from the U.S. market. *Abacus*, 43(3), 332–357.
- Basel Committee on Banking Supervision (2019). *The Basel Framework*, CRE36.69: definition of default (90 days past due).
- U.S. Bureau of Labor Statistics (2024). 34.7 percent of business establishments born in 2013 were still operating in 2023. *The Economics Daily*.
- U.S. Bureau of Labor Statistics (2025). Job Openings and Labor Turnover Survey, January 2025: accommodation and food services separations rate 5.2%.
- Bühlmann, H. (1967). Experience rating and credibility. *ASTIN Bulletin*, 4(3), 199–207.
- Central Bank of Kenya (2013). Prudential Guidelines, CBK/PG/04: Risk classification of assets and provisioning.
- Complete Controller (2025). Restaurant cost benchmarks.
- U.S. Department of Justice and Federal Trade Commission (2023). *Merger Guidelines*.
- Dun & Bradstreet. PAYDEX score: 80–100 pays within terms (low risk); 50–79 up to 15 days late; below 50 30+ days late.
- Financial Accounting Standards Board. ASC 280-10-50-42: disclosure of any single customer providing 10% or more of revenue.
- FinRegLab (2019). *The Use of Cash-Flow Data in Underwriting Credit: Empirical Research Findings*.
- Republic of Kenya (2023). Finance Act, 2023: expenses not supported by an eTIMS invoice disallowed from 1 January 2024.
- Gruen, T. W., Corsten, D. S., & Bharadwaj, S. (2002). *Retail Out-of-Stocks: A Worldwide Examination of Extent, Causes and Consumer Responses*.
- International Accounting Standards Board. IFRS 9 Financial Instruments, paragraphs 5.5.11 and B5.5.37.
- Internal Revenue Service (2021). Notice 2021-20: significant decline in gross receipts.
- Farrell, D., & Wheat, C. (2016). *Cash Is King: Flows, Balances, and Buffer Days*. JPMorgan Chase Institute.
- Kenya National Bureau of Statistics (2016). *Micro, Small and Medium Establishments (MSME) Survey: Basic Report*.
- La Porta, R., & Shleifer, A. (2014). Informality and development. *Journal of Economic Perspectives*, 28(3), 109–126.
- Nardo, M., et al. (2008). *Handbook on Constructing Composite Indicators: Methodology and User Guide*. OECD and European Commission JRC.
- Reichheld, F. F., & Sasser, W. E. (1990). Zero defections: Quality comes to services. *Harvard Business Review*, 68(5), 105–111.
- U.S. Small Business Administration (2021). Second Draw PPP loans: 25% reduction in gross receipts requirement.
- Siddiqi, N. (2017). *Intelligent Credit Scoring* (2nd ed.). Wiley.
- Strategies. The dirty truth about salon and spa service payroll costs.
- Republic of Kenya (2015). Tax Procedures Act, section 23: keeping of records for five years.
- Versapay. Collection effectiveness index (CEI): 80% or above is considered good.
