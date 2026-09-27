# API reference

This document describes the HTTP API.

The API has an interactive reference at `/docs`. The OpenAPI schema is at `/openapi.json`.

## Base URL

When you run the API on your computer, the base URL is `http://localhost:8100`.

## Authentication

The API uses two types of credentials:

1. **API key.** This key is optional. If the `API_KEYS` setting has a value, each request to `/v1/...` must have the header `X-API-Key`. The value must be one of the keys in `API_KEYS`.
2. **BASEPOINT credentials.** Each scoring request contains the company code and the PIN of the business. The API uses them to log in to BASEPOINT. The API does not store them.

## GET /health

This endpoint shows that the API operates.

### Response

```json
{
  "status": "ok",
  "version": "0.2.0",
  "engine_version": "0.2.0"
}
```

## POST /v1/scores

This endpoint calculates the health score of a business. The response contains all the data that the web page shows.

The request can take up to 90 seconds for a large business.

### Request

| Field | Type | Necessary | Description |
|---|---|---|---|
| `company_code` | string | Yes | The BASEPOINT company code of the business |
| `pin` | string | Yes | The PIN of a user of the business |
| `username` | string | No | The username. Use it only if the account needs a username. |
| `as_of_date` | date (`YYYY-MM-DD`) | No | The date of the score. The default is today (UTC). |

Example:

```json
{
  "company_code": "XXXX-000000",
  "pin": "****",
  "as_of_date": "2026-09-27"
}
```

Use an administrator login. A user who is not an administrator can see fewer shops. Thus, the result can be incomplete.

### Response

| Field | Type | Description |
|---|---|---|
| `status` | string | `scored`, `insufficient_data` or `data_unavailable` |
| `score` | number or null | The health score from 0 to 100. It is null if `status` is not `scored`. |
| `score_uncapped` | number | The score before the red flag limits |
| `band` | string | `Strong`, `Healthy`, `Watch`, `Weak` or `Distressed` |
| `confidence` | string | `High`, `Medium` or `Low` |
| `products_used` | list of strings | The BASEPOINT products that had activity in the last 3 months |
| `measure_weight_available` | number | The part of the total measure weight that has data (0 to 1) |
| `business` | object | The business details |
| `dimensions` | object | The score of each of the 6 dimensions |
| `measures` | list | Each measure that has data: its value, score and weight |
| `measures_not_available` | list | The measures that do not have data |
| `red_flags` | list | The red flags and the limit that each red flag sets |
| `drivers` | object | The 3 strongest and the 3 weakest measures |
| `shops` | list | The score and revenue of each shop |
| `shop_network` | object or null | The shop network measure. It is null if the business has fewer than 2 shops. |
| `aging` | object | The receivables and payables aging buckets |
| `context` | object | Supporting values. Examples: revenue, credit share, supplier tracking. |
| `data_coverage` | list | Each BASEPOINT endpoint that the application called, with the number of records |
| `data_warnings` | list of strings | The BASEPOINT requests that failed |
| `record_counts` | object | The number of records in each standard table |
| `scored_as` | object | The BASEPOINT user that the application logged in as |
| `as_of` | date | The date of the score |
| `scored_at` | string | The time of the calculation (UTC) |
| `engine_version` | string | The version of the scoring rules |
| `duration_seconds` | number | The time that the calculation took |

#### Status values

| Status | Meaning |
|---|---|
| `scored` | The application calculated a score |
| `insufficient_data` | The business has less than 3 months of sales, or 2 or more dimensions have no data |
| `data_unavailable` | BASEPOINT did not return the sales data. Try again later. |

### Errors

| HTTP status | Cause |
|---|---|
| 401 | The API key is missing or not correct. Or BASEPOINT did not accept the company code or the PIN. |
| 422 | A request field is missing or not correct |
| 503 | BASEPOINT is not available |
| 500 | An error in the application |

The body of an error response has one field, `detail`. This field contains a description of the error.

### Example

```bash
curl -X POST http://localhost:8100/v1/scores \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your API key>" \
  -d '{"company_code": "XXXX-000000", "pin": "****"}'
```
