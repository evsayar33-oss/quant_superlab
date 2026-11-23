"""Metadata-only source evidence tracer for independently running strategy repos.

Extracts provenance, timestamp coverage and data quality counts from REAL
repo-native inputs. It never exports quotes, positions, user data or raw
vendor datasets into a public central repository. The tracer is run by each
repository in its own existing SHA-chained source evidence worktree.

"first_seen" is the real collector UTC only; original publication timestamps
are reported separately and NEVER synthesized from report period dates.
"""
from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone

SCHEMA = "QS.native_source_telemetry.v1"
MAX_EXAMINED = 25000
MAX_STATUS_LABELS = 10
TIME_NAMES = frozenset({
    "asof_utc","as_of_utc","observed_at","observed_utc","observed_at_ms",
    "published_at","published_utc","published_time","release_time",
    "issued","issued_at","accepted_at","accepted_utc","first_seen_at",
    "ts","timestamp","ts_utc","signal_ts","scan_utc","scan_utc_ms",
    "last_updated","updated_at","generated_at","attempted_at_utc",
    "last_bar","last_candle_ms","book_ts","funding_ts","oi_ts",
})
DATE_NAMES = frozenset({"date","session","last_eod_date","report_date",
                       "fiscal_date","filing_date","period_end"})
ARRAY_KEYS = ("records","entries","events","trades","ticks","observations",
              "hypotheses","variants","forecasts","candidates",
              "results","assets","markets","history")
LABEL_KEYS = ("status","verdict","readiness","data_status","mode")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _moment(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (float,int)):
            n = float(value)
            if n <= 0:
                return None
            unit = 1e6 if n >= 1e15 else (1e3 if n >= 1e12 else 1)
            obj = datetime.fromtimestamp(n / unit, timezone.utc)
        else:
            string = str(value).strip()
            if "T" not in string and " " not in string:
                return None
            obj = datetime.fromisoformat(string.replace("Z","+00:00"))
            if obj.tzinfo is None:
                return None
            obj = obj.astimezone(timezone.utc)
        if not 1990 <= obj.year <= 2100:
            return None
        return obj.isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _safe_status(value):
    if not isinstance(value,str):
        return None
    clean = value.strip()
    if (not clean or len(clean)>55 or
            not re.fullmatch(r"[A-Za-z0-9_./:-]+",clean)):
        return None
    return clean


def _scan_records(records, fields, raw_len):
    earliest = latest = None
    date_earliest = date_latest = None
    count, status, nulls = 0, Counter(), Counter()
    examined = 0
    for obj in records:
        if not isinstance(obj, dict):
            continue
        count += 1
        if examined >= MAX_EXAMINED:
            continue
        examined += 1
        for k in list(obj)[:80]:
            value = obj[k]
            if value is None or value == "":
                nulls[k] += 1
            if k in LABEL_KEYS:
                state = _safe_status(value)
                if state:
                    status[state] += 1
            if k in TIME_NAMES:
                t = _moment(value)
                if t is not None:
                    earliest = min(earliest,t) if earliest else t
                    latest = max(latest,t) if latest else t
            elif k in DATE_NAMES and isinstance(value,str) and DATE_RE.fullmatch(value):
                date_earliest = min(date_earliest,value) if date_earliest else value
                date_latest = max(date_latest,value) if date_latest else value
    return {
        "records_total":count,"records_examined":examined,
        "records_truncated_for_quality_scan":count>examined,
        "available_fields":fields[:60],
        "event_timestamp_min_utc":earliest,
        "event_timestamp_max_utc":latest,
        "date_only_period_min":date_earliest,
        "date_only_period_max":date_latest,
        "categorical_status_counts":dict(status.most_common(MAX_STATUS_LABELS)),
        "missing_value_counts":{k:v for k,v in nulls.most_common(20)},
        "actual_data_asof_inferred_from_period_end":False,
        "independent_pit_verified":False,
    }


