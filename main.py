import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import redis.asyncio as redis
import httpx
import json
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from backend_debugging import main
from backend_sync import get_article_contents, get_summaries

load_dotenv()
API_KEY = os.getenv('NEWS_API_KEY')
DEFAULT_KEY = "Today's Top Headlines"
CACHE_TTL = 86400

# "*" with allow_credentials=True is rejected by browsers; set CORS_ORIGINS in
# the environment (comma-separated) once you know your frontend's origin.
CORS_ORIGINS = [o.strip() for o in os.getenv('CORS_ORIGINS', '*').split(',') if o.strip()]

# Initialize scheduler globally
scheduler = AsyncIOScheduler()


async def cache_summaries(redis_client, all_summaries):
    """Write each category to Redis, skipping empty results.

    A category that failed to fetch returns []; overwriting a good cache entry
    with that would blank out the endpoint until the next successful refresh.
    """
    for category, summaries in all_summaries.items():
        key = DEFAULT_KEY if category == 'default' else category
        if not summaries:
            print(f'[{datetime.now()}] Skipping empty result for {key} (keeping previous cache)')
            continue
        try:
            await redis_client.set(key, json.dumps({key: summaries}), ex=CACHE_TTL)
            print(f'[{datetime.now()}] Cached: {key}')
        except Exception as e:
            print(f'[{datetime.now()}] Failed to cache {key}: {e}')


async def refresh_all_news_cache(redis_client):
    """Background task to refresh all news categories"""
    print(f'[{datetime.now()}] Starting background news refresh...')
    try:
        all_summaries = await main()
        await cache_summaries(redis_client, all_summaries)
        print(f'[{datetime.now()}] Background news refresh completed!')
    except Exception as e:
        print(f'[{datetime.now()}] Error during refresh: {e}')


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    app.state.redis = redis.from_url(redis_url, decode_responses=True)
    app.state.http_client = httpx.AsyncClient()

    try:
        await app.state.redis.ping()
        print(f'[{datetime.now()}] Connected to Redis.')
    except Exception as e:
        # Don't abort startup — the endpoints degrade to fetch-on-demand.
        print(f'[{datetime.now()}] WARNING: Redis unavailable at {redis_url}: {e}')

    # Warm the cache in the background. Doing this inline would hold the port
    # closed for minutes while 7 categories scrape and summarize, and the
    # platform health check would kill the deploy before it ever bound.
    print(f'[{datetime.now()}] Scheduling initial cache population...')
    app.state.warmup_task = asyncio.create_task(refresh_all_news_cache(app.state.redis))

    scheduler.add_job(
        refresh_all_news_cache,
        'cron',
        minute=58,  # Runs at :58 of every hour
        args=[app.state.redis],
        id='news_refresh_job',
        replace_existing=True,
    )
    scheduler.start()
    print(f'[{datetime.now()}] Background scheduler started! Will refresh at :58 of every hour.')

    yield

    scheduler.shutdown()
    app.state.warmup_task.cancel()
    try:
        await app.state.warmup_task
    except asyncio.CancelledError:
        print(f'[{datetime.now()}] Cache warmup cancelled on shutdown.')
    await app.state.http_client.aclose()
    await app.state.redis.aclose()
    print(f'[{datetime.now()}] Scheduler and connections closed.')


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ORIGINS != ['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


async def read_cache(key):
    try:
        return await app.state.redis.get(key)
    except Exception as e:
        print(f'[{datetime.now()}] Redis read failed for {key}: {e}')
        return None


async def fetch_and_cache(key, category):
    """Blocking fallback used on a cache miss, run off the event loop."""
    print(f'[{datetime.now()}] Cache miss for {key} - fetching...')
    if not API_KEY:
        raise HTTPException(status_code=503, detail='NEWS_API_KEY is not configured')
    articles = await asyncio.to_thread(get_article_contents, API_KEY, category)
    summaries = await asyncio.to_thread(get_summaries, articles)
    if not summaries:
        raise HTTPException(status_code=503, detail=f'No articles available for {key} yet')
    try:
        await app.state.redis.set(key, json.dumps({key: summaries}), ex=CACHE_TTL)
    except Exception as e:
        print(f'[{datetime.now()}] Redis write failed for {key}: {e}')
    return {key: summaries}


@app.get('/')
async def root():
    return {'status': 'ok', 'endpoints': ['/news', '/news/{category}', '/healthz']}


@app.get('/healthz')
async def healthz():
    """Liveness only — deliberately does not depend on Redis or the cache."""
    return {'status': 'ok'}


@app.get('/news')
async def get_summaries_default():
    """Return cached breaking news instantly"""
    cached = await read_cache(DEFAULT_KEY)
    if cached:
        return json.loads(cached)
    return await fetch_and_cache(DEFAULT_KEY, 'default')


@app.get('/news/{category}')
async def get_summaries_by_category(category: str):
    """Return cached category news instantly"""
    cached = await read_cache(category)
    if cached:
        return json.loads(cached)
    return await fetch_and_cache(category, category)
