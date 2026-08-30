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

MODEL_NAME = os.getenv('SUMMARIZER_MODEL', 'openai/gpt-oss-20b')
# The gpt-oss/qwen models on Groq are reasoning models, and reasoning tokens are
# billed against max_tokens. Too small a budget and the model spends it all
# thinking, returning finish_reason='length' with empty content — which shows up
# as an article with a title and image but no summary.
MAX_SUMMARY_TOKENS = int(os.getenv('MAX_SUMMARY_TOKENS', '1024'))
# Keeps reasoning short so the budget goes to the answer. Set to '' for models
# that don't accept the parameter.
REASONING_EFFORT = os.getenv('GROQ_REASONING_EFFORT', 'low')
# 6s between requests => ~10 req/min => ~6K tokens/min, under the 8K/min cap.
MIN_REQUEST_INTERVAL = float(os.getenv('GROQ_MIN_REQUEST_INTERVAL', '6.0'))
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


def _request_kwargs(article_text):
    kwargs = {
        'model': MODEL_NAME,
        'messages': _messages(article_text),
        'max_tokens': MAX_SUMMARY_TOKENS,
        'temperature': 0.3,
    }
    if REASONING_EFFORT:
        kwargs['reasoning_effort'] = REASONING_EFFORT
    return kwargs


def _extract(response):
    """Pull the summary out, refusing anything empty or obviously truncated.

    Raising here rather than returning a blank means the caller's except-block
    skips the article, so a half-generated summary never reaches the frontend.
    """
    choice = response.choices[0]
    text = (choice.message.content or '').strip()
    if not text:
        raise ValueError(
            f'empty summary (finish_reason={choice.finish_reason}); '
            'the model likely spent max_tokens on reasoning'
        )
    if choice.finish_reason == 'length':
        raise ValueError('summary truncated before completion (finish_reason=length)')
    return text


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
            return _extract(get_client().chat.completions.create(**_request_kwargs(article_text)))
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
            return _extract(await get_async_client().chat.completions.create(**_request_kwargs(article_text)))
        except RateLimitError as e:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            await asyncio.sleep(_backoff_seconds(e, attempt))
