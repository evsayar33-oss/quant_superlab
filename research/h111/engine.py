"""H111 forward-only, no-orders, two frozen BTC 4H long/short hypotheses."""
from __future__ import annotations
import hashlib,json,math,sys,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h109"))
from campaign_core import aggregate,indicators,signal,HOUR
sys.path.insert(0,str(ROOT/"research"/"h104"))
from history import gate_history,canonical
sys.path.insert(0,str(ROOT/"research"/"h096"))
from market import fetch as okx_fetch
FOUR=4*HOUR
VENUES=("okx","gate")
STRATEGIES=(("zscore_revert","long"),("two_bar_reversal","short"))
COST_BPS=(12,16,20)
SCHEMA="h111.paper.v1"
def fetch_json(url):
 with urlopen(Request(url,headers={"User-Agent":"quant-superlab-h111-paper/1.0"}),timeout=20) as r:return json.load(r)
def snapshot(venue,now_ms):
 if venue=="okx":
  payload=okx_fetch("BTC","1H",pages=5)
  bars,gaps=canonical(payload["bars"])
  q=fetch_json("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP")
  if q.get("code")!="0" or not q.get("data"):raise ValueError("OKX_TICKER_BAD")
  t=q["data"][0];bid=float(t["bidPx"]);ask=float(t["askPx"]);quote_ms=int(t["ts"])
 else:
  payload=gate_history("BTC",lookback_days=20,max_pages=2)
  bars,gaps=canonical(payload["bars"])
  t=fetch_json("https://api.gateio.ws/api/v4/futures/usdt/tickers?contract=BTC_USDT")
  if not isinstance(t,list) or not t:raise ValueError("GATE_TICKER_BAD")
  bid=float(t[0]["highest_bid"]);ask=float(t[0]["lowest_ask"])
  quote_ms=int(float(t[0].get("timestamp",0))*1000) if t[0].get("timestamp") else now_ms
 if gaps:raise ValueError("HISTORY_GAPS")
 if not (0<bid<=ask and all(math.isfinite(x) for x in (bid,ask))):raise ValueError("INVALID_BOOK")
 if abs(now_ms-quote_ms)>180_000:raise ValueError("STALE_TICKER")
 if len(bars)<350:raise ValueError("INSUFFICIENT_WARMUP")
 if bars[-1]["ts"]+HOUR>now_ms:raise ValueError("UNCLOSED_LAST_BAR")
 if now_ms-(bars[-1]["ts"]+HOUR)>2*HOUR:raise ValueError("STALE_CANDLES")
 return {"venue":venue,"bid":bid,"ask":ask,"quote_ms":quote_ms,
         "bars":bars,"bar_hash":hashlib.sha256(json.dumps(bars,sort_keys=True).encode()).hexdigest()}
def seed(now_ms):
 return {"schema":SCHEMA,"started_ms":now_ms,"ends_ms":now_ms+30*24*HOUR,
  "last_tick_ms":None,"ticks":[],"positions":{},"trades":[],
  "rejected":[], "outages":[], "alpha_accepted":False,
  "research_only":True,"finalized":False}
def cost_r(entry,risk,bps):return bps/10000*entry/risk
def close_trade(state,key,pos,exit_price,exit_ms,reason):
 gross=(exit_price-pos["entry"])*pos["direction"]/pos["risk"]
 record={**pos,"exit_ms":exit_ms,"exit_price":exit_price,"reason":reason,
  "gross_r":gross,"net_r":{str(b):gross-cost_r(pos["entry"],pos["risk"],b) for b in COST_BPS}}
 state["trades"].append(record);del state["positions"][key]