def source_detail(alias, raw, meta):
    """Metadata and strict source hashes only; never any actual trading row."""
    blob = {"alias":alias,"source_reference":meta.get("reference"),
            "source_commit":meta.get("commit"),
            "source_sha256":meta.get("sha256"),
            "source_bytes":len(raw),
            "content_kind":"UNSUPPORTED"}
    path = str(meta.get("path","")).lower()
    try:
        if path.endswith(".csv"):
            buffer = io.StringIO(raw.decode("utf-8-sig"))
            reader = csv.DictReader(buffer)
            if reader.fieldnames is None:
                raise ValueError("MISSING_CSV_HEADER")
            summary = _scan_records(reader,reader.fieldnames,len(raw))
            kind = "CSV"
        elif path.endswith(".jsonl"):
            parsed = []
            for line in raw.decode("utf-8-sig").splitlines():
                if not line.strip():
                    continue
                parsed.append(json.loads(line))
            fields = list(parsed[0]) if parsed and isinstance(parsed[0],dict) else []
            summary = _scan_records(parsed,fields,len(raw))
            kind = "JSONL"
        elif path.endswith(".json"):
            parsed = json.loads(raw.decode("utf-8-sig"))
            if isinstance(parsed,list):
                rows,fields = parsed,(list(parsed[0]) if parsed and isinstance(parsed[0],dict) else [])
            elif isinstance(parsed,dict):
                fields = list(parsed)
                # A named array or dict is observable; its size is evidence
                # coverage, not an endorsement of its labels/strategies.
                rows = [parsed]
                candidates=[]
                for key in ARRAY_KEYS:
                    value = parsed.get(key)
                    if isinstance(value,list):
                        candidates.append((key,len(value),value))
                    elif isinstance(value,dict):
                        vals=list(value.values())
                        candidates.append((key,len(vals),vals))
                if candidates:
                    key,_,rows=max(candidates,key=lambda x:x[1])
                    blob["nested_evidence_collection"] = key
                elif len(parsed)>30 and all(isinstance(x,dict) for x in parsed.values()):
                    rows=list(parsed.values())
                    blob["nested_evidence_collection"] = "named_map"
            else:
                raise ValueError("NON_STRUCTURED_JSON")
            summary = _scan_records(rows,fields,len(raw))
            if isinstance(parsed,dict):
                # These report-level metadata keys are not row values.
                top=_scan_records([parsed],fields,len(raw))
                summary["report_top_level_timestamp_min_utc"]=top["event_timestamp_min_utc"]
                summary["report_top_level_timestamp_max_utc"]=top["event_timestamp_max_utc"]
                summary["report_top_level_status_counts"]=top["categorical_status_counts"]
            kind="JSON"
        else:
            kind="NON_STRUCTURED_TEXT_OR_BINARY"
            summary={"records_total":None,"records_examined":0,
                     "actual_data_asof_inferred_from_period_end":False,
                     "independent_pit_verified":False}
        blob.update(summary)
        blob["content_kind"]=kind
        blob["schema_checked"]=kind in ("CSV","JSON","JSONL")
    except (UnicodeError,ValueError,csv.Error,TypeError,OverflowError):
        blob.update({"content_kind":"STRUCTURE_INVALID",
                     "records_total":None,
                     "schema_checked":False,
                     "independent_pit_verified":False})
    return blob


def trace_native_sources(contents,meta,errors,first_observed_utc):
    collected=_moment(first_observed_utc)
    if collected is None:
        raise ValueError("TRACE_MUST_HAVE_REAL_CAPTURE_UTC")
    inputs=[]
    for alias in sorted(contents):
        if alias not in meta:
            raise ValueError("UNPINNED_SOURCE_INPUT")
        inputs.append(source_detail(alias,contents[alias],meta[alias]))
    # Alias/error type only. Do not copy confidential provider error bodies.
    return {"schema":SCHEMA,
            "collector_first_observed_utc":collected,
            "first_seen_meaning":"COLLECTOR_CAPTURE_NOT_HISTORICAL_EVENT_PUBLICATION",
            "source_count":len(inputs),
            "missing_source_count":len(errors),
            "missing_source_types":{k:v.get("type","UNKNOWN") for k,v in sorted(errors.items())},
            "inputs":inputs,
            "historical_dates_are_not_prospective_signal_times":True,
            "completed_forward_tests_inferred":0,
            "paper_approved":False,
            "live_approved":False,
            "raw_price_or_private_position_data_exported":False}
