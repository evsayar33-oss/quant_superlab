"""Prospective H118 decision diagnostics; never change frozen H117 signals.

Describes *necessary* conditions for trade candidates on fully closed bars.
Where a band/rebalance state could suppress a candidate, the exact mechanism
is labelled unresolved rather than misrepresented as a proven cause.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

ASSETS=("BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT")
MODELS=("mom2_baseline","regime_band30","regime_7d_band20")


def explain(closes: pd.DataFrame, targets: dict) -> dict:
    if len(closes)<1201 or not set(ASSETS).issubset(closes.columns):
        raise ValueError("H118_DIAGNOSTIC_HISTORY_SHORT")
    if closes[list(ASSETS)].isna().any().any() or (closes[list(ASSETS)]<=0).any().any():
        raise ValueError("H118_DIAGNOSTIC_BAD_HISTORY")
    returns=closes[list(ASSETS)].pct_change(fill_method=None)
    vol=returns.rolling(180,min_periods=90).std()*math.sqrt(365.25*6)
    above=closes[list(ASSETS)]>closes[list(ASSETS)].rolling(1200,min_periods=1200).mean()
    votes=sum((closes[list(ASSETS)]>closes[list(ASSETS)].shift(n*6)).astype(int)
              for n in (30,90,180))
    s90=closes[list(ASSETS)].pct_change(540,fill_method=None)
    base_ok=(vol>1e-8)&above&(votes>=2)
    regime=bool(above["BTCUSDT"].iloc[-1] and s90["BTCUSDT"].iloc[-1]>0)
    eligible_pair=[a for a in ASSETS[:2] if bool(base_ok[a].iloc[-1])]
    eligible_rotation=[a for a in ASSETS if bool(base_ok[a].iloc[-1])
                       and pd.notna(s90[a].iloc[-1])]
    reasons={}
    for model in MODELS:
        if model not in targets or set(targets[model])!=set(ASSETS):
            raise ValueError("H118_MISSING_MODEL_TARGETS:"+model)
        weights=targets[model]
        if any(not math.isfinite(float(x)) or float(x)<0 for x in weights.values()):
            raise ValueError("H118_INVALID_SIGNAL_TARGET:"+model)
        if any(float(v)>0 for v in weights.values()):
            reason="ACTIVE_TARGET"
        elif model=="mom2_baseline":
            reason=("NO_ELIGIBLE_BTC_ETH" if not eligible_pair
                    else "BASELINE_BAND_OR_OTHER_SIGNAL_GATE")
        elif not regime:
            reason="BTC_REGIME_OFF"
        elif not eligible_rotation:
            reason="NO_ELIGIBLE_ROTATION_ASSET"
        else:
            reason="BAND_OR_REBALANCE_ZERO_UNRESOLVED"
        reasons[model]={"reason":reason,
                        "target_exposure":round(sum(float(v) for v in weights.values()),8)}
    return {"version":1,"diagnostic_only":True,
            "btc_regime_on":regime,
            "btc_above_sma200":bool(above["BTCUSDT"].iloc[-1]),
            "btc_90d_positive":bool(s90["BTCUSDT"].iloc[-1]>0),
            "eligible_mom2_assets":eligible_pair,
            "eligible_rotation_assets":eligible_rotation,
            "momentum_votes":{a:int(votes[a].iloc[-1]) for a in ASSETS},
            "models":reasons}
