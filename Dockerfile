FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FASTEMBED_CACHE_PATH=/app/.fastembed_cache

WORKDIR /app
COPY pyproject.toml README.md ./
COPY resolve ./resolve
COPY apps/api ./apps/api
COPY data ./data
COPY evals ./evals

RUN pip install --no-cache-dir -e ".[retrieve]" anthropic==2.6.0 \
 && python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')" \
 && useradd --create-home --uid 10001 app \
 && mkdir -p /app/var /app/data/index \
 && chown -R app /app

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
