"""Article summarization via Groq's hosted inference.

Replaces the former local transformers/torch pipeline. No model weights live in
this process any more, which is what lets the service run in a 512MB container
instead of needing ~2.5GB.

The binding constraint here is Groq's free tier, not latency. A full refresh is
21 summaries (7 categories x 3 articles); fired back-to-back that would breach
the ~8K tokens/minute cap, so requests are paced to a minimum interval and
retried on rate-limit errors. A refresh taking ~2 minutes is fine — it runs in
the background every 3 hours.
"""
import asyncio
import os
import time
from threading import Lock

MODEL_NAME = os.getenv('SUMMARIZER_MODEL', 'llama-3.3-70b-versatile')
MAX_SUMMARY_TOKENS = int(os.getenv('MAX_SUMMARY_TOKENS', '320'))
# 5s between requests => ~12 req/min => ~5.5K tokens/min, under the 8K/min cap.
MIN_REQUEST_INTERVAL = float(os.getenv('GROQ_MIN_REQUEST_INTERVAL', '5.0'))
MAX_ATTEMPTS = 5

SYSTEM_PROMPT = (
    'You summarize news articles. Reply with a single paragraph of three to four '
    'sentences capturing the key facts. Write plain prose: no preamble, no bullet '
    'points, no closing commentary, and do not mention that you are summarizing.'
)

_sync_client = None
_async_client = None
_client_lock = Lock()

_last_request = 0.0
_sync_pace_lock = Lock()
_async_pace_lock = asyncio.Lock()


def _api_key():
    key = os.getenv('GROQ_API_KEY')
    if not key:
        raise RuntimeError(
            'GROQ_API_KEY is not set. Get a free key at https://console.groq.com'
        )
    return key


def get_client():
    global _sync_client
    if _sync_client is None:
        with _client_lock:
            if _sync_client is None:
                from groq import Groq
                _sync_client = Groq(api_key=_api_key())
    return _sync_client


def get_async_client():
    global _async_client
    if _async_client is None:
        from groq import AsyncGroq
        _async_client = AsyncGroq(api_key=_api_key())
    return _async_client


def _messages(article_text):
    return [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': f'Summarize this news article:\n\n{article_text}'},
    ]


def _backoff_seconds(exc, attempt):
    """Honour the server's retry-after when present, else exponential backoff."""
    headers = getattr(getattr(exc, 'response', None), 'headers', None) or {}
    try:
        return float(headers.get('retry-after'))
    except (TypeError, ValueError):
        return min(2 ** attempt, 30)


def _pace_sync():
    global _last_request
    with _sync_pace_lock:
        delay = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request)
        if delay > 0:
            time.sleep(delay)
        _last_request = time.monotonic()


async def _pace_async():
    global _last_request
    async with _async_pace_lock:
        delay = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request)
        if delay > 0:
            await asyncio.sleep(delay)
        _last_request = time.monotonic()


def summarize(article_text):
    """Blocking summarization. Used by the cache-miss fallback path."""
    from groq import RateLimitError
    for attempt in range(MAX_ATTEMPTS):
        _pace_sync()
        try:
            response = get_client().chat.completions.create(
                model=MODEL_NAME,
                messages=_messages(article_text),
                max_tokens=MAX_SUMMARY_TOKENS,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except RateLimitError as e:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(_backoff_seconds(e, attempt))


async def summarize_async(article_text):
    """Async summarization. Used by the scheduled refresh."""
    from groq import RateLimitError
    for attempt in range(MAX_ATTEMPTS):
        await _pace_async()
        try:
            response = await get_async_client().chat.completions.create(
                model=MODEL_NAME,
                messages=_messages(article_text),
                max_tokens=MAX_SUMMARY_TOKENS,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except RateLimitError as e:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            await asyncio.sleep(_backoff_seconds(e, attempt))
