#!/usr/bin/env bash
# 야간 상시 제작 (20:00~08:00). 큐가 비면 즉시 종료한다.
set -uo pipefail
cd /home/mooner92/aivideo
LOG="logs/night/$(date +%F).log"
Q=works/queue.txt; D=works/done.txt
touch "$Q" "$D"
say() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }

say "=== 야간 배치 시작 ==="
while :; do
  # 08:00 이후면 새 작품을 시작하지 않는다 (진행 중인 것은 이미 끝난 상태)
  [ "$(date +%H)" -ge 8 ] && [ "$(date +%H)" -lt 20 ] && { say "주간 시간대 — 종료"; break; }
  line=$(grep -vE '^\s*(#|$)' "$Q" | head -1) || true
  [ -z "${line:-}" ] && { say "큐 비어 있음 — 종료"; break; }

  work=$(echo "$line" | cut -f1)
  facts=$(echo "$line" | cut -f2)
  ending=$(echo "$line" | cut -f3)
  say "▶ $work 시작"

  if venv/bin/python scripts/write_script.py --title "$work" --facts "$facts" \
       --scenes 8 --minlen 22 --maxlen 33 --ending "$ending" \
       --out "output/$work/narration_night.json" >> "$LOG" 2>&1; then
    say "  대본 완료"
  else
    say "  대본 실패 — 건너뜀"
  fi

  # 처리한 줄을 큐에서 제거하고 done 으로 옮긴다 (실패해도 무한 재시도 금지)
  grep -vxF "$line" "$Q" > "$Q.tmp" && mv "$Q.tmp" "$Q"
  printf '%s\t%s\n' "$(date +%FT%T)" "$line" >> "$D"
  say "◀ $work 종료"
done
say "=== 야간 배치 끝 ==="
