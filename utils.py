# utils.py
import feedparser
from newspaper import Article

DEFAULT_RSS = [
    'https://rss.cnn.com/rss/edition.rss',
    'http://feeds.reuters.com/reuters/topNews',
]


def collect_feed_items(feeds=None, max_per_feed=5):
    feeds = feeds or DEFAULT_RSS
    items = []
    for f in feeds:
        feed = feedparser.parse(f)
        for e in feed.entries[:max_per_feed]:
            items.append({'title': e.get('title'), 'link': e.get('link'), 'summary': e.get('summary', '')})
    # naive dedupe by link
    seen = set()
    filtered = []
    for it in items:
        if it['link'] in seen:
            continue
        seen.add(it['link'])
        filtered.append(it)
    return filtered


def fetch_full_article(url, timeout=20):
    a = Article(url)
    a.download()
    a.parse()
    title = a.title
    text = a.text
    return title, text
