#!/usr/bin/env bash
# TN10 storm-max start/stop wrapper. TESTNET-10 ONLY.
# DECIDED by stp 2026-10-01: path (b) recycled index-free lanes, 24 h, n0 utxoindex OFF, auto slowdown at pruning windows
# (storm-watch.sh writes /tmp/smx-rate; runner honors it). Path (a) is Appendix A in the plan, not wired here.
# DEFAULT IS DRY-RUN: prints every command it WOULD run and checks preconditions; executes nothing that changes state.
# To actually act: STORM_LIVE=1 ./storm.sh <cmd>   (only on stp's explicit go; 'start' starts load).
#   ./storm.sh check     read-only preflight (node synced, disk %, RAM, miners, STOP file, api-tn10 last health line)
#   ./storm.sh baseline  start read-only samplers (kit api/rpc + host_sampler --share + api_health_min + storm-watch)
#   ./storm.sh prep      halt the 6 box miners (touch /tmp/pool-miners.HALT, then exact-pid kill)
#   ./storm.sh start     fee daemon + feeder + runner (LOAD!)
#   ./storm.sh stop      touch STOP, stop senders by exact pid, stop samplers (keeps node running)
#   ./storm.sh restore   remove /tmp/pool-miners.HALT and restart pool-miners-supervisor.sh
#   ./storm.sh status    pids + last watcher line
set -uo pipefail
D=[local path] KIT=[local path] RUN=$D/run; DATA=$D/data
R6=[local path]
LIVE="${STORM_LIVE:-0}"; API_HEALTH_INTERVAL="${API_HEALTH_INTERVAL:-120}"; LANES="${LANES:-1400}"; BASE_RATE="${BASE_RATE:-1500}"
mkdir -p "$RUN" "$DATA"
do_(){ if [ "$LIVE" = 1 ]; then echo "+ $*"; eval "$@"; else echo "[dry-run] $*"; fi; }
bg_(){ local name=$1; shift; if [ "$LIVE" = 1 ]; then echo "+ (bg $name) $*"; nohup setsid bash -c "$*" >>"$DATA/$name.out" 2>&1 </dev/null & echo $! >"$RUN/$name.pid"; else echo "[dry-run bg $name] $*"; fi; }
killpid_(){ local f="$RUN/$1.pid"; [ -f "$f" ] || { echo "$1: no pid file"; return; }; local p; p=$(cat "$f");
  if [ "$LIVE" = 1 ]; then kill -TERM "$p" 2>/dev/null && echo "TERM $1 pid $p"; rm -f "$f"; else echo "[dry-run] kill -TERM $p   # $1 (exact pid)"; fi; }
