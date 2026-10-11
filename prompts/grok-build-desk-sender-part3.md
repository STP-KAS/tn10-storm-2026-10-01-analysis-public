# Grok Build, part 3: desk sender through public TN10 nodes (storm 1–2 Oct 2026)

Paste below into Grok Build on stp's desk **after** parts 1–2 (miner keeper at ~75% CPU + observer) are running.

---

You add a second, independent load source to my Kaspa **Testnet-10** storm. The main storm runs from Grok Bot's computer through our own node. You send from my desk through **public TN10 nodes**, so we learn how the wider network handles load that enters from several places. TN10 only, never mainnet.

## Rules
1. **TN10 only.** Refuse to run if the network id is not `testnet-10`. Never touch mainnet keys or wallets.
2. **Your own new wallet.** Generate a fresh TN10 wallet (mnemonic) on this desk. Store it only in a local file outside any git repo (e.g. `%USERPROFILE%\tn10-desk-sender\wallet.secret`). Never print the mnemonic or keys, never commit them, never paste them into chat. Show me only the receive address.
3. **Don't starve the miners.** Keep my 20 miners at about 75% CPU (part 1 keeps doing that). Your sender gets the rest. If miner hashrate drops more than 10% from before you started, slow down.
4. **Public nodes via wRPC, not websites.** Connect through the Kaspa SDK's public Resolver (`networkId: "testnet-10"`), or another public TN10 wRPC node. Do **not** use `api-tn10.kaspa.org` or any REST explorer for sending or for UTXO lookups; at most one REST call per 5 min for health, logged.
5. **Back off on pushback.** If a node rejects, rate-limits or disconnects you, log it (that's data), wait, reconnect through the Resolver (it may give a different node), and lower your rate. Never hammer one node.
6. **No public posts.** Commit only to `STP-KAS/tn10-storm-2026-10-01-analysis-public` (private), only in `desk/`. No tags, releases, issues or PRs anywhere.
7. **Never invent numbers.** Every number in your summary must come from your own logs.

## Step A: wallet + funding (do now)
- Install what you need (Node.js 20+ and the official Kaspa WASM SDK from the rusty-kaspa releases, or the `kaspa` npm package; say which and which version).
- Create the wallet, show me the `kaspatest:` receive address and stop. I'll have about **50,000 tKAS** sent to it from our mining address. Wait until you see the funds confirmed on a public node, then report the txid and balance.

## Step B: set up lanes
- Look up the current mass rules in the rusty-kaspa source (compute mass, KIP-9 storage mass, block mass limit, minimum fee rate) and cite the file/line URLs.
- Split the funds into lanes: about **200 lane outputs of ~200 tKAS each** (adjust so no split transaction breaks the storage-mass limit: storage mass punishes many small outputs). Keep ~5,000 tKAS spare for fees and re-splits.
- Each lane then sends **1-input 1-output** transactions to a new address of your own wallet (or back to itself), so the coins hop without creating small change outputs. A random **0.2–0.6 tKAS** fee-plus-dust variation is fine as long as each tx stays 1-in-1-out. Fee: the node's normal estimate ×2.

## Step C: send (only when I say "GO", which is the same moment the main storm starts)
- Ramp: 10 tx/s for 5 min, then 50, 100, 200, and keep stepping up every 5 min as long as more than 95% of submissions are accepted and the miners stay fine. Find your ceiling, then hold just below it.
- Every 5 minutes also send one **"normal user" probe**: a fresh 1 tKAS transfer at the plain normal fee (not ×2), and measure submit → seen in mempool → accepted in a block, in seconds.
- Every 5 minutes, `git pull` the analysis repo. If `control/STOP` exists, stop sending at once and go to step D. Also stop if I say stop, if the wallet drops below 2,000 tKAS, or after 24 h.

## Logs (local, then committed to `desk/` every 30 min)
- `desk/sender.jsonl`: one line per batch: UTC time, node url (from the Resolver), submitted, accepted, rejected (with the error text), current rate, CPU %.
- `desk/txids.csv`: every txid with submit time (sample if more than 100k/hour, and say how you sampled).
- `desk/probes.jsonl`: each probe: txid, fee rate, submit/mempool/accepted times, latency.
- `desk/nodes.jsonl`: every connect, disconnect, rate limit and node switch.
- `desk/miners.jsonl`: miner hashrate and CPU every 5 min (from part 1).

## Step D: wrap up
Sweep all lanes back to one address of your wallet (don't send anything anywhere else), then write `desk/SUMMARY.md`: what you sent, peak and sustained tx/s, accept rate, which nodes pushed back and how, probe latency over time (normal fee vs storm), miner hashrate impact, final balance, and three plain-English conclusions. Commit it and give me the commit link.
