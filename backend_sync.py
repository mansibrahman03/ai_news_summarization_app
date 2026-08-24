import requests
from newspaper import Article, Config
from transformers.utils.logging import set_verbosity_error
from dotenv import load_dotenv
import os

from summarizer import get_summarizer


set_verbosity_error()


MAX_ENTRIES = 3
MINIMUM_SUMMARY_LENGTH = 130
MAXIMUM_SUMMARY_LENGTH = 200

# newspaper3k's default user-agent gets 403'd by a lot of publishers.
article_config = Config()
article_config.browser_user_agent = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
)
article_config.request_timeout = 15
article_config.fetch_images = False


def get_article_contents(API_KEY, CATEGORY):
    if CATEGORY == 'default':
        URL = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={API_KEY}'
    else:
        URL = f'https://newsapi.org/v2/top-headlines?category={CATEGORY}&apiKey={API_KEY}'
    response = requests.get(URL, timeout=15)
    data = response.json()
    return fetch_article_data(data)


def fetch_article_data(DATA):
    download_successes = 0
    article_data = {}
    articles = DATA.get('articles')
    if articles is None:
        # NewsAPI returns {'status': 'error', 'message': ...} on a bad or missing key.
        print(f"NewsAPI returned no articles: {DATA.get('message', DATA)}")
        return article_data
    for article in articles:
        if download_successes >= MAX_ENTRIES:
            break
        article_title = article['title']
        article_url = article['url']
        article_author = article['author']
        article_source = article['source']['name']
        article_image = article['urlToImage']
        try:
            art = Article(article_url, config=article_config)
            art.download()
            art.parse()
            article_data[article_title] = {
                'text': art.text,
                'author': article_author,
                'source': article_source,
                'image': article_image,
            }
            download_successes += 1
        except Exception as e:
            print(f'Could not fetch content for Article: {article_title}. Error {e}')
    return article_data


def summarize_article(article_text):
    summarizer = get_summarizer()
    return summarizer(
        article_text,
        max_length=MAXIMUM_SUMMARY_LENGTH,
        min_length=MINIMUM_SUMMARY_LENGTH,
        do_sample=False,
    )


def get_summaries(ARTICLE_CONTENTS):
    summaries = []
    for title, data in ARTICLE_CONTENTS.items():
        content = data['text'][:1024]
        if not content.strip():
            continue
        summaries.append({
            'title': title,
            'summary': summarize_article(content)[0]['summary_text'],
            'author': data['author'],
            'source': data['source'],
            'image': data['image'],
        })
    return summaries


if __name__ == '__main__':
    load_dotenv()
    api_key = os.getenv('NEWS_API_KEY')
    articles = get_article_contents(api_key, 'entertainment')
    print(get_summaries(articles))
