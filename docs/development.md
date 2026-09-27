# Development

This document tells you how to set up, test and change the application.

## Set up

1. Install Python 3.11 or later.
2. Create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install the application with the development tools:

   ```bash
   pip install -e ".[dev]"
   ```

## Run the tests

```bash
pytest
```

The tests do not connect to BASEPOINT. They use a fake client (`tests/conftest.py`). The fake client returns synthetic data for a business with two shops.

| Test file | Contents |
|---|---|
| `tests/test_client.py` | The BASEPOINT client: login, unknown company codes, outages and the tenant field whitelist |
| `tests/test_engine.py` | Measure scores, bands, weights and the supplier tracking factor |
| `tests/test_scoring.py` | The collector, the measures and the engine together |
| `tests/test_service.py` | The scoring service |
| `tests/test_api.py` | The HTTP API, authentication and errors |

## Check the code

The project uses Ruff for linting and formatting. The settings are in `pyproject.toml`.

```bash
ruff check .
ruff format .
```

The CI workflow runs the lint, the format check and the tests on each push and pull request. The workflow is in `.github/workflows/ci.yml`.

## Change a weight or a threshold

1. Open `health_score/scoring/registry.py`.
2. Change the value in the `MEASURES` list or the `DIMENSIONS` table.
3. Make sure that the measure weights in each dimension add up to 100. The module checks this when it loads.
4. Increase `ENGINE_VERSION`.
5. Update the methodology document: `docs/methodology/business-health-score.md`.
6. Run the tests.

## Add a measure

1. Add the measure to `MEASURES` in `registry.py`. Give it a unique `id`, a dimension, a weight, a kind and the thresholds.
2. Change the weights of the other measures in the same dimension. The total must be 100.
3. Calculate the value in `compute_measures()` in `health_score/scoring/measures.py`. Put the value in the `v` dictionary with the same `id`.
4. If the data for the measure does not exist, do not set a value. Do not set 0.
5. Add a test.
6. Increase `ENGINE_VERSION`.
7. Update the methodology document.

The measure kinds are:

| Kind | Meaning |
|---|---|
| `higher` | A larger value is better. The score is 100 at `good` and 0 at `poor`. |
| `lower` | A smaller value is better. The score is 100 at `good` and 0 at `poor`. |
| `range` | The best values are between `good` and `good_high`. The score is 0 at `poor` and at `poor_high`. |
| `score` | The value is already a score from 0 to 100. |

## Add a BASEPOINT dataset

1. Add a job to the lists in `collect()` in `health_score/basepoint/collector.py`.
2. Add a normalizer. The normalizer changes the records into a DataFrame.
3. Add the DataFrame to the `tables` dictionary.
4. Add the dataset to the fake client data in `tests/conftest.py`.

## Rules for the code

- Keep each layer separate. The scoring layer must not send HTTP requests.
- Do not store credentials. Do not write credentials to the log.
- Do not return 0 for missing data. Leave the measure out.
- Use the same terms as the methodology: measure, dimension, band, red flag.
