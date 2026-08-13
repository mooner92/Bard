#!/usr/bin/env bash
# 야간 상시 제작 v2 (20:00~08:00) — 대본부터 자가점검까지 전 공정.
#
# v1 대비 달라진 점
#  1) 큐 5열째에 톤(담담/따뜻/서늘/긴장/속삭임/생동)을 받는다. 비면 담담.
#  2) 문장 길이 30~42자 — 8문장 45초 명세를 맞춘다 (v1 은 22~33자라 37초에 그쳤다).
#  3) TTS 를 scripts/tts_render.py 로 합성한다. 톤별 prosody + 텐션 곡선 + 강세.
#  4) 최종 인코딩에 loudnorm(-14 LUFS) — v1 산출물은 -17 LUFS 로 조용했다.
#  5) 완성 직후 scripts/review_output.py 자가점검을 돌려 logs/review/ 에 남긴다.
#  6) 네거티브에 글자류를 보강 — 생성 이미지의 가짜 한글 낙서를 줄인다.
#
# 설계 원칙(v1 유지)
#  - 재개 가능: 각 단계는 산출물이 있으면 건너뛴다.
#  - 큐에서 줄을 지우는 시점은 "완성" 또는 "영구 실패" 뿐이다.
#  - 08:00 이후에는 새 작품·새 클립을 시작하지 않는다.
#  - 산출물은 output/ 까지만. deliverables/ 승격과 업로드는 사람이 승인한다.
set -uo pipefail
cd /home/mooner92/aivideo
export TZ=Asia/Seoul   # 서버 시계는 UTC. 작업창·로그 날짜는 한국시간으로 판정한다.

LOCK=/tmp/aivideo-night.lock
LOGDIR=logs/night; mkdir -p "$LOGDIR" works output/tts logs/review
LOG="$LOGDIR/$(date +%F).log"
Q=works/queue.txt; DONE=works/done.txt; FAIL=works/failed.txt
touch "$Q" "$DONE" "$FAIL"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

exec 9>"$LOCK"
flock -n 9 || { say "이미 실행 중 — 종료"; exit 0; }

DISK_MIN_GB=50
work_window() { local h; h=$(date +%-H); [ "$h" -ge 20 ] || [ "$h" -lt 8 ]; }
disk_ok() {
  local free; free=$(df -BG --output=avail . | tail -1 | tr -dc '0-9')
  [ "${free:-0}" -ge "$DISK_MIN_GB" ] || { say "디스크 여유 ${free}GB < ${DISK_MIN_GB}GB — 중단"; return 1; }
}
svc_ok() {
  curl -sf -m 10 http://127.0.0.1:8188/queue >/dev/null || { say "ComfyUI 무응답"; return 1; }
  curl -sf -m 10 http://127.0.0.1:11434/api/tags >/dev/null || { say "Ollama 무응답"; return 1; }
}

STYLE_DEFAULT="19th century copperplate engraving illustration, hand-etched crosshatching lines, aged yellowed paper texture, muted indigo and faded amber ink palette, antique book plate aesthetic. "
# 글자류를 앞쪽에 몰아 둔다. 생성물에 가짜 한글이 적히는 사례가 잦다(실측).
NEG="text, letters, hangul, korean characters, handwriting, printed words, caption, subtitle, inscription, signature, watermark, rectangular box head, slab, eraser, photorealistic, photograph, 3d render, cgi, glossy, vibrant saturated colors, bright blue sky, modern clothing, anime, smooth digital art, blurry, deformed"
MOTION_NEG="static, still, motionless, frozen, jittery, flickering, warping, morphing, text, watermark, blurry, distorted, deformed"

produced=0; failed=0
say "=== 야간 배치 v2 시작 (큐 $(grep -cvE '^[[:space:]]*(#|$)' "$Q") 건) ==="

