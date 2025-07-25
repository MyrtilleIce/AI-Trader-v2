"""Learning utilities including web research and optimisation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import keras
import openai
import optuna
import pandas as pd
import requests
from dotenv import dotenv_values
from keras.layers import Dense
from keras.models import Sequential


class Researcher:
    """Use SerpAPI and OpenAI to fetch and summarize trading tips."""

    def __init__(self, config_path: str = ".env") -> None:
        cfg = dotenv_values(config_path)
        self.serp_key = cfg.get("SERPAPI_KEY", "")
        openai.api_key = cfg.get("OPENAI_API_KEY", "")
        self.log = logging.getLogger(self.__class__.__name__)

    def search(self, query: str, num_results: int = 5) -> List[str]:
        url = "https://serpapi.com/search.json"
        params = {"q": query, "num": num_results, "api_key": self.serp_key}
        try:
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
            return [item.get("snippet", "") for item in data.get("organic_results", [])]
        except Exception as exc:  # noqa: BLE001
            self.log.error("Search failed: %s", exc)
            return []

    def summarize(self, texts: List[str]) -> str:
        prompt = "\n".join(texts)
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
            )
            return completion.choices[0].message["content"]
        except Exception as exc:  # noqa: BLE001
            self.log.error("Summarization failed: %s", exc)
            return ""


class AutoOptimizer:
    """Simple daily Optuna optimisation of strategy parameters."""

    def __init__(self, trials: int = 50) -> None:
        self.trials = trials
        self.log = logging.getLogger(self.__class__.__name__)

    def optimise(self, data: pd.DataFrame) -> None:
        def objective(trial: optuna.Trial) -> float:
            threshold = trial.suggest_float("threshold", 0.1, 1.0)  # noqa: F841
            window = trial.suggest_int("window", 10, 50)  # noqa: F841
            # TODO: backtest with given parameters
            return 0.0

        try:
            study = optuna.create_study(direction="maximize")
            study.optimize(objective, n_trials=self.trials)
            self.log.info("Best params: %s", study.best_params)
        except Exception as exc:  # noqa: BLE001
            self.log.error("Optimisation failed: %s", exc)


class DenseModel:
    """Optional neural network for short-term prediction."""

    def __init__(self, input_dim: int, model_path: str = "model.h5") -> None:
        self.model_path = model_path
        self.model = Sequential(
            [Dense(32, activation="relu", input_shape=(input_dim,)), Dense(1)]
        )
        self.model.compile(optimizer="adam", loss="mse")
        self.log = logging.getLogger(self.__class__.__name__)
        if Path(self.model_path).exists():
            self.load()

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        self.model.fit(X, y, epochs=10, verbose=0)
        self.save()

    def predict(self, X: pd.DataFrame) -> List[float]:
        return self.model.predict(X, verbose=0).flatten().tolist()

    def save(self) -> None:
        self.model.save(self.model_path)
        self.log.info("Model saved to %s", self.model_path)

    def load(self) -> None:
        self.model = keras.models.load_model(self.model_path)
        self.log.info("Model loaded from %s", self.model_path)
