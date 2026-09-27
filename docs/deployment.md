# Deployment

This document tells you how to run the application. You can use Streamlit Community Cloud for the web page. You can use Docker for the API and the web page.

The application does not store data. Thus, it does not need a database or a volume.

## Streamlit Community Cloud (web page)

1. Sign in to Streamlit Community Cloud.
2. Select **Create app**.
3. Enter these values:

   | Field | Value |
   |---|---|
   | Repository | `Hospitality-POS/business-scoring-model` |
   | Branch | `main` |
   | Main file path | `streamlit_app.py` |

4. Select **Deploy**.
5. Open the sharing settings. Make the app private. Invite only the persons who need access.

Streamlit Community Cloud installs the packages in `requirements.txt`. When you push to `main`, it deploys the new version.

## Docker

### Build the image

```bash
docker build -t business-health-score .
```

### Run the API

```bash
docker run -d -p 8100:8100 --env-file .env business-health-score
```

### Run the API and the web page

```bash
docker compose up -d
```

This command starts two containers:

| Container | Port | Contents |
|---|---|---|
| `api` | 8100 | The HTTP API |
| `web` | 8501 | The web page |

### Check the API

```bash
curl http://localhost:8100/health
```

The response must contain `"status": "ok"`.

## Production checklist

Do these steps before you make the API available to other systems:

1. Set `API_KEYS`. Refer to [Configuration](configuration.md).
2. Put the API behind HTTPS. Use a reverse proxy, for example nginx, or a load balancer.
3. Set the request timeout of the proxy to 120 seconds or more. A large business can take up to 90 seconds.
4. Do not log request bodies at the proxy. The request body contains the PIN.
5. Monitor `GET /health`.
