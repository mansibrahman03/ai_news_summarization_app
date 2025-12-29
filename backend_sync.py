import requests
from newspaper import Article
from transformers import pipeline
from transformers.utils.logging import set_verbosity_error
from dotenv import load_dotenv
import os
# from langchain_huggingface import HuggingFacePipeline
# from langchain.prompts import PromptTemplate


set_verbosity_error()


MAX_ENTRIES = 3
MINIMUM_SUMMARY_LENGTH = 130
MAXIMUM_SUMMARY_LENGTH = 200


# def generate_summary_chain():
    # summarization_pipeline = pipeline("summarization", model="facebook/bart-large-cnn", device=0)
    # summarizer = HuggingFacePipeline(pipeline=summarization_pipeline)
    # refinement_pipeline = pipeline("summarization", model="facebook/bart-large", device=0)
    # refiner = HuggingFacePipeline(pipeline=refinement_pipeline)
    # refinement_prompt = PromptTemplate.from_template("Provide a brief summary for the following news article:\n{article_content}")
    # summary_chain = refinement_prompt | summarizer | refiner
    # return summary_chain


def get_article_contents(API_KEY, CATEGORY):
    if CATEGORY == 'default':
        URL = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={API_KEY}'
    else:
        URL = f'https://newsapi.org/v2/top-headlines?category={CATEGORY}&apiKey={API_KEY}'
    response = requests.get(URL)
    data = response.json()
    article_contents = fetch_article_data(data)
    # number_of_runs = 1
    # while len(article_contents) < MAX_ENTRIES:
    #     first_article_index = number_of_runs * MAX_ENTRIES
    #     run_data = fetch_article_data(data, first_article_index, MAX_ENTRIES+run_data[2]) # error, 
    #     number_of_runs+=1
    #     article_contents.update(run_data[0])
    return article_contents

def fetch_article_data(DATA):
    download_successes = 0
    # download_fails = 0
    article_data = {}
    articles = DATA['articles'] # fetching a list consisting of data for each article: description, title, url, etc.
    for article in articles:
        if download_successes < MAX_ENTRIES:
            article_title = article['title']
            article_url = article['url']
            article_author = article['author']
            article_source = article['source']['name']
            article_image = article['urlToImage']
            try:
                art = Article(article_url)
                art.download()
                art.parse()
                # content = art.text
                # word_list = content.split()
                # if (len(word_list) > 121):
                article_data[article_title] = article_data[article_title] = {'text': art.text, 'author': article_author, 'source': article_source, 'image': article_image}
                download_successes+=1
                # else:
                #     download_fails+=1
            except Exception as e:
                print(f'Could not fetch content for Article: {article_title}. Error {e}')
                # download_fails+=1
        else:
            break
    return article_data


def summarize_article(article_text):
    # summary_chain = generate_summary_chain()
    # summary = summary_chain.invoke({'article_content': article_text})
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    summary = summarizer(article_text, max_length=MAXIMUM_SUMMARY_LENGTH, min_length=MINIMUM_SUMMARY_LENGTH, do_sample=False)
    return summary

def get_summaries(ARTICLE_CONTENTS):
    summaries = []
    for title, data in ARTICLE_CONTENTS.items():
        content = data['text']
        content = content[:1024]
        summarized_content = summarize_article(content)[0]['summary_text']
        summary = {}
        summary['title'] = title
        summary['summary'] = summarized_content
        summary['author'] = data['author']
        summary['source'] = data['source']
        summary['image'] = data['image']
        summaries.append(summary)
    return summaries

load_dotenv()
api_key = os.getenv('NEWS_API_KEY')
category = 'entertainment'
articles = get_article_contents(api_key, category)
print(get_summaries(articles))
        
