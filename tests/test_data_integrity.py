"""Regression: missing Yahoo instruments must not alter the paper-trading universe."""
import sys
from types import SimpleNamespace
import pandas as pd
import pytest
from lab import data, watch


def test_watch_rejects_missing_assets():
    with pytest.raises(RuntimeError, match="PAPER_DATA_INCOMPLETE.*GC=F"):
        watch.require_full_watch_universe(["SI=F","HG=F"], ["GC=F","SI=F","HG=F"], "metals")
    watch.require_full_watch_universe(["GC=F","SI=F","HG=F"], ["GC=F","SI=F"], "metals")


def test_yahoo_serial_retry_recovers_partial_batch(monkeypatch):
    idx = pd.date_range("2026-11-10", periods=3)
    base = pd.DataFrame({x:[10.,11.,12.] for x in
        ["Open","High","Low","Close","Volume"]}, index=idx)
    calls = []
    def download(request, **kwargs):
        assert kwargs["threads"] is False
        tickers = [request] if isinstance(request,str) else list(request)
        calls.append(tickers)
        if tickers == ["GC=F"]:
            return pd.concat({"GC=F":base},axis=1)
        return pd.concat({"SI=F":base},axis=1)
    monkeypatch.setitem(sys.modules,"yfinance",SimpleNamespace(download=download))
    monkeypatch.setattr(data.time,"sleep",lambda _: None)
    result=data._yf_download(["GC=F","SI=F"],"2026-11-01")
    assert set(result)=={"GC=F","SI=F"}
    assert len(result["GC=F"])==3
    assert ["GC=F"] in calls


def test_yahoo_missing_asset_never_imputed(monkeypatch):
    idx=pd.date_range("2026-11-10",periods=3)
    base=pd.DataFrame({x:[1.,2.,3.] for x in
        ["Open","High","Low","Close","Volume"]},index=idx)
    def download(request, **kwargs):
        tickers=[request] if isinstance(request,str) else list(request)
        return pd.concat({"SI=F":base},axis=1) if "SI=F" in tickers else pd.DataFrame()
    monkeypatch.setitem(sys.modules,"yfinance",SimpleNamespace(download=download))
    monkeypatch.setattr(data.time,"sleep",lambda _: None)
    result=data._yf_download(["GC=F","SI=F"],"2026-11-01")
    assert set(result)=={"SI=F"}
