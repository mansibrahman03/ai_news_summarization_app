import asyncio
from dotenv import load_dotenv
import time
import os
import aiohttp
from bs4 import BeautifulSoup
from transformers import pipeline
from concurrent.futures import ThreadPoolExecutor


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


async def get_article_contents(category):
    if category == 'default':
        url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}'
    else:
        url = f'https://newsapi.org/v2/top-headlines?category={category}&apiKey={api_key}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            article_contents = await fetch_article_data(data)
            # article_contents = run_data[0]
            # number_of_runs = 1
            # while len(article_contents) < MAX_ENTRIES:
            #     first_article_index = number_of_runs * MAX_ENTRIES
            #     run_data = await fetch_article_data(data, first_article_index, MAX_ENTRIES+run_data[2])
            #     number_of_runs+=1
            #     article_contents.update(run_data[0])
    return article_contents


async def fetch_article_data(DATA):
    download_successes = 0
    article_data = {}
    if 'articles' not in DATA:
        articles = []
        print("error, key 'articles'  not found in DATA")
    else:
        articles = DATA['articles']
    async with aiohttp.ClientSession() as session:
        for article in articles:
            if download_successes < MAX_ENTRIES:
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
                        content = article_text
                        word_list = content.split()
                        if (len(word_list) > 200):
                            article_data[article_title] = {'text': article_text, 'author': article_author, 'source': article_source, 'image': article_image}
                            download_successes+=1
                except Exception as e:
                    print(f'Could not fetch content for Article: {article_title}. Error {e}')
            else:
                break
    return article_data


summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
executor = ThreadPoolExecutor(max_workers=2)
summarize_semaphore = asyncio.Semaphore(2)


def summarize_article(article_text):
    summary = summarizer(article_text, max_length=MAXIMUM_SUMMARY_LENGTH, min_length=MINIMUM_SUMMARY_LENGTH, do_sample=False)
    return summary


async def summarize_article_async(article_text):
    async with summarize_semaphore:
        loop = asyncio.get_running_loop()
        summary_info = await loop.run_in_executor(executor, summarize_article, article_text)
        summary = summary_info[0]['summary_text']
        return summary


async def get_summaries(ARTICLE_CONTENTS):
    summaries = []
    for title, data in ARTICLE_CONTENTS.items():
        content = data['text']
        content = content[:1024]
        summarized_content = await summarize_article_async(content)
        summary = {}
        summary['title'] = title
        summary['summary'] = summarized_content
        summary['author'] = data['author']
        summary['source'] = data['source']
        summary['image'] = data['image']
        summaries.append(summary)
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
    end_time = time.time()
    current_delay = end_time - start_time
    print(f'{name}: Fetched data (Time: {current_delay:.2f}s). Producing article contents...')
    await category_queues[category].put(articles)
    print(f'{name}: Produced article contents...')


async def consume(name, category):
    print(f'{name}: Waiting for data...')
    article_contents = await category_queues[category].get()
    if article_contents is None:
        print(f'{name}: Terminating...')
        return
    print(f'{name}: Received article contents, summarizing articles...')
    summaries = await get_summaries(article_contents)
    async with lock:
       all_summaries[category] = summaries
    print(f'{name}: {summaries}')


async def main():
    producer_tasks = []
    consumer_tasks = []
    async with asyncio.TaskGroup() as tg:
        for producer, category in producers.items():
            task = tg.create_task(produce(producer, category))
            producer_tasks.append(task)
        for consumer, category in consumers.items():
            task = tg.create_task(consume(consumer, category))
            consumer_tasks.append(task)
    for category in categories:
        await category_queues[category].put(None)
    return all_summaries


if __name__ == '__main__':
    asyncio.run(main())

