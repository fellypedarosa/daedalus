FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS runtime

WORKDIR /app/.mcp
COPY requirements.txt requirements-search.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY daedalus_mcp.py daedalus_paths.py daedalus.py ./
COPY daedalus_search/ ./daedalus_search/
COPY daedalus_ingest/ ./daedalus_ingest/
COPY daedalus_validation/ ./daedalus_validation/
COPY INGEST.md ./
COPY scripts/ ./scripts/

ENV PYTHONUNBUFFERED=1 \
    DAEDALUS_VAULT_DIR=/vault \
    DAEDALUS_INDEX_DIR=/var/lib/daedalus-search \
    DAEDALUS_INGEST_DIR=/var/lib/daedalus-ingest \
    DAEDALUS_SYNC_DIR=/var/lib/daedalus-sync \
    DAEDALUS_MODEL_DIR=/models \
    DAEDALUS_TOKENS_FILE=/run/daedalus/tokens.json \
    DAEDALUS_AUDIT_LOG=/var/log/daedalus/access.jsonl \
    DAEDALUS_TEST_AUDIT_LOG=/var/log/daedalus/test.jsonl \
    HF_HUB_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=2 \
    PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready', timeout=8)" || exit 1
CMD ["python", "daedalus_mcp.py", "--sse", "--port", "8000"]

FROM runtime AS test
ENV DAEDALUS_SYNC_DIR=""
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY tests/ ./tests/
COPY deploy/deploy.sh ./deploy/deploy.sh
RUN python -m unittest discover -s tests/search -t . -v
RUN python -m unittest discover -s tests/ingest -t . -v
RUN python -m unittest tests.test_layout.LayoutTests -v
