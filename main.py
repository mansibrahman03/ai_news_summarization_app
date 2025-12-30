from contextlib import asynccontextmanager
from fastapi import FastAPI
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

# Initialize scheduler globally
scheduler = AsyncIOScheduler()

async def refresh_all_news_cache(redis_client):
    """Background task to refresh all news categories"""
    print(f"[{datetime.now()}] Starting background news refresh...")
    
    try:
        all_summaries = await main()
        
        for category, summaries in all_summaries.items():
            if category == 'default':
                data_str = json.dumps({'Today\'s Top Headlines': summaries})
                await redis_client.set('Today\'s Top Headlines', data_str, ex=86400)
                print(f"[{datetime.now()}] Cached: Today's Top Headlines")
            else:
                data_str = json.dumps({category: summaries})
                await redis_client.set(category, data_str, ex=86400)
                print(f"[{datetime.now()}] Cached: {category}")
        
        print(f"[{datetime.now()}] Background news refresh completed!")
    except Exception as e:
        print(f"[{datetime.now()}] Error during refresh: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Redis and HTTP client
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    app.state.redis = redis.from_url(redis_url, decode_responses=True)
    redis_client = app.state.redis
    app.state.http_client = httpx.AsyncClient()
    
    # Initial cache population on startup
    print(f"[{datetime.now()}] Populating initial cache...")
    all_summaries = await main()
    for category, summaries in all_summaries.items():
        if category == 'default':
            data_str = json.dumps({'Today\'s Top Headlines': summaries})
            await redis_client.set('Today\'s Top Headlines', data_str, ex=86400)
        else:
            data_str = json.dumps({category: summaries})
            await redis_client.set(category, data_str, ex=86400)
    print(f"[{datetime.now()}] Initial cache populated!")
    
    # Schedule background refresh to run 1 minute before every hour (at :58)
    scheduler.add_job(
        refresh_all_news_cache,
        'cron',
        minute=58,  # Runs at :58 of every hour
        args=[redis_client],
        id='news_refresh_job'
    )
    
    # Start the scheduler
    scheduler.start()
    print(f"[{datetime.now()}] Background scheduler started! Will refresh at :58 of every hour.")
    
    yield
    
    # Cleanup on shutdown
    scheduler.shutdown()
    await app.state.http_client.aclose()
    await app.state.redis.close()
    print(f"[{datetime.now()}] Scheduler and connections closed.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/news')
async def get_summaries_default():
    """Return cached breaking news instantly"""
    redis_client = app.state.redis
    cached = await redis_client.get('Today\'s Top Headlines')
    
    if cached:
        return json.loads(cached)
    
    # Fallback: fetch if cache is empty (shouldn't happen after startup)
    print(f"[{datetime.now()}] Cache miss for Today's Top Headlines - fetching...")
    articles = get_article_contents(API_KEY, 'default')
    summarized_articles = get_summaries(articles)
    data_str = json.dumps({'Today\'s Top Headlines': summarized_articles})
    await redis_client.set('Today\'s Top Headlines', data_str, ex=86400)
    return json.loads(data_str)


@app.get('/news/{category}')
async def get_summaries_by_category(category: str):
    """Return cached category news instantly"""
    redis_client = app.state.redis
    cached = await redis_client.get(category)
    
    if cached:
        return json.loads(cached)
    
    # Fallback: fetch if cache is empty
    print(f"[{datetime.now()}] Cache miss for {category} - fetching...")
    articles = get_article_contents(API_KEY, category)
    summarized_articles = get_summaries(articles)
    data_str = json.dumps({category: summarized_articles})
    await redis_client.set(category, data_str, ex=86400)
    return json.loads(data_str)
