> **Experimental. We are just trying this.**
>
> We test, we write down what we think we saw, and that is the whole product. A number here is not the truth. A chart is not the truth. Any other sentence that sounds sure of itself is not the truth either. Do not count any of it as a claim.
>
> [Disclaimer](DISCLAIMER.md)
>
> **Part of [tn-master](https://github.com/STP-KAS/tn-master)**, the map of every TN10 storm. Renamed on 11 Oct 2026 from `tn10-storm-2026-10-analysis`; old links redirect here.
>
> ← previous storm: [tn10-storm-2026-10-01](https://github.com/STP-KAS/tn10-storm-2026-10-01) | next storm: [tn10-storm-2026-10-01-reports-public](https://github.com/STP-KAS/tn10-storm-2026-10-01-reports-public) →
>
> **Public clean copy** of `STP-KAS/tn10-storm-2026-10-01-analysis` (private, archived), made on 11 Oct 2026 from its current files only. IPs, tunnel hosts, wallet addresses, 64-hex hashes and local paths are replaced by `[ip]`, `[tunnel]`, `[address]`, `[hash]` and `[local path]`; dropped: control/STOP, desk/txids.csv. The full history stays private.

# TN10 storm, 1–2 Oct 2026: raw data for analysis (private)

> **Mainnet labels (added 4 Oct 2026).** Kaspa Testnet-10 only. Every statement about mainnet in this file now carries a label: **A** = shown on TN10, backed by our own measured data (TN10 only, never proof for mainnet); **B** = plausible for mainnet but unsure, reason given; **C** = unknown, needs more testing and review. Claims, evidence and the tests still needed: [TN10 storms: what they do and do not say about a mainnet storm](https://github.com/STP-KAS/tn10-storm-2026-10-01/blob/main/TN10-STORMS-MAINNET-IMPLICATIONS-2026-10-04.md).

Kaspa **Testnet-10 only**. A 24 h transaction storm sent through our own node n0 (kaspad 2.1.0, `uacomment 'stp grok bot'`).
Grok Bot (box) runs the load and the samplers and pushes the raw data here about every 30 minutes.
Grok Build (stp's desk) analyses it with `prompts/grok-build-analyse-storm.md`.

Nothing here is a finished claim. The data files are the evidence, and every finding must cite file + timestamp.

Desk public read, 2 Oct 2026: [`analysis/desk-public-read-2026-10-02.md`](analysis/desk-public-read-2026-10-02.md). It is the public REST view of the same storm, the cross-check against [`analysis/BOX-REPORT.md`](analysis/BOX-REPORT.md), and the mainnet minimum-fee bill for a raw 1-input 1-output with no hashrate refund (**B**: arithmetic, not a mainnet measurement).

## Run design (decided by stp, 1 Oct 2026)
- Recycled 1-in-1-out lanes (fixed set of throwaway addresses, coins hop between them), random 0.2–0.6 tKAS per hop, fee at 2x the node's normal estimate.
- Target 1,200–2,500 tx/s, ramped 25% → 50% → 100%. Pace drops to 25% in the pruning windows (07:05–08:05 and 19:05–20:10 CEST),
  to 50% below 22 GB free disk, to 25% below 20 GB, and pauses if the mempool tops 80k. Hard stop: node > 5 min behind, disk < 15%, STOP file, or stp.
- n0 runs **without utxoindex** during the run. Box miners are halted. Hashrate on our side comes from stp's 20 desk miners only (through n0).
- Our side mines a large share of TN10 blocks (about 25% at 18:51 CEST with box miners off; 59.5% in the 24 h before), so a big part of the fees comes back to our own mining address. **Self-mined results must be kept separate.**
- Timeline (CEST): baseline from 18:41:30 on 1 Oct, 2-min smoke test after 20:10, full ramp about 20:15, KNS registrations at 50/min from about 21:15 (run by the separate kns tn10 bot). Exact times land in `notes/timeline.md`.

## Files (`data/`; all times UTC unless the line says otherwise)
| File | Source | Cadence | What it shows |
|---|---|---|---|
| `host.jsonl` | `scripts/host_sampler.mjs` on n0 | 15 s | disk, RAM, load, kaspad CPU/RSS, mempool, tx processed/s, blocks/s, and `share`: blocks mined by box / desk / rest of network (from n0 block-added notifications) |
| `tn10-n0-rpc.jsonl`, `tn10-n0-vcc.jsonl` | Grok Build's metrics kit, against n0 | 10 s | node info, DAA, virtual-chain changes (accepted txs per chain block) |
| `api-health-min.jsonl` | `scripts/api_health_min.py` | 120 s | api-tn10 `/info/health`: HTTP, latency, `acceptedTxBlockTimeDiff` (indexer lag), backends, `stall_suspected` |
| `api-tn10.jsonl`, `api-vcbs-watch.jsonl` | metrics kit | 300 s | api-tn10 health + virtual-chain blue score |
| `api-mined-watch.jsonl` | `scripts/api_mined_watch.py` | 300 s | newest **coinbase** for our mining address as the public API shows it vs blocks n0 says we mined in the same window; `mined_stall=true` means the API stopped showing our mined blocks while we were still mining them |
| `storm-watch.jsonl` | `scripts/storm-watch.sh` | ~30 s | stop/slowdown decisions and the rate multiplier |
| `runner*.jsonl` / `storm*.out` | storm runner (when live) | per batch | submitted/accepted counts, rejects, tx ids |
| `public-api-calls.log` | all samplers | per call | audit of every public API call we made |
Mining address (ours): `[address]`.

## Earlier rounds (context)
Private: `STP-KAS/tn10-storm-2026-10-01-reports-public`, `STP-KAS/tn10-storm-2026-09-25-indexer-stall` (api-tn10 indexer stalled 25 Sep 19:55:38Z during our storm, cause unproven).
Public: `STP-KAS/tn10-storm-2026-09-25`, `STP-KAS/tn10-storm-2026-09-26-verdict` (round 6: about 10.1M txs in about 159 min).
