"""Optional local Streamlit research UI. It never connects to the decision registry.

Run: pip install -r requirements-research-ui.txt
     streamlit run dashboard/vectorbt_research.py
"""
import io
import json

import pandas as pd
import streamlit as st

from lab.adapters.vbt_research import read_csv_prices, run_research, parameter_pairs

st.set_page_config(page_title="Quant Superlab | Research-only", layout="wide")
st.title("Quant Superlab · vectorbt independent research")
st.warning("RESEARCH ONLY — no ACCEPT verdict, no live orders, no registry mutation.")
st.caption("Provide a CSV containing Date and Close. Signals at close t fill at close t+1. "
           "Both engines use the same source prices; this is accounting parity, not independent market evidence.")

uploaded = st.file_uploader("Upload historical CSV (Date, Close)", type="csv")
c1, c2, c3, c4 = st.columns(4)
with c1:
    fast_min = st.number_input("Fast start", 2, 300, 5)
    fast_max = st.number_input("Fast stop (inclusive)", 2, 300, 50)
    fast_step = st.number_input("Fast step", 1, 100, 5)
with c2:
    slow_min = st.number_input("Slow start", 2, 1000, 50)
    slow_max = st.number_input("Slow stop (inclusive)", 2, 1000, 250)
    slow_step = st.number_input("Slow step", 1, 100, 10)
with c3:
    fee = st.number_input("Fee per side (%)", 0.0, 10.0, 0.10, step=0.01) / 100
    slippage = st.number_input("Slippage per side (%)", 0.0, 10.0, 0.05, step=0.01) / 100
with c4:
    cash = st.number_input("Initial cash", 1.0, 100000000.0, 10000.0)
    tolerance = st.number_input("Maximum equity gap (%)", 0.0001, 10.0, 0.01) / 100

try:
    fasts = range(int(fast_min), int(fast_max) + 1, int(fast_step))
    slows = range(int(slow_min), int(slow_max) + 1, int(slow_step))
    trials = len(parameter_pairs(fasts, slows))
    st.caption(f"Pre-registered grid size: {trials} valid trials. Max 500.")
except ValueError as exc:
    st.error(str(exc))
    trials = 0

if st.button("Run exploration", disabled=uploaded is None or trials == 0):
    try:
        # Process uploaded bytes without writing the repository or decision files.
        raw = pd.read_csv(io.BytesIO(uploaded.getvalue()))
        if not {"Date", "Close"}.issubset(raw.columns):
            raise ValueError("CSV must have Date and Close columns")
        raw["Date"] = pd.to_datetime(raw["Date"], errors="raise", utc=True)
        prices = pd.Series(pd.to_numeric(raw["Close"], errors="coerce").to_numpy(),
                           index=raw["Date"].dt.tz_localize(None), name="Close")
        frame, summary = run_research(prices, fasts, slows, fee, slippage,
                                      initial_cash=cash, tolerance=tolerance)
        st.metric("Trials", summary["trial_count"])
        st.metric("Engine agreement", "PASS" if summary["all_engines_agree"] else "FAIL")
        st.metric("Maximum equity gap", f'{summary["max_equity_gap_pct_of_initial"]:.6f}%')
        if not summary["all_engines_agree"]:
            st.error("Engine discrepancy detected. Results cannot be trusted until reconciled.")
        st.dataframe(frame, use_container_width=True)
        pivot = frame.pivot(index="fast", columns="slow", values="sharpe")
        st.caption("Exploratory in-sample Sharpe grid (not a selection recommendation)")
        st.dataframe(pivot.style.background_gradient(axis=None), use_container_width=True)
        st.download_button("Download full trials CSV", frame.to_csv(index=False),
                           "vbt_research.csv", "text/csv")
        st.download_button("Download limitations and assumptions JSON",
                           json.dumps(summary, indent=2), "vbt_research.json", "application/json")
    except Exception as exc:
        st.error(f"Research could not complete: {exc}")
