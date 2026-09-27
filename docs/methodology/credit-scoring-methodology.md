**Credit Scoring Methodology**

**Introduction**

The credit score model will be based on 2 scenarios:

1.  When there is no historical record e.g in the case of a blacklist

2.  When there are historical/past transaction records e.g. Payment behavior can be determined

**What is already in the market?**  
**FICO Score **

The FICO score, named after its developer, Fair Isaac Corporation, is the longest-running credit score issuer. It was invented in 1956 and became the standard for consumer lending in 1989. To obtain a FICO score, you must have had one credit account open for at least six months. 

FICO uses the following factors to calculate your credit score, listed in order of importance: 

1.  Payment history (35% of your credit score): Do you make your payments on time? 

2.  Amounts owed (30% of your credit score): What is the ratio of your debt to your credit limit (i.e., your total credit debt divided by your total available credit)? 

3.  Length of credit history (15% of your credit score): How long have you been managing credit? 

4.  New credit (10% of your credit score): How often do you apply for new credits? 

5.  Credit mix (10% of your credit score): How many different types of credit do you have, and how do you handle each? 

**VantageScore **

VantageScore is a relative newcomer to the scene, debuting in 2006. It was introduced by the three major credit bureaus—Equifax, Experian, and TransUnion—to better account for changes in technology and borrower behavior. 

VantageScore uses the following factors to determine your score: 

1.  Payment history (40% of your score) 

2.  Age and type of credit (21% of your score) 

3.  Percentage of credit limit used (20% of your score) 

4.  Balances (11% of your score) 

5.  Recent credit (5% of your score) 

6.  Available credit (3% of your score) 

**What is Afrimark’s Approach?**

**Scenario 1: A Blacklist**

Given that no historical data is present at this stage, a composite score will be developed with relative weights.

> **Composite Scoring I**
>
> Scaling factor: 100. The score will be based on two main components:

- **Base Verified Score - 20%**

> A client who has been verified gets a base score of 20. This contributes to 20% of the total score

- **The Payment Performance Score - 60%**

> This is based on the normalized probability of default(PD) derived from the weighted DBT ratios. To get the PPS we take the complement of the PD.
>
> i.e: (1-PD)\*100
>
> Where 100 is the scaling factor
>
> This will mean a client with a PD of 0(lowest risk) gets a PPS of 100 and vice versa
>
> Why 60%: *Payment history and the derived PD are typically the strongest credit risk indicators. Clients who have consistently met payment terms, even if they have some exposure, are generally lower risk.*

- **The Exposure Score - 20%**

> This is based on the total amount owed by a client. It gives insights into the scale of their liabilities
>
> Use Normalized Exposure: use min-max scaling = Divide( (max exposure-client exposure), (max exposure-min exposure)) \*100
>
> A client with the lowest exposure gets a score of 100 and vice versa
>
> Why 20%: *While the total amount owed hints at the potential loss severity, it is secondary to the client’s payment behavior i.e.: A large company might owe more but still be creditworthy if it pays reliably. Thus, exposure gets a smaller weight to adjust the final score.*

**The Composite Score**

> Composite score =Base Score+ 0.60\*PPS + 0.20\*ES
>
> A higher score indicates better creditworthiness.

**Risk Classification 👍**

| **Composite Score Range** | **Risk Class** | **Risk Description** |
|---------------------------|----------------|----------------------|
| 80 - 100                  | 1              | Low                  |
| 60 - 79                   | 2              | Low to Medium        |
| 40 - 59                   | 3              | Medium               |
| 20 - 39                   | 4              | Medium to High       |
| 1 - 19                    | 5              | High                 |

**Example:**

<table>
<colgroup>
<col style="width: 11%" />
<col style="width: 13%" />
<col style="width: 9%" />
<col style="width: 14%" />
<col style="width: 12%" />
<col style="width: 16%" />
<col style="width: 20%" />
</colgroup>
<thead>
<tr class="header">
<th>Client</th>
<th>Normalized PD</th>
<th>PPS%</th>
<th>Total Amount Owed</th>
<th>Expose Score (ES)</th>
<th><p>Composite Score</p>
<p>0.75PPS+0.25ES</p></th>
<th>Reasons for score</th>
</tr>
<tr class="odd">
<th>A</th>
<th>0</th>
<th>100</th>
<th>27000</th>
<th>0</th>
<th>75</th>
<th>Lowest PD, Highest Exposure</th>
</tr>
<tr class="header">
<th>B</th>
<th>0.70</th>
<th>30</th>
<th>27000</th>
<th>0</th>
<th>22.5</th>
<th>High PD, Highest Exposure</th>
</tr>
<tr class="odd">
<th>C</th>
<th>0.15</th>
<th>85</th>
<th>12000</th>
<th>88</th>
<th>85.8</th>
<th>Moderate PD, Lower exposure</th>
</tr>
<tr class="header">
<th>D</th>
<th>1.00</th>
<th>0</th>
<th>20000</th>
<th>41</th>
<th>10.3</th>
<th>Highest PD, high exposure</th>
</tr>
<tr class="odd">
<th>E</th>
<th>0</th>
<th>100</th>
<th>10000</th>
<th>100</th>
<th>100</th>
<th>Lowest PD, Lowest Exposure</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

These weights can be adjusted over time as more data becomes available or based on empirical validation. This method creates a balanced view of creditworthiness, reflecting both the likelihood of default (via PD) and the scale of risk exposure.

**Methodology to Calculate Normalized PD**

| **Supplier** | **Client** | **Amounts Due** | **Payment Terms** | **Average Days Overdue** | **DBT Ratio** |
|--------------|------------|-----------------|-------------------|--------------------------|---------------|
| 1            | A          | 10000           | 30                | 5                        | **0.167**     |
| 1            | B          | 15000           | 30                | 15                       | **0.5**       |
| 1            | C          | 5000            | 30                | 0                        | **0**         |
| 2            | A          | 8000            | 60                | 10                       | **0.167**     |
| 2            | B          | 12000           | 60                | 30                       | **0.5**       |
| 2            | D          | 20000           | 60                | 40                       | **0.667**     |
| 3            | A          | 9000            | 45                | 0                        | **0**         |
| 3            | C          | 7000            | 45                | 15                       | **0.333**     |
| 3            | E          | 10000           | 45                | 5                        | **0.111**     |

> **Normalized Weighted Risk - \[TBD\]**
>
> Calculate the DBT Ratio of each client. The DBT ratio measures how much a client exceeds the agreed-upon payment terms and is a key indicator of payment behavior.
>
> Get the weighted DBT ratios based on amounts due for each client
>
> Ie: for client A
>
> Total amount owed = 10000+8000+9000 =27000
>
> Weighted DBT = \[(10000\*0.167)+(8000\*0.167)+(9000\*0)\]/27000 = 0.111
>
> Normalized PD = (0.111-0.111) / (0.667-0.111)

| **Client** | **Weighted DBT** | **Normalized PD** |
|------------|------------------|-------------------|
| A          | 0.111            | 0                 |
| B          | 0.500            | 0.70              |
| C          | 0.194            | 0.15              |
| D          | 0.667            | 1.00              |
| E          | 0.111            | 0                 |

**Discussion Points:**

1.  **Probability of Default Calculation**

2.  **Need to add other metrics ie: Number of Invoices?**

**Scenario II: Where Historical Data is provided**

- Use ML model to predict probability of default

- Come up with metrics
