# Business Health Score

This application calculates a health score for a BASEPOINT business. The score is a number from 0 to 100.

The application gets the business data from the BASEPOINT API. It uses the data from all BASEPOINT products that the business uses:

- Duka: sales, stock, customers and shops
- Pesa: accounting
- Bandu: staff and payroll
- Mteja: customer relationships
- Dala: property

The application has two interfaces:

- An HTTP API. The API returns the full result as JSON.
- A web page. The web page shows the same result.

The application does not store data. It calculates each result when you send a request.

## Documents

| Document | Contents |
|---|---|
| [Methodology](docs/methodology/business-health-score.md) | How the application calculates the score |
| [Architecture](docs/architecture.md) | The structure of the application and the flow of data |
| [API reference](docs/api.md) | Endpoints, request fields, response fields and errors |
| [Configuration](docs/configuration.md) | Environment variables |
| [Deployment](docs/deployment.md) | How to run the application with Streamlit Community Cloud or Docker |
| [Development](docs/development.md) | How to set up, test and change the application |
| [BASEPOINT data model](docs/methodology/ERD.md) | The BASEPOINT entities and relationships |

## Quick start

Python 3.11 or later is necessary.

1. Clone the repository.
2. Create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install the application:

   ```bash
   pip install -e ".[dev]"
   ```

4. Start the API:

   ```bash
   uvicorn health_score.api.app:app --port 8100
   ```

5. Send a request. Replace the company code and the PIN with the credentials of the business:

   ```bash
   curl -X POST http://localhost:8100/v1/scores \
     -H "Content-Type: application/json" \
     -d '{"company_code": "XXXX-000000", "pin": "****"}'
   ```

6. To start the web page, use this command:

   ```bash
   streamlit run streamlit_app.py
   ```

The interactive API documentation is at `http://localhost:8100/docs`.

## How the score works

The application calculates 75 measures. Each measure gets a score from 0 to 100.

The measures are in 6 dimensions. Each dimension has a fixed weight:

| Dimension | Weight |
|---|---|
| Sales performance | 22% |
| Cash, collections and payables | 22% |
| Operational stability | 18% |
| Profitability and cost control | 13% |
| Customer and revenue base | 13% |
| Formality and compliance | 12% |

The health score is the weighted sum of the 6 dimension scores. Red flags can set a maximum on the score.

The score has a band:

| Score | Band |
|---|---|
| 80 to 100 | Strong |
| 65 to 79 | Healthy |
| 50 to 64 | Watch |
| 35 to 49 | Weak |
| 0 to 34 | Distressed |

For the full rules, read the [methodology](docs/methodology/business-health-score.md).

## Security

- The application uses the company code and the PIN for one request only. It does not store them. It does not write them to the log.
- Keep the API and the web page private. A person with access and valid credentials can score that business.
- To require an API key, set the `API_KEYS` environment variable. Refer to [Configuration](docs/configuration.md).
