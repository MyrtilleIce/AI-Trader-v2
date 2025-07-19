"""Optional ML model for ai_trader."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from sklearn.linear_model import LinearRegression


class SimpleModel:
    """Very basic model predicting next close price using linear regression."""

    def __init__(self, model_path: str = "model.pkl") -> None:
        self.model_path = Path(model_path)
        self.model = LinearRegression()
        self.log = logging.getLogger(self.__class__.__name__)
        if self.model_path.exists():
            self.load()

    def train(self, df: pd.DataFrame) -> None:
        if len(df) < 2:
            return
        X = df.index.values.reshape(-1, 1)
        y = df["close"].values
        self.model.fit(X, y)
        self.save()

    def predict(self, step: int) -> Optional[float]:
        try:
            return float(self.model.predict([[step]])[0])
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Prediction error: %s", exc)
            return None

    def save(self) -> None:
        import joblib

        joblib.dump(self.model, self.model_path)
        self.log.info("Model saved to %s", self.model_path)

    def load(self) -> None:
        import joblib

        self.model = joblib.load(self.model_path)
        self.log.info("Model loaded from %s", self.model_path)

