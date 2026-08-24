import asyncio
from dotenv import load_dotenv
import time
import os
import aiohttp
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

from summarizer import get_summarizer


load_dotenv()
api_key = os.getenv('NEWS_API_KEY')
categories = ['default', 'business', 'entertainment', 'sports', 'technology', 'science', 'health']
category_queues = {category: asyncio.Queue() for category in categories}
producers = {f'Producer-{category}': category for category in categories}
consumers = {f'Consumer-{category}': category for category in categories}
MAX_ENTRIES = 3
MINIMUM_SUMMARY_LENGTH = 130
MAXIMUM_SUMMARY_LENGTH = 200
all_summaries = {}
lock = asyncio.Lock()

# Publishers 403 anything that looks like a script.
BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)


async def get_article_contents(category):
    if category == 'default':
        url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}'
    else:
        url = f'https://newsapi.org/v2/top-headlines?category={category}&apiKey={api_key}'
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(url) as response:
            data = await response.json()
    return await fetch_article_data(data)


async def fetch_article_data(DATA):
    download_successes = 0
    article_data = {}
    articles = DATA.get('articles')
    if articles is None:
        # NewsAPI returns {'status': 'error', 'message': ...} on a bad or missing key.
        print(f"NewsAPI returned no articles: {DATA.get('message', DATA)}")
        return article_data
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT, headers=BROWSER_HEADERS) as session:
        for article in articles:
            if download_successes >= MAX_ENTRIES:
                break
            article_title = article['title']
            article_url = article['url']
            article_author = article['author']
            article_source = article['source']['name']
            article_image = article['urlToImage']
            try:
                async with session.get(article_url) as response:
                    html = await response.text()
                parsed = BeautifulSoup(html, 'html.parser')
                paragraphs = parsed.find_all('p')
                article_text = ' '.join(p.text for p in paragraphs)
                if len(article_text.split()) > 200:
                    article_data[article_title] = {
                        'text': article_text,
                        'author': article_author,
                        'source': article_source,
                        'image': article_image,
                    }
                    download_successes += 1
            except Exception as e:
                print(f'Could not fetch content for Article: {article_title}. Error {e}')
    return article_data


executor = ThreadPoolExecutor(max_workers=2)
summarize_semaphore = asyncio.Semaphore(2)


def summarize_article(article_text):
    summarizer = get_summarizer()
    return summarizer(
        article_text,
        max_length=MAXIMUM_SUMMARY_LENGTH,
        min_length=MINIMUM_SUMMARY_LENGTH,
        do_sample=False,
    )


async def summarize_article_async(article_text):
    async with summarize_semaphore:
        loop = asyncio.get_running_loop()
        summary_info = await loop.run_in_executor(executor, summarize_article, article_text)
        return summary_info[0]['summary_text']


async def get_summaries(ARTICLE_CONTENTS):
    summaries = []
    for title, data in ARTICLE_CONTENTS.items():
        content = data['text'][:1024]
        if not content.strip():
            continue
        summaries.append({
            'title': title,
            'summary': await summarize_article_async(content),
            'author': data['author'],
            'source': data['source'],
            'image': data['image'],
        })
    return summaries


async def produce(name, category, timeout=40):
    print(f'{name}: Starting fetch...')
    start_time = time.time()
    try:
        articles = await asyncio.wait_for(get_article_contents(category), timeout=timeout)
    except asyncio.TimeoutError:
        print(f'{name}: Timed out while fetching articles for category \'{category}\'')
        await category_queues[category].put(None)
        return
    except Exception as e:
        print(f'{name}: Failed to fetch articles for category \'{category}\': {e}')
        await category_queues[category].put(None)
        return
    current_delay = time.time() - start_time
    print(f'{name}: Fetched data (Time: {current_delay:.2f}s). Producing article contents...')
    await category_queues[category].put(articles)
    print(f'{name}: Produced article contents...')


async def consume(name, category):
    print(f'{name}: Waiting for data...')
    article_contents = await category_queues[category].get()
    # Always record the category, even on failure, so callers can tell an empty
    # refresh apart from a category that silently never reported.
    if article_contents is None:
        print(f'{name}: Terminating...')
        async with lock:
            all_summaries[category] = []
        return
    print(f'{name}: Received article contents, summarizing articles...')
    try:
        summaries = await get_summaries(article_contents)
    except Exception as e:
        print(f'{name}: Failed to summarize category \'{category}\': {e}')
        summaries = []
    async with lock:
        all_summaries[category] = summaries
    print(f'{name}: produced {len(summaries)} summaries for \'{category}\'')


async def main():
    all_summaries.clear()
    async with asyncio.TaskGroup() as tg:
        for producer, category in producers.items():
            tg.create_task(produce(producer, category))
        for consumer, category in consumers.items():
            tg.create_task(consume(consumer, category))
    # No sentinel push here: the TaskGroup has already joined every consumer, and
    # a leftover None would be the first thing the *next* refresh dequeues.
    return dict(all_summaries)


if __name__ == '__main__':
    asyncio.run(main())
