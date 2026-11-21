"""Reference next-open fills with backtesting.py, using one share per position."""
import numpy as np
from backtesting import Backtest, Strategy


def replay_positions(ohlc, orders, fee):
    """orders[i] is the signed unit position requested at close i for open i+1."""
    class Replay(Strategy):
        def init(self):
            pass

        def next(self):
            target = orders[len(self.data) - 1]
            if self.position.size == target:
                return
            self.position.close()
            if target > 0:
                self.buy(size=1)
            elif target < 0:
                self.sell(size=1)

    stats = Backtest(ohlc, Replay, cash=max(1e6, 10 * ohlc.High.max()),
                     commission=fee, trade_on_close=False).run()
    return stats["_trades"]


def audit_oos_fills(panel, trades, variants, exit_grid, costs, limit=12):
    """Replay sampled closed OOS market orders. Intrabar and partial exits need different models."""
    checked = []
    for trade in trades.itertuples(index=False, name=None):
        row = dict(zip(trades.columns, trade))
        key = row["_variant"]
        config = exit_grid[variants[key].params["_exit"]]
        if config.partial_r or row["reason"] not in {"signal", "reversal", "time", "ma_trail"}:
            continue
        asset = row["asset"]
        first, last = panel.o.index.get_indexer([row["entry"], row["exit"]])
        if first < 2 or last <= first:
            continue
        import pandas as pd
        frame = pd.DataFrame({name: values[asset] for name, values in
                              (("Open", panel.o), ("High", panel.h), ("Low", panel.l), ("Close", panel.c))}
                             ).iloc[first-2:last+1]
        if frame.isna().any().any():
            continue
        side = int(row["side"])
        orders = np.zeros(len(frame))
        orders[1:-2] = side
        fills = replay_positions(frame, orders, costs.per_turnover)
        if len(fills) != 1:
            raise ValueError("OOS reference replay missing round trip")
        fill = fills.iloc[0]
        expected_fee = (row["entry_px"] + row["exit_px"]) * costs.per_turnover
        if not (fill.EntryTime == row["entry"] and fill.ExitTime == row["exit"] and fill.Size == side
                and np.allclose([fill.EntryPrice, fill.ExitPrice, fill.Commission, fill.PnL],
                                [row["entry_px"], row["exit_px"], expected_fee,
                                 row["ret"] * row["entry_px"] - expected_fee], rtol=1e-8, atol=1e-9)):
            raise ValueError(f"OOS reference fill mismatch for {asset} at {row['entry']}")
        checked.append({"asset": asset, "entry": str(fill.EntryTime), "exit": str(fill.ExitTime), "side": side})
        if len(checked) == limit:
            break
    return {"status": "matched" if checked else "no_eligible_trades", "checked": checked,
            "scope": "unit market fills on recorded OOS order dates, excludes carry and partial exits"}
