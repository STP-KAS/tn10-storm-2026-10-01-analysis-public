# Grok Build prompt: analyse the TN10 storm (1–2 Oct 2026) and estimate mainnet attack cost

Paste everything below into Grok Build on stp's desk.

---

You are analysing a Kaspa **Testnet-10** stress test run by my bot team. Repo (private, mine): `https://github.com/STP-KAS/tn10-storm-2026-10-01-analysis-public`.
Clone it (or `git pull` if you already have it). Grok Bot pushes fresh raw data to `data/` about every 30 min while the storm runs (24 h from about 20:15 CEST on 1 Oct 2026). Read `README.md` first: it explains the run design and every data file.

## Rules
1. Never invent a number. Every figure needs a source: a data file + timestamp(s), a line of code with its URL, or a web page with its URL and the date you read it. If something can't be computed from the data, write "not measured".
2. Keep "Claims" (what someone said or expected) apart from "Verified" (what the data shows).
3. TN10 data only. Don't send any transaction, don't touch any node, don't call api-tn10 or any other public API more often than once per 5 min (you shouldn't need it at all: the data is here).
4. Don't post anything publicly. No issues, PRs, comments or reactions on anyone else's repo. No tags or releases. You may commit only to this repo, in `analysis/`.
5. Our side mines a large share of TN10 blocks, so many of the fees we paid came back to our own mining address. Keep self-mined numbers **separate** everywhere.

## Part 1: what happened (from `data/`)
Work in Python (pandas + matplotlib is fine). Save charts as PNG in `analysis/charts/`.
1. **Timeline.** Baseline, smoke test, ramp steps, full speed, pruning-window slowdowns, any disk/mempool slowdowns or stops (from `storm-watch.jsonl`), KNS start at about 21:15 CEST, and the end. Use UTC in tables and add CEST in brackets.
2. **Throughput.** Tx/s submitted vs accepted on chain (runner files vs `tn10-n0-vcc.jsonl` accepted counts vs `host.jsonl` `tx_processed_per_s`). Peak 1-min, peak 10-min, sustained 1 h and full-run averages, and total txs. Compare with round 6 (about 10.1M txs in about 159 min, around 1,060–1,200 tx/s). Say clearly whether we beat it and on which measure.
3. **Node health.** Mempool size, kaspad CPU and RAM, load, disk growth in GB per hour (and the projected GB per 24 h at the measured tx/s), sink age or lag, tips, blocks/s. Did n0 ever fall behind? When and how far?
4. **Block share and fees.** From `host.jsonl` `share`: blocks mined by desk / box / rest of network per hour. Estimate fees paid in total and the part that went to our own mining address (use the mined share as the proxy and say so). Net cost to us.
5. **Public API under load (the key question).**
   - `api-health-min.jsonl`: `acceptedTxBlockTimeDiff`, `blueScoreDiff`, HTTP codes, latency, backend versions, `stall_suspected`.
   - `api-mined-watch.jsonl`: did the public API keep showing our newest mined blocks (coinbases) while n0 says we kept mining them? Find every period where `mined_stall` is true or `newest_coinbase_lag_s` grows, and line it up against the storm's tx/s.
   - Last time, the explorer's "mined blocks" stopped updating fairly quickly. If it happens again, that's evidence the public indexer/API fails under a storm while the node keeps working. If it doesn't, say so: the fix held.
   - Be careful about cause vs correlation. Cloudflare caching (`cf_cache_status`, `age`) and backend switches (2.0.1 vs 2.1.0) are alternative explanations.
6. **dApp impact.** KNS registrations at 50/min during the storm: success rate and latency if the data is in the repo; otherwise mark it "data from the kns bot, not in repo".

## Part 2: what the same attack would cost on **mainnet**
On TN10 we get a big refund because our miners win a lot of the blocks. On mainnet an attacker has **no** such refund (assume 0% of hashrate). Estimate the cost of reproducing what we measured.
1. Look up and cite the current **mainnet** parameters from primary sources (rusty-kaspa source on GitHub and the official KIPs): blocks per second, block mass limit, minimum relay fee rate (sompi per gram), how the mass of a 1-input 1-output transaction is computed (compute mass plus KIP-9 storage mass), and how the fee estimator / mempool picks transactions under congestion. Show the mass of our transaction shape with the formula and inputs.
2. Use the **measured** TN10 rates from Part 1 (peak and sustained tx/s) and work out what fraction of mainnet block space that would fill.
3. Price: get the KAS/USD price from a named source and write down the exact date and time you read it.
4. Scenarios (table, in KAS and USD):
   - A. Floor fee, at our sustained rate.
   - B. Fee needed to stay ahead of honest users once blocks are full (use the fee level the TN10 data shows was needed, and the mainnet fee-estimator buckets, and explain the assumption).
   - C. Duration: 10 min burst, 1 h, 6 h, 24 h, 7 days.
   - Add the capital that must be parked in lanes (recoverable) and rough infrastructure cost (nodes, bandwidth), with stated assumptions.
5. Compare with our **net** TN10 cost (gross fees minus the self-mined refund) to show how much the refund hid.
6. Impact on honest users during such a storm: the fee they'd need to get in, confirmation delay, and the public API/indexer effect from Part 1. Short burst vs sustained.
Keep it as a resilience and cost analysis for Kaspa core developers. No step-by-step attack instructions beyond what the measurements need.

## Deliverables (commit to `analysis/` in this repo, then tell me the commit link)
- `analysis/REPORT.md` with sections: **What**, **Why**, **When**, **Facts** (table: metric, value, source file + timestamp), **Claims vs verified**, **Mainnet cost** (summary table), **Sources**, **Conclusion** (plain English, max 10 lines, with the three most important findings for Kaspa core).
- `analysis/mainnet-cost.md`: the full calculation, every input with its source.
- `analysis/charts/*.png`: tx/s, mempool, disk, API lag vs tx/s, block share.
- `analysis/notebook.py` (or `.ipynb`) that rebuilds every number from `data/`.
If the storm is still running when you start, do an interim pass, mark it **INTERIM** at the top, and redo it after the final data push.
