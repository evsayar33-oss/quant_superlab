"""Crypto core: simple literature rules with FIXED settings (no grid search). Same rules as lab/core.py
(config/core.yaml) so the decision gate judges exactly what the core study showed.
Long or cash per asset, equal capital per asset. Weights use closes up to t; the engine trades them at t+1."""
from __future__ import annotations

import pandas as pd

from lab import core
from lab.strategies import strategy


def _ppy(prices: pd.DataFrame) -> float:
    idx = prices.index
    yrs = (idx[-1] - idx[0]).total_seconds() / (365.25 * 86400) if len(idx) > 2 else 1
    return len(idx) / yrs if yrs > 0 else 365.0


def _weights(prices: pd.DataFrame, rule: str, prm: dict) -> pd.DataFrame:
    ppy = _ppy(prices)
    w = pd.DataFrame({c: core.exposure(prices[c], rule, prm, ppy) for c in prices.columns}, index=prices.index)
    n = prices.notna().sum(axis=1).replace(0, float("nan"))
    return w.div(n, axis=0).fillna(0.0)


@strategy("core_dual_trend_vt", grid={},
          defaults={"sma_days": 200, "horizons_days": (30, 90, 180), "target": 0.40, "lookback_days": 30},
          source="Faber (2007) SMA200 + Moskowitz, Ooi & Pedersen (2012) TSMOM + Moreira & Muir (2017) vol target",
          kind="time_series")
def core_dual_trend_vt(prices, sma_days, horizons_days, target, lookback_days):
    return _weights(prices, "dual_trend_vt", {"sma_days": sma_days, "horizons_days": list(horizons_days),
                                              "target": target, "lookback_days": lookback_days})


@strategy("core_tsmom_vt", grid={},
          defaults={"horizons_days": (30, 90, 180), "target": 0.40, "lookback_days": 30},
          source="Moskowitz, Ooi & Pedersen (2012); Liu & Tsyvinski (2021); Moreira & Muir (2017)",
          kind="time_series")
def core_tsmom_vt(prices, horizons_days, target, lookback_days):
    return _weights(prices, "tsmom_vt", {"horizons_days": list(horizons_days), "target": target,
                                         "lookback_days": lookback_days})


@strategy("core_dual_trend_vt_band", grid={},
          defaults={"sma_days": 200, "horizons_days": (30, 90, 180), "target": 0.40, "lookback_days": 30, "band": 0.10},
          source="H052 + 10% no-trade band (pre-registered variant V_band, config/core.yaml)",
          kind="time_series")
def core_dual_trend_vt_band(prices, sma_days, horizons_days, target, lookback_days, band):
    ppy = _ppy(prices)
    prm = {"sma_days": sma_days, "horizons_days": list(horizons_days), "target": target, "lookback_days": lookback_days}
    w = pd.DataFrame({c: core.apply_band(core.exposure(prices[c], "dual_trend_vt", prm, ppy), band)
                      for c in prices.columns}, index=prices.index)
    n = prices.notna().sum(axis=1).replace(0, float("nan"))
    return w.div(n, axis=0).fillna(0.0)
