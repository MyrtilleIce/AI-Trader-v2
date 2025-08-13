"""Placeholder news/sentiment API interface."""

from __future__ import annotations

from typing import List, Dict


def get_news() -> List[Dict]:
    """Return a list of news items.

    This is a stub implementation returning static data. Real integrations could
    fetch from an external API.
    """

    return [
        {
            "title": "Market update",
            "source": "placeholder",
            "sentiment": "neutral",
            "url": "https://example.com/news/1",
        }
    ]
