from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import redis.asyncio as redis
import httpx
import json
import os
from backend_debugging import main
from backend_sync import get_article_contents, get_summaries

app = FastAPI()

load_dotenv()
API_KEY = os.getenv('NEWS_API_KEY')

# Configure CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["https://id-preview--28fe6fad-7122-454a-8141-440d2ed85d18.lovable.app"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"]
# )

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis(host='localhost', port=6379, decode_responses=True) # connects to redis once
    redis_client = app.state.redis
    app.state.http_client = httpx.AsyncClient() # creates a reusable http client
    all_summaries = await main()
    for category, summaries in all_summaries.items():
        if category == 'default':
            data_str = json.dumps({'Today\'s Top Headlines': summaries})
            await redis_client.set('Today\'s Top Headlines', data_str, ex=86400)
        else:
            data_str = json.dumps({category: summaries})
            await redis_client.set(category, data_str, ex=86400)
    yield
    await app.state.http_client.aclose()
    await app.state.redis.close()


app = FastAPI(lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

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
    redis_client = app.state.redis
    cached = await redis_client.get('Today\'s Top Headlines')
    if cached:
        return json.loads(cached)
    articles = get_article_contents(API_KEY, 'default')
    summarized_articles = get_summaries(articles)
    data_str = json.dumps({'Today\'s Top Headlines': summarized_articles})
    await redis_client.set('Today\'s Top Headlines', data_str, ex=86400)  # cache for 24 hours
    cached = await redis_client.get('Today\'s Top Headlines')
    return json.loads(cached)


@app.get('/news/{category}')
async def get_summaries_by_category(category: str):
    redis_client = app.state.redis
    cached = await redis_client.get(category)
    if cached:
        return json.loads(cached)
    articles = get_article_contents(API_KEY, category)
    summarized_articles = get_summaries(articles)
    data_str = json.dumps({category: summarized_articles})
    await redis_client.set(category, data_str, ex=86400)
    cached = await redis_client.get(category)
    return json.loads(cached)

