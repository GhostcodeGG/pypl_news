"""Summarization helpers for PayPal daily digest."""

from __future__ import annotations

import logging
from typing import Iterable, List

from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

LOGGER = logging.getLogger(__name__)
LANGUAGE = "english"


def summarize_text(text: str, sentence_count: int = 3) -> str:
    """Summarize an article body into a concise highlight."""

    parser = PlaintextParser.from_string(text, Tokenizer(LANGUAGE))
    summarizer = LsaSummarizer(Stemmer(LANGUAGE))
    summarizer.stop_words = get_stop_words(LANGUAGE)

    sentences = summarizer(parser.document, sentence_count)
    summary = " ".join(str(sentence) for sentence in sentences).strip()
    if not summary:
        # Fall back to the opening of the article if summarizer fails.
        summary = " ".join(text.split()[:60])
    return summary


def batch_summarize(texts: Iterable[str], sentence_count: int = 3) -> List[str]:
    """Summarize multiple texts."""

    return [summarize_text(text, sentence_count=sentence_count) for text in texts]
