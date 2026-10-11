# TN10 storm-max: LAUNCH sheet (document only, nothing here has been run)

**TESTNET-10 only.** Written 2026-10-01 ~19:35 CEST, fee updated to 3x at 19:40 by Grok Bot (executor). **This file is only a document.** stp's rule:
**never start the full storm from this sheet without stp's explicit go.** The smoke test also needs its own separate
approval. Only one thing has been run so far: dry-runs, which submitted nothing.
All times are CEST. No key material is in this file. Key *paths* are named; their contents never are.

## 0. What is wired (files)
| File | Role |
|---|---|
| `../coinbase-feeder.mjs` | Local faucet feeder. It is read-only RPC and reads no key. It tracks qzffl5 coinbase outputs from n0 `block-added` and `virtual-chain-changed`, keeping only those **accepted on the selected chain**. If a reorg removes the accepting chain block, it drops them again. It backfills recent block bodies (`getBlocks` + `getVirtualChainFromBlock`, no utxoindex needed) and applies maturity `blockDaaScore + 1200 < virtualDaaScore`. Output goes atomically to `/tmp/r5-reserved-utxos.json`, using the r5-engine format. The float is capped at 98k TKAS (`FLOAT_MAX`, stp 19:38). Log: `data/feeder.log`. |
| `../storm-max-runner.mjs` | Index-free 1-in-1-out runner. It uses the round-6 engine `r5-engine.mjs` + `lib.mjs` from `[local path]`, imported and not modified. Each lane gets fresh throwaway keys. Lane count is live-resizable. LIVE needs `DRYRUN=0` **and** (`STORM_LIVE=1` or `--live`). `--build-only` runs the LIVE code path with submit stubbed. |
| `../storm.sh` | Subcommands: `check / baseline / prep / smoke / smoke-stop / start / topup / stop / restore / status`. Default is DRY-RUN (it prints commands only). Acting needs `STORM_LIVE=1`. |
| `../storm-watch.sh` | Watcher. Writes `/tmp/smx-rate` for pacing and the STOP file for halting. |
| `../smx-feerate.py` | Fee daemon (adapted copy of round-6 `r6-feerate.py`, original not edited). **`FEE_MULT` x normal estimate, default 3 (stp 19:38)**, floor `FEE_MULT`x100 sompi/g, every 30 s -> `/tmp/r6-feerate` (atomic). `storm.sh` waits until the file is fresh (<60 s) before starting the runner; the runner refuses LIVE if it is missing or >120 s old. |
| `../coinbase-collect.mjs` | A copy of `[local path]` with only the output path changed. Used to cross-check the feeder. |

## 0b. How the storm sends transactions (no wallet app)
- **No KasWare or other wallet, and no browser.** Every transaction is built and signed in code, in Node.js, with the
  official rusty-kaspa `kaspa` WASM SDK (`[local path]`, v2.1.0). The calls used are
  `createTransaction`, `signTransaction` and `calculateTransactionMass` (KIP-9 mass, used to size the fee).
- **Funding** comes from the qzffl5 mining address (`kaspatest:qzffl5…0v0ldx`). Its coinbase outputs are signed with
  **desk key 0**. The key is derived only inside `[local path]`, from a file under
  `[local path]`. It is never printed, logged or written anywhere else, and nothing besides lib.mjs reads it.
