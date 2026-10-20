#!/usr/bin/env bash
# 검수에서 걸린 컷 하나의 클립을 다시 뽑는다 (kf 는 이미 output/<w>_kf/night_sN_00001_.png 로 바꿔치기한 뒤).
#   scripts/patch_clip.sh <work> <n>
# 배치 ④ 단계와 같은 조리법: crop → 음성 길이로 프레임 수 → scene_prompt --motion → gen_i2v(seed 42).
# 옛 클립은 output/_archive/clipfix/ 로 옮긴다. 끝나면 reassemble_final.sh 로 재조립·재발행할 것.
set -u
cd "$(dirname "$0")/.."
W=${1:?work}; N=${2:?n}
TRE=works/handwritten/$W/treatment.json; [ -s "$TRE" ] || TRE=output/$W/treatment.json
MOTION_NEG="static, still, motionless, frozen, jittery, flickering, warping, morphing, text, watermark, blurry, distorted, deformed"
src=$(ls output/${W}_kf/night_s${N}_*.png 2>/dev/null | head -1); [ -s "$src" ] || { echo "kf 없음: s$N"; exit 1; }
venv/bin/python scripts/crop_keyframe.py --src "$src" --dst "ComfyUI/input/night_${W}_${N}.png" || exit 2
d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "output/tts/${W}_night_s${N}.wav")
fr=$(python3 -c "
import math
d=$d; f=max(81, math.ceil(d*24)); f = f + (4 - (f-1) % 4) % 4; print(min(f, 117))")
mot=$(venv/bin/python scripts/scene_prompt.py --motion --index "$N" --treatment "$TRE" 2>/dev/null)
[ -z "$mot" ] && mot="gentle continuous motion in the scene, slow camera drift"
venv/bin/python - "$N" "$mot" <<PY
import json, pathlib, sys
f = pathlib.Path('output/${W}_kf/prompts.json')
d = json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}
d.setdefault(sys.argv[1], {})['motion'] = sys.argv[2]
f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
PY
old="output/${W}_i2v/night_s${N}_00001_.mp4"
if [ -s "$old" ]; then mkdir -p output/_archive/clipfix; mv "$old" "output/_archive/clipfix/${W}_s${N}_$(date +%m%d%H%M).mp4"; fi
echo "[$W] S$N 클립 재생성: ${fr}프레임 (음성 ${d%.*}초) — motion ${#mot}자"
venv/bin/python scripts/comfy_wait.py >/dev/null 2>&1
venv/bin/python scripts/gen_i2v.py --image "night_${W}_${N}.png" --prefix "${W}_i2v/night_s${N}" --length "$fr" --seed 42 \
  --prompt "$mot" --negative "$MOTION_NEG" >/dev/null 2>&1
[ -s "$old" ] && echo "[$W] S$N 클립 완료" || echo "[$W] S$N 클립 실패(파일 없음 — ComfyUI 작업이 아직 돌면 기다릴 것)"
