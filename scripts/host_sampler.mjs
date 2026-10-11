#!/usr/bin/env node
// TN10 storm host+node sampler. READ-ONLY (local n0 wRPC borsh [ip] + /proc + df). Sends nothing.
// Every --interval s (default 15): disk free, load avg, MemAvailable, kaspad RSS/CPU, n0 mempool, getMetrics consensus
// counters (tx processed/s, blocks submitted/s, chain blocks/s). Optional --share: subscribes block-added and splits
// coinbase payouts into OURS (stp payout spk) by miner UA tag: box ("stp grok bot") / desk (other UA, our spk) /
// network (other spk) -> self-mined share kept SEPARATE from the rest of TN10. --share costs CPU under load:
// measure it in the baseline first. Usage: node host_sampler.mjs --out data/host.jsonl [--interval 15] [--share] [--once]
import { createRequire } from "node:module";
import fs from "node:fs";
import { execSync } from "node:child_process";
const require = createRequire(import.meta.url);
globalThis.WebSocket = require("[local path]").w3cwebsocket;
const kaspa = require(process.env.KASPA_SDK || "[local path]");
const arg = (n, d) => { const i = process.argv.indexOf("--" + n); return i > 0 && i + 1 < process.argv.length ? process.argv[i + 1] : d; };
const has = (n) => process.argv.includes("--" + n);
const OUT = arg("out", "[local path]");
const INTERVAL = Number(arg("interval", "15")); const ONCE = has("once"); const SHARE = has("share");
const URL_ = "ws://[ip]";
// stp payout address kaspatest:qzffl5...0v0ldx as script hex (verified 2026-10-01 from a live coinbase on n0)
const OUR_SPK = arg("spk", "20929fd0c42cc35d22cb593895826c539f508ce88ba01f622c61e198accbcfcda0ac");
fs.mkdirSync(require("node:path").dirname(OUT), { recursive: true });
const w = (o) => fs.appendFileSync(OUT, JSON.stringify(o, (k, v) => (typeof v === "bigint" ? Number(v) : v)) + "\n");
const rpc = new kaspa.RpcClient({ url: URL_, encoding: kaspa.Encoding.Borsh, networkId: "testnet-10" });
await rpc.connect({ timeoutDuration: 8000 });
let share = { blocks: 0, box: 0, desk: 0, network: 0 };
if (SHARE) {
  rpc.addEventListener("block-added", (e) => {
    try { const cb = e.data.block.transactions[0]; const p = Buffer.from(typeof cb.payload === "string" ? cb.payload : Buffer.from(cb.payload).toString("hex"), "hex");
      const len = p[18]; const spk = p.subarray(19, 19 + len).toString("hex"); const ua = p.subarray(19 + len).toString("utf8");
      share.blocks++; if (spk !== OUR_SPK) share.network++; else if (ua.includes("stp grok bot")) share.box++; else share.desk++;
    } catch {}
  });
  await rpc.subscribeBlockAdded();
}
const kaspadPid = () => { try { return execSync("pgrep -x kaspad | head -1").toString().trim(); } catch { return ""; } };
const procStat = (pid) => { try { const s = fs.readFileSync(`/proc/${pid}/stat`, "utf8").split(") ")[1].split(" "); return { ticks: Number(s[11]) + Number(s[12]), rssMB: Math.round(Number(s[21]) * 4096 / 1048576) }; } catch { return null; } };
let prev = null;
async function tick() {
  const t = Date.now(); const rec = { type: "host", ts: new Date(t).toISOString() };
  const [df] = execSync("df -P /workspace | awk 'NR==2{print $2,$4}'").toString().trim().split("\n");
  const [tot, avail] = df.split(" ").map(Number); rec.disk_free_gb = +(avail / 1048576).toFixed(2); rec.disk_free_pct = +(100 * avail / tot).toFixed(1);
  rec.load = fs.readFileSync("/proc/loadavg", "utf8").split(" ").slice(0, 3).map(Number);
  rec.mem_avail_mb = Math.round(Number(/MemAvailable:\s+(\d+)/.exec(fs.readFileSync("/proc/meminfo", "utf8"))[1]) / 1024);
  const pid = kaspadPid(); const ps = pid ? procStat(pid) : null; rec.kaspad = { pid, rssMB: ps?.rssMB };
  try { rec.mempool = Number((await rpc.getInfo({})).mempoolSize); } catch (e) { rec.infoErr = String(e).slice(0, 80); }
  try { const m = await rpc.getMetrics({ processMetrics: false, connectionMetrics: true, bandwidthMetrics: false, consensusMetrics: true, storageMetrics: false, customMetrics: false });
    const c = m.consensusMetrics; rec.c = { txProcessed: Number(c.nodeTransactionsProcessedCount), blocksSubmitted: Number(c.nodeBlocksSubmittedCount),
      chainBlocks: Number(c.nodeChainBlocksProcessedCount), bodies: Number(c.nodeBodiesProcessedCount), daa: Number(c.networkVirtualDaaScore), tips: Number(c.networkTipHashesCount) };
    rec.peers = m.connectionMetrics?.activePeers;
  } catch (e) { rec.metricsErr = String(e).slice(0, 80); }
  if (prev && rec.c && prev.c) { const dt = (t - prev.t) / 1000;
    rec.rate = { tx_processed_per_s: +((rec.c.txProcessed - prev.c.txProcessed) / dt).toFixed(1), // processed-body counter: overcounts parallel blocks (~x1.337, round 7)
      blocks_submitted_per_s: +((rec.c.blocksSubmitted - prev.c.blocksSubmitted) / dt).toFixed(2), chain_blocks_per_s: +((rec.c.chainBlocks - prev.c.chainBlocks) / dt).toFixed(2),
      daa_per_s: +((rec.c.daa - prev.c.daa) / dt).toFixed(2) };
    if (ps && prev.ps) rec.kaspad.cpu_pct = +(100 * (ps.ticks - prev.ps.ticks) / 100 / dt).toFixed(0); }
  if (SHARE) { rec.share = { ...share, ours_pct: share.blocks ? +(100 * (share.box + share.desk) / share.blocks).toFixed(1) : null }; share = { blocks: 0, box: 0, desk: 0, network: 0 }; }
  w(rec); prev = { t, c: rec.c, ps };
  return rec;
}
const stop = async () => { w({ type: "stop", ts: new Date().toISOString() }); try { await rpc.disconnect(); } catch {} process.exit(0); };
process.on("SIGTERM", stop); process.on("SIGINT", stop);
w({ type: "start", ts: new Date().toISOString(), pid: process.pid, interval: INTERVAL, share: SHARE });
if (ONCE) { await tick(); await new Promise((r) => setTimeout(r, Math.min(INTERVAL, 10) * 1000)); const r = await tick(); console.log(JSON.stringify(r)); await stop(); }
setInterval(tick, INTERVAL * 1000); tick();
