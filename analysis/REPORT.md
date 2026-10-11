# INTERIM. TN10 storm, 1 Oct 2026, as far as the pushed data goes

> **Mainnet labels (added 4 Oct 2026).** Kaspa Testnet-10 only. Every statement about mainnet in this file now carries a label: **A** = shown on TN10, backed by our own measured data (TN10 only, never proof for mainnet); **B** = plausible for mainnet but unsure, reason given; **C** = unknown, needs more testing and review. Claims, evidence and the tests still needed: [TN10 storms: what they do and do not say about a mainnet storm](https://github.com/STP-KAS/tn10-storm-2026-10-01/blob/main/TN10-STORMS-MAINNET-IMPLICATIONS-2026-10-04.md).

**INTERIM.** Every sampler in `data/` stops together at about 18:22:56Z (20:22:56 CEST). The planned 24 h run had only just left the evening pruning window. There is no `runner*.jsonl`, no `storm*.out`, and no `notes/timeline.md`. Our own submit count is not in this repo. Numbers below come from `analysis/notebook.py` reading `data/` on this clone. Git pull at analysis time was already up to date.

## What

A Testnet-10 node, n0, kaspad 2.1.0, utxoindex off, was sampled from 16:41:30Z (18:41:30 CEST) through 18:22:56Z (20:22:56 CEST). The watcher held the sender at 25% through the scheduled pruning window and back at full rate after 18:10:10Z. A short fee log shows the runner quoting 300 sompi/gram from 18:12:14Z to 18:16:44Z. In that same minute the node's body-processing counter rose to a few hundred tx/s and the mempool touched 216. Then the samples stop. No stop reason is written.

This slice did not reach the run's 1,200–2,500 tx/s design, and it did not beat round 6 on any figure this repo can check.

## Why

The run exists to see what a recycled 1-in-1-out storm does to n0, to the public API, and to the fee an outsider would pay for the same load on mainnet with none of the block reward coming back. The data that arrived answers a narrower question: the samplers, the pruning slowdown, and a two-minute bump at the start of full rate. It does not yet answer the full-speed question. The September indexer freeze happened while n0 was logging about 6k tx/s (kaspad's "Processed" counter, which overstates unique transactions). Nothing in this slice is that load, so a healthy API here does not show that the September failure is fixed.

## When

UTC, with CEST in brackets. Watcher lines are `data/storm-watch.jsonl`. The fee log is `data/feerate.jsonl`.

| Segment | From | To | What the files show |
|---|---|---|---|
| Samples start | 16:41:30Z (18:41:30) | | `host.jsonl` start, `storm-watch` first line, rate multiplier 1, mempool 0, sink age 0.5 s |
| Full rate, before pruning | 16:41:31Z (18:41:31) | 17:04:55Z (19:04:55) | `rate_why=full`, `smx_rate=1`. 143 watcher lines are `full`, split around the prune gap |
| Pruning window | 17:05:00Z (19:05:00) | 18:09:55Z (20:09:55) | 258 lines, `rate_why=prune-window`, `smx_rate=0.25`. Matches the 19:05–20:10 CEST window in `scripts/storm-watch.sh` |
| Full rate again | 18:10:10Z (20:10:10) | 18:22:41Z (20:22:41) | `smx_rate=1`. This is the only full-rate stretch after the prune |
| Smoke fee log | 18:12:14Z (20:12:14) | 18:16:44Z (20:16:44) | 10 lines, normal 100, priority 100, `fee_mult` 3, `feerate_used` 300 |
| Body-processing bump | 18:15:01Z (20:15:01) | 18:17:46Z (20:17:46) | Node processed 46,772 txs in 165 s, 283.5/s. Mempool peak 216 at 18:16:16Z |
| Samples end | 18:21:13Z to 18:22:56Z (20:21–20:22) | | Health and mined-watch end on their 120 s and 300 s cadence. Host, vcc, and the watcher end within 15 s of each other. No `reason`, no `pause` |
| KNS at 50/min | 19:15Z (21:15) planned | | Not in this data. The clock had not got there |

No watcher line has a pause or a stop reason. Disk never tripped the 22 GB or 20 GB slowdowns (free space stayed above 51 GB). Mempool never reached the 80k pause.

## Facts

| Metric | Value | Source |
|---|---|---|
| Sample window, host rows with a rate | 405 rows, 16:41:46Z–18:22:46Z (18:41:46–20:22:46 CEST), 6,060.1 s | `data/host.jsonl` |
| n0 identity | kaspad 2.1.0, synced on all 609 polls, `isUtxoIndexed` false | `data/tn10-n0-rpc.jsonl` poll at 16:41:32.621Z and the set of later polls |
| Transactions the node processed | counter delta 642,464; average 106.015/s | `host.jsonl` `c.txProcessed` first rate-row to last |
| Same counter, before pruning | 89.842/s over 1,380 s (123,985 txs), 16:41:46Z–17:04:46Z | same counter, split in `analysis/notebook.py` |
| Same counter, pruning window | 103.341/s over 3,885.1 s | 17:05:01Z–18:09:46Z |
| Same counter, after pruning | 148.878/s over 765 s | 18:10:01Z–18:22:46Z |
| Same counter, the bump | 283.462/s over 165 s (46,772 txs) | 18:15:01Z–18:17:46Z |
| Highest 15 s sample | 432.2 tx/s at 18:16:31.258Z, mempool 80, chain blocks 6.6/s, DAA 10.87/s | `host.jsonl` |
| Highest 1 min mean of those samples | 334.28/s, 18:16:01Z–18:17:01Z | five host samples |
| Highest 10 min mean | 163.23/s, 18:08:46Z–18:18:31Z | |
| Highest 1 h mean | 116.33/s, 17:22:01Z–18:21:46Z | |
| Our submitted txs, our accepted txs | not measured | no `runner*.jsonl`, no `storm*.out` |
| `tn10-n0-vcc.jsonl` field `a` | sum 36,825 over 48,414 lines. Per minute it equals `added` in `tn10-n0-rpc.jsonl` minute rows (107/107, 247/247, 676/676 events). Max `a` is 9 | not an accepted-tx count. README's sentence "accepted txs per chain block" does not match the fields |
| Virtual DAA rate | median 8.27/s, min 2.93, max 13.47 | `host.jsonl` `rate.daa_per_s` |
| Chain blocks processed | median 5.07/s | `host.jsonl` `rate.chain_blocks_per_s` |
| n0 mempool | min 0, max 216 (host, 18:16:16.258Z). Watcher max 174 | `host.jsonl`, `storm-watch.jsonl` |
| Sink age | median 0.4 s, max 3.0 s at 16:57:41Z (18:57:41 CEST). `synced:false` count 0 | `storm-watch.jsonl` |
| Kit lines typed `deep_reorg` | 959. Median blocks removed 3, max 8. The start line sets `hashesMin` 3, so any virtual-chain change that drops 3 or more blocks is logged under that name | `tn10-n0-rpc.jsonl` |
| kaspad CPU | median 23%, one sample 250% at 17:35:31.208Z | `host.jsonl` `kaspad.cpu_pct` |
| kaspad RSS | 386 MB at first rate row, 2,165 MB at last, peak 3,206 MB at 18:02:01.235Z | `host.jsonl` |
| Load | median 1.54, max 7.1 | `host.jsonl` `load[0]` |
| Tips | 1 to 10 | `host.jsonl` `c.tips` |
| Disk free | 55.94 GB first, 51.01 GB minimum at 17:54:01.227Z (19:54:01 CEST, mempool 0, inside the prune window), 55.57 GB last. Net use 0.37 GB, 0.220 GB/h, about 5.3 GB per 24 h at this same rate | `host.jsonl` `disk_free_gb` |
| Node feerate | priority 100 on 608 of 609 polls. One poll at 17:01:01.191Z: priority 102.00, normal 101.48, mempool 51 | `tn10-n0-rpc.jsonl` |
| Blocks n0 saw, by miner | box 0, desk 14,310, other 34,466, total 48,776. Ours 29.34%. Partial hours: 16Z 24.7% (1,277/5,178), 17Z 28.9% (8,435/29,219), 18Z 32.0% (4,598/14,379). Box is zero in every hour | `host.jsonl` `share`, summed. Each line is one 15 s window |
| Fees we paid, self-mined refund, net cost | not measured | no per-tx fee sum and no runner totals. Share above is the only refund proxy, and it is a block count, not kas |
| Public health | 50 × HTTP 200, 1 timeout at 18:17:30.925Z with no body. `stall_suspected` true: 0. Accepted-tx lag min 1 s, median 3 s, max 5 s. `blueScoreDiff` max 518, on the slow 200 at 18:19:30.925Z (15,536 ms, accepted-tx lag 2 s). Cache `MISS` on the 50 successes. Backend `v` 2.0.1 on 16 samples, 2.1.0 on 34 | `data/api-health-min.jsonl`. Stall rule is in `scripts/api_health_min.py`: lag > 120 s and blueScoreDiff < 200 |
| Public mined-block watch | 20 × HTTP 200. `mined_stall` true: 0. Newest coinbase lag min 3.0 s, median 4.0 s, max 11.4 s at 16:51:12Z (`cf-cache-status` HIT). Cache on the other samples: EXPIRED 18, MISS 1 | `data/api-mined-watch.jsonl`. Stall means coinbase lag > 300 s while n0 still counts our blocks. Script: `scripts/api_mined_watch.py` |
| KNS at 50/min | not in this repo | planned for about 21:15 CEST, after the last sample |

The processed-tx counter is every transaction in every block body n0 handled, including other people's. `scripts/host_sampler.mjs` says that counter overcounts parallel blocks by about 1.337, from a round 7 note. That factor is not re-measured here. Do not read 106/s or 432/s as "txs we accepted."

## Claims vs verified

| Claim | Verdict |
|---|---|
| 24 h storm from about 20:15 CEST, target 1,200–2,500 tx/s (`README.md`) | Not in this data. Samples end 20:22:46 CEST. The highest measured node-wide processing rate is 432.2/s for 15 s, and 283.5/s across the 165 s bump. Our submits are not measured |
| Pace drops to 25% in the 19:05–20:10 CEST pruning window | Verified. 258 watcher lines, `smx_rate` 0.25, 17:05:00Z–18:09:55Z |
| Mempool pause at 80k, disk slowdowns under 22 GB and 20 GB | Did not trip. Mempool max 216. Disk free minimum 51.01 GB. All 401 watcher lines have an empty `pause` and an empty `reason` |
| n0 fell behind | Not observed. Sink age max 3.0 s, synced on every watcher line and every poll |
| Box miners off, desk miners carry our hashrate (`README.md`) | Verified for this window. Box blocks 0. Desk blocks 14,310, 29.34% of blocks n0 observed. README's "about 25% at 18:51 CEST" is a claim from before this file; the measured window average is 29.34% |
| A large share of fees came back to our mining address | The block-share proxy is 29.34% desk, 0% box. The kas amount is not measured |
| Round 6 was about 10.1 M txs in about 159 min, about 1,060–1,200 tx/s | That is the headline in `STP-KAS/tn10-storm-2026-09-26-r6` (accepted 10,058,024, whole-round about 1,057/s, full-gusto about 1,191/s). Not re-summed from round 6 logs here. This slice does not beat it: 642,464 node-processed txs in 101 min, and that counter is the larger, overcounting one |
| Last time, the public "mined blocks" view froze (25 Sep 19:55:38Z, `STP-KAS/tn10-storm-2026-09-25-indexer-stall`) | That note's accepted-tx pointer freeze is a separate, earlier event, at roughly 6k tx/s, cause marked unproven there. In this slice `mined_stall` is false on all 20 samples and coinbase lag stays under 12 s. The API kept up. The load that froze it last time was not present |
| `tn10-n0-vcc.jsonl` is accepted txs per chain block (`README.md`) | Not what the fields do. `a` matches minute `added`. The histogram matches minute `removed` |
| KNS registrations at 50/min | Not in this repo |

## Mainnet cost

Label for this section: **B**. It is arithmetic on mainnet parameters from source code, not a mainnet measurement. It assumes the floor feerate gets included, no fee war and the same relay policy. Real mainnet behaviour under this load is **C**.

Summary only. The arithmetic, the mass formula, and the sources are in `analysis/mainnet-cost.md`.

Price used: 1 KAS = $0.04130969, CoinGecko, read 2026-10-01T22:09:55Z.

The shape priced is one standard version-0, 1-input 1-output, empty payload, Schnorr signature. Compute mass 1,624. Relay floor 100 sompi/gram. Floor fee 162,400 sompi = 0.001624 KAS per tx. Mainnet compute cap for that shape is 307 tx per block × 10 blocks/s = 3,070 tx/s.

Two tables. The first prices the only tx rate this data actually contains, and that rate is the whole node's body processing, not our storm. The second prices the README target. The second was not measured.

Node-wide processed average, 106.015 tx/s, floor fee. About 3.5% of the 3,070 tx/s cap. Treat as an upper bound on a fee bill only if every one of those txs were an attacker's. Most of them, before 18:10Z, are the ordinary ~90 tx/s the node was already processing.

| Duration | KAS | USD |
|---|---:|---:|
| 10 min | 103.30 | 4.27 |
| 1 h | 619.81 | 25.60 |
| 6 h | 3,718.84 | 153.62 |
| 24 h | 14,875.34 | 614.50 |
| 7 d | 104,127.40 | 4,301.47 |

README target, not measured. 1,200 tx/s is 39% of the cap. 2,500 tx/s is 81%.

| Duration | 1,200 tx/s KAS (USD) | 2,500 tx/s KAS (USD) |
|---|---:|---:|
| 10 min | 1,169.28 ($48.30) | 2,436.00 ($100.63) |
| 1 h | 7,015.68 ($289.82) | 14,616.00 ($603.78) |
| 6 h | 42,094.08 ($1,738.89) | 87,696.00 ($3,622.69) |
| 24 h | 168,376.32 ($6,955.57) | 350,784.00 ($14,490.78) |
| 7 d | 1,178,634.24 ($48,689.02) | 2,455,488.00 ($101,435.45) |

Scenario B, the fee required to outbid honest users: same as the floor in this slice. The node never left ~100 sompi/gram, and the mempool never filled. Capital locked in lanes, and hardware dollars: not measured.

On TN10 the desk mined 29.34% of observed blocks, so a fee spread across random blocks would be expected to return about 29% to our address. The kas amount of that refund is not measured, because the fee bill is not measured. A mainnet attacker with no hashrate gets none of it back (**B**, protocol logic). The refund is the part this test cannot see.

Honest users during this slice were not priced out. Confirmation on the public API stayed a few seconds (coinbase lag median 4 s). A run that actually held 1,200–2,500 tx/s would occupy most of a block's compute mass, and the September rounds already showed the estimator leaving the floor once blocks were busy. That price was not observed here.

## Sources

- This repo's `data/*.jsonl`, read from the clone after `git pull` reported already up to date. Window above.
- `scripts/host_sampler.mjs`, `scripts/storm-watch.sh`, `scripts/api_health_min.py`, `scripts/api_mined_watch.py` for what each field means.
- `README.md` of this repo for the run design. Treated as claims unless a data line agrees.
- Round 6 headline: https://github.com/STP-KAS/tn10-storm-2026-09-26-r6 (README, read 2026-10-01). Not re-summed.
- September indexer note: https://github.com/STP-KAS/tn10-storm-2026-09-25-indexer-stall (README, read 2026-10-01).
- Mainnet parameters and the mass formula: `analysis/mainnet-cost.md`.
- KAS/USD: CoinGecko `simple/price?ids=kaspa&vs_currencies=usd`, HTTP date Thu, 01 Oct 2026 22:09:55 GMT, `usd` 0.04130969.

## Conclusion

The pushed data is the first two hours, not the 24 h storm. Samplers stop at 18:22:56Z with no reason written, mempool at most 216, and the node processing about 106 tx/s on average. The only bump is 283 tx/s for 165 s at 18:15Z, peaking at 432 tx/s for one 15 s sample. Our own submits were not recorded, so the attack's fee bill is not measurable yet.

Round 6's reported ~1,060–1,200 accepted tx/s is not beaten. The virtual-chain file cannot be used as accepted tx/s: its `a` field matches blocks added to the selected chain.

n0 did not fall behind (sink age at most 3 s). The public API did not freeze: no health stall, no mined-block stall, coinbase lag median 4 s. That is under a quiet mempool. The 25 Sep freeze was at roughly 6k tx/s, so this slice does not show the fix holding under a real storm.

For Kaspa core, three points. First (**B**, arithmetic), a 1-in-1-out at the relay floor costs 0.001624 KAS on today's mainnet parameters, and 2,500 of them per second would be about 81% of the 500,000 compute-mass block limit at 10 blocks/s, about $100 for 10 minutes at the 22:09Z price, with no hashrate refund. Second, TN10 gave that refund a 29% block-share during this window, all of it desk miners, and the samples available so far never made the fee estimator leave 100 sompi/gram. Third, the public indexer stayed current, and the data ended before any load comparable to the September stall had been applied.
