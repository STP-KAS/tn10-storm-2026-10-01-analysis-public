#!/usr/bin/env python3
"""TN10 ops asked for a per-minute api-tn10 /info/health logger (acceptedTxBlockTimeDiff, blueScoreDiff).
READ-ONLY. One cache-busted GET /info/health per tick. Appends one JSONL line per tick to --out, AND appends a
one-line audit entry per call to --apilog (every public-API call is logged, per the TN10 ops rule).
Default interval 300 s (<= every 5 min, the storm plan rule). Ops' per-minute ask = --interval 60 (1,440 calls/day);
see the plan's justification. Python stdlib only. No writes to any API.
"""
import argparse, json, os, signal, time, urllib.request, urllib.error
from datetime import datetime, timezone
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
STOP = False
def _stop(*_):
    global STOP; STOP = True
def z(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
def iso_ms(ms):
    try: return datetime.fromtimestamp(float(ms)/1000, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
    except Exception: return None
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=300.0, help="seconds between ticks (default 300; ops per-minute = 60)")
    ap.add_argument("--duration", type=float, default=0)
    ap.add_argument("--base", default="https://api-tn10.kaspa.org")
    ap.add_argument("--out", default="[local path]")
    ap.add_argument("--apilog", default="[local path]")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    t_end = time.time() + a.duration if a.duration > 0 else None
    with open(a.out, "a", buffering=1) as f:
        f.write(json.dumps({"type": "start", "ts": z(), "pid": os.getpid(), "interval": a.interval, "base": a.base}) + "\n")
        nxt = time.time()
        while not STOP:
            url = f"{a.base}/info/health?cb={time.time_ns()}"
            with open(a.apilog, "a") as al:
                al.write(f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] GET {url} (api_health_min, interval={a.interval}s)\n")
            rec = {"type": "health", "ts": z()}; t0 = time.time()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", "Cache-Control": "no-cache"})
                try:
                    with urllib.request.urlopen(req, timeout=20) as r:
                        code, hdrs, body = r.status, dict(r.headers), r.read()
                except urllib.error.HTTPError as e:            # 503 carries the JSON body (the stall signature)
                    code, hdrs, body = e.code, dict(e.headers or {}), (e.read() if hasattr(e, "read") else b"")
                h = {k.lower(): v for k, v in hdrs.items()}
                rec.update({"http": code, "ms": round((time.time()-t0)*1000), "cf_cache_status": h.get("cf-cache-status"), "cf_ray": h.get("cf-ray"), "age": h.get("age")})
                j = json.loads(body) if body else {}
                db = (j or {}).get("database") or {}
                rec["acceptedTxBlockTimeDiff"] = db.get("acceptedTxBlockTimeDiff")
                rec["blueScoreDiff"] = db.get("blueScoreDiff")
                rec["db_isSynced"] = db.get("isSynced")
                rec["db_blueScore"] = db.get("blueScore")
                rec["acceptedTxBlockTime_iso"] = iso_ms(db.get("acceptedTxBlockTime")) if db.get("acceptedTxBlockTime") else None
                rec["backends"] = [{"v": s.get("serverVersion"), "synced": s.get("isSynced"), "utxoIndexed": s.get("isUtxoIndexed")} for s in (j.get("kaspadServers") or [])]
                # STALL FLAG: acceptedTxBlockTimeDiff keeps growing while blueScoreDiff stays small -> indexer stalled (25 Sep signature)
                rec["stall_suspected"] = bool(db.get("acceptedTxBlockTimeDiff") and db.get("acceptedTxBlockTimeDiff") > 120 and (db.get("blueScoreDiff") or 0) < 200)
            except Exception as e:
                rec["error"] = repr(e)[:200]
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")
            if a.once: break
            nxt += a.interval
            while not STOP and time.time() < nxt and (t_end is None or time.time() < t_end): time.sleep(min(1.0, max(0.0, nxt - time.time())))
            if t_end is not None and time.time() >= t_end: break
        f.write(json.dumps({"type": "stop", "ts": z()}) + "\n")
if __name__ == "__main__": main()
