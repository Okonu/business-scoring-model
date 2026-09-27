# Configuration

The application gets its settings from environment variables. It also reads a `.env` file in the working directory, if the file exists.

All settings are optional. Each setting has a default value.

## Settings

| Variable | Default | Description |
|---|---|---|
| `FSS_API_URL` | `https://api.hospitality.reliatech.co.ke` | The base URL of the BASEPOINT API |
| `FSS_TIMEOUT_SECONDS` | `90` | The maximum time in seconds for one BASEPOINT request |
| `API_KEYS` | empty | API keys, separated by commas. If this setting is empty, the API does not require a key. |
| `LOG_LEVEL` | `INFO` | The logging level: `DEBUG`, `INFO`, `WARNING` or `ERROR` |

## Set the configuration

1. Copy the example file:

   ```bash
   cp .env.example .env
   ```

2. Change the values in `.env`.
3. Start the application again.

Do not commit the `.env` file. The `.gitignore` file excludes it.

## API keys

To require an API key for the API:

1. Make a long random key:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. Set the key in `API_KEYS`. To use more than one key, separate the keys with commas.
3. Give each client its key. Each client sends the key in the `X-API-Key` header.

To replace a key, add the new key first. Then remove the old key after all clients use the new key.

The API key does not apply to the web page. To control access to the web page, use the sharing settings of Streamlit Community Cloud.

## Scoring rules

The weights, thresholds and other scoring rules are not environment variables. They are in `health_score/scoring/registry.py`. Refer to [Development](development.md).
