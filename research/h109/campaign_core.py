"""Fixed, causal historical hypothesis grid. Nothing here approves live trading."""
from __future__ import annotations
import math
from statistics import mean, pstdev
HOUR=3_600_000
VENUES=("okx","gate")
SYMBOLS=("BTC","ETH")
TIMEFRAMES=("1H","4H")
SIDES=("long","short")
FAMILIES=("trend_cross","breakout","zscore_revert","rsi2_revert","momentum",
          "compressed_breakout","channel_reentry","two_bar_reversal","calendar_control")
COSTS=(0,10,20,40,80,120)

def validate(rows):
    if len(rows)<100:raise ValueError("SHORT_HISTORY")
    previous=-1
    for r in rows:
        t=r["ts"];o,h,l,c=(r[k] for k in ("open","high","low","close"))
        if not isinstance(t,int) or t%HOUR or t<=previous:raise ValueError("BAD_TIMESTAMP_ORDER")
        if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in (o,h,l,c)):
            raise ValueError("NONFINITE_OHLC")
        if not l<=min(o,c)<=max(o,c)<=h:raise ValueError("BAD_OHLC")
        previous=t
    return rows

def aggregate(rows):
    groups={}
    for r in rows:groups.setdefault(r["ts"]//(4*HOUR),[]).append(r)
    output=[]
    for key,block in sorted(groups.items()):
        if len(block)!=4 or [x["ts"] for x in block]!=[key*4*HOUR+i*HOUR for i in range(4)]:continue
        output.append({"ts":key*4*HOUR,"open":block[0]["open"],
                       "high":max(x["high"] for x in block),"low":min(x["low"] for x in block),
                       "close":block[-1]["close"]})
    return output

def indicators(bars,step):
    out=[None]*len(bars)
    c=[x["close"] for x in bars]
    for i in range(74,len(bars)-1):
        if any(bars[j]["ts"]-bars[j-1]["ts"]!=step for j in range(i-73,i+1)):continue
        p24=bars[i-24:i];p72=bars[i-72:i]
        avg=mean(x["close"] for x in p24);sd=pstdev(x["close"] for x in p24)
        diffs=[c[k]-c[k-1] for k in (i-1,i)]
        old=[c[k]-c[k-1] for k in (i-2,i-1)]
        def rsi(d):
            up=sum(max(v,0) for v in d);down=sum(max(-v,0) for v in d)
            return 100*up/(up+down) if up+down else 50
        r24=mean((x["high"]-x["low"])/x["close"] for x in bars[i-23:i+1])
        r72=mean((x["high"]-x["low"])/x["close"] for x in bars[i-71:i+1])
        out[i]={"f":mean(c[i-23:i+1]),"s":mean(c[i-71:i+1]),
                "pf":mean(c[i-24:i]),"ps":mean(c[i-72:i]),
                "hi":max(x["high"] for x in p24),"lo":min(x["low"] for x in p24),
                "phi":max(x["high"] for x in bars[i-25:i-1]),
                "plo":min(x["low"] for x in bars[i-25:i-1]),
                "z":(c[i]-avg)/sd if sd else 0,"pz":(c[i-1]-avg)/sd if sd else 0,
                "rsi":rsi(diffs),"prsi":rsi(old),
                "mom":c[i]/c[i-24]-1,"pmom":c[i-1]/c[i-25]-1,
                "r24":r24,"r72":r72,
                "vol":"high_vol" if r24>=r72 else "low_vol",
                "atr":mean(x["high"]-x["low"] for x in bars[i-13:i+1])}
    return out

def signal(fam,side,bars,i,x):
    long=side=="long";c=bars[i]["close"];p=bars[i-1]["close"]
    if fam=="trend_cross":
        return (x["pf"]<=x["ps"] and x["f"]>x["s"]) if long else (x["pf"]>=x["ps"] and x["f"]<x["s"])
    if fam=="breakout":
        return (c>x["hi"] and p<=x["phi"]) if long else (c<x["lo"] and p>=x["plo"])
    if fam=="zscore_revert":
        return (x["pz"]>=-1.8 and x["z"]< -1.8) if long else (x["pz"]<=1.8 and x["z"]>1.8)
    if fam=="rsi2_revert":
        return (x["prsi"]>=15 and x["rsi"]<15) if long else (x["prsi"]<=85 and x["rsi"]>85)
    if fam=="momentum":
        return (x["pmom"]<=.03 and x["mom"]>.03) if long else (x["pmom"]>=-.03 and x["mom"]<-.03)
    if fam=="compressed_breakout":
        return x["r24"]<.8*x["r72"] and signal("breakout",side,bars,i,x)
    if fam=="channel_reentry":
        return (p<x["plo"] and c>x["lo"]) if long else (p>x["phi"] and c<x["hi"])
    if fam=="two_bar_reversal":
        pp=bars[i-2]["close"]
        return (pp>p and c>bars[i-1]["high"]) if long else (pp<p and c<bars[i-1]["low"])
    if fam=="calendar_control":return i%48==(0 if long else 24)
    raise ValueError("UNKNOWN_FAMILY")

def simulate(bars,i,side,atr,step):
    if i>=len(bars) or bars[i]["ts"]-bars[i-1]["ts"]!=step:return None
    direction=1 if side=="long" else -1
    entry=bars[i]["open"];risk=2*atr
    if not 0<risk<entry*.25:return None
    stop=entry-direction*risk;target=entry+direction*3*atr
    hold=48 if step==HOUR else 12
    if i+hold>len(bars):return None
    last=i+hold-1;price=bars[last]["close"];cause="TIME"
    for j in range(i,i+hold):
        b=bars[j]
        if j>i and b["ts"]-bars[j-1]["ts"]!=step:return None
        if direction*(b["open"]-stop)<=0:price=b["open"];last=j;cause="STOP_GAP";break
        if b["low"]<=stop if direction==1 else b["high"]>=stop:
            price=stop;last=j;cause="STOP";break
        if direction*(b["open"]-target)>=0:price=target;last=j;cause="TARGET_GAP";break
        if b["high"]>=target if direction==1 else b["low"]<=target:
            price=target;last=j;cause="TARGET";break
    gross=direction*(price-entry)/risk
    return {"entry_ms":bars[i]["ts"],"exit_ms":bars[last]["ts"],
            "gross_r":gross,"entry":entry,"risk":risk,"cause":cause,
            "net_r":{str(c):gross-c/10000*entry/risk for c in COSTS}}

def btc_regime(bars,step):
    result={}
    for i in range(73,len(bars)):
        if bars[i]["ts"]-bars[i-72]["ts"]!=72*step:continue
        result[bars[i]["ts"]+step]="risk_on" if bars[i]["close"]>bars[i-72]["close"] else "risk_off"
    return result

def evaluate(bars,step,fam,side,context):
    ind=indicators(bars,step)
    trades=[];end=-1
    for i in range(74,len(bars)-1):
        x=ind[i]
        if x is None or not signal(fam,side,bars,i,x) or bars[i+1]["ts"]<=end:continue
        t=simulate(bars,i+1,side,x["atr"],step)
        if t is None:continue
        t["vol_regime"]=x["vol"]
        t["btc_regime"]=context.get(bars[i+1]["ts"],"unclassified")
        trades.append(t);end=t["exit_ms"]
    return trades
