"""Forecasting models. Each takes a weekly series and a horizon and returns point forecasts.

Baselines   naive (last value) · drift (last value + average weekly change) · ma4 (mean of last 4 weeks)
            snaive (same week last year; seasonal series only)
Statistical ets   Holt's linear trend with damping (statsmodels ExponentialSmoothing)
            arima ARIMA(p,d,q), order chosen by AIC on a small grid
            dhr   dynamic harmonic regression: ARIMA errors + yearly Fourier terms (seasonal series only)
Combination ensemble = median of the statistical models + drift
"""

from __future__ import annotations

import warnings
from itertools import product

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

YEAR = 52.18


def naive(y: pd.Series, h: int, **_) -> np.ndarray:
    return np.repeat(y.iloc[-1], h)


def drift(y: pd.Series, h: int, **_) -> np.ndarray:
    # slope from the last 26 weeks so old regimes don't dominate
    tail = y.iloc[-26:]
    slope = (tail.iloc[-1] - tail.iloc[0]) / max(len(tail) - 1, 1)
    return y.iloc[-1] + slope * np.arange(1, h + 1)


def ma4(y: pd.Series, h: int, **_) -> np.ndarray:
    return np.repeat(y.iloc[-4:].mean(), h)


def snaive(y: pd.Series, h: int, **_) -> np.ndarray:
    if len(y) < 53:
        return naive(y, h)
    # same week last year, shifted to today's level (avoids the yearly level change dominating)
    base = y.iloc[-52: -52 + h].to_numpy() if h < 52 else y.iloc[-52:].to_numpy()
    return y.iloc[-1] + (base - y.iloc[-53])


def ets(y: pd.Series, h: int, **_) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    m = ExponentialSmoothing(y.to_numpy(), trend="add", damped_trend=True, initialization_method="estimated")
    return np.asarray(m.fit(optimized=True).forecast(h))


def select_arima_order(y: pd.Series) -> tuple[int, int, int]:
    from statsmodels.tsa.arima.model import ARIMA

    best, best_aic = (0, 1, 1), np.inf
    for p, q in product(range(3), range(3)):
        try:
            aic = ARIMA(y.to_numpy(), order=(p, 1, q)).fit().aic
        except Exception:
            continue
        if aic < best_aic:
            best, best_aic = (p, 1, q), aic
    return best


def arima(y: pd.Series, h: int, order=(1, 1, 1), **_) -> np.ndarray:
    from statsmodels.tsa.arima.model import ARIMA

    return np.asarray(ARIMA(y.to_numpy(), order=order).fit().forecast(h))


def fourier(n_start: int, n: int, k: int = 2) -> np.ndarray:
    t = np.arange(n_start, n_start + n)
    cols = []
    for i in range(1, k + 1):
        cols += [np.sin(2 * np.pi * i * t / YEAR), np.cos(2 * np.pi * i * t / YEAR)]
    return np.column_stack(cols)


def dhr(y: pd.Series, h: int, **_) -> np.ndarray:
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    if len(y) < 60:
        return arima(y, h)
    X = fourier(0, len(y))
    m = SARIMAX(y.to_numpy(), exog=X, order=(1, 1, 1), trend="n").fit(disp=False)
    return np.asarray(m.forecast(h, exog=fourier(len(y), h)))


BASELINES = {"naive": naive, "drift": drift, "ma4": ma4}
STATISTICAL = {"ets": ets, "arima": arima}
SEASONAL = {"snaive": snaive, "dhr": dhr}


def model_set(seasonal: bool) -> dict:
    m = {**BASELINES, **STATISTICAL}
    if seasonal:
        m.update(SEASONAL)
    return m


def predict(name: str, y: pd.Series, h: int, seasonal: bool, order=(1, 1, 1)) -> np.ndarray:
    if name == "ensemble":
        parts = [predict(n, y, h, seasonal, order) for n in (["ets", "arima", "drift"] + (["dhr"] if seasonal else []))]
        return np.median(np.vstack(parts), axis=0)
    fn = model_set(seasonal)[name]
    try:
        out = fn(y, h, order=order)
    except Exception:
        out = naive(y, h)
    return np.clip(np.asarray(out, dtype=float), 0, None)
