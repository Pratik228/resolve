FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY resolve /app/resolve
COPY apps/api /app/apps/api
COPY data /app/data
COPY evals /app/evals

RUN pip install --no-cache-dir -e ".[dev]"

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
