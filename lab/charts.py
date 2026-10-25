"""PNG charts for reports (readable on a phone inside GitHub)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

INK, MUTED, ACC, BAD, GRID = "#1f2937", "#9ca3af", "#2563eb", "#dc2626", "#e5e7eb"


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID, "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False})
    return plt


def equity_dd(r: pd.Series, bench: pd.Series | None, path: Path, title: str) -> str:
    plt = _plt()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    eq = (1 + r.fillna(0)).cumprod()
    a1.plot(eq.index, eq, color=ACC, lw=1.4, label="strategy (OOS)")
    if bench is not None and len(bench):
        be = (1 + bench.reindex(r.index).fillna(0)).cumprod()
        a1.plot(be.index, be, color=MUTED, lw=1, label="equal-weight benchmark")
    a1.set_yscale("log"); a1.legend(frameon=False); a1.set_title(title, loc="left", color=INK)
    dd = eq / eq.cummax() - 1
    a2.fill_between(dd.index, dd, 0, color=BAD, alpha=0.35, lw=0)
    a2.set_ylabel("drawdown")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path.name


def monthly_heatmap(table: pd.DataFrame, path: Path) -> str:
    plt = _plt()
    t = table.drop(columns=["Year"], errors="ignore")
    fig, ax = plt.subplots(figsize=(8, 0.35 * len(t) + 1.2))
    v = np.nan_to_num(t.values.astype(float))
    lim = max(abs(v).max(), 1e-6)
    ax.imshow(v, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(t.shape[1]), [str(c) for c in t.columns])
    ax.set_yticks(range(t.shape[0]), [str(i) for i in t.index])
    for (i, j), x in np.ndenumerate(t.values.astype(float)):
        if np.isfinite(x):
            ax.text(j, i, f"{x * 100:.1f}", ha="center", va="center", fontsize=7, color=INK)
    ax.grid(False); ax.set_title("Monthly returns % (OOS)", loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path.name


def bar_dict(d: dict, path: Path, title: str, key: str = "sharpe") -> str:
    plt = _plt()
    items = [(k, v[key] if isinstance(v, dict) else v) for k, v in d.items() if isinstance(v, (dict, int, float))]
    items = [(k, x) for k, x in items if x is not None]
    fig, ax = plt.subplots(figsize=(8, 0.3 * len(items) + 1))
    ax.barh([str(k) for k, _ in items], [x for _, x in items], color=[ACC if x >= 0 else BAD for _, x in items])
    ax.set_title(title, loc="left"); fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path.name


def exit_heatmap(table: pd.DataFrame, path: Path) -> str | None:
    if table is None or table.empty:
        return None
    plt = _plt()
    best_hold = table.groupby("max_hold")["t"].max().idxmax()
    t = table[table["max_hold"] == best_hold].copy()
    t["stop"] = t["stop"].fillna(0).map(lambda x: "none" if x == 0 else f"{x:.0%}")
    t["target"] = t["target"].fillna(0).map(lambda x: "none" if x == 0 else f"{x:.0%}")
    pv = t.pivot_table(index="stop", columns="target", values="mean")
    fig, ax = plt.subplots(figsize=(6, 4))
    v = pv.values.astype(float)
    lim = max(np.nanmax(abs(v)), 1e-6)
    ax.imshow(v, cmap="RdBu", vmin=-lim, vmax=lim)
    ax.set_xticks(range(pv.shape[1]), pv.columns); ax.set_yticks(range(pv.shape[0]), pv.index)
    for (i, j), x in np.ndenumerate(v):
        ax.text(j, i, f"{x * 100:.2f}", ha="center", va="center", fontsize=7)
    ax.set_xlabel("take-profit"); ax.set_ylabel("stop-loss"); ax.grid(False)
    ax.set_title(f"Avg trade % after costs, max hold {best_hold} bars", loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path.name


def holding_curve(es: dict, path: Path) -> str | None:
    ks = [k for k in es if isinstance(k, int)]
    if not ks:
        return None
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(ks, [es[k]["mean"] * 100 for k in ks], marker="o", color=ACC)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_xlabel("bars held after signal"); ax.set_ylabel("avg return %")
    ax.set_title("Event study: when does the edge peak?", loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path.name
