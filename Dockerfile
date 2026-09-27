FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY health_score ./health_score
COPY streamlit_app.py pyproject.toml README.md ./

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8100 8501

# Default: the HTTP API. See docker-compose.yml for the web page.
CMD ["uvicorn", "health_score.api.app:app", "--host", "0.0.0.0", "--port", "8100"]