while work_window; do
  disk_ok || break
  svc_ok  || { say "서비스 이상 — 60초 후 재확인"; sleep 60; continue; }

  line=$(grep -vE '^[[:space:]]*(#|$)' "$Q" | head -1) || true
  [ -z "${line:-}" ] && { say "큐 비어 있음 — 종료"; break; }

  work=$(echo "$line" | cut -f1)
  facts=$(echo "$line" | cut -f2)
  ending=$(echo "$line" | cut -f3)
  style=$(echo "$line" | cut -f4); [ -z "$style" ] && style="$STYLE_DEFAULT"
  tone=$(echo "$line" | cut -f5); [ -z "$tone" ] && tone="담담"
  say "▶ $work (톤 $tone)"

  NAR="output/$work/narration_night.json"
  mkdir -p "output/$work" "output/${work}_kf" "output/${work}_i2v"
  ok=1

  # ── ① 대본 ──
  if [ -s "$NAR" ] && python3 -c "import json,sys; sys.exit(0 if json.load(open('$NAR'))['sentences'] else 1)" 2>/dev/null; then
    say "  ① 대본 있음 — 건너뜀"
  elif [ ! -f "$facts" ]; then
    say "  ① 사실파일 없음($facts) — 영구 실패"; ok=0
  else
    venv/bin/python scripts/write_script.py --title "$work" --facts "$facts" \
      --scenes 8 --minlen 30 --maxlen 42 --tone "$tone" --emphasis \
      --ending "$ending" --out "$NAR" >>"$LOG" 2>&1
    if [ -s "$NAR" ]; then
      say "  ① 대본 준비됨"   # 검증 미통과여도 진행하고 아침에 사람이 검수한다
    else
      say "  ① 대본 실패"; ok=0
    fi
  fi
  if [ "$ok" != 1 ]; then
    printf '%s\t%s\tscript\n' "$(date +%FT%T)" "$line" >>"$FAIL"
    grep -vxF "$line" "$Q" >"$Q.t" && mv "$Q.t" "$Q"
    failed=$((failed+1)); continue
  fi

  N=$(python3 -c "import json;print(len(json.load(open('$NAR'))['sentences']))")

  # ── ② TTS (톤·텐션 곡선·강세) ──
  if [ "$(ls output/tts/${work}_night_s*.wav 2>/dev/null | wc -l)" -ne "$N" ]; then
    venv/bin/python scripts/tts_render.py --narration "$NAR" --tone "$tone" --arc 산형 \
      --prefix "output/tts/${work}_night_s" >>"$LOG" 2>&1
  fi
  got=$(ls output/tts/${work}_night_s*.wav 2>/dev/null | wc -l)
  [ "$got" -eq "$N" ] || { say "  ② TTS $got/$N — 일시 실패, 큐 유지"; continue; }
  say "  ② TTS $N개"

  # ── ③ 키프레임 ──
  for i in $(seq 1 "$N"); do
    work_window || break
    ls output/${work}_kf/night_s${i}_*.png >/dev/null 2>&1 && continue
    # 강세 표시(*낱말*)는 그림 프롬프트에 들어가면 안 된다
    desc=$(python3 -c "
import json
print(json.load(open('$NAR'))['sentences'][$i-1].replace('*',''))")
    venv/bin/python scripts/gen_keyframe.py --seed $((200+i)) \
      --prefix "${work}_kf/night_s${i}" --prompt "${style}${desc}" --negative "$NEG" >>"$LOG" 2>&1 \
      || say "  ③ s${i} 키프레임 실패"
  done
  kf=$(ls output/${work}_kf/night_s*.png 2>/dev/null | wc -l)
  [ "$kf" -eq "$N" ] || { say "  ③ 키프레임 $kf/$N — 큐 유지(다음 밤 이어감)"; continue; }
  say "  ③ 키프레임 $N장"

  # ── ④ 크롭 → I2V ──
  for i in $(seq 1 "$N"); do
    work_window || break
    [ -s "output/${work}_i2v/night_s${i}_00001_.mp4" ] && continue
    src=$(ls output/${work}_kf/night_s${i}_*.png 2>/dev/null | head -1)
    [ -z "$src" ] && continue
    ffmpeg -y -i "$src" -vf "crop=iw:ih*0.88:0:ih*0.06,crop='min(iw,ih*480/848)':'min(ih,iw*848/480)',scale=480:848:flags=lanczos" \
      "ComfyUI/input/night_${work}_${i}.png" >/dev/null 2>&1
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "output/tts/${work}_night_s${i}.wav")
    # 감속 1.5배 상한을 지키는 최소 프레임 수를 4n+1 로 **올림**한다.
    # 내림하면 프레임이 모자라 감속이 1.5배를 살짝 넘는다(실측 1.52~1.54).
    fr=$(python3 -c "
import math
d=$d; f=max(81, math.ceil(d*24/1.5))
print(f + (4 - (f-1) % 4) % 4)")
    venv/bin/python scripts/gen_i2v.py --image "night_${work}_${i}.png" \
      --prefix "${work}_i2v/night_s${i}" --length "$fr" --seed 42 \
      --prompt "gentle continuous motion in the scene, slow camera drift" \
      --negative "$MOTION_NEG" >>"$LOG" 2>&1 || say "  ④ s${i} I2V 실패"
  done
  cl=$(ls output/${work}_i2v/night_s*.mp4 2>/dev/null | wc -l)
  [ "$cl" -eq "$N" ] || { say "  ④ 클립 $cl/$N — 큐 유지(다음 밤 이어감)"; continue; }
  say "  ④ 클립 $N개"

  # ── ⑤ 조립 (음량 -14 LUFS 로 정규화) ──
  ASM=/tmp/night_asm_$work; rm -rf "$ASM"; mkdir -p "$ASM"
  for i in $(seq 1 "$N"); do
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "output/tts/${work}_night_s${i}.wav")
    c="output/${work}_i2v/night_s${i}_00001_.mp4"
    cd_=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$c")
    f=$(python3 -c "print(f'{$d/$cd_:.6f}')")
    ffmpeg -y -i "$c" -vf "setpts=${f}*PTS,scale=1080:1920:flags=lanczos" -r 24 \
      -c:v libx264 -crf 18 -pix_fmt yuv420p -an "$ASM/v$i.mp4" >/dev/null 2>&1
    echo "file '$ASM/v$i.mp4'" >> "$ASM/v.txt"
    echo "file '$PWD/output/tts/${work}_night_s${i}.wav'" >> "$ASM/a.txt"
  done
  ffmpeg -y -f concat -safe 0 -i "$ASM/v.txt" -c copy "$ASM/v.mp4" >/dev/null 2>&1
  ffmpeg -y -f concat -safe 0 -i "$ASM/a.txt" -c copy "$ASM/a.wav" >/dev/null 2>&1
  OUT="output/$work/final_night.mp4"
  ffmpeg -y -i "$ASM/v.mp4" -i "$ASM/a.wav" -c:v libx264 -crf 20 -profile:v high -pix_fmt yuv420p \
    -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUT" >/dev/null 2>&1

  # 완료 판정은 종료코드가 아니라 스트림 확인으로 한다 (거짓 성공 방지)
  types=$(ffprobe -v error -show_entries stream=codec_type -of csv=p=0 "$OUT" 2>/dev/null)
  if echo "$types" | grep -q video && echo "$types" | grep -q audio; then
    dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
    say "  ⑤ 완성 ${dur%.*}초 → $OUT"
    grep -vxF "$line" "$Q" >"$Q.t" && mv "$Q.t" "$Q"
    printf '%s\t%s\t%ss\n' "$(date +%FT%T)" "$line" "${dur%.*}" >> "$DONE"
    produced=$((produced+1))
    # ── ⑥ 자가점검 ──
    venv/bin/python scripts/review_output.py --work "$work" --fix-loudness >>"$LOG" 2>&1
    say "  ⑥ 자가점검 → logs/review/${work}.md"
  else
    say "  ⑤ 조립 검증 실패 — 큐 유지"
  fi
  rm -rf "$ASM"
done

say "=== 끝 · 완성 ${produced}편 · 실패 ${failed}건 · 큐 잔여 $(grep -cvE '^[[:space:]]*(#|$)' "$Q") ==="
printf '%s\tproduced=%s\tfailed=%s\tqueue=%s\n' \
  "$(date +%F)" "$produced" "$failed" "$(grep -cvE '^[[:space:]]*(#|$)' "$Q")" >> "$LOGDIR/summary.tsv"
