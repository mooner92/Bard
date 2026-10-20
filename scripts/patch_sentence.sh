#!/usr/bin/env bash
# 한 문장만 다시 합성해 끼운다. 전체 재합성(remaster_v2)은 한 호흡 생성이라 회차마다
# 문장 속도가 ±20% 흔들려 고친 문장 대신 다른 문장이 새로 1.5배를 넘곤 했다(09-09 실측).
# 문장 모드는 시드가 고정이라 같은 글은 같은 소리 — 길면 글을 줄이는 수밖에 없다.
#   scripts/patch_sentence.sh <work> <n> [톤]     (대본은 미리 관문을 통과시켜 둘 것)
set -u
cd "$(dirname "$0")/.."
W=${1:?work}; N=${2:?n}; TONE=${3:-담담}
S=${SCRATCH:-/tmp/claude-1000/-home-mooner92-aivideo/eaaf2866-ffc9-4a27-90d7-e8d83d21e029/scratchpad}
NAR=works/handwritten/$W/narration_night.json; [ -s "$NAR" ] || NAR=output/$W/narration_night.json
[ "$NAR" != "output/$W/narration_night.json" ] && cp -p "$NAR" output/$W/narration_night.json
mkdir -p "$S/patch" "$S/v2"
python3 - "$NAR" "$N" "$S/patch/${W}_s$N.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); n = int(sys.argv[2])
d["sentences"] = [d["sentences"][n - 1]]
json.dump(d, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False)
print(f"[{sys.argv[1].split('/')[-2]}] S{n}: {d['sentences'][0]}")
PY
rm -f "$S/patch/${W}_s${N}_1.wav"
venv-tts/bin/python scripts/qwen_voice.py --narration "$S/patch/${W}_s$N.json" --mode sentence --tone "$TONE" \
  --device auto --prefix "$S/patch/${W}_s${N}_" 2>&1 | grep -E '^\{"sentences"|대사|실패'
NEW="$S/patch/${W}_s${N}_1.wav"; [ -s "$NEW" ] || { echo "[$W] S$N 합성 실패"; exit 4; }
A=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$NEW")
C=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "output/${W}_i2v/night_s${N}_00001_.mp4")
R=$(python3 -c "print(f'{$A/$C:.2f}')")
echo "[$W] S$N 새 wav ${A%.*}초 / 클립 ${C%.*}초 → ${R}배"
awk -v r="$R" 'BEGIN{exit !(r>1.5)}' && { echo "[$W] S$N 아직 1.5배 초과 — 글을 더 줄일 것(끼우지 않음)"; exit 5; }
cp -p "output/tts/${W}_night_s$N.wav" "$S/patch/${W}_s${N}_old.wav" 2>/dev/null
cp -p "$NEW" "output/tts/${W}_night_s$N.wav"
bash scripts/reassemble_final.sh "$W" 2>&1 | grep -E "조립|발행|실패|감속"
Q=$(ffmpeg -nostdin -hide_banner -i output/$W/final_night.mp4 -vn -af silencedetect=noise=-35dB:d=1.0 -f null - 2>&1 | grep -c silence_start)
ffmpeg -nostdin -y -loglevel error -i output/$W/final_night.mp4 -vf scale=540:960 -c:v libx264 -crf 33 -preset medium \
  -c:a aac -b:a 64k -movflags +faststart "$S/v2/${W}_v2.mp4"
echo "[$W] 무음(>=1s)=$Q · 전송본 $(du -k "$S/v2/${W}_v2.mp4" | cut -f1)KB"
