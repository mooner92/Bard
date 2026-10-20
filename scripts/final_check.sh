#!/usr/bin/env bash
# 발행된 영상 한 편의 최종 점검 — 컨택트시트·무음·전송본을 한 번에 만든다.
#   scripts/final_check.sh <work> [outdir]
# 손으로 세 번씩 치던 ffmpeg 을 묶은 것이다(09-17). 길이·배속은 조립 로그에 있고
# 여기서는 **눈으로 볼 것**(15컷 한 장)과 **귀로 놓치는 것**(1초 이상 무음)만 본다.
set -u
cd "$(dirname "$0")/.."
W=${1:?work}
OUT=${2:-/tmp/claude-1000/-home-mooner92-aivideo/final}
mkdir -p "$OUT"
F="output/$W/final_night.mp4"
[ -s "$F" ] || { echo "[$W] final_night.mp4 없음"; exit 2; }
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$F" | cut -d. -f1)
STEP=$(( D * 24 / 15 )); [ "$STEP" -lt 1 ] && STEP=1
ffmpeg -v error -y -i "$F" -vf "select='not(mod(n\,$STEP))',scale=216:-2,tile=5x3" \
  -frames:v 1 "$OUT/${W}_sheet.png"
SIL=$(ffmpeg -v info -i "$F" -af silencedetect=n=-40dB:d=1.0 -f null - 2>&1 | grep -c silence_start)
ffmpeg -v error -y -i "$F" -vf scale=360:-2 -crf 32 -preset slow -c:v libx264 \
  -c:a aac -b:a 64k "$OUT/${W}_360p.mp4"
KB=$(( $(stat -c%s "$OUT/${W}_360p.mp4") / 1024 ))
echo "[$W] ${D}초 · 무음(>=1s) ${SIL}곳 · 전송본 ${KB}KB"
echo "  $OUT/${W}_sheet.png"
echo "  $OUT/${W}_360p.mp4"
