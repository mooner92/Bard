#!/usr/bin/env bash
# 책방 하루 한 번 갱신 (사용자 타이머 aivideo-books-daily.timer, 매일 09:00 KST)
#  1) 정보나루 순위 — 달이 바뀌었으면 전부, 아니면 빠진 것만(--retry) 다시 받는다
#  2) KEI 소장 — 백엔드를 한 번 불러 24시간 지난 항목을 뒤에서 새로 받게 하고, 끝날 때까지 기다린다
#  3) 기준 시각을 data/loans/books_updated.txt 에 적는다 → 페이지 상단 "YYMMDD(요일) HH:MM 기준"
set -u
cd "$(dirname "$0")/.."
venv/bin/python scripts/our_ranks.py --retry >> logs/our_ranks.log 2>&1
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  n=$(curl -s "http://127.0.0.1:8010/api/books/ours" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for b in d['books'] if b['holding']=='unknown'))" 2>/dev/null || echo 0)
  [ "${n:-0}" = "0" ] && break
  sleep 20
done
date +"%Y-%m-%dT%H:%M:%S%z" > data/loans/books_updated.txt
echo "[$(date +%H:%M:%S)] 책방 갱신 완료 (소장 미확인 ${n:-0}건)" >> logs/our_ranks.log
