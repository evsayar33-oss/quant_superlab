"""H114 genuinely new, predeclared multi-market daily next-open research.
Research only; all models use completed prior-session OHLCV. No broker orders.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from lab import data
P=Path(__file__).parent
VERSION="h114.new_signals.v1"
STOCKS=("AAPL","MSFT","NVDA","AMZN","GOOGL","META","JPM","V","XOM","JNJ","PG","MA","HD","AVGO","LLY","ABBV","MRK","PEP","KO","WMT","BAC","CVX","ORCL","CSCO","ADBE","CRM","NFLX","AMD","QCOM","CAT")
ETFS=("GLD","SLV","SPY","QQQ")
FUTURES={"GC=F":(100,.1),"SI=F":(5000,.005),"ES=F":(50,.25),"NQ=F":(20,.25)}
SINGLES=ETFS+tuple(FUTURES)
FAMILIES=("wick_reclaim","shock_absorption","trend_efficiency","squeeze_release","gap_repair","vol_state","failed_breakout")
STOCK_RULES=("residual_momentum","shock_recovery","gap_repair","defensive_efficiency","volatility_calm")
PORTFOLIOS={
 "metal_pair":("GLD","SLV"),
 "index_pair":("SPY","QQQ"),
 "four_asset":("GLD","SLV","SPY","QQQ"),
 "gold_equity":("GLD","SPY"),
 "silver_nasdaq":("SLV","QQQ"),
}
# Scenario fields are explicitly NOT exchange fills. Futures = assumed all-in
# commission per side USD + assumed ticks of adverse movement per side.
ETF_SCENARIOS={"optimistic":(1.0,1.5),"base":(3.0,1.5),"stress":(8.0,1.5),"double_stress":(16.0,1.5)}
FUTURE_SCENARIOS={"optimistic":(1,2.5),"base":(2,2.5),"stress":(4,2.5),"double_stress":(8,2.5)}
CUTS=(pd.Timestamp("2021-01-01"),pd.Timestamp("2024-01-01"),pd.Timestamp("2026-11-14"))
MIN_DAYS=500
def normalized(df):
 if not {"Open","High","Low","Close","Volume"}<=set(df.columns):raise ValueError("OHLCV_REQUIRED")
 x=df[["Open","High","Low","Close","Volume"]].copy()
 x.index=pd.DatetimeIndex(x.index).tz_localize(None).normalize()
 if x.index.duplicated().any():raise ValueError("DUPLICATE_BARS")
 x=x.sort_index()
 x=x.loc[(x.index>=pd.Timestamp("2015-01-01"))&(x.index<CUTS[-1])]
 if len(x)<MIN_DAYS or (x[["Open","High","Low","Close"]]<=0).any().any() or not np.isfinite(x.to_numpy(float)).all():
  raise ValueError("INCOMPLETE_OR_NONFINITE_OHLCV")
 return x
def sigs(b,allow_short=False):
 o,h,l,c=(b[v] for v in ("Open","High","Low","Close"))
 prev=c.shift(1);rng=(h-l).clip(lower=1e-10)
 vol=c.pct_change().rolling(21,min_periods=21).std()
 body=(c-o)/rng
 low_wick=(np.minimum(c,o)-l)/rng
 hi_wick=(h-np.maximum(c,o))/rng
 mid=(h+l)/2
 efficiency=(c-c.shift(21)).abs()/(c.diff().abs().rolling(21,min_periods=21).sum()+1e-10)
 r3=c.pct_change(3);r21=c.pct_change(21)
 vshort=c.pct_change().rolling(5).std();vlong=c.pct_change().rolling(35).std()
 range5=rng.rolling(5).mean();range35=rng.rolling(35).mean()
 hh=c.rolling(21).max().shift(1);ll=c.rolling(21).min().shift(1)
 # Seven unrelated, preregistered signal grammars (not tuned by results):
 signals={
  # failed downside auction, closing near top after a sharp lower wick
  "wick_reclaim":((low_wick>.55)&(body>0)&(c>c.rolling(60).mean())).astype(float),
  # shock recovers into rising long trend after large negative move
  "shock_absorption":((r3< -1.25*vol*np.sqrt(3))&(body>.4)&(r21>0)).astype(float),
  # steady directional efficiency and positive intermediate trend
  "trend_efficiency":((efficiency>.48)&(r21>0)&(c>c.rolling(100).mean())).astype(float),
  # range compression followed by expanded bullish candle
  "squeeze_release":((range5.shift(1)<.7*range35.shift(1))&(rng>1.3*range35)&(body>.45)).astype(float),
  # previous session's negative opening gap repaired at its close, enter next open
  "gap_repair":((o<prev*.995)&(c>prev)&(body>.3)).astype(float),
  # volatility state transition: short-term calm with positive drift
  "vol_state":((vshort<.7*vlong)&(r21>.01)&(c>c.rolling(100).mean())).astype(float),
  # upthrust above prior 21-day high failing at close, short only futures
  "failed_breakout":(-((h>hh)&(c<hh)&(hi_wick>.35)).astype(float) if allow_short else ((l<ll)&(c>ll)&(low_wick>.4)).astype(float))
 }
 for key in signals:
  signals[key]=signals[key].where(c.rolling(100,min_periods=100).mean().notna(),0.).fillna(0.)
 return signals
def net_daily(b,signals,scenario,fee_model):
 """Return series indexed by entry open date. Exit at following open.
 Signals computed at close d, entry at open d+1, next change at next open.
 Missing sessions are not filled or interpolated.
 """
 entry=b["Open"].iloc[1:-1]
 gross=(b["Open"].shift(-1)/b["Open"]-1).iloc[1:-1]
 pos=signals.shift(1).iloc[1:-1].fillna(0).astype(float)
 prev=pos.shift(1).fillna(0)
 turn=(pos-prev).abs()
 if fee_model=="future":
  ticks,commission=scenario
  multiplier,tick=FUTURES[b.attrs["ticker"]]
  per_side=(ticks*tick+commission/multiplier)/entry
 else:
  slip_bps,usd=scenario
  # $1.50 per side per $2000 ticket == 7.5bps; fixed ticket reference
  per_side=(slip_bps+usd/2000*10000)/10000
 net=pos*gross-turn*per_side
 last_close_cost=abs(float(pos.iloc[-1]))*float(per_side.iloc[-1] if hasattr(per_side,"iloc") else per_side)
 if len(net):net.iloc[-1]-=last_close_cost
 if not np.isfinite(net).all() or (net<=-1).any():raise ValueError("INVALID_RETURNS")
 return pd.DataFrame({"net":net,"gross":pos*gross,"pos":pos,"turn":turn,"unit_cost":per_side,
  "entry_open":entry},index=entry.index)
def metrics_frame(d):
 if d.empty:return {"n":0}
 s=d["net"];nav=(1+s).cumprod();sd=s.std(ddof=1)
 return {"n":len(d),"return":float(nav.iloc[-1]-1),"sharpe":float(np.sqrt(252)*s.mean()/sd) if sd>1e-12 else None,
  "max_dd":float((nav/nav.cummax()-1).min()),"avg_daily":float(s.mean()),
  "traded_days":int((d["turn"]>0).sum()),"turnover_sum":float(d["turn"].sum()),
  "active_days":int((d["pos"]!=0).sum())}
def bh(ps):
 v=np.asarray(ps,float);n=len(v);out=np.empty(n);order=np.argsort(v);cur=1.
 for k in range(n-1,-1,-1):
  cur=min(cur,v[order[k]]*n/(k+1));out[order[k]]=cur
 return out
def month_pvalue(d):
 # Calendar months; no treating correlated trading days as independent.
 m=d["net"].groupby(d.index.to_period("M")).sum()
 if len(m)<10 or m.std(ddof=1)<1e-10:return 1.
 return float(stats.ttest_1samp(m.to_numpy(),0,alternative="greater").pvalue)
def scope(d):
 names=("discovery","validation","reused_holdout")
 return {name:d.loc[(d.index>=pd.Timestamp("2015-01-01") if i==0 else d.index>=CUTS[i-1])&(d.index<CUTS[i])]
  for i,name in enumerate(names)}
def audit_single(asset,b,bench,records,store):
 b.attrs["ticker"]=asset
 families=sigs(b,allow_short=asset in FUTURES)
 costs=FUTURE_SCENARIOS if asset in FUTURES else ETF_SCENARIOS
 # All registered combinations, including failures and zero-trade rows.
 for fam,signal in families.items():
  for cname,cfg in costs.items():
   d=net_daily(b,signal,cfg,"future" if asset in FUTURES else "etf")
   parts=scope(d);m={p:metrics_frame(z) for p,z in parts.items()}
   pval=month_pvalue(parts["discovery"]) if cname=="base" else None
   bench_b=bench.loc[bench.index.intersection(d.index)]
   # Benchmark SPY open-to-next-open on matched days, not an investable NAV replica.
   bret=(bench["Open"].shift(-1)/bench["Open"]-1).reindex(d.index)
   matched=bret.notna()
   benchmark=float((1+bret[matched]).prod()-1) if matched.any() else None
   record={"family":"single","asset":asset,"rule":fam,"cost":cname,
    "total":metrics_frame(d),"splits":m,"p_discovery":pval,
    "benchmark_spy_return":benchmark,"benchmark_days":int(matched.sum()),
    "real_fills_verified":False,"funding_roll_verified":False,
    "historical_reused":True,"accepted":False}
   records.append(record)
   if cname=="base":
    z=d[["net","gross","pos","turn"]].copy();z["asset"]=asset;z["rule"]=fam
    store.append(z.reset_index().rename(columns={"index":"date"}))
 return families
def audit_cross_assets(bars,records):
 # Fixed equal-dollar sleeves. Cash stays cash. No cherry-picked weights.
 for name,assets in PORTFOLIOS.items():
  for fam in FAMILIES:
   for cost,cfg in ETF_SCENARIOS.items():
    parts=[]
    for a in assets:
     b=bars[a].copy();b.attrs["ticker"]=a
     s=sigs(b)[fam]
     d=net_daily(b,s,cfg,"etf")
     parts.append(d[["net","pos","turn"]].rename(columns={x:f"{a}_{x}" for x in ("net","pos","turn")}))
    idx=parts[0].index
    for d in parts[1:]:idx=idx.intersection(d.index)
    if len(idx)<MIN_DAYS:continue
    joined=pd.concat([d.reindex(idx) for d in parts],axis=1)
    net=joined[[f"{a}_net" for a in assets]].mean(axis=1)
    pos=joined[[f"{a}_pos" for a in assets]].abs().mean(axis=1)
    turn=joined[[f"{a}_turn" for a in assets]].mean(axis=1)
    d=pd.DataFrame({"net":net,"pos":pos,"turn":turn})
    m={k:metrics_frame(v) for k,v in scope(d).items()}
    records.append({"family":"multi_asset","asset":name,"rule":fam,"cost":cost,
     "total":metrics_frame(d),"splits":m,"p_discovery":month_pvalue(scope(d)["discovery"]) if cost=="base" else None,
     "real_fills_verified":False,"historical_reused":True,"accepted":False})
def stock_portfolios(bars,records,stock_store):
 # Cross-sectional stock signals: screen solely with information known at previous close.
 available=[a for a in STOCKS if a in bars]
 if len(available)<25:raise ValueError("INSUFFICIENT_US_STOCK_COVERAGE")
 spy=bars["SPY"];idx=spy.index
 aligned={}
 for a in available:
  q=bars[a].reindex(idx)
  if q[["Open","Close"]].isna().mean().max()>.12:continue
  aligned[a]=q
 if len(aligned)<25:raise ValueError("STOCK_DATA_GAPS")
 opens=pd.DataFrame({a:q["Open"] for a,q in aligned.items()})
 closes=pd.DataFrame({a:q["Close"] for a,q in aligned.items()})
 ret=closes.pct_change(fill_method=None)
 spyret=spy["Close"].pct_change(fill_method=None)
 vol=ret.rolling(21,min_periods=21).std()
 signals={
 "residual_momentum":ret.sub(spyret,axis=0).rolling(63,min_periods=63).sum()/vol.replace(0,np.nan),
 "shock_recovery":(closes/opens-1)*(-ret.rolling(3,min_periods=3).sum().shift(1))/vol.replace(0,np.nan),
 "gap_repair":(closes/opens-1)-(opens/closes.shift(1)-1),
 "defensive_efficiency":closes.pct_change(42,fill_method=None)/vol.replace(0,np.nan),
 "volatility_calm":closes.pct_change(21,fill_method=None)/(vol+1e-6)
 }
 eligibility=(closes>closes.rolling(200,min_periods=200).mean())&(opens>0)
 for rule,score in signals.items():
  # At close t choose top five *strictly by lagged information*. No future winners.
  ranks=score.where(eligibility).rank(axis=1,ascending=False,method="first")
  w=(ranks<=5).astype(float)
  w=w.div(w.sum(axis=1).replace(0,np.nan),axis=0).fillna(0)
  held=w.shift(1).iloc[1:-1].fillna(0)
  r=(opens.shift(-1)/opens-1).iloc[1:-1]
  valid=held.notna()&r.notna()
  weights=held.where(valid,0)
  # Keep missing-open equities unallocated rather than replacing with a future price
  turn=(weights-weights.shift(1).fillna(0)).abs().sum(axis=1)
  gross=(weights*r.fillna(0)).sum(axis=1)
  for cname,(slip,usd) in ETF_SCENARIOS.items():
   cost=(slip+usd/2000*10000)/10000
   net=gross-turn*cost
   if len(net):net.iloc[-1]-=weights.iloc[-1].abs().sum()*cost
   d=pd.DataFrame({"net":net,"pos":weights.abs().sum(axis=1),"turn":turn})
   m={k:metrics_frame(v) for k,v in scope(d).items()}
   benchmark=(spy["Open"].shift(-1)/spy["Open"]-1).reindex(d.index)
   excess=(net-benchmark)
   excess_d=pd.DataFrame({"net":excess.fillna(0.)},index=d.index)
   p_excess=month_pvalue(scope(excess_d)["discovery"]) if cname=="base" else None
   if cname=="base":
    stock_store.append(pd.DataFrame({"date":d.index,"rule":rule,"net":net.to_numpy(),
     "spy_open_to_open":benchmark.to_numpy(),"net_minus_spy":excess.to_numpy(),
     "turn":turn.to_numpy(),"pos":d["pos"].to_numpy()}))
   records.append({"family":"us_stock_cross_section","asset":"US30","rule":rule,"cost":cname,
    "total":metrics_frame(d),"splits":m,
    "p_discovery":month_pvalue(scope(d)["discovery"]) if cname=="base" else None,
    "p_discovery_vs_spy":p_excess,
    "benchmark_spy_return":float((1+benchmark.dropna()).prod()-1),
    "stocks_loaded":len(aligned),"historical_reused":True,"accepted":False,
    "survivorship_point_in_time_verified":False})
def main():
 p=argparse.ArgumentParser();p.add_argument("--out",default="results/h114");p.add_argument("--start",default="2015-01-01")
 args=p.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 symbols=list(dict.fromkeys(list(SINGLES)+list(STOCKS)))
 raw=data.load_ohlcv(symbols,args.start,"1d")
 bars={};errors={}
 for a in symbols:
  try:bars[a]=normalized(raw[a])
  except Exception as e:errors[a]=str(e)
 if any(s not in bars for s in SINGLES):raise RuntimeError("MISSING_REQUIRED_MARKET:"+str(errors))
 if len([a for a in STOCKS if a in bars])<25:raise RuntimeError("MISSING_STOCK_COVERAGE:"+str(errors))
 records=[];store=[];stock_store=[]
 for a in SINGLES:audit_single(a,bars[a],bars["SPY"],records,store)
 audit_cross_assets(bars,records)
 stock_portfolios(bars,records,stock_store)
 # BH adjustment across ALL registered base-cost family variants, not only the winners.
 base=[r for r in records if r["cost"]=="base"]
 q=bh([r["p_discovery"] for r in base])
 verdict={}
 for r,z in zip(base,q):
  r["q_all_base_bh"]=float(z)
  verdict[(r["family"],r["asset"],r["rule"])]=float(z)
 for r in records:
  r["q_all_base_bh"]=verdict[(r["family"],r["asset"],r["rule"])]
  s=r["splits"];r["positive_all_three"]=all(s[x].get("avg_daily",0)>0 and s[x].get("active_days",0)>=15
   for x in ("discovery","validation","reused_holdout"))
  r["research_watch"]=bool(r["positive_all_three"] and r["q_all_base_bh"]<=.10
    and r["total"]["traded_days"]>=30 and r["cost"] in ("base","stress"))
  # No historical selection is allowed to turn research results into certified alpha.
  r["alpha_accepted"]=False
 for r in records:
  if r["cost"]=="base" and r["research_watch"]:
   peer=[v for v in records if (v["family"],v["asset"],v["rule"])==(r["family"],r["asset"],r["rule"]) and v["cost"]=="stress"]
   r["stress_survives"]=bool(peer and peer[0]["positive_all_three"])
 result={"schema":VERSION,"run_scope":"new_signals_not_H083_repricing",
  "data_source":"Yahoo/yfinance historical adjusted research proxies via lab.data",
  "start_date":args.start,"last_complete_day":"2026-11-13",
  "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  "models":len(base),"scenario_rows":len(records),"markets":list(SINGLES),
  "us_stocks_requested":len(STOCKS),"us_stocks_loaded":len([x for x in STOCKS if x in bars]),
  "source_errors":errors,"research_watch_base":[{"family":r["family"],"asset":r["asset"],"rule":r["rule"],"q":r["q_all_base_bh"],"stress_survives":r.get("stress_survives",False)} for r in base if r["research_watch"]],
  "positive_three_base":sum(x["positive_all_three"] for x in base),
  "positive_three_stress":sum(x["positive_all_three"] for x in records if x["cost"]=="stress"),
  "verified_prospective":False,"real_execution_verified":False,"alpha_accepted":False,
  "limitations":["Historical research, all 2026 and earlier results are reused; no fresh sealed OOS",
    "Yahoo OHLCV can be survivorship-adjusted, restated and incomplete for delisted stocks",
    "Open-to-next-open fills are optimistic price proxies, not guaranteed executable",
    "Futures continuous =F contract rolls, contract mapping, margin and expiry costs unknown",
    "Futures tick slippage and commission are assumed per contract; not broker invoice",
    "ETF fee $1.50 per side per $2k ticket and assumed slippage may not match user broker",
    "Open gaps, overnight news, order rejections and intra-session liquidity remain unverified",
    "Many models tested: BH across entire family, not a discovery significance guarantee"]}
 stocks=[r for r in base if r["family"]=="us_stock_cross_section"]
 q_stock=bh([r["p_discovery_vs_spy"] for r in stocks])
 result["stock_vs_spy_discovery"]=[{"rule":r["rule"],"p":r["p_discovery_vs_spy"],
   "q_five_stock_bh":float(z),"benchmark_spy_total":r["benchmark_spy_return"],
   "strategy_total":r["total"]["return"],"positive_all_three":r["positive_all_three"]}
  for r,z in zip(stocks,q_stock)]
 (out/"summary.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
 (out/"all_models.json").write_text(json.dumps(records,indent=2,allow_nan=False)+"\n")
 rows=[]
 for r in records:
  row_base={k:r[k] for k in ("family","asset","rule","cost","positive_all_three","research_watch","q_all_base_bh","alpha_accepted")}
  for k in ("discovery","validation","reused_holdout","total"):
   row={**row_base,"split":k,**r["splits"].get(k,r["total"] if k=="total" else {})}
   rows.append(row)
 pd.DataFrame(rows).to_csv(out/"results_by_split.csv",index=False)
 pd.DataFrame(store,columns=["date","net","gross","pos","turn","asset","rule"]).to_csv(out/"base_single_daily_returns.csv",index=False) if not store else pd.concat(store,ignore_index=True).to_csv(out/"base_single_daily_returns.csv",index=False)
 if stock_store:pd.concat(stock_store,ignore_index=True).to_csv(out/"stock_strategy_daily_vs_spy.csv",index=False)
 (out/"report_tr.md").write_text("# H114 — Yeni çoklu piyasa stratejileri\n\n"
 +"Önceki stratejilerin yeniden fiyatlandırılması **değildir**. "
 +"Tamamen yeni sinyal aileleriyle yeni tarihsel denemeler yapılmıştır.\n\n"
 +f"Deneme modeli: {len(base)}, maliyet senaryosu: {len(records)}, üç dönemde pozitif (base): {result['positive_three_base']}, üç dönemde pozitif (stress): {result['positive_three_stress']}.\n\n"
 +"## Araştırma izleme adayları\n\n"
 +("".join(f"- {r['family']} / {r['asset']} / {r['rule']}; q={r['q_all_base_bh']:.3f}; stress={r.get('stress_survives',False)}\n" for r in base if r["research_watch"]) or "Yok.\n")
 +"\n**Hiçbir strateji canlı işlem için kabul edilmedi.**\n")
 print(json.dumps({"models":len(base),"rows":len(records),"watch":len(result["research_watch_base"]),"positive_base":result["positive_three_base"]}))
 return result
if __name__=="__main__":main()
