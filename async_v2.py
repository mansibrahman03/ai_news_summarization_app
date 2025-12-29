import asyncio
from dotenv import load_dotenv
import os
from get_news import get_article_contents, get_summaries


load_dotenv()
api_key = os.getenv('NEWS_API_KEY')
categories = ['default', 'business', 'entertainment', 'health', 'science', 'sports', 'technology']
queue = asyncio.Queue()


async def produce(name, category):
    article_contents = await asyncio.to_thread(get_article_contents, api_key, category)
    await queue.put({'Category': category, 'Article Contents': article_contents})
    print(f'{name}: produce article contents for category: {category}')
    await asyncio.sleep(1)


async def consume(name):
    info = await queue.get()
    article_contents = info['Article Contents']
    category = info['Category']
    summaries = await asyncio.to_thread(get_summaries, article_contents)
    print(f'{name}: produced summaries for category: {category}')
    print(f'{summaries}')
    queue.task_done()


async def main():
    producer_tasks = [asyncio.create_task(produce(f'Producer-{category}', category)) for category in categories]
    consumer_tasks = [asyncio.create_task(consume(f'Consumer-{category}')) for category in categories]
    await asyncio.gather(*producer_tasks, *consumer_tasks)


if __name__ == '__main__':
    asyncio.run(main())

