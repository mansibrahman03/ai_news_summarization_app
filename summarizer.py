"""Process-wide summarization pipeline, built on first use.

Constructing the pipeline downloads ~1.6GB of weights and holds a couple of GB
resident, so it must never be built at import time (that blocks startup before
the port binds) and never more than once per process.
"""
import os
from threading import Lock

MODEL_NAME = os.getenv('SUMMARIZER_MODEL', 'facebook/bart-large-cnn')

_summarizer = None
_lock = Lock()


def get_summarizer():
    global _summarizer
    if _summarizer is None:
        with _lock:
            if _summarizer is None:
                from transformers import pipeline
                print(f'Loading summarization model {MODEL_NAME}...')
                _summarizer = pipeline('summarization', model=MODEL_NAME)
                print('Summarization model loaded.')
    return _summarizer
