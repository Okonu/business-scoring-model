# Architecture

This document describes the structure of the application and the flow of data.

## Summary

The application is a Python package with the name `health_score`. The package has five layers. Each layer has one responsibility.

| Layer | Package | Responsibility |
|---|---|---|
| Data source | `health_score.basepoint` | Log in to BASEPOINT and get the business data |
| Scoring | `health_score.scoring` | Calculate the measures and the score |
| Service | `health_score.service` | Connect the data source to the scoring |
| API | `health_score.api` | Receive HTTP requests and return JSON |
| Web page | `health_score.web` | Show the result in a browser |

The API and the web page use the same service. Thus, they always show the same result.

## Directory structure

```
health_score/
├── __init__.py            Package version
├── settings.py            Settings from environment variables
├── logging_config.py      Logging setup
├── service.py             ScoringService: log in, collect, score
├── basepoint/
│   ├── client.py          FSSClient: read-only BASEPOINT API client
│   ├── collector.py       collect(): get all data and make standard tables
│   └── errors.py          AuthenticationError, BasepointUnavailableError
├── scoring/
│   ├── registry.py        Dimensions, measures, weights and thresholds
│   ├── measures.py        compute_measures(): one calculation for each measure
│   └── engine.py          score_business(): the scorecard
├── api/
│   ├── app.py             create_app(): the FastAPI application
│   ├── schemas.py         Request and response models
│   ├── dependencies.py    Service access and API key check
│   └── routes/
│       ├── system.py      GET /health
│       └── scores.py      POST /v1/scores
└── web/
    └── app.py             The Streamlit page
streamlit_app.py           Entry point for Streamlit
tests/                     Tests
docs/                      Documents
```

## Data flow

The application does these steps for each request:

1. The API or the web page receives the company code and the PIN.
2. The service creates an `FSSClient`.
3. The client sends the company code to `POST /tenants/verify`.
4. The client sends the PIN to `POST /users/login`. BASEPOINT returns a token.
5. The collector sends approximately 40 requests to BASEPOINT at the same time. It uses the token.
6. The collector changes the responses into standard tables. An example is the `transactions` table.
7. The measures module calculates the value of each measure.
8. The engine changes each value into a score from 0 to 100. Then it calculates the dimension scores and the health score.
9. The service adds the business details and the data coverage report.
10. The API returns the result as JSON. The web page shows the result.

The application keeps the token in memory for one request only.

## Data source layer

### Client

`FSSClient` is a read-only client for the BASEPOINT API. It does these tasks:

- It logs in with the company code and the PIN.
- It sends GET requests with the token.
- It gets all pages of a paginated list at the same time.
- It tries a request one more time after a timeout or a server error.
- It records each request in a coverage list.

The `/tenants/verify` response contains database credentials. The client reads only the fields in `TENANT_FIELDS`. It does not keep the other fields.

### Collector

The `collect()` function gets all data for one business. It changes the data into pandas DataFrames.

The collector gets orders one month at a time for 16 months. BASEPOINT returns an error if one request asks for too many orders.

The collector makes the `transactions` table. This table has one row for each sale. It does not count a sale two times. For example, BASEPOINT makes an invoice for each POS order. The collector does not count these invoices.

## Scoring layer

### Registry

`registry.py` contains the scoring rules as data:

- The 6 dimensions and their weights
- The 75 measures, with their weights and thresholds
- The bands, the supplier tiers and the minimum data rules

To change a weight or a threshold, change this file. Then increase `ENGINE_VERSION`.

### Measures

`compute_measures()` calculates the value of each measure. If the data for a measure does not exist, the function does not return that measure. The function never returns 0 for missing data.

### Engine

`score_business()` does these steps:

1. It changes each measure value into a score from 0 to 100.
2. It calculates each dimension score. It uses only the measures that have data.
3. It calculates the health score from the dimension scores and the fixed weights.
4. It applies the red flag limits.
5. It calculates the confidence.
6. It calculates a score for each shop.

## Service layer

`ScoringService.score()` connects the other layers. The service does not store data. It calculates a new result for each request.

The service marks the result as `data_unavailable` if BASEPOINT did not return the sales data. It does not mark this result as `insufficient_data`.

## Errors

| Error | Cause | HTTP status |
|---|---|---|
| `AuthenticationError` | BASEPOINT did not accept the company code or the PIN | 401 |
| `BasepointUnavailableError` | BASEPOINT is not available | 503 |
| Request validation error | A request field is missing or not correct | 422 |
| Other error | An error in the application | 500 |

## Design principles

- **One responsibility for each module.** The data source does not calculate scores. The scoring does not send HTTP requests.
- **Rules as data.** The weights and thresholds are in the registry, not in the calculation code.
- **Dependency injection.** The service receives a client factory. The API receives a service. The tests use this to replace BASEPOINT with a fake client.
- **No stored state.** The application does not store business data, credentials or results.
- **Typed interfaces.** The API uses Pydantic models for requests and responses.
