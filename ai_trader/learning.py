"""Automatic strategy improvement via web research."""

from __future__ import annotations

import logging
from typing import List

import openai
import requests
from dotenv import dotenv_values


class Researcher:
    """Use SerpAPI and OpenAI to fetch and summarize trading tips."""

    def __init__(self, config_path: str = ".env") -> None:
        cfg = dotenv_values(config_path)
        self.serp_key = cfg.get("SERPAPI_KEY", "")
        openai.api_key = cfg.get("OPENAI_API_KEY", "")
        self.log = logging.getLogger(self.__class__.__name__)

    def search(self, query: str, num_results: int = 5) -> List[str]:
        """Search Google and return result snippets."""
        url = "https://serpapi.com/search.json"
        params = {"q": query, "num": num_results, "api_key": self.serp_key}
        try:
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
            return [item.get("snippet", "") for item in data.get("organic_results", [])]
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Search failed: %s", exc)
            return []

    def summarize(self, texts: List[str]) -> str:
        """Summarize texts using OpenAI."""
        prompt = "\n".join(texts)
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
            )
            return completion.choices[0].message["content"]
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Summarization failed: %s", exc)
            return ""