def exits(state,key,pos,bars,now_ms,bid,ask):
 # Only evaluate fully closed 1H candles whose open >= next hour AFTER entry timestamp.
 # Entry-hour intrabar path is unknowable from OHLC; recorded as a blind spot.
 first=((pos["entry_ms"]//HOUR)+1)*HOUR
 eligible=[b for b in bars if first<=b["ts"] and b["ts"]+HOUR<=now_ms
           and b["ts"]>pos["last_examined_bar_ms"]]
 for b in eligible:
  direction=pos["direction"];stop=pos["stop"];target=pos["target"]
  if (b["open"]<=stop if direction==1 else b["open"]>=stop):
   close_trade(state,key,pos,b["open"],b["ts"],"STOP_GAP_PROXY");return
  if (b["low"]<=stop if direction==1 else b["high"]>=stop):
   close_trade(state,key,pos,stop,b["ts"]+HOUR,"STOP_PROXY");return
  if (b["open"]>=target if direction==1 else b["open"]<=target):
   close_trade(state,key,pos,b["open"],b["ts"],"TARGET_GAP_PROXY");return
  if (b["high"]>=target if direction==1 else b["low"]<=target):
   close_trade(state,key,pos,target,b["ts"]+HOUR,"TARGET_PROXY");return
  pos["last_examined_bar_ms"]=b["ts"]
 if now_ms-pos["entry_ms"]>=48*HOUR:
  close_trade(state,key,pos,bid if pos["direction"]==1 else ask,now_ms,"TIME_QUOTE_PROXY")
def tick(state,now_ms,quotes):
 if state["schema"]!=SCHEMA or state["finalized"]:raise ValueError("INVALID_STATE")
 if state["last_tick_ms"] is not None and now_ms<=state["last_tick_ms"]:raise ValueError("NON_MONOTONIC_TICK")
 if now_ms<state["started_ms"]:raise ValueError("OUTSIDE_WINDOW")
 if set(quotes)!=set(VENUES):raise ValueError("BOTH_VENUES_REQUIRED")
 for venue in VENUES:
  q=quotes[venue];bars=q["bars"]
  closed4=aggregate(bars)
  if len(closed4)<76:raise ValueError("NO_4H_WARMUP")
  # H109 indicators reserve the final array slot for next-bar execution.
  # Append an indicator-only sentinel (never used as a candle or price fill)
  # so the newest *closed* 4H candle can be evaluated causally.
  sentinel={**closed4[-1],"ts":closed4[-1]["ts"]+FOUR}
  ind=indicators(closed4+[sentinel],FOUR)
  sig_i=len(closed4)-1
  if ind[sig_i] is None:raise ValueError("NO_VALID_SIGNAL_WINDOW")
  for family,side in STRATEGIES:
   key=f"{venue}_BTC_4H_{family}_{side}"
   if key in state["positions"]:
    exits(state,key,state["positions"][key],bars,now_ms,q["bid"],q["ask"])
   if key in state["positions"]:continue
   if now_ms>=state["ends_ms"]:continue
   # At most one entry per completed 4h signal bar; signal can only be
   # observed on/after its closure and never retroactively filled.
   sig_ts=closed4[sig_i]["ts"]
   signal_end=sig_ts+FOUR
   if not (signal_end<=now_ms<=signal_end+2*HOUR):continue
   seen_key=key+"_"+str(sig_ts)
   if seen_key in state.setdefault("seen_signals",[]):continue
   state["seen_signals"].append(seen_key)
   if not signal(family,side,closed4,sig_i,ind[sig_i]):continue
   direction=1 if side=="long" else -1
   entry=q["ask"] if direction==1 else q["bid"]
   atr=ind[sig_i]["atr"];risk=2*atr
   if not 0<risk<entry*.25:continue
   state["positions"][key]={"key":key,"venue":venue,"family":family,
    "side":side,"direction":direction,"entry_ms":now_ms,"signal_ms":sig_ts,
    "entry":entry,"risk":risk,"stop":entry-direction*risk,
    "target":entry+direction*3*atr,"last_examined_bar_ms":-1,
    "entry_book_bid":q["bid"],"entry_book_ask":q["ask"],
    "entry_source_sha256":q["bar_hash"],"entry_quote_ms":q["quote_ms"],
    "unobserved_entry_hour":True}
 state["ticks"].append({"ts":now_ms,"quotes":{v:{"bid":quotes[v]["bid"],
    "ask":quotes[v]["ask"],"quote_ms":quotes[v]["quote_ms"],
    "bar_hash":quotes[v]["bar_hash"]} for v in VENUES},
    "open_positions":len(state["positions"]),"closed_trades":len(state["trades"])})
 state["last_tick_ms"]=now_ms
 if now_ms>=state["ends_ms"]:
  for key,pos in list(state["positions"].items()):
   q=quotes[pos["venue"]]
   close_trade(state,key,pos,q["bid"] if pos["direction"]==1 else q["ask"],now_ms,"WINDOW_END_QUOTE_PROXY")
  state["finalized"]=True
 return state
def summary(state):
 trades=state["trades"];by_key={}
 for venue in VENUES:
  for fam,side in STRATEGIES:
   key=f"{venue}_BTC_4H_{fam}_{side}"
   ts=[t for t in trades if t["key"]==key]
   by_key[key]={"closed_trades":len(ts),
    "mean_net_r":{str(b):sum(t["net_r"][str(b)] for t in ts)/len(ts) if ts else None for b in COST_BPS}}
 return {"schema":SCHEMA,"started_ms":state["started_ms"],"ends_ms":state["ends_ms"],
  "last_tick_ms":state["last_tick_ms"],"finalized":state["finalized"],
  "ticks":len(state["ticks"]),"outages":len(state["outages"]),
  "open_positions":len(state["positions"]),"closed_trades":len(trades),
  "by_strategy":by_key,"alpha_accepted":False,"prospective_oos_verified":False,
  "execution_verified":False,"funding_verified":False,"portfolio_nav_verified":False,
  "limitations":["Quote snapshots are observed, not exchange fills",
    "Stop/target execution uses 1H OHLC proxy with stop-first; entry-hour path not observable",
    "No exchange-account funding ledger, measured impact, or orderbook depth",
    "30 elapsed calendar days alone does not guarantee adequate trade count or execution validity"]}
