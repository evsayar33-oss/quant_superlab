"""H115: immutable-rule, genuinely prospective, 180-calendar-day quote paper monitoring.

Never places orders. 30/90/180 checkpoints are diagnostics, not automatic approvals.
Underlying H114 research code is reused unchanged; no on-the-fly retuning.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.h114.research import STOCKS,ETFS,FUTURES,sigs
SCHEMA="h115.prospective.v1"
NY=ZoneInfo("America/New_York")
ARMS={
 "US30_residual_momentum":("stock","residual_momentum",tuple(STOCKS)),
 "US30_volatility_calm":("stock","volatility_calm",tuple(STOCKS)),
 "US30_defensive_efficiency":("stock","defensive_efficiency",tuple(STOCKS)),
 "US30_shock_recovery_CONTROL":("stock","shock_recovery",tuple(STOCKS)),
 "US30_gap_repair_CONTROL":("stock","gap_repair",tuple(STOCKS)),
 "SLV_wick_reclaim":("single","wick_reclaim",("SLV",)),
 "SPY_trend_efficiency":("single","trend_efficiency",("SPY",)),
 "GLD_vol_state_DIAGNOSTIC":("single","vol_state",("GLD",)),
 "QQQ_trend_efficiency_DIAGNOSTIC":("single","trend_efficiency",("QQQ",)),
 "ETF_index_pair_trend":("single","trend_efficiency",("SPY","QQQ")),
 "ETF_four_asset_trend":("single","trend_efficiency",("GLD","SLV","SPY","QQQ")),
 "ETF_metal_pair_wick":("single","wick_reclaim",("GLD","SLV")),
 "SI_gap_repair_FUTURES_DIAGNOSTIC":("single","gap_repair",("SI=F",)),
 "ES_trend_efficiency_FUTURES_DIAGNOSTIC":("single","trend_efficiency",("ES=F",))
}
SYMBOLS=tuple(dict.fromkeys((*ETFS,*STOCKS,"SI=F","ES=F")))
SCENARIOS=("base","stress","double_stress")
# Each asset's position is a fractional notional sleeve, not actual contract count.
ETF_BPS={"base":10.5,"stress":15.5,"double_stress":23.5}
FUTURE_COST={"base":(2,2.5),"stress":(4,2.5),"double_stress":(8,2.5)}
def canonical(v):return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def frozen():
 return {"schema":SCHEMA,"h114_sha":hashlib.sha256((ROOT/"research/h114/research.py").read_bytes()).hexdigest(),
  "h115_sha":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  "arms_hash":digest(ARMS),"scenarios":list(SCENARIOS),"markets":list(SYMBOLS),
  "benchmark":"SPY","checkpoints":[30,90,180]}
def seed(now_utc):
 started=now_utc.date().isoformat()
 return {"schema":SCHEMA,"started_at":now_utc.isoformat(),"started_date":started,
  "end_date":(now_utc+pd.Timedelta(days=180)).date().isoformat(),
  "freeze":frozen(),"records":[],"head":"0"*64,"last_session":None,
  "positions":{a:{} for a in ARMS},"marks":{},"bench_first":None,
  "bench_latest":None,"nav":{a:{s:1. for s in SCENARIOS} for a in ARMS},
  "outages":[],"finalized":False,"alpha_accepted":False}
def verify(state):
 if state["schema"]!=SCHEMA or state["freeze"]!=frozen():raise ValueError("FREEZE_MISMATCH")
 prev="0"*64;last=""
 for r in state["records"]:
  actual=r["sha256"];t={k:v for k,v in r.items() if k!="sha256"}
  if t["previous_sha256"]!=prev or digest(t)!=actual:raise ValueError("TAMPERED_EVIDENCE_CHAIN")
  if t["session"]<=last:raise ValueError("DUPLICATE_OR_OUT_OF_ORDER")
  last=t["session"];prev=actual
 if prev!=state["head"] or (state["records"] and last!=state["last_session"]):
  raise ValueError("HEAD_MISMATCH")
 return True
def normalize_history(df,session):
 if not {"Open","High","Low","Close","Volume"}.issubset(df):raise ValueError("BROKEN_HISTORY_SCHEMA")
 b=df[["Open","High","Low","Close","Volume"]].copy()
 idx=pd.DatetimeIndex(b.index)
 if idx.tz is not None:idx=idx.tz_convert(NY).tz_localize(None)
 b.index=idx.normalize();b=b[b.index<pd.Timestamp(session)].sort_index()
 if b.index.duplicated().any():raise ValueError("DUPLICATE_HISTORY_DATE")
 if len(b)<250:raise ValueError("HISTORY_WARMUP_SHORT")
 if not np.isfinite(b.iloc[-250:].to_numpy(float)).all() or (b[["Open","High","Low","Close"]].iloc[-250:]<=0).any().any():raise ValueError("INVALID_HISTORY_PRICES")
 if (pd.Timestamp(session)-b.index[-1]).days>5:raise ValueError("STALE_CLOSED_DAILY_BAR")
 return b
def extract_intraday(raw,symbol):
 """Preserve provider UTC/NY timezone; lab.data._split strips it."""
 frame=raw[symbol] if isinstance(raw.columns,pd.MultiIndex) else raw
 if not isinstance(frame.index,pd.DatetimeIndex) or frame.index.tz is None:
  raise ValueError("INTRADAY_TIMESTAMP_MISSING_TIMEZONE")
 if "Close" not in frame:raise ValueError("INTRADAY_CLOSE_MISSING")
 return frame.dropna(subset=["Close"]).sort_index()
def live_market_data(now_utc):
 """Two distinct feeds: daily closed candles and intraday recent 5m price proxies.
 The latter are NOT executable broker quotes and may be delayed.
 """
 import yfinance as yf
 from lab.data import _yf_download
 local=now_utc.astimezone(NY)
 if local.weekday()>4 or not (10<=local.hour<16):
  return None
 session=local.date().isoformat()
 history_raw=_yf_download(list(SYMBOLS),"2022-01-01","1d")
 hist={};prices={};times={};errors={}
 for symbol in SYMBOLS:
  try:hist[symbol]=normalize_history(history_raw[symbol],session)
  except Exception as e:errors[symbol]="daily:"+type(e).__name__+":"+str(e)
 # Yahoo may rate-limit: complete equity universe is required for stock arms.
 for i in range(0,len(SYMBOLS),12):
  chunk=list(SYMBOLS[i:i+12])
  try:
   raw=yf.download(chunk,period="5d",interval="5m",auto_adjust=True,
    progress=False,threads=False,group_by="ticker")
   for symbol in chunk:
    frame=extract_intraday(raw,symbol)
    if frame.empty:raise ValueError("NO_INTRADAY_QUOTE")
    if frame.empty:raise ValueError("NO_INTRADAY_CLOSE")
    idx=pd.Timestamp(frame.index[-1])
    if idx.tzinfo is None:raise ValueError("QUOTETIME_NO_TZ")
    ts=idx.tz_convert(timezone.utc)
    if ts.astimezone(NY).date().isoformat()!=session:raise ValueError("STALE_TRADING_SESSION")
    age=(now_utc-ts.to_pydatetime()).total_seconds()
    if age< -60 or age>5400:raise ValueError("STALE_OR_FUTURE_QUOTE")
    px=float(frame["Close"].iloc[-1])
    if not math.isfinite(px) or px<=0:raise ValueError("INVALID_QUOTE")
    prices[symbol]=px;times[symbol]=ts.isoformat()
  except Exception as e:
   for symbol in chunk:errors.setdefault(symbol,"intraday:"+type(e).__name__+":"+str(e))
 return {"session":session,"history":hist,"prices":prices,"quote_times":times,"errors":errors,
  "received_at":now_utc.isoformat(),"source":"Yahoo 5m recent bars (delayed/nonexecutability unknown)"}
def stock_weights(history,rule):
 # IDENTICAL signal grammar to H114 stock_portfolios, evaluated at most recent
 # fully closed prior-day bar. Missing members => fail closed, not dynamic selection.
 idx=history["SPY"].index
 frames={}
 for symbol in STOCKS:
  b=history[symbol].reindex(idx)
  if b[["Open","Close"]].iloc[-250:].isna().any().any():raise ValueError("STOCK_UNIVERSE_GAPS")
  frames[symbol]=b
 op=pd.DataFrame({a:x["Open"] for a,x in frames.items()})
 cl=pd.DataFrame({a:x["Close"] for a,x in frames.items()})
 ret=cl.pct_change(fill_method=None)
 spyret=history["SPY"]["Close"].pct_change(fill_method=None)
 vol=ret.rolling(21,min_periods=21).std()
 ss={
 "residual_momentum":ret.sub(spyret,axis=0).rolling(63,min_periods=63).sum()/vol.replace(0,np.nan),
 "shock_recovery":(cl/op-1)*(-ret.rolling(3,min_periods=3).sum().shift(1))/vol.replace(0,np.nan),
 "gap_repair":(cl/op-1)-(op/cl.shift(1)-1),
 "defensive_efficiency":cl.pct_change(42,fill_method=None)/vol.replace(0,np.nan),
 "volatility_calm":cl.pct_change(21,fill_method=None)/(vol+1e-6)}
 e=(cl>cl.rolling(200,min_periods=200).mean())&(op>0)
 ranks=ss[rule].where(e).iloc[-1].rank(ascending=False,method="first")
 picked=ranks[ranks<=5].index.tolist()
 return {a:1/len(picked) for a in picked} if picked else {}
def compute_targets(snapshot):
 required=set(STOCKS)|set(ETFS)
 missing=required-set(snapshot["prices"])|required-set(snapshot["history"])
 if missing:raise ValueError("MISSING_EQUITY_MARKS:"+",".join(sorted(missing)))
 history=snapshot["history"];targets={}
 latest_spy=history["SPY"].index[-1]
 if any(history[a].index[-1]!=latest_spy for a in required):
  raise ValueError("MISMATCHED_CLOSED_EQUITY_SESSIONS")
 for arm,(kind,rule,assets) in ARMS.items():
  if any(a not in history or a not in snapshot["prices"] for a in assets):
   # Future-only diagnostics may be unavailable independently of equities.
   if "FUTURES_DIAGNOSTIC" in arm:continue
   raise ValueError("MISSING_ARM_DATA:"+arm)
  if kind=="stock":targets[arm]=stock_weights(history,rule)
  else:
   signals={a:float(sigs(history[a],allow_short=a in FUTURES)[rule].iloc[-1]) for a in assets}
   targets[arm]={a:v/len(assets) for a,v in signals.items() if abs(v)>0}
 return targets
def side_cost(symbol,price,scenario):
 if symbol in FUTURES:
  n,commission=FUTURE_COST[scenario];mult,tick=FUTURES[symbol]
  return (n*tick+commission/mult)/price
 return ETF_BPS[scenario]/10000.
def apply(state,snapshot):
 verify(state)
 if state["finalized"]:raise ValueError("STUDY_FINALIZED")
 session=snapshot["session"]
 if state["last_session"] and session<=state["last_session"]:raise ValueError("SESSION_REPLAY")
 if session<state["started_date"]:raise ValueError("BACKDATED_MARKET_EVENT")
 targets=compute_targets(snapshot)
 # If an existing position loses its price or prior mark, fail closed entirely.
 old_mark=state["marks"];marks=snapshot["prices"]
 for arm,weights in state["positions"].items():
  for a,v in weights.items():
   if abs(v)>0 and (a not in old_mark or a not in marks):raise ValueError("UNPRICED_HELD_POSITION:"+a)
 newnav={};day_returns={}
 for arm in ARMS:
  if arm not in targets:
   newnav[arm]=state["nav"][arm].copy()
   day_returns[arm]={"status":"MISSING_DIAGNOSTIC_MARKET","net":{}}
   continue
  old=state["positions"][arm];new=targets[arm]
  gross=sum(float(w)*(marks[a]/old_mark[a]-1) for a,w in old.items()) if old else 0.
  cost={s:sum(abs(new.get(a,0)-old.get(a,0))*side_cost(a,marks[a],s)
    for a in set(new)|set(old)) for s in SCENARIOS}
  ret={s:gross-cost[s] for s in SCENARIOS}
  if any(v<=-1 or not math.isfinite(v) for v in ret.values()):raise ValueError("INVALID_NAV_RETURN")
  newnav[arm]={s:state["nav"][arm][s]*(1+ret[s]) for s in SCENARIOS}
  day_returns[arm]={"status":"OK","gross":gross,"net":ret,"turnover":sum(abs(new.get(a,0)-old.get(a,0)) for a in set(new)|set(old)),
   "positions":new,"assumed_costs":cost}
 spy=marks["SPY"]
 if state["bench_first"] is None:state["bench_first"]=spy
 benchmark=spy/state["bench_first"]
 record={"session":session,"observed_at":snapshot["received_at"],
  "quote_times":snapshot["quote_times"],"quotes":marks,
  "closed_history_last":{a:x.index[-1].date().isoformat() for a,x in snapshot["history"].items()},
  "targets":targets,"returns":day_returns,"nav":newnav,
  "benchmark_spy_nav":benchmark,"data_errors":snapshot["errors"],"previous_sha256":state["head"]}
 record["sha256"]=digest(record)
 state["records"].append(record);state["head"]=record["sha256"]
 state["last_session"]=session
 state["positions"]={a:targets.get(a,state["positions"][a]) for a in ARMS}
 state["marks"]={a:float(v) for a,v in marks.items()}
 state["bench_latest"]=benchmark;state["nav"]=newnav
 return state
def note_outage(state,now_utc,exc):
 # No fabricated market return; errors never advance the observed session.
 state["outages"].append({"at_utc":now_utc.isoformat(),"reason":type(exc).__name__,
  "message":str(exc)[:240]})
 return state
def report(state,now_utc):
 elapsed=(now_utc.date()-pd.Timestamp(state["started_date"]).date()).days
 n=len(state["records"]);by_arm={}
 weeks=len({pd.Timestamp(r["session"]).isocalendar()[:2] for r in state["records"]})
 bdays=max(0,len(pd.bdate_range(state["started_date"],now_utc.date().isoformat())))
 coverage=n/max(1,bdays)
 for arm,navs in state["nav"].items():
  rebalances=sum(1 for r in state["records"] if r["returns"].get(arm,{}).get("turnover",0)>0)
  observed_path=[1.]+[float(r["nav"][arm]["base"]) for r in state["records"]]
  peaks=np.maximum.accumulate(np.asarray(observed_path,float))
  mdd=float(np.min(np.asarray(observed_path)/peaks-1)) if len(observed_path)>1 else 0.
  final=navs["base"]
  baseline=(state["bench_latest"] if state["bench_latest"] is not None else None)
  # These are research MANUAL REVIEW eligibility checks, never approval.
  diagnostic_only=("DIAGNOSTIC" in arm or "CONTROL" in arm)
  review_ready=bool(elapsed>=180 and n>=85 and weeks>=20 and rebalances>=25
    and coverage>=.85 and len(state["outages"])<=max(1,int(.05*n))
    and final>1. and navs["stress"]>1. and baseline is not None
    and final>baseline and mdd>=-.20 and not diagnostic_only)
  by_arm[arm]={"nav":navs,"net_return_base":final-1,"rebalances":rebalances,
   "max_drawdown_mark_to_mark":mdd,"beats_spy_at_base":(final>baseline) if baseline is not None else None,
   "review_ready_only":review_ready,"manual_review_required":True,
   "approval_blockers":["no executable exchange fill audit","no verified point-in-time stock membership"
    if arm.startswith("US30_") else "no independent provider verification",
    "research-only futures proxy" if "FUTURES" in arm else "prospective sample uncertainty"],
   "execution_verified":False}
 checkpoints={}
 for day in (30,90,180):
  minimum={30:8,90:38,180:85}[day]
  checkpoints[str(day)]={"reached":elapsed>=day,"observed_sessions":n,
   "observed_calendar_weeks":weeks,"trading_day_coverage_proxy":round(coverage,4),
   "min_observed_sessions":minimum,"sample_adequacy":n>=minimum,
   "outages":len(state["outages"]),"live_trading_approval":False}
 return {"schema":SCHEMA,"elapsed_calendar_days":elapsed,"started_at":state["started_at"],
  "ends_at_calendar_date":state["end_date"],"last_session":state["last_session"],
  "observed_sessions":n,"observed_weeks":weeks,
  "trading_day_coverage_proxy":round(coverage,4),"outages":len(state["outages"]),
  "finalized":state["finalized"],"benchmark_spy_nav":state["bench_latest"],
  "arms":by_arm,"checkpoints":checkpoints,"alpha_accepted":False,
  "execution_verified":False,"contract_roll_verified":False,
  "point_in_time_stock_membership_verified":False,"paper_only":True,
  "limitations":["Intraday 5-minute Yahoo reference price is delayed/non-executable; NOT a broker quote",
  "Futures continuous contracts ignore roll/expiry and are diagnostic only",
  "Fixed historical stock universe creates survivorship bias and lacks point-in-time membership",
  "Trading days not observed are never backfilled","180 days cannot guarantee independent sample adequacy"]}
def run(mode,state_path,out_path,now_utc=None):
 now_utc=now_utc or datetime.now(timezone.utc)
 if now_utc.tzinfo is None:raise ValueError("NEED_UTC")
 if mode=="start":
  if state_path.exists():raise ValueError("ALREADY_STARTED")
  state=seed(now_utc)
 elif mode=="tick":
  if not state_path.exists():
   print("NO_ACTIVE_STUDY");return None
  state=json.loads(state_path.read_text());verify(state)
 else:raise ValueError("INVALID_MODE")
 failed_observation=False
 if not state["finalized"] and now_utc.date()>=pd.Timestamp(state["end_date"]).date():
  state["finalized"]=True
 elif mode=="tick" and not state["finalized"]:
  try:
   snapshot=live_market_data(now_utc)
   if snapshot is not None and snapshot["session"]!=state["last_session"]:
    apply(state,snapshot)
  except Exception as exc:
   failed_observation=True
   note_outage(state,now_utc,exc)
   print("H115_FAIL_CLOSED:",type(exc).__name__,str(exc),file=sys.stderr)
 state_path.parent.mkdir(parents=True,exist_ok=True)
 state_path.write_text(json.dumps(state,indent=2,sort_keys=True,allow_nan=False)+"\n")
 out_path.mkdir(parents=True,exist_ok=True)
 (out_path/"summary.json").write_text(json.dumps(report(state,now_utc),indent=2,sort_keys=True,allow_nan=False)+"\n")
 (out_path/"state.json").write_text(json.dumps(state,indent=2,sort_keys=True,allow_nan=False)+"\n")
 (out_path/"execution_status.txt").write_text("OUTAGE\n" if failed_observation else "OK\n")
 print(json.dumps({"mode":mode,"observed":len(state["records"]),"outages":len(state["outages"]),"finalized":state["finalized"]}))
 return state
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--mode",required=True,choices=("start","tick"))
 p.add_argument("--state",default="results/h115/state.json")
 p.add_argument("--out",default="results/h115/report")
 a=p.parse_args();run(a.mode,Path(a.state),Path(a.out))
