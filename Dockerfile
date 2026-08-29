FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# newspaper3k reaches for these at parse time; fetching them at build time keeps
# the first request from failing on a missing corpus.
RUN python -m nltk.downloader -d /usr/share/nltk_data punkt punkt_tab

COPY . .

EXPOSE 8000

# Shell form so ${PORT} expands — Render injects it; 8000 is the local default.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
