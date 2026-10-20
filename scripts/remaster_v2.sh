#!/usr/bin/env bash
# v2 리마스터 — 낭독 대본을 고친 작품의 TTS 재합성 → 재조립 → 무음 검사 → 전송본.
# 클립은 그대로 둔다. 대본은 works/handwritten/<work>/narration_night.json 또는
# output/<work>/narration_night.json (손글씨가 없으면) 을 쓴다.
#   scripts/remaster_v2.sh <work> [톤]
set -u
cd "$(dirname "$0")/.."
W=${1:?work}; TONE=${2:-담담}
S=${SCRATCH:-/tmp/claude-1000/-home-mooner92-aivideo/eaaf2866-ffc9-4a27-90d7-e8d83d21e029/scratchpad}
NAR=works/handwritten/$W/narration_night.json; [ -s "$NAR" ] || NAR=output/$W/narration_night.json
[ "$NAR" != "output/$W/narration_night.json" ] && cp -p "$NAR" output/$W/narration_night.json
E=$(grep -P "\t$W\t" works/done.txt | tail -1 | cut -f4)
G=$(venv/bin/python scripts/gate_script.py --narration "$NAR" --ending "$E" --maxlen 36 2>&1 | tail -n 1)
C=$(venv/bin/python scripts/check_craft.py 2>/dev/null | grep -E "^  $W:" | grep -oE "(말투[^,]*|S[0-9]+ 이 앞 두 문장과 이어지지 않는다|낭독이 박자보다[^,]*)" | paste -sd, -)
echo "[$W] gate: $G | craft: ${C:-통과}"
echo "$G" | grep -q 통과 || exit 2
[ -z "$C" ] || exit 3
mkdir -p "$S/tts_old/${W}_v1" "$S/v2"; cp -p output/tts/${W}_night_s*.wav "$S/tts_old/${W}_v1/" 2>/dev/null
rm -f output/tts/${W}_night_s*.wav
venv-tts/bin/python scripts/qwen_voice.py --narration output/$W/narration_night.json --tone "$TONE" --device auto \
  --prefix output/tts/${W}_night_s 2>&1 | grep -E '^\{"sentences"|정렬|물러남|대사'
N=$(python3 -c "import json;print(len(json.load(open('output/$W/narration_night.json'))['sentences']))")
[ "$(ls output/tts/${W}_night_s*.wav 2>/dev/null | wc -l)" -eq "$N" ] || { echo "[$W] TTS 실패"; exit 4; }
bash scripts/reassemble_final.sh "$W" 2>&1 | grep -E "조립|발행|실패|감속"
Q=$(ffmpeg -nostdin -hide_banner -i output/$W/final_night.mp4 -vn -af silencedetect=noise=-35dB:d=1.0 -f null - 2>&1 | grep -c silence_start)
ffmpeg -nostdin -y -loglevel error -i output/$W/final_night.mp4 -vf scale=540:960 -c:v libx264 -crf 33 -preset medium \
  -c:a aac -b:a 64k -movflags +faststart "$S/v2/${W}_v2.mp4"
echo "[$W] 무음(>=1s)=$Q · 전송본 $(du -k "$S/v2/${W}_v2.mp4" | cut -f1)KB"
