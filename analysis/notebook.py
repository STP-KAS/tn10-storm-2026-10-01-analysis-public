#!/usr/bin/env python3
"""Rebuild every number in analysis/REPORT.md and analysis/mainnet-cost.md from data/.

Run from the repo root:
    python analysis/notebook.py

Writes analysis/facts.json and analysis/charts/*.png.
No network calls. Mainnet price and consensus constants are the values recorded
in MAINNET below, with the URL and read time next to each one.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "analysis"
CHARTS = OUT / "charts"

CEST = timezone(timedelta(hours=2))

# Recorded 2026-10-01T22:09:55Z from CoinGecko.
# GET https://api.coingecko.com/api/v3/simple/price?ids=kaspa&vs_currencies=usd&include_last_updated_at=true
# Body: {"kaspa":{"usd":0.04130969,"last_updated_at":1790892490}}
# HTTP Date: Thu, 01 Oct 2026 22:09:55 GMT
KAS_USD = 0.04130969
KAS_USD_READ = "2026-10-01T22:09:55Z"
KAS_USD_SOURCE = "https://api.coingecko.com/api/v3/simple/price?ids=kaspa&vs_currencies=usd&include_last_updated_at=true"

# rusty-kaspa commit 01b532e8b553523216471682649693af92f0fd16, read 2026-10-01.
# consensus/core/src/config/params.rs MAINNET_PARAMS
# mining/src/mempool/config.rs DEFAULT_MINIMUM_RELAY_TRANSACTION_FEE
# consensus/core/src/constants.rs STORAGE_MASS_PARAMETER, TRANSIENT_BYTE_TO_MASS_FACTOR
# consensus/core/src/mass/mod.rs and mass/units.rs
RUSTY = "https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16"
MAINNET = {
    "commit": "01b532e8b553523216471682649693af92f0fd16",
    "bps": 10,  # BlockrateParams::new::<10>(), params.rs MAINNET_PARAMS.blockrate
    "pre_crescendo_ms": 1000,  # pre_crescendo_target_time_per_block
    "crescendo_daa": 110_165_000,  # comment in params.rs: roughly 2025-05-05 1500 UTC
    "compute_limit": 500_000,
    "storage_limit": 500_000,
    "transient_limit": 1_000_000,
    "mass_per_tx_byte": 1,
    "mass_per_spk_byte": 10,
    "grams_per_sigop": 1000,  # consensus/core/src/mass/units.rs GRAMS_PER_SIGOP_COUNT_UNIT
    "storage_mass_parameter": 100_000_000 * 10_000,  # SOMPI_PER_KASPA * 10_000
    "transient_byte_factor": 4,
    "relay_sompi_per_kg": 100_000,  # config.rs: 100 sompi per gram
    "relay_sompi_per_gram": 100,
    # Standard v0 1-in-1-out, empty payload, no covenant.
    # Sigscript 66 bytes: 1-byte push of a 64-byte Schnorr sig plus 1 sighash byte.
    # SPK 34 bytes: 1-byte push of a 32-byte x-only key plus OP_CHECKSIG. 1 sigop.
    "sigscript_len": 66,
    "spk_len": 34,
    "hash_size": 32,
    "subnetwork_id_size": 20,
    "hop_sompi_example": 40_000_000,  # 0.4 tKAS, middle of the README 0.2-0.6 range. Assumption, not measured.
}


def load_jsonl(name: str) -> list[dict]:
    rows = []
    path = DATA / name
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def parse_time(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    if len(text) >= 5 and text[-5] in "+-" and text[-3] != ":":
        text = text[:-2] + ":" + text[-2:]
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cest(dt: datetime) -> str:
    return dt.astimezone(CEST).strftime("%Y-%m-%d %H:%M:%S CEST")


def both(dt: datetime) -> str:
    return f"{iso(dt)} ({cest(dt)})"


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - rank) + ordered[hi] * (rank - lo)


def rolling_max(pairs: list[tuple[datetime, float]], window: timedelta, *, rate_from_counts: bool = False) -> dict | None:
    """Max of a trailing window.

    If the values are already rates sampled on a steady cadence, the result is
    their mean. If the values are event counts on sparse seconds, the result is
    sum(counts) / span, so missing seconds count as zero.
    """
    if not pairs:
        return None
    best = None
    start = 0
    total = 0.0
    for end, (t, v) in enumerate(pairs):
        total += v
        while pairs[start][0] < t - window:
            total -= pairs[start][1]
            start += 1
        span = (t - pairs[start][0]).total_seconds()
        if span < window.total_seconds() * 0.8:
            continue
        n = end - start + 1
        mean = (total / span) if rate_from_counts else (total / n)
        if best is None or mean > best["mean"]:
            best = {
                "mean": round(mean, 4),
                "from": iso(pairs[start][0]),
                "to": iso(t),
                "n": n,
                "span_s": round(span, 1),
            }
    return best


def tx_serialized_size() -> int:
    p = MAINNET
    header = 2 + 8 + 8 + 8 + p["subnetwork_id_size"] + 8 + p["hash_size"] + 8
    inp = (p["hash_size"] + 4) + 8 + p["sigscript_len"] + 8
    out = 8 + 2 + 8 + p["spk_len"]
    return header + inp + out


def shape_masses(output_sompi: int, fee_sompi: int) -> dict:
    size = tx_serialized_size()
    spk_mass = (2 + MAINNET["spk_len"]) * MAINNET["mass_per_spk_byte"]
    compute = size * MAINNET["mass_per_tx_byte"] + spk_mass + MAINNET["grams_per_sigop"]
    transient = size * MAINNET["transient_byte_factor"]
    cofactor_t = MAINNET["compute_limit"] / MAINNET["transient_limit"]
    transient_norm = math.ceil(transient * cofactor_t)
    fee_mass = max(compute, transient_norm)
    # Relaxed KIP-9 path, plurality 1, one input and one output.
    # storage = max(0, C/out - C/inp) = C * fee / (out * inp), integer division as in calc_storage_mass.
    c = MAINNET["storage_mass_parameter"]
    inp = output_sompi + fee_sompi
    storage = max(0, (c // output_sompi) - (c // inp)) if output_sompi and inp else None
    floor_fee = fee_mass * MAINNET["relay_sompi_per_kg"] // 1000
    return {
        "serialized_bytes": size,
        "compute_mass": compute,
        "transient_mass": transient,
        "transient_normalized": transient_norm,
        "fee_mass": fee_mass,
        "storage_mass_at_example_output": storage,
        "floor_fee_sompi": floor_fee,
        "output_sompi_example": output_sompi,
        "fee_sompi_assumed_for_storage": fee_sompi,
    }


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    host = [r for r in load_jsonl("host.jsonl") if r.get("type") == "host" and r.get("rate")]
    watch = load_jsonl("storm-watch.jsonl")
    health = [r for r in load_jsonl("api-health-min.jsonl") if r.get("type") == "health"]
    mined = [r for r in load_jsonl("api-mined-watch.jsonl") if r.get("type") == "mined"]
    vcc = load_jsonl("tn10-n0-vcc.jsonl")
    rpc = load_jsonl("tn10-n0-rpc.jsonl")
    fees = load_jsonl("feerate.jsonl")
    api = [r for r in load_jsonl("api-tn10.jsonl") if r.get("type") == "api"]
    runner = list(DATA.glob("runner*.jsonl")) + list(DATA.glob("storm*.out")) + list(ROOT.glob("notes/timeline.md"))

    host_t = [parse_time(r["ts"]) for r in host]
    host_tx = [r["rate"]["tx_processed_per_s"] for r in host]
    host_chain = [r["rate"]["chain_blocks_per_s"] for r in host]
    host_daa = [r["rate"]["daa_per_s"] for r in host]
    host_mp = [r.get("mempool") for r in host]
    host_disk = [r["disk_free_gb"] for r in host]
    host_cpu = [r["kaspad"].get("cpu_pct") for r in host if r.get("kaspad", {}).get("cpu_pct") is not None]
    host_rss = [r["kaspad"].get("rssMB") for r in host if r.get("kaspad", {}).get("rssMB") is not None]
    host_load = [r["load"][0] for r in host if r.get("load")]
    host_tips = [r["c"]["tips"] for r in host if r.get("c")]

    first_c = host[0]["c"]["txProcessed"]
    last_c = host[-1]["c"]["txProcessed"]
    span_s = (host_t[-1] - host_t[0]).total_seconds()
    processed_total = last_c - first_c
    processed_avg = processed_total / span_s

    # Virtual-chain accepted txs. Cross-check `a` against the kit's per-minute histogram.
    per_min_a = defaultdict(int)
    per_min_n = defaultdict(int)
    for row in vcc:
        t = datetime.fromtimestamp(row["t"] / 1000, tz=timezone.utc).replace(second=0, microsecond=0)
        per_min_a[t] += int(row.get("a") or 0)
        per_min_n[t] += 1
    minutes = [r for r in rpc if r.get("type") == "minute" and not r.get("partial")]
    compared = []
    for row in minutes:
        # minute field is UTC "YYYY-MM-DDTHH:MMZ".
        key = datetime.fromisoformat(row["minute"].replace("Z", "+00:00"))
        if key.tzinfo is None:
            key = key.replace(tzinfo=timezone.utc)
        key = key.astimezone(timezone.utc).replace(second=0, microsecond=0)
        hist_sum = sum(int(k) * int(v) for k, v in (row.get("hist") or {}).items())
        compared.append({"minute": iso(key), "hist": hist_sum, "vcc_a": per_min_a.get(key, 0), "hist_n": row.get("n"), "vcc_n": per_min_n.get(key, 0)})
    matched = sum(1 for row in compared if row["hist"] == row["vcc_a"])

    sec_bins = defaultdict(int)
    for row in vcc:
        sec = int(row["t"] // 1000)
        sec_bins[sec] += int(row.get("a") or 0)
    if sec_bins:
        vcc_pairs = [(datetime.fromtimestamp(s, tz=timezone.utc), c) for s, c in sorted(sec_bins.items())]
    else:
        vcc_pairs = []
    vcc_total = sum(sec_bins.values())
    vcc_span = (vcc_pairs[-1][0] - vcc_pairs[0][0]).total_seconds() if len(vcc_pairs) > 1 else None
    vcc_avg = (vcc_total / vcc_span) if vcc_span else None

    one_min = rolling_max([(t, v) for t, v in zip(host_t, host_tx)], timedelta(minutes=1))
    ten_min = rolling_max([(t, v) for t, v in zip(host_t, host_tx)], timedelta(minutes=10))
    one_hour = rolling_max([(t, v) for t, v in zip(host_t, host_tx)], timedelta(hours=1))
    vcc_1 = rolling_max(vcc_pairs, timedelta(minutes=1), rate_from_counts=True)
    vcc_10 = rolling_max(vcc_pairs, timedelta(minutes=10), rate_from_counts=True)
    vcc_60 = rolling_max(vcc_pairs, timedelta(hours=1), rate_from_counts=True)

    # Phase from storm-watch.
    watch_rows = []
    for row in watch:
        t = parse_time(row["t"])
        watch_rows.append({**row, "_t": t})
    why = Counter(row.get("rate_why") or "" for row in watch_rows)
    pauses = Counter(row.get("pause") or "" for row in watch_rows)
    reasons = Counter(row.get("reason") or "" for row in watch_rows)
    rates = Counter(row.get("smx_rate") for row in watch_rows)
    sink = [float(row["sinkAgeS"]) for row in watch_rows if row.get("sinkAgeS") is not None]
    watch_mp = [row.get("mempool") for row in watch_rows if row.get("mempool") is not None]

    def phase_bounds(name: str) -> dict | None:
        rows = [row for row in watch_rows if row.get("rate_why") == name]
        if not rows:
            return None
        return {"from": both(rows[0]["_t"]), "to": both(rows[-1]["_t"]), "n": len(rows), "from_iso": iso(rows[0]["_t"]), "to_iso": iso(rows[-1]["_t"])}

    # Disk slope, GB used per hour (free falling is positive usage).
    t0 = host_t[0]
    xs = [(t - t0).total_seconds() / 3600 for t in host_t]
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(host_disk)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, host_disk)) / var_x  # GB free per hour
    used_per_hour = -slope

    # Share. Each host line is one 15 s window, then the sampler resets the counters.
    share = {"box": 0, "desk": 0, "network": 0, "blocks": 0}
    hourly = defaultdict(lambda: {"box": 0, "desk": 0, "network": 0, "blocks": 0})
    for row, t in zip(host, host_t):
        s = row.get("share") or {}
        for key in share:
            share[key] += int(s.get(key) or 0)
            hourly[t.strftime("%Y-%m-%dT%H:00Z")][key] += int(s.get(key) or 0)
    ours = share["box"] + share["desk"]
    ours_pct = (100.0 * ours / share["blocks"]) if share["blocks"] else None

    # API.
    http = Counter(row.get("http") for row in health)
    stall = sum(1 for row in health if row.get("stall_suspected") is True)
    lags = [row["acceptedTxBlockTimeDiff"] for row in health if row.get("acceptedTxBlockTimeDiff") is not None]
    blue = [row["blueScoreDiff"] for row in health if row.get("blueScoreDiff") is not None]
    latency = [row["ms"] for row in health if row.get("ms") is not None]
    cache = Counter(row.get("cf_cache_status") for row in health)
    versions = Counter()
    for row in health:
        for backend in row.get("backends") or []:
            versions[backend.get("v")] += 1
    mined_stall = sum(1 for row in mined if row.get("mined_stall") is True)
    coin_lag = [row["newest_coinbase_lag_s"] for row in mined if row.get("newest_coinbase_lag_s") is not None]
    mined_http = Counter(row.get("http") for row in mined)
    mined_cache = Counter(row.get("cf_cache_status") for row in mined)

    polls = [r for r in rpc if r.get("type") == "poll" and r.get("fee")]
    poll_fee = []
    for row in polls:
        fee = row["fee"]
        normal = fee.get("normal") or [{}]
        poll_fee.append(
            {
                "t": row["ts"],
                "priority": fee.get("priority", {}).get("feerate"),
                "normal": normal[0].get("feerate") if normal else None,
                "mempool": (row.get("info") or {}).get("mempoolSize"),
                "synced": (row.get("info") or {}).get("isSynced"),
                "version": (row.get("info") or {}).get("serverVersion"),
                "utxo": (row.get("info") or {}).get("isUtxoIndexed"),
                "tips": (row.get("dag") or {}).get("tips"),
            }
        )
    reorgs = [r for r in rpc if r.get("type") == "deep_reorg"]
    removed_n = [int(r.get("removed") or 0) for r in reorgs]

    fee_used = Counter(row.get("feerate_used") for row in fees)
    fee_span = None
    if fees:
        fee_span = {"from": fees[0]["t"], "to": fees[-1]["t"], "n": len(fees), "used": fee_used}

    def counter_rate(start_iso: str, end_iso: str) -> dict | None:
        a = parse_time(start_iso)
        b = parse_time(end_iso)
        rows = [(t, r) for r, t in zip(host, host_t) if a <= t < b and r.get("c")]
        if len(rows) < 2:
            return None
        dt = (rows[-1][0] - rows[0][0]).total_seconds()
        delta = rows[-1][1]["c"]["txProcessed"] - rows[0][1]["c"]["txProcessed"]
        return {
            "from": iso(rows[0][0]),
            "to": iso(rows[-1][0]),
            "tx_processed": delta,
            "span_s": round(dt, 1),
            "per_s": round(delta / dt, 3),
        }

    phase_rates = {
        "pre_prune": counter_rate("2026-10-01T16:41:00Z", "2026-10-01T17:05:00Z"),
        "prune": counter_rate("2026-10-01T17:05:00Z", "2026-10-01T18:10:00Z"),
        "after_prune": counter_rate("2026-10-01T18:10:00Z", "2026-10-01T18:23:00Z"),
        "smoke_bump": counter_rate("2026-10-01T18:15:00Z", "2026-10-01T18:18:00Z"),
    }

    masses = shape_masses(MAINNET["hop_sompi_example"], 1624 * 100)
    # Recompute storage with the floor fee the formula itself produces, once.
    masses = shape_masses(MAINNET["hop_sompi_example"], masses["floor_fee_sompi"])
    per_block = MAINNET["compute_limit"] // masses["compute_mass"]
    chain_tx_s = per_block * MAINNET["bps"]

    def cost(tx_s: float, feerate: float, seconds: float) -> dict:
        fee_sompi = masses["fee_mass"] * feerate  # feerate is sompi/gram; fee_mass already in grams
        # Integer relay path divides sompi/kg by 1000. At 100 sompi/g that is exact.
        # For a non-integer feerate, keep the gram product. TN10 quotes were integers.
        sompi = fee_sompi * tx_s * seconds
        kas = sompi / 1e8
        return {
            "tx_s": tx_s,
            "feerate_sompi_per_gram": feerate,
            "seconds": seconds,
            "fee_sompi_per_tx": fee_sompi,
            "kas": kas,
            "usd": kas * KAS_USD,
        }

    # `a` matches rpc minute.added (selected-chain blocks), not accepted transactions.
    # Accepted tx/s is therefore not taken from tn10-n0-vcc.jsonl.
    measured_sustained = processed_avg
    durations = {
        "10 min": 600,
        "1 h": 3600,
        "6 h": 6 * 3600,
        "24 h": 24 * 3600,
        "7 d": 7 * 24 * 3600,
    }
    scenarios = {}
    if measured_sustained is not None:
        scenarios["A_floor_sustained"] = {name: cost(measured_sustained, 100, secs) for name, secs in durations.items()}
        scenarios["B_same_as_A"] = (
            "Across 609 polls, priority feerate was 100 sompi/gram except one poll at 102.00 "
            "(2026-10-01T17:01:01Z, mempool 51). n0 mempool peaked at 216. "
            "No higher fee was required to get into a block during this slice."
        )
    # README design band. Not measured. Kept out of the verified table.
    design = {
        "low_1200": {name: cost(1200, 100, secs) for name, secs in durations.items()},
        "high_2500": {name: cost(2500, 100, secs) for name, secs in durations.items()},
        "label": "README run-design target 1200-2500 tx/s. Not measured in data/.",
    }

    facts = {
        "generated_note": "Rebuilt by analysis/notebook.py from data/. Interim: samplers stop together just after 18:22Z.",
        "coverage": {
            "host": {"n": len(host), "from": both(host_t[0]), "to": both(host_t[-1])},
            "vcc": {"n": len(vcc), "from": iso(vcc_pairs[0][0]), "to": iso(vcc_pairs[-1][0]), "sum_a": vcc_total},
            "watch": {"n": len(watch_rows), "from": both(watch_rows[0]["_t"]), "to": both(watch_rows[-1]["_t"])},
            "health": {"n": len(health), "from": health[0]["ts"], "to": health[-1]["ts"]},
            "mined": {"n": len(mined), "from": mined[0]["ts"], "to": mined[-1]["ts"]},
            "fees": fee_span,
            "runner_files": [p.name for p in runner],
            "timeline_md": (ROOT / "notes" / "timeline.md").exists(),
        },
        "vcc_vs_minute_hist": {"minutes_compared": len(compared), "exact_matches": matched, "examples": compared[:3] + compared[-2:]},
        "throughput": {
            "host_tx_processed_counter_delta": processed_total,
            "host_span_s": round(span_s, 1),
            "host_counter_avg_per_s": round(processed_avg, 3),
            "host_sample_peak": max(host_tx),
            "host_1min": one_min,
            "host_10min": ten_min,
            "host_1h": one_hour,
            "vcc_sum_a": vcc_total,
            "vcc_avg_per_s": None if vcc_avg is None else round(vcc_avg, 4),
            "vcc_1min": vcc_1,
            "vcc_10min": vcc_10,
            "vcc_1h": vcc_60,
            "phase_rates_tx_processed": phase_rates,
        "processed_counter_note": "nodeTransactionsProcessedCount covers every transaction in every block body the node handled. host_sampler.mjs says this overcounts parallel blocks by about 1.337 (its round 7 comment). That factor is not re-measured here. This counter is not our submit count.",
            "chain_blocks_per_s_median": round(statistics.median(host_chain), 3),
            "daa_per_s_median": round(statistics.median(host_daa), 3),
            "daa_per_s_min": min(host_daa),
            "daa_per_s_max": max(host_daa),
        },
        "phases": {
            "why": dict(why),
            "smx_rate": {str(k): v for k, v in rates.items()},
            "pause": dict(pauses),
            "reason": dict(reasons),
            "prune": phase_bounds("prune-window"),
            "full": phase_bounds("full"),
        },
        "health": {
            "mempool_host_max": max(v for v in host_mp if v is not None),
            "mempool_host_min": min(v for v in host_mp if v is not None),
            "mempool_watch_max": max(watch_mp) if watch_mp else None,
            "sink_age_max_s": max(sink) if sink else None,
            "sink_age_median_s": statistics.median(sink) if sink else None,
            "synced_false": sum(1 for row in watch_rows if row.get("synced") is False),
            "cpu_pct_max": max(host_cpu) if host_cpu else None,
            "cpu_pct_median": statistics.median(host_cpu) if host_cpu else None,
            "rss_mb_first": host_rss[0] if host_rss else None,
            "rss_mb_last": host_rss[-1] if host_rss else None,
            "rss_mb_max": max(host_rss) if host_rss else None,
            "load1_max": max(host_load) if host_load else None,
            "load1_median": statistics.median(host_load) if host_load else None,
            "tips_min": min(host_tips) if host_tips else None,
            "tips_max": max(host_tips) if host_tips else None,
            "disk_free_gb_first": host_disk[0],
            "disk_free_gb_last": host_disk[-1],
            "disk_free_gb_min": min(host_disk),
            "disk_net_used_gb": round(host_disk[0] - host_disk[-1], 3),
            "disk_net_used_gb_per_hour": round((host_disk[0] - host_disk[-1]) / (span_s / 3600), 4),
            "disk_regression_used_gb_per_hour": round(used_per_hour, 4),
            "disk_note": "Free space dipped and recovered (pruning). The net first-to-last change is the figure to project. The regression is steeper because of that dip.",
            "deep_reorg_events": len(reorgs),
            "deep_reorg_removed_max": max(removed_n) if removed_n else None,
            "deep_reorg_removed_median": statistics.median(removed_n) if removed_n else None,
            "n0_version": poll_fee[0]["version"] if poll_fee else None,
            "n0_utxoindex": poll_fee[0]["utxo"] if poll_fee else None,
            "polls": len(poll_fee),
            "poll_priority_feerate_set": sorted({row["priority"] for row in poll_fee}),
            "poll_normal_feerate_set": sorted({row["normal"] for row in poll_fee}),
            "poll_synced_false": sum(1 for row in poll_fee if row["synced"] is False),
            "poll_mempool_max": max(row["mempool"] for row in poll_fee if row["mempool"] is not None),
        },
        "share": {
            **share,
            "ours": ours,
            "ours_pct": None if ours_pct is None else round(ours_pct, 2),
            "hourly": hourly,
        },
        "api": {
            "http": dict(http),
            "stall_suspected_true": stall,
            "accepted_tx_lag_s_min": min(lags) if lags else None,
            "accepted_tx_lag_s_median": statistics.median(lags) if lags else None,
            "accepted_tx_lag_s_max": max(lags) if lags else None,
            "blue_score_diff_max": max(blue) if blue else None,
            "latency_ms_median": statistics.median(latency) if latency else None,
            "latency_ms_max": max(latency) if latency else None,
            "cf_cache": dict(cache),
            "backend_versions": dict(versions),
            "mined_stall_true": mined_stall,
            "mined_http": dict(mined_http),
            "mined_cf_cache": dict(mined_cache),
            "coinbase_lag_s_min": min(coin_lag) if coin_lag else None,
            "coinbase_lag_s_median": statistics.median(coin_lag) if coin_lag else None,
            "coinbase_lag_s_max": max(coin_lag) if coin_lag else None,
            "api_tn10_rows": len(api),
        },
        "mass": masses,
        "mainnet_capacity_tx_s": chain_tx_s,
        "tx_per_block_compute": per_block,
        "fraction_of_mainnet_compute_at_processed_avg": round(processed_avg / chain_tx_s, 6),
        "vcc_a_is": "added selected-chain blocks per notification. It matches rpc minute.added. It is not an accepted-tx count. README's description of this file does not match the fields.",
        "scenarios_measured": scenarios,
        "scenarios_design_not_measured": design,
        "kas_usd": {"price": KAS_USD, "read": KAS_USD_READ, "source": KAS_USD_SOURCE},
        "round6_claim": {
            "source": "https://github.com/STP-KAS/tn10-storm-2026-09-26-r6 README headline, read 2026-10-01",
            "submitted": 10_117_549,
            "accepted": 10_058_024,
            "window_min": 159,
            "gusto_tx_s": 1191,
            "whole_round_tx_s": 1057,
            "note": "Those figures are that repo's report. This notebook does not re-sum round 6 logs.",
        },
    }

    (OUT / "facts.json").write_text(json.dumps(facts, indent=2, default=str), encoding="utf-8")

    # Charts
    def stamp(ax, title, ylabel):
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.set_xlabel("UTC on 2026-10-01")

    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(host_t, host_tx, color="#1f4e79", lw=1.2, label="host tx_processed_per_s (15 s, all txs the node handled)")
    stamp(ax, "TN10 n0 body-processing rate (interim slice)", "tx/s")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS / "tx-per-s.png", dpi=120)
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(host_t, host_mp, color="#1f4e79", lw=1.2, label="host.jsonl mempool")
    ax.plot([r["_t"] for r in watch_rows], [r.get("mempool") or 0 for r in watch_rows], color="#548235", lw=1.0, alpha=0.8, label="storm-watch mempool")
    stamp(ax, "n0 mempool size", "transactions")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS / "mempool.png", dpi=120)
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(host_t, host_disk, color="#1f4e79", lw=1.2)
    stamp(ax, "Disk free on the n0 host", "GB free")
    fig.tight_layout()
    fig.savefig(CHARTS / "disk.png", dpi=120)
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 4.2))
    ht = [parse_time(r["ts"]) for r in health if r.get("acceptedTxBlockTimeDiff") is not None]
    ax.plot(ht, lags, color="#c45911", lw=1.2, label="acceptedTxBlockTimeDiff (s)")
    ax2 = ax.twinx()
    ax2.plot(host_t, host_tx, color="#1f4e79", lw=1.0, alpha=0.7, label="tx_processed_per_s")
    ax.set_title("Public API accepted-tx lag vs n0 processed tx/s")
    ax.set_ylabel("API lag (s)")
    ax2.set_ylabel("tx/s")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_xlabel("UTC on 2026-10-01")
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS / "api-lag.png", dpi=120)
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 4.2))
    hours = sorted(hourly)
    x = range(len(hours))
    box = [hourly[h]["box"] for h in hours]
    desk = [hourly[h]["desk"] for h in hours]
    net = [hourly[h]["network"] for h in hours]
    ax.bar(x, box, color="#c45911", label="box")
    ax.bar(x, desk, bottom=box, color="#1f4e79", label="desk")
    bottom = [b + d for b, d in zip(box, desk)]
    ax.bar(x, net, bottom=bottom, color="#a6a6a6", label="rest of network")
    ax.set_xticks(list(x))
    ax.set_xticklabels(hours, rotation=15, ha="right")
    ax.set_title("Blocks seen by n0, by who mined them")
    ax.set_ylabel("blocks in host.jsonl share windows")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHARTS / "block-share.png", dpi=120)
    plt.close()

    print(json.dumps({
        "coverage_to": facts["coverage"]["host"]["to"],
        "processed_avg": facts["throughput"]["host_counter_avg_per_s"],
        "vcc_avg": facts["throughput"]["vcc_avg_per_s"],
        "vcc_match": f"{matched}/{len(compared)}",
        "mempool_max": facts["health"]["mempool_host_max"],
        "sink_max": facts["health"]["sink_age_max_s"],
        "ours_pct": facts["share"]["ours_pct"],
        "stalls": stall,
        "mined_stalls": mined_stall,
        "fee_mass": masses["fee_mass"],
        "floor_fee": masses["floor_fee_sompi"],
        "capacity": chain_tx_s,
        "disk_net_gb_h": facts["health"]["disk_net_used_gb_per_hour"],
        "disk_min": facts["health"]["disk_free_gb_min"],
        "why": facts["phases"]["why"],
        "reorgs": len(reorgs),
        "removed_max": facts["health"]["deep_reorg_removed_max"],
    }, indent=2))


if __name__ == "__main__":
    main()
