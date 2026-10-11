#!/usr/bin/env bash
# Box-side: copy storm data into the analysis repo and push every ${SYNC_EVERY:-1800}s. Read-only on the storm itself.
set -uo pipefail
SRC=[local path] R=[local path]
once(){
  cd "$R" || return 1
  cp -f "$SRC"/data/*.jsonl data/ 2>/dev/null; cp -f "$SRC"/public-api-calls.log data/ 2>/dev/null
  [ -f "$SRC/run/LAUNCH.md" ] && cp -f "$SRC/run/LAUNCH.md" notes/LAUNCH.md
  [ -f "$SRC/run/timeline.md" ] && cp -f "$SRC/run/timeline.md" notes/timeline.md
  for f in data/*.jsonl; do s=$(stat -c%s "$f"); if [ "$s" -gt 90000000 ]; then gzip -kf "$f" && git rm -q --cached "$f" 2>/dev/null; echo "$(basename "$f")" >> .gitignore; fi; done
  sort -u -o .gitignore .gitignore 2>/dev/null
  if rg -q -i 'xprv|tprv|mnemonic|private.?key|seed phrase' data notes scripts --glob '!scripts/sync-data.sh'; then echo "$(date -Iseconds) ABORT: secret-looking text found, not pushing"; return 1; fi
  git add -A && git -c user.name=STP-KAS -c user.email=227352643+STP-KAS@users.noreply.github.com commit -qm "data sync $(date -u +%FT%TZ)" && git push -q origin main && echo "$(date -Iseconds) pushed $(git rev-parse --short HEAD)"
}
if [ "${1:-}" = once ]; then once; exit; fi
while [ ! -f "$SRC/SYNC_STOP" ]; do once; sleep "${SYNC_EVERY:-1800}"; done
