import aiohttp
import asyncio
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from transformers import pipeline
from concurrent.futures import ThreadPoolExecutor
import os


load_dotenv()
api_key = os.getenv('NEWS_API_KEY')
MAX_ENTRIES = 3


async def get_article_contents(category):
    if category == 'default':
        url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}'
    else:
        url = f'https://newsapi.org/v2/top-headlines?category={category}&apiKey={api_key}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            run_data = await fetch_article_data(data, 0, MAX_ENTRIES)
            article_contents = run_data[0]
            number_of_runs = 1
            while len(article_contents) < MAX_ENTRIES:
                first_article_index = number_of_runs * MAX_ENTRIES
                run_data = await fetch_article_data(data, first_article_index, MAX_ENTRIES+run_data[2])
                number_of_runs+=1
                article_contents.update(run_data[0])
            return article_contents


async def fetch_article_data(DATA, FIRST_ARTICLE_INDEX, LAST_ARTICLE_INDEX):
    download_successes = 0
    download_fails = 0
    article_data = {}
    articles = DATA['articles'][FIRST_ARTICLE_INDEX:LAST_ARTICLE_INDEX]
    async with aiohttp.ClientSession() as session:
        for article in articles:
            article_title = article['title']
            article_url = article['url']
            try:
                async with session.get(article_url) as response:
                    html = await response.text()
                    parsed = BeautifulSoup(html, 'html.parser')
                    paragraphs = parsed.find_all('p')
                    article_text = ' '.join(p.text for p in paragraphs)
                    article_data[article_title] = article_text
                    download_successes+=1
            except Exception as e:
                print(f'Could not fetch content for Article: {article_title}. Error {e}')
                download_fails+=1
    return [article_data, download_successes, download_fails]


summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
executor = ThreadPoolExecutor(max_workers=2)
summarize_semaphore = asyncio.Semaphore(2)


def summarize_article(article_text):
    summary = summarizer(article_text, max_length=130, min_length=30, do_sample=False)
    return summary


async def summarize_article_async(article_text):
    async with summarize_semaphore:
        loop = asyncio.get_running_loop()
        summary_info = await loop.run_in_executor(executor, summarize_article, article_text)
        summary = summary_info[0]['summary_text']
        return summary


async def get_summaries(ARTICLE_CONTENTS):
    summaries = {}
    for title, content in ARTICLE_CONTENTS.items():
        content = content[:1024]
        summarized_content = await summarize_article_async(content)
        summaries[title] = summarized_content
    return summaries


async def main():
    contents = await get_article_contents('default')
    summaries = await get_summaries(contents)
    return summaries

