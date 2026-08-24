FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf_cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch. The default PyPI wheel pulls in CUDA (~2.5GB) that this image
# can never use. Installed before requirements.txt so it stays cached.
RUN pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# newspaper3k reaches for these at parse time; fetching them at build time keeps
# the first request from failing on a missing corpus.
RUN python -m nltk.downloader -d /usr/share/nltk_data punkt punkt_tab

COPY . .

EXPOSE 8000

# Shell form so ${PORT} expands — Render injects it; 8000 is the local default.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
