# Mainnet cost of the measured TN10 slice, and of the unmeasured design target

> **Mainnet labels (added 4 Oct 2026).** Kaspa Testnet-10 only. Every statement about mainnet in this file now carries a label: **A** = shown on TN10, backed by our own measured data (TN10 only, never proof for mainnet); **B** = plausible for mainnet but unsure, reason given; **C** = unknown, needs more testing and review. Claims, evidence and the tests still needed: [TN10 storms: what they do and do not say about a mainnet storm](https://github.com/STP-KAS/tn10-storm-2026-10-01/blob/main/TN10-STORMS-MAINNET-IMPLICATIONS-2026-10-04.md).

Read with `analysis/REPORT.md`. This file is the arithmetic. Every mainnet figure here is **B**: computed from parameters and measured TN10 counts, not measured on mainnet, and it assumes the floor feerate gets included with no fee war. Every input has a source. The storm data ends 2026-10-01T18:22:56Z. Where the data does not contain a figure, the line says not measured.

Price timestamp: CoinGecko `https://api.coingecko.com/api/v3/simple/price?ids=kaspa&vs_currencies=usd&include_last_updated_at=true`, body `{"kaspa":{"usd":0.04130969,"last_updated_at":1790892490}}`, HTTP `Date: Thu, 01 Oct 2026 22:09:55 GMT`. Used as $0.04130969 per KAS.

Consensus sources are kaspanet/rusty-kaspa commit `01b532e8b553523216471682649693af92f0fd16`, read 2026-10-01. Paths below are in that tree. KIP-0009 is the storage-mass note the same code comments cite: https://github.com/kaspanet/kips/blob/master/kip-0009.md.

## 1. Mainnet parameters

| Input | Value | Where |
|---|---|---|
| Block rate after Crescendo | 10 blocks/s | `consensus/core/src/config/params.rs`, `MAINNET_PARAMS.blockrate = BlockrateParams::new::<10>()`. `bps()` is `1000 / target_time_per_block`. Pre-Crescendo target is 1,000 ms. Activation DAA score 110,165,000, comment in that file "roughly 2025-05-05 1500 UTC". This estimate assumes October 2026 is past that activation. A live mainnet DAA was not read for this note |
| Compute mass limit per block | 500,000 | same struct, `block_mass_limits.compute` |
| Storage mass limit per block | 500,000 | `block_mass_limits.storage` |
| Transient mass limit per block | 1,000,000 | `block_mass_limits.transient` |
| Mass per tx byte | 1 | `mass_per_tx_byte` |
| Mass per script-public-key byte | 10 | `mass_per_script_pub_key_byte` |
| Grams per sigop | 1,000 | `consensus/core/src/mass/units.rs`, `GRAMS_PER_SIGOP_COUNT_UNIT` |
| Storage-mass parameter C | 1,000,000,000,000 | `consensus/core/src/constants.rs`, `STORAGE_MASS_PARAMETER = SOMPI_PER_KASPA * 10_000`, `SOMPI_PER_KASPA = 100_000_000` |
| Transient bytes to mass | ×4 | `TRANSIENT_BYTE_TO_MASS_FACTOR` |
| Minimum relay fee | 100,000 sompi per kg of mass, which is 100 sompi per gram | `mining/src/mempool/config.rs` lines 17–20, `DEFAULT_MINIMUM_RELAY_TRANSACTION_FEE`. `minimum_feerate()` divides by 1,000 |

The fee floor uses non-contextual mass only. `mining/src/mempool/check_transaction_standard.rs`:

```text
fee_mass = max(compute_mass, normalized_transient_mass)
minimum_fee = fee_mass * minimum_relay_transaction_fee / 1000
```

Storage mass is not part of that floor. The comment there says storage growth is handled by the storage-mass limit, not by a second relay fee. Transient mass is scaled by `compute_limit / transient_limit` = 500,000 / 1,000,000 = 0.5 before the max (`NonContextualMasses::normalized_transient` in `consensus/core/src/mass/mod.rs`).

The mempool fills a block template by feerate until `max_block_mass` (`mining/src/mempool/model/frontier/selectors.rs`). When the pool is empty the estimator sits on `minimum_feerate()`. That is what n0 reported for almost this entire slice.

## 2. Mass of a 1-input 1-output

This is the run's shape (`README.md`: recycled 1-in-1-out). The byte lengths are the standard version-0 Schnorr payment, not bytes copied from a storm transaction. No storm transaction was measured for size in `data/`.

Assumptions, stated so they can be checked:

- Transaction version 0, so no 2-byte compute-budget field on the input.
- Empty payload, no covenant.
- One sigop.
- Signature script 66 bytes: a push of a 64-byte Schnorr signature plus one sighash byte.
- Script public key 34 bytes: a push of a 32-byte x-only key plus OP_CHECKSIG.
- `HASH_SIZE` 32 (`crypto/hashes/src/lib.rs`). `SUBNETWORK_ID_SIZE` 20 (`consensus/core/src/subnets.rs`).

`transaction_estimated_serialized_size` in `consensus/core/src/mass/mod.rs`:

| Piece | Bytes |
|---|---:|
| version u16, input count u64, output count u64, lock time u64, subnetwork 20, gas u64, payload hash 32, payload length u64 | 94 |
| outpoint 36, sigscript length u64, sigscript 66, sequence u64 | 118 |
| value u64, spk version u16, spk length u64, spk 34 | 52 |
| Total | 264 |

Compute mass = `size * 1 + (2 + spk_len) * 10 + sigops * 1000` = 264 + 360 + 1,000 = **1,624**.

Transient mass = 264 × 4 = 1,056. Normalized = ceil(1,056 × 0.5) = 528.

Fee mass = max(1,624, 528) = **1,624**.

Floor fee = 1,624 × 100,000 / 1,000 = **162,400 sompi = 0.001624 KAS**. At the price above, $0.00006709 per transaction.

Storage mass, for the record, uses the relaxed KIP-9 path because there is one input and one output, plurality 1 (a standard 34-byte script fits one 100-byte unit, `utxo_plurality` in the same file):

```text
storage = max(0, C/output - C/input)
```

with input = output + fee. At the README's middle hop of 0.4 KAS (40,000,000 sompi, an assumption, not a measured output) and the floor fee:

```text
storage = 10^12/40_000_000 - 10^12/40_162_400 = 102
```

102 is far under 1,624, so storage does not set the relay fee and does not fill the storage limit first. A short payload, if the runner adds one, adds 1 compute-gram and 4 transient-grams per payload byte. Not measured here.

## 3. How much of a mainnet block that rate fills

Transactions per block on compute mass = floor(500,000 / 1,624) = 307 (307 × 1,624 = 498,568). At 10 blocks/s the compute cap is **3,070 tx/s**. Transient would allow floor(1,000,000 / 1,056) = 946 per block, so compute binds first. Block templates also leave a small search gap under the cap (`mining/src/mempool/model/frontier.rs` comments a 25,000-mass gap on a 500,000 limit). The fractions below use the 500,000 consensus limit, so they are slightly generous to the attacker.

| Rate | What it is | Fraction of 3,070 tx/s |
|---|---|---:|
| 106.015/s | node-wide `txProcessed` average, 16:41:46Z–18:22:46Z | 3.45% |
| 283.462/s | same counter, 18:15:01Z–18:17:46Z | 9.23% |
| 432.2/s | highest 15 s sample, 18:16:31Z | 14.1% |
| 1,200/s | README target, not measured | 39.1% |
| 2,500/s | README target, not measured | 81.4% |

The 106/s figure includes ordinary TN10 traffic. Before the pruning window the same counter was already 89.8/s with mempool 0. It is not a count of transactions this run submitted.

## 4. Price

Fee per tx at feerate R sompi/gram = 1,624 × R sompi. At the floor, R = 100, fee = 162,400 sompi.

KAS = tx/s × 162,400 × seconds / 1e8. USD = KAS × 0.04130969.

### A and B. This slice

Scenario A is the floor fee at the measured node-wide average, 106.015 tx/s.

Scenario B is the fee required to stay ahead of honest users once blocks are full. In this slice that fee was not above the floor. Of 609 `getFeeEstimate` polls, 608 had priority feerate 100. The exception is 2026-10-01T17:01:01.191Z, priority 102.0036, normal 101.4812, mempool 51. Host mempool peaked at 216 at 18:16:16.258Z. The runner's own log wanted 300 sompi/gram (`feerate.jsonl`, `fee_mult` 3) while the node was still quoting 100. Paying 300 was a choice, not a price the mempool had reached. B is the same bill as A for this slice.

| Duration | Seconds | KAS | USD |
|---|---:|---:|---:|
| 10 min | 600 | 103.30 | 4.27 |
| 1 h | 3,600 | 619.81 | 25.60 |
| 6 h | 21,600 | 3,718.84 | 153.62 |
| 24 h | 86,400 | 14,875.34 | 614.50 |
| 7 d | 604,800 | 104,127.40 | 4,301.47 |

These dollars buy the whole node's observed processing rate, not a proven attack. Using them as an attack invoice overstates what this run spent.

The only elevated window, 283.462 tx/s for 165 s, is 75.96 KAS ($3.14) at the floor, again if every processed tx were the attacker's.

### C. The design target, not measured

Same floor fee. This is what the README said the run would attempt. `data/` does not show it.

| Duration | 1,200 tx/s KAS | USD | 2,500 tx/s KAS | USD |
|---|---:|---:|---:|---:|
| 10 min | 1,169.28 | 48.30 | 2,436.00 | 100.63 |
| 1 h | 7,015.68 | 289.82 | 14,616.00 | 603.78 |
| 6 h | 42,094.08 | 1,738.89 | 87,696.00 | 3,622.69 |
| 24 h | 168,376.32 | 6,955.57 | 350,784.00 | 14,490.78 |
| 7 d | 1,178,634.24 | 48,689.02 | 2,455,488.00 | 101,435.45 |

If blocks were actually full, R would rise above 100 and both columns would scale linearly with R. This slice does not contain that R. Round 6's fee log, a different day, did: its README table shows a normal estimate of 864.6 (used 1,729) at 12:23 CEST on 26 Sep, then 188–194 after the storm was cut. That is prior-round evidence, not a measurement from `data/` here. A mainnet estimator under a full block would move the same way (**B**: same estimator code, not tested on mainnet): the next transaction has to beat the cheapest transaction that still fits. The number it settles at is not in this file.

### Capital and machines

Lane float: not measured. No runner file records how many coins were in flight. README's hop size is 0.2–0.6 tKAS on testnet. On mainnet the same pattern would lock 0.2–0.6 KAS per live output (**B**), and that lock comes back when the lanes are swept, minus the fees. The count of lanes is not measured, so the locked KAS is not measured.

Machines: not measured. No invoice is in the repo. The run description is one n0 plus the desk miners. Those miners are why the TN10 refund exists. They are not part of a 0% hashrate mainnet case (**B**, protocol logic).

## 5. What the TN10 refund hid

Desk blocks 14,310, box blocks 0, other blocks 34,466 (`host.jsonl` share, summed over 16:41:46Z–18:22:46Z). Our share of observed blocks is 14,310 / 48,776 = 29.34%.

If our transactions were included uniformly across blocks, about 29% of the fees we paid would be expected to land in a block our desk miners found. That expectation is the proxy. It is not a measured refund: the fee total is not in the data, and a miner only collects the fees of the transactions in the blocks it finds.

Net TN10 cost = gross fees × (1 − 0.2934), and gross fees are not measured, so the net is not measured.

Mainnet case in the prompt: attacker hashrate 0%. Refund 0. The tables in section 4 are already that case. The 29% is the fraction this testnet run would be expected to hide, if a fee total is later computed as (measured fees) × 0.2934 returned and × 0.7066 actually spent.

## 6. Honest users

During 16:41Z–18:22Z an honest transaction at 100 sompi/gram was paying the same feerate as the priority bucket. API accepted-tx lag stayed at 1–5 s (median 3 s) except one timed-out health poll at 18:17:30Z and one slow 15.5 s HTTP 200 at 18:19:30Z whose accepted-tx lag was still 2 s. Newest public coinbase lag median 4.0 s, max 11.4 s. `mined_stall` never became true.

A 10 minute burst at the unmeasured 2,500 tx/s target would fill about 81% of compute mass. Users at the floor would still fit in the remaining mass until the pool grew past one block. Held for an hour, the same rate is a standing queue, the estimator leaves the floor, and the public indexer is in the regime where it froze on 25 Sep (about 6k tx/s at 19:55:38Z, `STP-KAS/tn10-storm-2026-09-25-indexer-stall`, cause marked unproven). This slice did not enter that regime. Saying the API "held" is true for these two hours and is not evidence about a full storm.
