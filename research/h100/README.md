# H100 — Cross-venue robustness audit (research only)

H099 returned 12 independent venue/timeframe/symbol comparison sets and 3,998 **configuration-level matched trade records**. Those are not 3,998 unique trades, and H099 did not establish profitability.

H100 evaluates the **fixed H099 1R, assumed 20 bps round-trip** research specification across the three reachable independent perpetual venues: Gate, Bitget, and MEXC. Binance and Bybit remain in the refreshed H099 input as diagnostics but are not required to pass H100's predeclared screen.

## Fixed screen (no winner selection)
- 2 symbols × 2 timeframes × 6 event families × 2 sides × 2 parent cohorts = **96 configuration cells**.
- Require all **3** independent venues, at least **30 matched trades per venue per configuration**, and >= **50%** exact entry-time match rate to primary OKX trades.
- Report per-venue matched sample, mean assumed net R, match rate, moving-block-bootstrap descriptive interval, worst venue mean, median venue mean and the count of positive venues.
- Mark a cell `DESCRIPTIVE_CONSISTENT_POSITIVE` only if all three means are positive; a positive bootstrap lower bound is displayed separately. **Neither status is alpha approval.**
- Inaccessible venues, thin samples, missing intervals, invalid or absent data fail closed. No imputation, no cherry-picking accessible winners, no changes to production or H089.

## Critical evidence limitations
1. **No true untouched OOS**: H100 reuses H099 historical data; independent venues observe the same global crypto market. Historical cross-venue replication is not fresh prospective evidence.
2. **No execution cost stress**: H099 stores net R at 20 bps but omits per-trade entry price/risk; extra bps cannot be reliably converted to R from the summary alone. H100 explicitly returns `NOT_TESTABLE_FROM_H099_SUMMARY_REQUIRES_TRADE_LEVEL_ENTRY_RISK`, rather than fabricating a sensitivity result. A subsequent version must preserve trade-level risk/price and funding settlement observations.
3. **No multiple-testing corrected significance**: the 96 cells overlap, trades are dependent, and H099's block-bootstrap is descriptive. Lower confidence limits are not valid familywise inference.
4. **Inherited H096 limitation**: the `all` cohort still requires a known higher-timeframe parent event and is not unconditional. It is retained unchanged to avoid silently breaking comparability.

## Usage

```bash
python -m unittest discover -s research/h100 -p 'test_*.py' -v
python research/h099/run.py --pages 8 --out results/h099
python research/h100/run.py --source results/h099/summary.json --out results/h100/summary.json
```

After merge, run **H100 — Cross-venue robustness screen (read-only)** manually on main. Inspect `results/h100/summary.json` in the 90-day artifact. `alpha_accepted` remains false. No schedule is added, and H089 is unchanged.
