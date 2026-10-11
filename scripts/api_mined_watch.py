#!/usr/bin/env python3
"""READ-ONLY. Every --interval s (default 300 = the 5-min public-API rule) asks api-tn10 for the newest txs of our
mining address and compares the newest COINBASE it shows (subnetwork 01..) with our own node's truth (blocks we mined
in the same window, from host.jsonl --share, written by host_sampler from n0 block-added notifications).
mined_stall = API's newest coinbase is > --stall s old WHILE n0 shows we mined blocks in the last window.
That is the 'mining blocks stop showing during the storm' proof stp asked for. Every call is logged to --apilog."""
import argparse, json, os, signal, time, urllib.request, urllib.error
from datetime import datetime, timezone
ADDR = "[address]"
UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/128.0 Safari/537.36"
STOP = False
def _stop(*_):
    global STOP; STOP = True
def z(t=None): return datetime.fromtimestamp(t if t else time.time(), tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
def node_mined(host_path, window):
    cut = time.time() - window; ours = blocks = 0
    try:
        with open(host_path, "rb") as f:
            f.seek(0, 2); f.seek(max(0, f.tell() - 200_000)); lines = f.read().decode(errors="ignore").splitlines()[1:]
        for ln in lines:
            try: r = json.loads(ln)
            except Exception: continue
            s = r.get("share"); ts = r.get("ts")
            if not s or not ts: continue
            if datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() < cut: continue
            ours += s.get("box", 0) + s.get("desk", 0); blocks += s.get("blocks", 0)
    except FileNotFoundError: return None, None
    return ours, blocks
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=300.0); ap.add_argument("--stall", type=float, default=300.0)
    ap.add_argument("--base", default="https://api-tn10.kaspa.org")
    ap.add_argument("--out", default="[local path]")
    ap.add_argument("--host", default="[local path]")
    ap.add_argument("--apilog", default="[local path]")
    ap.add_argument("--once", action="store_true"); a = ap.parse_args()
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    with open(a.out, "a", buffering=1) as f:
        f.write(json.dumps({"type": "start", "ts": z(), "pid": os.getpid(), "interval": a.interval, "addr": ADDR}) + "\n")
        nxt = time.time()
        while not STOP:
            url = f"{a.base}/addresses/{ADDR}/full-transactions-page?limit=50&resolve_previous_outpoints=no&fields=transaction_id,block_time,subnetwork_id,is_accepted"
            with open(a.apilog, "a") as al:
                al.write(f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] GET {url} (api_mined_watch, interval={a.interval}s)\n")
            rec = {"type": "mined", "ts": z()}; t0 = time.time()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", "Cache-Control": "no-cache"})
                try:
                    with urllib.request.urlopen(req, timeout=30) as r: code, hdrs, body = r.status, dict(r.headers), r.read()
                except urllib.error.HTTPError as e: code, hdrs, body = e.code, dict(e.headers or {}), (e.read() if hasattr(e, "read") else b"")
                h = {k.lower(): v for k, v in hdrs.items()}
                rec.update({"http": code, "ms": round((time.time() - t0) * 1000), "cf_cache_status": h.get("cf-cache-status"), "age": h.get("age")})
                j = json.loads(body) if body else []
                if isinstance(j, list):
                    cb = [t for t in j if str(t.get("subnetwork_id", "")).startswith("01")]
                    rec["txs_returned"] = len(j); rec["coinbases_returned"] = len(cb)
                    if j: rec["newest_tx_lag_s"] = round(time.time() - j[0]["block_time"] / 1000, 1)
                    if cb:
                        rec["newest_coinbase_id"] = cb[0]["transaction_id"]; rec["newest_coinbase_time"] = z(cb[0]["block_time"] / 1000)
                        rec["newest_coinbase_lag_s"] = round(time.time() - cb[0]["block_time"] / 1000, 1)
                else: rec["body"] = str(j)[:200]
            except Exception as e: rec["error"] = repr(e)[:200]
            ours, blocks = node_mined(a.host, a.interval)
            rec["node_ours_last_window"] = ours; rec["node_blocks_last_window"] = blocks
            lag = rec.get("newest_coinbase_lag_s")
            rec["mined_stall"] = bool(ours and (lag is None or lag > a.stall))
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")
            if a.once: break
            nxt += a.interval
            while not STOP and time.time() < nxt: time.sleep(1)
if __name__ == "__main__": main()