- **Each lane** gets a **fresh random throwaway key**, created in memory (`crypto.randomBytes(32)`). Every hop moves the whole
  UTXO to another fresh key: 1 input, 1 output, ~1,745 g, with a random 0.2–0.6 tKAS tag in the payload. Live chain ends
  (outpoint + that lane's throwaway key) are saved mode 600 to `[local path]` and `-RET.json`, so
  a stop doesn't strand balances. They are never logged.
- **Submission:** each tx goes straight to **our own local node n0** over wRPC (`ws://[ip]`, Borsh,
  `submitTransaction`). There is **no public API**. Acceptance is tracked from n0's own `virtual-chain-changed` notifications.
- **Fee:** n0's own `getFeeEstimate` normal bucket **× FEE_MULT=3** (floor 300 sompi/g). `smx-feerate.py` recomputes it
  every 30 s into `/tmp/r6-feerate`, and the engine re-reads it every 2 s.
- **Why code and not a wallet:** a browser wallet needs a click or popup per transaction, so it manages a few tx per minute.
  Code-signed lanes have no UI in the loop, and one Node process signed **~1,500–1,600 tx/s on one CPU core** (measured,
  build-only). The storm's ceiling is set by CPU cores and node acceptance, not by a person approving transactions.

**STOP file:** `[local path]`. The runner and feeder halt on it. The runner also honors the
engine's existing `/tmp/r5-games.HALT` and `/tmp/tps-storm.HALT`, but only reads them; it never creates them.

## 1. Smoke test (load only, small). Needs stp's separate approval.
50 lanes, 100 tx/s, no ramp. The runner **stops itself after 120 s**: it sets rate to 0, waits 5 s for in-flight submits,
saves chain ends, and exits.
```
cd [local path]
STORM_LIVE=1 ./storm.sh check                                            # read-only preflight
STORM_LIVE=1 SMOKE_LANES=50 SMOKE_RATE=100 SMOKE_S=120 ./storm.sh smoke  # fee daemon + feeder, waits 150 s, then runner1
```
**Smoke stop.** This stops only what smoke started, by exact pid from `run/*.pid`. Samplers and the watcher keep running:
```
STORM_LIVE=1 ./storm.sh smoke-stop       # SIGTERM runner1 (saves chain ends), then feeder, then feerate
# emergency alternative: touch [local path]   (then remove it before any later start)
```
Expect about 50 funding txs plus ~11,000 hops at 3x fee (300 sompi/g at today's normal 100). Funding costs about 0.8 TKAS and hops about 58 TKAS in fees. About 615 TKAS
of coinbase is locked in 50 lanes. Those chain ends are saved to `[local path]` (mode 600).

## 2. Full start (DO NOT RUN without stp's explicit go)
Defaults: `LANES=1400 BASE_RATE=1500 WORKERS=2`. That is 2 signer processes, each with 700 lanes and 750 tx/s.
The ramp is **25% → 50% → 100%** at 0 / 7.5 / 15 min (`RAMP=0.25@0,0.5@450,1@900`). **The ramp clock is held during
pruning windows**, and `storm-watch` also caps the rate at 0.25 there.
```
cd [local path]
STORM_LIVE=1 ./storm.sh check
STORM_LIVE=1 ./storm.sh baseline        # only if samplers/watch are not already running (they are: run/*.pid)
STORM_LIVE=1 LANES=1400 BASE_RATE=1500 ./storm.sh start
```
Don't start during **19:05–20:10** or **07:05–08:10**. The earliest sensible start is about **20:15** tonight.

**Top-up to 2500 lanes during the run** (no restart). Do it once the ramp reaches 100% (~15 min), mempool is < 50k,
and p95 latency looks normal:
```
STORM_LIVE=1 LANES=2500 ./storm.sh topup     # writes /tmp/smx-lanes-SMX1 and -SMX2 = 1250; each runner adds up to 200 lanes / 5 s
```

## 3. Full stop
```
cd [local path]
STORM_LIVE=1 ./storm.sh stop
#  1) writes STOP. Runners force rate 0, wait 5 s, persist chain ends, and exit by themselves (the script waits 12 s)
#  2) SIGTERMs the exact pids in run/runner1.pid, runner2.pid, feeder.pid, feerate.pid
#     (a SIGTERM to a runner also triggers the graceful save)
#  3) stops the samplers: watch, health, host, mined (exact pids), then kit ./stop.sh
```
Nothing is ever killed by name or pattern. kaspad, the miners, bore, ks_bridge, the watchdog and HALT files are not touched.

**Chain-end recovery / sweep:**
- Live chain ends are saved every 5 s, and on halt, to `[local path]` (mode 600). Restarting a
  runner with the same `--tag SMX<i>` resumes those chains first, so a stop does not strand balances.
- Chains that fell below the 0.2-TKAS floor, or whose hop failed, are saved to `[local path]`.
  Each holds ≤ ~0.2 TKAS. **A sweep tool for these files is not written yet (gap).** The existing round-6 `r6-sweeper.mjs`
  expects a different input file. Over 24 h this could add up to several thousand TKAS of ≤0.2-TKAS dust.
- Consumed seed outpoints (public txid:index only) are listed in `run/smx-used-seeds.txt`. Claims are in `/tmp/smx-claims/`.
  Seeds from a failed funding submit are never retried. If one is actually still unspent, it is still a qzffl5 coinbase
  and stays spendable by the faucet key.

## 4. Guards (what each one does)
| Guard | Where | Action |
|---|---|---|
| n0 `isSynced=false` for ≥2 ticks (30 s) | storm-watch | **STOP** |
| n0 sink age > 300 s for ≥2 ticks | storm-watch | **STOP** |
| Free disk < **19 G** (≈15% of 126 G) **for > 15 min**. Seconds inside a pruning window are not counted, so a pruning dip is not a stop | storm-watch | **STOP** |
| Free disk < 10 G (emergency floor, applies even in a pruning window) | storm-watch | **STOP** |
| Free disk < 22 G → smx-rate 0.5; < 20 G → 0.25 | storm-watch | slow down |
| Free disk < 19 G | runner | pause (rate 0) until it recovers. storm-watch decides the STOP |
| MemAvailable < 1 G | storm-watch: STOP; runner: pause | |
| Mempool > 80k → smx-rate 0 until < 55k | storm-watch | pause |
| Mempool > **90k** → pause until < 55k (backstop on the runner's own 2-s `getInfo`) | runner (engine token bucket) | pause |
| Pruning windows **07:05–08:10 / 19:05–20:10** (`PRUNE_WINDOWS`). n0 log shows moves at 07:13→07:52 and 19:11→19:59; ops say ~07:00 / 19:00 with ~14 G disk spikes | storm-watch: smx-rate 0.25; runner: **ramp clock held** (no ramp during pruning) | slow down |
| STOP file or SIGTERM | runner + feeder | rate 0, save chain ends, exit |
| `/tmp/smx-rate` missing | runner LIVE | refuses to start (fail-safe) |
| `/tmp/r6-feerate` missing or > 120 s old | runner LIVE | refuses to start. This prevents the engine's 20,000 sompi/g fallback (100× fees) |
| Node not `ws://[ip]` | runner + feeder | refuse |
| LIVE without `STORM_LIVE=1`/`--live` | runner | refuse (exit 5) |
| Fee | smx-feerate.py → `/tmp/r6-feerate` | **max(FEE_MULT×100, FEE_MULT × normal estimate) sompi/g, FEE_MULT default 3** (stp 19:38), engine re-reads every 2 s |

## 5. Funding: measured inflow, shape, time, tKAS locked
**Coinbase maturity:** the rusty-kaspa source gives `Bps<10> × COINBASE_MATURITY_SECONDS(100)` = **1000 DAA** for TN10, and
consensus rejects `entry.daa + 1000 > pov_daa`. TN10 ops' 1000 is correct. We use the **larger, 1200**, as a margin.
Note that n0's virtual DAA advanced only **~4.7/s** in measurement, so 1200 DAA ≈ **4.3 min**.

**Inflow** (qzffl5 coinbase accepted on the selected chain; box miners halted; desk miners only):
- Feeder live ticks: **~160–320 TKAS/min**.
- Collector 10-min buckets after the 18:38 HALT: 18:40 197, 18:50 233, 19:00 290, 19:10 350 TKAS/min.
  Before the HALT (box miners on) it was ~1,270 TKAS/min.
- Planning figure: **~250 TKAS/min ≈ 15k TKAS/h ≈ 81 coinbases/min.** About 40% of seen coinbases were red or reorged
  and were dropped.

**Old 8.4M balance:** it is **not visible** without the utxoindex (no balance query, no UTXO list). What *is* visible is
every coinbase still in n0's block bodies, back to the pruning point (~42 h ago). The feeder backfills them:
`--backfill-chain 30000` covers ~3 h and found **~31.5k mature accepted coinbases ≈ 98k TKAS**. No in-window spends were
seen. Anything older than the pruning point stays invisible.

**Funding shapes** (KIP-9 mass, built in memory at 200 sompi/g; the limit is 100,000 g per tx; fees below scale ×1.5 at the 3x fee of 300 sompi/g):
| Shape | Mass | Valid | Fee |
|---|---:|---|---:|
| 1 coinbase → 1 lane (whole, 3.09 TKAS) | 1,736 g | yes | 0.0035 |
| **4 coinbases → 1 lane (whole, ~12.3 TKAS) [chosen default, `FUND_TKAS=12`]** | **5,290 g** | yes | **0.0106** |
| 1 coinbase → 2 × 0.4 (+ change in last output) | 25,510 g | yes, but 7× heavier | 0.051 |
| 1 coinbase → 4 × 0.4 | 77,117 g | barely | 0.154 |
| 1 coinbase → 5 × 0.4 | 103,578 g | **NO** | — |
| 1 coinbase → 2 × 0.2 + change | 100,524 g | **NO** | — |
| consolidate 80 → 1 | 95,272 g | yes | 0.19 |
| consolidate 84 → 1 | 100,008 g | **NO** (max ~83 inputs) | — |

Splitting coinbases into 0.2–0.6 seeds is the expensive, mass-heavy option. The cheapest valid shape is **whole-UTXO
1-output funding**; no consolidation or split is needed. The "random 0.2–0.6 tKAS" lives in the payload tag. Hops on a
0.2-TKAS input are still **1,690 g**, so the chain floor is set to 0.2 TKAS (`MINCH_SOMPI=20000000`).

| Lanes | Funding txs | Coinbases | tKAS locked | Funding fees | From backfilled float (98k) | From live inflow only (250/min) |
|---:|---:|---:|---:|---:|---|---|
| 1400 | 1,400 | 5,600 | **~17.3k** | ~22 TKAS (3x) | **< 1 min** (spawn 2 × 200 lanes / 5 s ≈ 18 s) | ~69 min (+4.3 min maturity) |
| 2500 | 2,500 | 10,000 | **~30.9k** | ~40 TKAS (3x) | **< 1 min** (≈ 32 s) | ~124 min |

With 1:1 shape instead: 1400 lanes = 4.3k TKAS, 2500 = 7.7k TKAS. Lanes then refund ~4× more often.
**Running cost at 3x fee (stp 19:38):** a ~1,745 g hop at 300 sompi/g = **~0.0052 TKAS**; 1,500 tx/s × 0.0052 = **~470 TKAS/min gross
(~28k TKAS/h)** vs **~250 TKAS/min desk inflow** → net drain ~220 TKAS/min (~13k TKAS/h) before the share of fees that comes back
in desk-mined blocks. The 98k float (backfill) plus inflow lasts roughly **6–7 h at full rate** without fee return, longer
with it and with pruning-window/disk throttling. When `mature_all_tkas` in `data/feeder.log` falls, lanes simply wait for seeds
(`no_seed` rises); nothing breaks, the rate drops to what inflow can fund. At 2x it would have been ~313 TKAS/min.
**Conclusion:** both 1400 and 2500 can be funded right away from the backfill. Plan stays: start at 1400, top up to 2500 later.

**Contention warning:** `[local path]` collected the same qzffl5 coinbases (another agent). If something
else spends qzffl5 coinbases during the run, some of our fund txs will fail with "already spent". The runner then
abandons those seeds; it does not retry them.

## 6. CPU reality: 2500 lanes vs 1400
- Box: **8 cores**, box miners **halted (0 running)**, load ~1, kaspad idle ~10% CPU (it will take ~1–2 cores under load).
  That leaves ~6 cores for signers.
- Measured with build-only (the LIVE code path, submit stubbed, signing with real keys in memory): **one runner process
  tops out at ~1,500–1,600 tx/s on ~1 core.** At the 1,500 tx/s cap, **1400 lanes built 91.8k txs / 60 s and 2500 lanes
  built 90.2k / 60 s: identical.**
- **Plainly: 2500 lanes do not add throughput on this box. They add signing/bookkeeping overhead, ~13.6k more TKAS locked,
  and more RAM.** Throughput comes from signer processes (`WORKERS`) and node acceptance, not lane count. Round 6 saturated
  at ~1,200 lanes on 2 free cores. More lanes only help if per-chain mempool chaining (orphan / "already spent" races)
  turns out to be the limit during the run. That is the only reason to run the top-up.

## 7. Disk warning (read this)
- Live `df` at writing (19:34 CEST): **56 G free of 126 G (54% used)**. The STOP line is 19 G sustained, so there is **~37 G of headroom**.
- The plan estimates **~2 GB/h at 1,000 tx/s (~48 GB / 24 h)**, roughly ~3 GB/h at 1,500 tx/s. Pruning windows add
  **~14 G transient spikes** about every 12 h.
- **1,500 tx/s for 24 h is not expected to be sustainable on this disk.** At ~3 GB/h the 22 G / 20 G soft lines are
  reached in ~11–12 h. The watcher will then throttle to 0.5 / 0.25, and a sustained < 19 G stops the run.
  Pruning may reclaim space every ~12 h; that is not guaranteed.
- The box is shared. Other agents' git clones have already moved free disk by ~6 G in 20 min. The guards read live `df`.
