#!/usr/bin/env bash
# 클립은 그대로 두고 낭독(wav)만 바뀐 작품을 다시 조립·자가점검·발행한다.
# night_batch_v2.sh 의 ⑤⑥⑦ 과 같은 명령. 옛 완성본은 output/_archive/ttsfix/ 에 보관.
#
#   scripts/reassemble_final.sh <work> [--no-publish]
set -u
cd "$(dirname "$0")/.."
work=${1:?work}; shift || true
PUB=1; [ "${1:-}" = "--no-publish" ] && PUB=0
NAR="output/$work/narration_night.json"
N=$(python3 -c "import json;print(len(json.load(open('$NAR'))['sentences']))")
for i in $(seq 1 "$N"); do
  [ -s "output/tts/${work}_night_s${i}.wav" ] || { echo "wav 없음: s$i"; exit 1; }
  [ -s "output/${work}_i2v/night_s${i}_00001_.mp4" ] || { echo "클립 없음: s$i"; exit 1; }
done
OUT="output/$work/final_night.mp4"
if [ -s "$OUT" ]; then
  mkdir -p output/_archive/ttsfix
  cp -p "$OUT" "output/_archive/ttsfix/${work}_final_night_$(date +%m%d%H%M).mp4"
fi
ASM=$(mktemp -d /tmp/reasm_${work}_XXXX)
ratios=()
for i in $(seq 1 "$N"); do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "output/tts/${work}_night_s${i}.wav")
  c="output/${work}_i2v/night_s${i}_00001_.mp4"
  cd_=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$c")
  f=$(python3 -c "print(f'{$d/$cd_:.6f}')")
  ratios+=("$(printf '%.2f' "$f")")
  ffmpeg -y -i "$c" -vf "setpts=${f}*PTS,scale=1080:1920:flags=lanczos" -r 24 \
    -c:v libx264 -crf 18 -pix_fmt yuv420p -an "$ASM/v$i.mp4" >/dev/null 2>&1
  echo "file '$ASM/v$i.mp4'" >> "$ASM/v.txt"
  echo "file '$PWD/output/tts/${work}_night_s${i}.wav'" >> "$ASM/a.txt"
done
ffmpeg -y -f concat -safe 0 -i "$ASM/v.txt" -c copy "$ASM/v.mp4" >/dev/null 2>&1
ffmpeg -y -f concat -safe 0 -i "$ASM/a.txt" -c copy "$ASM/a.wav" >/dev/null 2>&1
ffmpeg -y -i "$ASM/v.mp4" -i "$ASM/a.wav" -c:v libx264 -crf 20 -profile:v high -pix_fmt yuv420p \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUT.tmp.mp4" >/dev/null 2>&1
types=$(ffprobe -v error -show_entries stream=codec_type -of csv=p=0 "$OUT.tmp.mp4" 2>/dev/null)
if echo "$types" | grep -q video && echo "$types" | grep -q audio; then
  mv "$OUT.tmp.mp4" "$OUT"
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
  echo "조립 ${dur%.*}초 → $OUT · 배속 ${ratios[*]}"
  # 대사가 든 문장은 wav 가 길어 클립(최대 117프레임=4.9초)이 1.5배 넘게 느려질 수 있다 — 지문을 26자 안쪽으로.
  k=0; for r in "${ratios[@]}"; do k=$((k+1)); awk -v r="$r" 'BEGIN{exit !(r>1.5)}' && echo "  !! 감속 초과 S$k (${r}배) — 지문을 줄여 다시 합성할 것"; done
  venv/bin/python scripts/review_output.py --work "$work" --fix-loudness >/dev/null 2>&1 && echo "자가점검 → logs/review/${work}.md"
  if [ "$PUB" = 1 ]; then
    venv/bin/python scripts/publish_final.py --work "$work" >/dev/null 2>&1 && echo "발행 → /data/bard/video" || echo "발행 실패(수동 확인)"
  fi
  rm -rf "$ASM"; exit 0
else
  echo "조립 검증 실패 — 옛 완성본 유지"; rm -f "$OUT.tmp.mp4"; rm -rf "$ASM"; exit 1
fi
