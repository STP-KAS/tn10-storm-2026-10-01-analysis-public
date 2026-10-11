#!/usr/bin/env bash
# TN10 storm-max STOP-condition watcher. READ-ONLY except it may create the STOP file. Starts no load.
# Writes [local path] (runner + feeder treat it as HALT) when ANY stop condition trips.
# DECIDED (stp 2026-10-01): also writes a live rate multiplier to $RATE_FILE (default /tmp/smx-rate, 0..1) that the runner
# honors: slowdown in pruning windows (clock) + disk soft lines + mempool pause. Evidence for windows: n0 log pruning moves
# 2026-09-30 07:13->07:52, 19:11->19:59, 2026-10-01 07:16->07:56 (CEST).
# Kills NOTHING by itself (operator kills sender pids by EXACT pid). TN10 only. Logs one JSONL line per tick.
set -uo pipefail
DIR=[local path]
STOP="${STOP_FILE:-$DIR/STOP}"; LOG="${WATCH_LOG:-$DIR/data/storm-watch.jsonl}"; APILOG="$DIR/public-api-calls.log"
mkdir -p "$DIR/data"
INTERVAL="${INTERVAL:-15}"                 # seconds between local checks
DISK_MIN_PCT="${DISK_MIN_PCT:-15}"         # stop line: <15% free
MEMPOOL_MAX="${MEMPOOL_MAX:-80000}"        # pause guard (100k cap panics)
RAM_MIN_MB="${RAM_MIN_MB:-1024}"           # RAM floor
LAG_MAX_S="${LAG_MAX_S:-300}"             # n0 >5 min behind network
API_EVERY="${API_EVERY:-300}"             # public api lag cross-check: <= every 5 min, logged
RATE_FILE="${RATE_FILE:-/tmp/smx-rate}"
PRUNE_WINDOWS="${PRUNE_WINDOWS:-07:05-08:05,19:05-20:10}"   # local CEST HH:MM-HH:MM, comma-separated
PRUNE_RATE="${PRUNE_RATE:-0.25}"                            # rate multiplier inside a pruning window
DISK_SOFT1_GB="${DISK_SOFT1_GB:-22}"; DISK_SOFT1_RATE="${DISK_SOFT1_RATE:-0.5}"
DISK_SOFT2_GB="${DISK_SOFT2_GB:-20}"; DISK_SOFT2_RATE="${DISK_SOFT2_RATE:-0.25}"
MEMPOOL_RESUME="${MEMPOOL_RESUME:-55000}"
NOW_HHMM="${NOW_HHMM:-}"                                    # dry-run only: override the clock, e.g. NOW_HHMM=19:30
ONCE="${ONCE:-0}"; NO_API="${NO_API:-0}"   # dry-run: ONCE=1 NO_API=1 STOP_FILE=/tmp/x WATCH_LOG=/tmp/y
PY=[local path]
set_stop(){ echo "$1" > "$STOP"; }
last_api=0
mp_paused=0
in_window(){ # echo 1 if HH:MM (now or NOW_HHMM) is inside any PRUNE_WINDOWS range
  local hm="${NOW_HHMM:-$(date +%H:%M)}"; local m=$((10#${hm%:*}*60 + 10#${hm#*:})); local w a b am bm
  IFS=',' read -ra W <<<"$PRUNE_WINDOWS"
  for w in "${W[@]}"; do a=${w%-*}; b=${w#*-}; am=$((10#${a%:*}*60+10#${a#*:})); bm=$((10#${b%:*}*60+10#${b#*:}))
    if [ "$am" -le "$bm" ]; then [ "$m" -ge "$am" ] && [ "$m" -lt "$bm" ] && { echo 1; return; }
    else { [ "$m" -ge "$am" ] || [ "$m" -lt "$bm" ]; } && { echo 1; return; }; fi; done; echo 0; }
fmin(){ awk -v a="$1" -v b="$2" 'BEGIN{print (a<b)?a:b}'; }
ts(){ date -Iseconds; }
while true; do
  [ -f "$STOP" ] && { echo "{\"t\":\"$(ts)\",\"ev\":\"stop_present\",\"reason\":\"$(head -c200 "$STOP")\"}" >>"$LOG"; sleep "$INTERVAL"; continue; }
  # --- local, free: disk / ram / load ---
  read -r dfree_kb dpct < <(df -P /workspace | awk 'NR==2{gsub("%","",$5); print $4, 100-$5}')
  ram_av=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  load1=$(awk '{print $1}' /proc/loadavg)
  # --- n0 via LOCAL wRPC (not public): mempool, sink age, sync ---
  n0=$("$PY" - <<'PYEOF' 2>/dev/null
import asyncio,json,time,websockets
async def main():
  try:
    async with websockets.connect("ws://[ip]",open_timeout=4) as ws:
      async def c(i,m,p={}):
        await ws.send(json.dumps({"id":i,"method":m,"params":p}))
        while True:
          r=json.loads(await asyncio.wait_for(ws.recv(),8))
          if r.get("id")==i: return r.get("params") or r
      info=await c(1,"getInfo"); d=await c(2,"getBlockDagInfo")
      age=None
      try:
        b=await c(3,"getBlock",{"hash":d["sink"],"includeTransactions":False})
        age=round(time.time()-int(b["block"]["header"]["timestamp"])/1000,1)
      except Exception: pass
      print(json.dumps({"mempool":info.get("mempoolSize"),"synced":info.get("isSynced"),"sinkAgeS":age,"daa":d.get("virtualDaaScore")}))
  except Exception as e:
    print(json.dumps({"err":str(e)[:120]}))
asyncio.run(main())
PYEOF
)
  mempool=$(echo "$n0" | sed -n 's/.*"mempool": *\([0-9]*\).*/\1/p')
  sinkage=$(echo "$n0" | sed -n 's/.*"sinkAgeS": *\([0-9.]*\).*/\1/p')
  synced=$(echo "$n0" | grep -q '"synced": *true' && echo true || echo false)
  reason=""
  awk "BEGIN{exit !($dpct < $DISK_MIN_PCT)}" && reason="disk<${DISK_MIN_PCT}% (free ${dpct}%)"
  [ -z "$reason" ] && [ -n "${ram_av:-}" ] && [ "$ram_av" -lt "$RAM_MIN_MB" ] && reason="ram<${RAM_MIN_MB}MB (${ram_av})"
  [ -z "$reason" ] && [ "$synced" = "false" ] && reason="n0 not synced"
  [ -z "$reason" ] && [ -n "${sinkage:-}" ] && awk "BEGIN{exit !($sinkage > $LAG_MAX_S)}" && reason="n0 sink age ${sinkage}s > ${LAG_MAX_S}s (>5 min behind)"
  # mempool is a PAUSE guard, not a hard stop (runner also self-pauses at 75k)
  pause=""
  if [ -n "${mempool:-}" ]; then
    if [ "$mempool" -gt "$MEMPOOL_MAX" ]; then mp_paused=1; elif [ "$mempool" -lt "$MEMPOOL_RESUME" ]; then mp_paused=0; fi
  fi
  [ "$mp_paused" = 1 ] && pause="mempool>${MEMPOOL_MAX} until <${MEMPOOL_RESUME} (${mempool})"
  # ---- auto-pace multiplier (min of all active rules) ----
  dfree_gb=$(awk -v k="$dfree_kb" 'BEGIN{printf "%.2f", k/1048576}')
  rate=1; why="full"
  if [ "$(in_window)" = 1 ]; then rate=$(fmin "$rate" "$PRUNE_RATE"); why="prune-window"; fi
  if awk "BEGIN{exit !($dfree_gb < $DISK_SOFT2_GB)}"; then rate=$(fmin "$rate" "$DISK_SOFT2_RATE"); why="$why,disk<${DISK_SOFT2_GB}G"
  elif awk "BEGIN{exit !($dfree_gb < $DISK_SOFT1_GB)}"; then rate=$(fmin "$rate" "$DISK_SOFT1_RATE"); why="$why,disk<${DISK_SOFT1_GB}G"; fi
  [ "$mp_paused" = 1 ] && { rate=0; why="$why,mempool-pause"; }
  why=${why#full,}
  printf '%s\n' "$rate" > "$RATE_FILE.tmp" && mv "$RATE_FILE.tmp" "$RATE_FILE"
  echo "{\"t\":\"$(ts)\",\"disk_free_pct\":$dpct,\"disk_free_kb\":$dfree_kb,\"ram_av_mb\":${ram_av:-null},\"load1\":$load1,\"mempool\":${mempool:-null},\"sinkAgeS\":${sinkage:-null},\"synced\":$synced,\"pause\":\"$pause\",\"smx_rate\":$rate,\"rate_why\":\"$why\",\"disk_free_gb\":$dfree_gb,\"reason\":\"$reason\"}" >>"$LOG"
  if [ -n "$reason" ]; then printf "0\n" > "$RATE_FILE"; set_stop "$reason @ $(ts)"; echo "{\"t\":\"$(ts)\",\"ev\":\"STOP_SET\",\"reason\":\"$reason\"}" >>"$LOG"; fi
  # optional public-API lag cross-check, <= every API_EVERY s, each call logged
  now=$(date +%s)
  if [ "$NO_API" != 1 ] && [ $((now - last_api)) -ge "$API_EVERY" ]; then
    cb=$(date +%s%N); echo "[$(ts)] GET https://api-tn10.kaspa.org/info/virtual-chain-blue-score?cb=$cb (storm-watch lag cross-check)" >>"$APILOG"
    curl -sS --max-time 15 -H 'User-Agent: Mozilla/5.0' "https://api-tn10.kaspa.org/info/virtual-chain-blue-score?cb=$cb" >>"$DIR/data/api-vcbs-watch.jsonl" 2>/dev/null; echo >>"$DIR/data/api-vcbs-watch.jsonl"
    last_api=$now
  fi
  [ "$ONCE" = 1 ] && break
  sleep "$INTERVAL"
done
