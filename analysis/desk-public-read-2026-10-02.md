# Desk public read, 2 Oct 2026

> **Mainnet labels (added 4 Oct 2026).** Kaspa Testnet-10 only. Every statement about mainnet in this file now carries a label: **A** = shown on TN10, backed by our own measured data (TN10 only, never proof for mainnet); **B** = plausible for mainnet but unsure, reason given; **C** = unknown, needs more testing and review. Claims, evidence and the tests still needed: [TN10 storms: what they do and do not say about a mainnet storm](https://github.com/STP-KAS/tn10-storm-2026-10-01/blob/main/TN10-STORMS-MAINNET-IMPLICATIONS-2026-10-04.md).

Testnet-10 only. This file is the desk reading of the public REST APIs after the run. It does not replace [`BOX-REPORT.md`](BOX-REPORT.md). The box report is what n0 and the box runners recorded. This file is what `api-tn10.kaspa.org` and `api.kaspa.org` returned, plus the mainnet fee arithmetic for a raw 1-input 1-output with no hashrate and no fee refund.

Read times are 2 Oct 2026, about 07:45 UTC. The TN10 day counts below are `GET /transactions/count/2026-10-01` (HTTP 200, `CF-Cache-Status: HIT`, `Date: Fri, 02 Oct 2026 07:45:13 GMT`) and `GET /transactions/count/2026-10-02` (HTTP 200, about three minutes earlier). Hours before 07:00 UTC on 1 Oct are absent from that payload (zeros). The 07:00 UTC hour on 2 Oct had not been published yet. Kaspa.stream TN10 is a client-rendered shell. Its HTML has no TPS. The figures it draws come from this same REST API. No page script was decoded.

The desk sender log is a third meter. Its batch lines run from `2026-10-01T18:38:37.650Z` to `2026-10-02T07:40:33.393Z`: 16,972,123 submits, 15,697,431 acks, 1,274,692 rejects (7.5%). An ack is a node accepting `submitTransaction`. It is not a virtual-chain inclusion. One 53-second stretch acked about 13,000 per second. That rate cannot fit in a block.

## 1. What the indexer accepted

`regular` is the API's accepted non-coinbase count for that UTC hour. Divide by 3,600 for the per-second column.

| UTC hour | Indexer regular | Per second | Box runners included in the same hour |
|---|---:|---:|---:|
| 1 Oct 08:00–17:00, mean of 10 hours | 197,712 | 54.9 | quiet baseline, before the desk log |
| 1 Oct 18:00 | 1,173,884 | 326.1 | 931,445 |
| 1 Oct 19:00 | 6,124,882 | 1,701.4 | 5,465,669 |
| 1 Oct 20:00 | 9,833,770 | 2,731.6 | 6,752,022 |
| 1 Oct 21:00 | 8,267,200 | 2,296.4 | 5,636,914 |
| 1 Oct 22:00 | 2,405,444 | 668.2 | 1,494,571 |
| 1 Oct 23:00 | 6,519,837 | 1,811.1 | 3,736,763 |
| 2 Oct 00:00 | 2,791,276 | 775.4 | 1,000,230 |
| 2 Oct 01:00 | 1,269,585 | 352.7 | 1,069,629 |
| 2 Oct 02:00 | 1,278,992 | 355.3 | 1,080,743 |
| 2 Oct 03:00 | 1,296,834 | 360.2 | 1,092,789 |
| 2 Oct 04:00 | 1,816,592 | 504.6 | 1,607,942 |
| 2 Oct 05:00 | 220,640 | 61.3 | 15,449 |
| 2 Oct 06:00 | 195,047 | 54.2 | runners already stopped |

The box column is the per-hour included line in `BOX-REPORT.md`, shifted by two hours because that report labels hours in CEST. Example: its "22h" is 1 Oct 20:00 UTC. Where the indexer is higher, the gap is traffic the box runners did not count as their own inclusion. In the peak hour that gap is 9,833,770 − 6,752,022 = 3,081,748 transactions, about 856 per second.

Mainnet, `api.kaspa.org` `/transactions/count/` for the 31 hours from 1 Oct 00:00 through 2 Oct 06:00 UTC: mean **1.07 regular transactions per second**. Coinbase on that payload sits near 6.8 per second all day. That coinbase column is not the block rate. Mainnet virtual DAA score at this read was 555,066,384, past Crescendo activation at 110,165,000, and the parameter set is 10 blocks per second.

On TN10 the same coinbase column falls to about 4 per second in the peak hour and sits near 6.3 per second in the quiet morning. It is not the block rate either. Two `/info/health` reads, accepted-tx timestamps 1790926817666 and 1790927061210, moved the database blue score from 574,420,276 to 574,422,923. That is 2,647 blue steps in 243.5 seconds, **10.9 per second**, after the storm had already drained.

## 2. Bottleneck

Block compute mass is the ceiling. Three shapes were in this storm, so one tx/s cap does not fit all of them.

| Shape | Compute mass | Transactions per block | At 10 blocks/s |
|---|---:|---:|---:|
| Box P2W hop, as named in the box report | 643 g | 777 | 7,770 tx/s |
| Standard raw payment used for the bill below | 1,624 g | 307 | 3,070 tx/s |
| Box SMX hop, about 1,745 g | 1,745 g | 286 | 2,860 tx/s |

The 1,624 figure is the standard version-0, one-input, one-output, empty payload, one Schnorr signature: 264 bytes + 360 script-public-key grams + 1,000 sigop grams. Block compute limit 500,000. Storage limit 500,000. Transient limit 1,000,000. For this shape compute binds first. Floor fee uses non-contextual mass only, so storage mass is not charged. `floor(500000 / 1624) = 307`, and `307 × 1624 = 498,568`.

The kaspad mass log, quoted in the box report, is the fullness measurement. Half-hour mean compute mass was 88.5% of 500,000 at 21:00 CEST and **92.8% at 21:30 CEST**, then 86% at 22:00 and 80% at 22:30. From 02:30 to 06:30 CEST the same mean was 11–26%. The chain did get within a few percent of the compute cap, and it did not stay there. A tx/s reading cannot be turned into a fullness percent unless every transaction has the same mass. The peak indexer hour, 2,732 per second, is a mix of the shapes above plus other senders.

What else limited the run:

- Submit rate above the cap only grows mempools. The desk log's pipe-mempool samples have median 49,012 and maximum 682,175. n0's own peak in the box report is 99,992 at 01:35:47 CEST. At 07:45 UTC the public REST node reported mempool 5,673. Those are different nodes at different times. Miners include what is in the template they build.
- Orphans. On the desk log the last error on a batch was an orphan 213 times, already-spent 32 times, and a timeout 5 times. Rejects are 7.5% of submits.
- The public indexer lagged the chain and then caught up. The box report's health samples mark `stall_suspected` from 22:29 to 01:30 CEST, peak accepted-tx lag 704 seconds, and 28 HTTP 503s. This desk read, at 07:45 UTC, got HTTP 200, synced, kaspad 2.1.0, accepted-tx lag 52 seconds, `blueScoreDiff` 60. One `/info/kaspad` a few minutes earlier still said server 2.0.0 and mempool 1,875. The REST backend moved during the read. One `/info/fee-estimate` timed out at 25 seconds and the retry returned 100 sompi/gram on every bucket.
- After new submits stopped, inclusion fell. Indexer hours 02:00 and 03:00 UTC are 355 and 360 per second with the desk sender acking zero. Hour 06:00 is 54 per second, back on the pre-storm baseline. The 350 per second plateau is the mempool draining plus whatever else was still sending. It is not a full block. The box mass log already shows those hours at 11–26% compute mass.
- Small outputs are a weaker clog. Storage mass fills its own 500,000 limit while compute mass is still free, so a normal payment still fits. The busy half-hours were compute-bound, not that case.

A same-fee queue at the peak inclusion rate of 2,732 per second is about 37 seconds deep at 100,000 transactions and about 4 minutes deep at 670,000. kaspad 2.1.0, on the TN10 nodes this desk fed, panics if a transaction is inserted while the mempool cap is already 100,000. That removes the node. It does not stop miners on nodes that are still up.

## 3. Mainnet bill, no fee returned

Label for this section: **B**. It is arithmetic on live mainnet readings and measured TN10 counts, not a mainnet measurement. It assumes the floor feerate gets included and no fee war. How a real mainnet network would handle the flood is **C**.

The question this section answers: what the same raw payment would cost on mainnet if the sender mines nothing, so no subsidy and no fee comes back.

Live mainnet at 07:45 UTC, `api.kaspa.org`: priority, normal, and low feerate all **100 sompi/gram**, mempool 1, hashrate **338,836.66 TH/s**. TN10 hashrate at the same read was **4.778e-5 TH/s** (47.8 MH/s). This test added no mainnet hashrate.

Price: CoinGecko `simple/price?ids=kaspa&vs_currencies=usd&include_last_updated_at=true`, body `{"kaspa":{"usd":0.04224456,"last_updated_at":1790927040}}`, HTTP `Date: Fri, 02 Oct 2026 07:45:16 GMT`. `api.kaspa.org/info/price` at that same second said **0.04219215**. The tables use CoinGecko. The Kaspa API price is 0.12% lower, and every USD figure would shrink by that much.

Fee per raw payment at the relay floor: `1624 × 100 = 162,400 sompi = 0.001624 KAS`. USD per transaction: `0.001624 × 0.04224456 = 0.000068605`.

The desk sender's rule is `max(2 × normal, priority)`. While the public quote is 100, that rule pays 200 and buys no extra block space. Doubling the feerate doubles every USD figure and does not raise the 3,070 cap. During the peak hour the desk log's own median quote on its sockets was about 3,581 sompi/gram, with those mempools around 273,000. That is what a loaded node asked for priority. A transaction at 100 sompi/gram is still the one that fills the block. The box report is the better fee record for what the runners actually paid: 3× the node estimate for most of the run, a fixed 6,000 sompi/gram for 23.7 minutes, then flat about 385–400. n0's normal estimate peaked at 24,144.8 sompi/gram at 01:51:21 CEST while the runners were paying about 400.

### Hold the indexer's peak hour above the quiet baseline

Peak hour 2,731.6 per second, minus the 54.9 per second quiet baseline, is **2,676.7 attacker transactions per second** if one sender had produced the whole excess and each transaction were the 1,624-gram payment. The storm did not do that. The box runners' own share of that hour was 1,875.6 per second, and those were not all 1,624-gram payments. The 24-hour row repeats the best hour. The test did not.

| Duration | Transactions | KAS | USD |
|---|---:|---:|---:|
| 1 h | 9,636,058 | 15,648.96 | 661.08 |
| 2 h | 19,272,116 | 31,297.92 | 1,322.16 |
| 3 h | 28,908,174 | 46,946.87 | 1,983.24 |
| 4 h | 38,544,232 | 62,595.83 | 2,644.32 |
| 5 h | 48,180,290 | 78,244.79 | 3,305.40 |
| 24 h | 231,265,392 | 375,575.00 | 15,866.00 |

Check: `2676.68 × 0.001624 × 3600 = 15,648.96 KAS`, times `0.04224456 = 661.08`.

### Fill the 1,624-gram compute cap

3,070 per second uses the last free mass of that shape. The busy half-hours reached about 93% of compute mass and left the rest. This row is the cost of not leaving it.

| Duration | Transactions | KAS | USD |
|---|---:|---:|---:|
| 1 h | 11,052,000 | 17,948.45 | 758.22 |
| 2 h | 22,104,000 | 35,896.90 | 1,516.45 |
| 3 h | 33,156,000 | 53,845.34 | 2,274.67 |
| 4 h | 44,208,000 | 71,793.79 | 3,032.90 |
| 5 h | 55,260,000 | 89,742.24 | 3,791.12 |
| 24 h | 265,248,000 | 430,762.75 | 18,197.38 |

A lighter hop costs proportionally less per transaction and packs more of them into the same mass. Scale the KAS and USD columns by `mass / 1624`. A 643-gram hop is 0.396 of this bill per transaction, and the block holds 777 of them instead of 307. The mass budget, not the transaction count, is what is being bought.

### What these TN10 hours would have cost at the same floor

Indexer regular transactions minus 54.9 per second, priced as if every one had been a 1,624-gram payment at 100 sompi/gram. This is a counterfactual on mixed traffic. It is lower than the flat peak-hour table because the rate fell after 21:00 UTC.

| Window (UTC) | Net transactions | KAS | USD |
|---|---:|---:|---:|
| 1 h, 1 Oct 20:00 | 9,636,058 | 15,648.96 | 661.08 |
| 2 h, 20:00–21:00 | 17,705,546 | 28,753.81 | 1,214.69 |
| 3 h, 19:00–21:00 | 23,632,715 | 38,379.53 | 1,621.33 |
| 4 h, 20:00–23:00 | 26,235,402 | 42,606.29 | 1,799.88 |
| 5 h, 19:00–23:00 | 32,162,572 | 52,232.02 | 2,206.52 |

### The fee the box runners actually recorded

`BOX-REPORT.md` sums **291,967 tKAS** of storm-runner fees, plus 63.4 for the smoke test. The 23.7 minutes at 6,000 sompi/gram are **122,320 tKAS**, 42% of the fees, for 11.5% of their included transactions. At the CoinGecko price, 291,967 KAS is **$12,334.02** and 122,320 KAS is **$5,167.36**. That translation treats testnet sompi as mainnet sompi and returns nothing to the sender. On TN10 a share of those fees landed in blocks this side mined. A mainnet sender with no hashrate does not get that share (**B**, protocol logic). This number is the runners' own fee rule, not the 100 sompi/gram floor.

## 4. What that does, and what it does not do

Block production continues. The attacker hashrate in this bill is zero, against a live mainnet hashrate of 338,837 TH/s. The fees are income for whoever is already mining.

Current mainnet demand is about 1 transaction per second. The subsidy at this read is 2.18267645 KAS per block. At 10 blocks per second that is 78,576.35 KAS per hour, **$3,319.42 per hour**. The peak-hour fee in the first table is 19.9% of that subsidy. The full-cap fee is 22.8%. The next subsidy cut is 5 Oct 2026 03:27:01 UTC, to 2.06017223 KAS. A 24-hour run starting at this read ends before that cut.

A flood that leaves spare compute mass does not, by itself, push today's mainnet payments out of the block (**B**: block-space arithmetic; whether other mainnet miners would include the flood, and how mempools and fees react, is **C**). The busy TN10 half-hours still had a few percent of compute mass free, and mainnet uses about 0.1 transaction per block. Same-fee payments wait when the mempool is deeper than the block. The waits measured here are tens of seconds to a few minutes at the mempool sizes above, plus the indexer lag of up to about 11 minutes while the node itself stayed synced (box report: sink age max 3.1 seconds).

The public REST and explorer view is the part that falls over first. Consensus on n0 did not.

24 hours at the 1,624-gram cap is 430,763 KAS. Circulating supply on `api.kaspa.org/info/coinsupply` at this read was 27,733,407,921 KAS. The fee is 0.00155% of that supply. It is a transfer to miners, not a sale into the book. Coins sitting in lanes come back when the lanes are swept. Only the fee is spent.

## 5. Limits

- The indexer does not record feerate or mass. The minimum-relay tables are protocol arithmetic, not a sum of fees read off the chain.
- The desk sender did not log a fee on each hop. Its 1,018 split records are lane setup, median mass 36,842 and median fee 0.232 KAS. They are not in the tables.
- Box included-counts and indexer regular-counts are different counters. The gap is real. It is not a proof that one outside wallet included the difference.
- The 24-hour rows repeat the best hour. The longest stretch near the top of the indexer series is the three hours 19:00–21:00 UTC, and the third of those is already 2,296 per second.
- No address, seed, or transaction id is in this file.