guard_tn10(){ # refuse anything that isn't our local TN10 node
  local v; v=$([local path] [local path] 2>/dev/null) || { echo "REFUSE: n0 status unreadable"; exit 3; }
  echo "n0: $v"; echo "$v" | grep -q '"isSynced": true' || { echo "REFUSE: n0 not synced"; exit 3; }
  ps -o args= -p "$(pgrep -x kaspad | head -1)" | grep -q -- '--testnet' || { echo "REFUSE: kaspad is not --testnet"; exit 3; }
  ps -o args= -p "$(pgrep -x kaspad | head -1)" | grep -q -- '--netsuffix=10' || { echo "REFUSE: kaspad is not TN10 (netsuffix=10)"; exit 3; }
}
case "${1:-check}" in
  check)
    guard_tn10
    echo "utxoindex flag on kaspad: $(ps -o args= -p "$(pgrep -x kaspad | head -1)" | grep -q -- --utxoindex && echo 'ON (DECIDED: turn OFF for the run, see prep)' || echo OFF)"
    echo "smx-rate: $(cat /tmp/smx-rate 2>/dev/null || echo 'absent (watcher not running)')"
    df -P /workspace | awk 'NR==2{printf "disk free %.1f G (%d%% free; stop line 15%%)\n",$4/1048576,100-$5}'
    awk '/MemAvailable/{printf "MemAvailable %.1f G\n",$2/1048576}' /proc/meminfo; echo "load $(cut -d' ' -f1-3 /proc/loadavg)"
    echo "box miners alive: $(pgrep -fc 'bin-x4/kaspa-miner')  HALT file: $([ -f /tmp/pool-miners.HALT ] && echo present || echo absent)"
    echo "STOP file: $([ -f $D/STOP ] && echo "PRESENT: $(cat $D/STOP)" || echo absent)"
    echo "last api health line: $(tail -1 $DATA/api-health-min.jsonl 2>/dev/null || echo none)"
    echo "public-API calls logged so far: $(grep -c 'GET https' $D/public-api-calls.log)";;
  baseline)
    guard_tn10
    do_ "cd $KIT && API_INTERVAL=300 RPC_POLL=10 OUT_DIR=$DATA ./start.sh all"
    bg_ host   "node $D/host_sampler.mjs --out $DATA/host.jsonl --interval 15 --share"
    bg_ health "python3 $D/api_health_min.py --interval $API_HEALTH_INTERVAL --out $DATA/api-health-min.jsonl --apilog $D/public-api-calls.log"
    bg_ mined  "python3 $D/api_mined_watch.py --interval 300"
    bg_ watch  "$D/storm-watch.sh";;
  prep)
    guard_tn10
    do_ "touch /tmp/pool-miners.HALT"
    echo "# then, after <=30 s, kill each box miner by EXACT pid (never pkill -f):"
    for p in $(pgrep -f 'bin-x4/kaspa-miner'); do do_ "kill -TERM $p"; done
    echo "# desk miners (stp's Windows) keep mining toward n0 via bore; verify with host.jsonl share.desk > 0"
    echo "# [DECIDED] n0 utxoindex OFF for the run (manual, node restart; do it AWAY from 07:05-08:05 / 19:05-20:10):"
    echo "#   1) graceful stop of kaspad pid $(pgrep -x kaspad | head -1) (SIGINT, wait for exit; never kill -9 during pruning)"
    echo "#   2) restart the SAME command line WITHOUT --utxoindex (see 'ps -o args= -p <pid>')"
    echo "#   3) after it is synced: rm -rf [local path]   (frees ~13 G)"
    echo "#   Reversal later: add --utxoindex back; rebuild took ~18.5 min offline + ~13 G (round 3/4).";;
  start)
    guard_tn10
    [ -f "$D/STOP" ] && { echo "REFUSE: STOP present: $(cat $D/STOP)"; exit 4; }
    [ "$(pgrep -fc 'bin-x4/kaspa-miner')" -gt 0 ] && echo "WARN: box miners still running (run ./storm.sh prep first)"
    [ -f "$RUN/watch.pid" ] || echo "WARN: storm-watch not running (run ./storm.sh baseline first)"
    bg_ feerate "python3 $R6/r6-feerate.py"            # 2x normal, min 200 -> /tmp/r6-feerate (reused round 6)
    [ -f /tmp/smx-rate ] || { echo "REFUSE: /tmp/smx-rate missing (storm-watch.sh owns pruning/disk pacing; run baseline)"; [ "$LIVE" = 1 ] && exit 4; }
    echo "BLOCKER before LIVE: local coinbase-tracking feeder not written yet (utxoindex OFF; round-6 feeder uses the public API every 30 s)."
    bg_ feeder  "echo 'TODO: local coinbase feeder (block-added) -> /tmp/r5-reserved-utxos.json'; exit 1"
    bg_ runner  "DRYRUN=0 node $D/storm-max-runner.mjs --lanes $LANES --rate $BASE_RATE --smx-rate-file /tmp/smx-rate --amt-min 0.2 --amt-max 0.6 --node ws://[ip]";;
  stop)
    do_ "echo 'manual stop @ $(date -Iseconds)' > $D/STOP"
    for n in runner feeder feerate; do killpid_ $n; done
    for n in watch health host mined; do killpid_ $n; done
    do_ "cd $KIT && ./stop.sh";;
  restore)
    do_ "rm -f /tmp/pool-miners.HALT"
    do_ "nohup setsid [local path] >/dev/null 2>&1 </dev/null &";;
  status)
    for f in "$RUN"/*.pid; do [ -f "$f" ] && { p=$(cat "$f"); echo "$(basename "$f" .pid) pid $p $(kill -0 "$p" 2>/dev/null && echo alive || echo dead)"; }; done
    tail -1 "$DATA/storm-watch.jsonl" 2>/dev/null;;
  *) sed -n 2,12p "$0";;
esac
