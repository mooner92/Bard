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
#  - 08:00 이후에는 새 작품을 시작하지 않되, 이미 시작한 작품은 끝까지 마친다.
#    다른 이용자가 10시쯤 서버를 쓰므로 09:40 이 최종 한계다.
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
# 시간 정책 (사용자 지정)
#  - 새 작품 착수: 20:00~08:00 만.
#  - 이미 시작한 작품: 08:00 이 지나도 끊지 않고 마무리한다.
#  - 다만 다른 이용자가 10시쯤 서버를 쓰기 시작하므로 09:40 을 넘기지 않는다.
#    09:40 이후에는 진행 중인 클립만 끝내고 멈춘다(산출물은 남아 다음 밤에 이어감).
# 기본값은 야간 자동화용. 개발 중 수동 실행은 환경변수로 풀어 쓴다.
#   START_BY=1930 FINISH_BY=1930 scripts/night_batch_v2.sh
START_BY=${START_BY:-800}    # 이 시각 이후에는 새 작품을 시작하지 않는다
FINISH_BY=${FINISH_BY:-940}  # 이 시각 이후에는 새 클립·새 장면도 시작하지 않는다
# 개발 기간 24시간 가동 (사용자 지정 2026-08-14: CPU 위주 서버라 GPU 는 풀로 쓴다).
# 운영 전환 시 DEV_247=0 으로 내리면 위 시간 정책이 다시 산다.
DEV_247=${DEV_247:-1}
hhmm() { echo $((10#$(date +%H%M))); }
# 주말(토·일)은 24시간 가동한다 — 금 20:00 부터 월 08:00(마무리 09:40)까지 연속.
# 평일 낮에만 서버를 다른 이용자에게 돌려준다. (사용자 지정, 2026-08-14)
weekend() { local d; d=$(date +%u); [ "$d" -ge 6 ]; }
start_ok() { [ "$DEV_247" = 1 ] && return 0; weekend && return 0; local t; t=$(hhmm); [ "$t" -ge 2000 ] || [ "$t" -lt "$START_BY" ]; }
grace_ok() { [ "$DEV_247" = 1 ] && return 0; weekend && return 0; local t; t=$(hhmm); [ "$t" -ge 2000 ] || [ "$t" -lt "$FINISH_BY" ]; }
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
NEG="text, letters, hangul, korean characters, handwriting, printed words, signboard, shop sign, poster, framed notice, product label, book spine with title, caption, subtitle, inscription, signature, watermark, rectangular box head, slab, eraser, photorealistic, photograph, 3d render, cgi, glossy, vibrant saturated colors, bright blue sky, modern clothing, anime, smooth digital art, blurry, deformed"
MOTION_NEG="static, still, motionless, frozen, jittery, flickering, warping, morphing, text, watermark, blurry, distorted, deformed"

produced=0; failed=0

# 08:00 정지 타이머는 SIGTERM 으로 끝낸다. 트랩이 없으면 마지막 요약 줄이
# 기록되지 않아 "몇 편 만들었나"가 남지 않는다(실측: 첫날 요약 누락).
finish() {
  local left; left=$(grep -cvE '^[[:space:]]*(#|$)' "$Q")
  say "=== 끝($1) · 완성 ${produced}편 · 실패 ${failed}건 · 큐 잔여 ${left} ==="
  printf '%s\t%s\tproduced=%s\tfailed=%s\tqueue=%s\n' \
    "$(date +%F)" "$1" "$produced" "$failed" "$left" >> "$LOGDIR/summary.tsv"
}
# 정지 신호를 받으면 자식(gen_keyframe/gen_i2v)까지 함께 내린다.
# 부모만 죽이면 자식이 flock 을 물고 남아 다음 기동이 "이미 실행 중"으로 죽는다(실측).
cleanup() { pkill -P $$ 2>/dev/null; finish "$1"; }
trap 'cleanup 정지신호; exit 0' TERM INT

say "=== 야간 배치 v2 시작 (큐 $(grep -cvE '^[[:space:]]*(#|$)' "$Q") 건) ==="

while grace_ok; do
  disk_ok || break
  svc_ok  || { say "서비스 이상 — 60초 후 재확인"; sleep 60; continue; }

  line=$(grep -vE '^[[:space:]]*(#|$)' "$Q" | head -1) || true
  [ -z "${line:-}" ] && { say "큐 비어 있음 — 종료"; break; }

  work=$(echo "$line" | cut -f1)
  facts=$(echo "$line" | cut -f2)
  ending=$(echo "$line" | cut -f3)
  style=$(echo "$line" | cut -f4); [ -z "$style" ] && style="$STYLE_DEFAULT"
  tone=$(echo "$line" | cut -f5); [ -z "$tone" ] && tone="담담"
  NAR="output/$work/narration_night.json"
  TRE="output/$work/treatment.json"
  # 대본이 있으면 이미 착수한 작품이다 — 시각과 무관하게 마무리한다.
  if [ ! -s "$NAR" ] && ! start_ok; then
    say "08:00 이후 — 새 작품($work)은 시작하지 않는다. 오늘 밤 이어감"
    break
  fi
  say "▶ $work (톤 $tone)"

  mkdir -p "output/$work" "output/${work}_kf" "output/${work}_i2v"
  ok=1

  # ── ①-0 트리트먼트 (이야기 줄기) ──
  # 이 단계가 없으면 여덟 문장이 서로 무관한 파편이 된다(실측: 방·거리·옥상이 따로 놀았다).
  if [ ! -s "$TRE" ] && [ -f "$facts" ]; then
    venv/bin/python scripts/treatment.py --title "$work" --facts "$facts" \
      --out "$TRE" >>"$LOG" 2>&1 && say "  ①-0 이야기 줄기 준비됨" \
      || say "  ①-0 트리트먼트 실패 — 줄기 없이 진행"
  fi
  TRE_ARG=""; [ -s "$TRE" ] && TRE_ARG="--treatment $TRE"

  # ── ① 대본 ──
  if [ -s "$NAR" ] && python3 -c "import json,sys; sys.exit(0 if json.load(open('$NAR'))['sentences'] else 1)" 2>/dev/null; then
    say "  ① 대본 있음 — 건너뜀"
  elif [ ! -f "$facts" ]; then
    say "  ① 사실파일 없음($facts) — 영구 실패"; ok=0
  else
    venv/bin/python scripts/write_script.py --title "$work" --facts "$facts" \
      --scenes 8 --minlen 27 --maxlen 38 --tone "$tone" --emphasis $TRE_ARG \
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
  # 장면 묘사에 넘길 작품 세계 한 줄 (사실파일 본문 앞부분)
  ctx=$(python3 -c "
import re,sys
t=open('$facts',encoding='utf-8').read()
body=[l for l in t.splitlines() if l and not l.startswith('[')]
print(re.sub(r'\s+',' ',' '.join(body))[:200])")

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
    grace_ok || break
    ls output/${work}_kf/night_s${i}_*.png >/dev/null 2>&1 && continue
    # 그림 프롬프트는 **영어로만** 만든다. 한글을 넣으면 Qwen-Image 가 그 글자를
    # 그림 안에 써 넣는다(실측: 화면 상단에 뭉개진 한글 자막).
    desc=$(venv/bin/python scripts/scene_prompt.py --narration "$NAR" --index "$i" \
             --context "$ctx" $TRE_ARG 2>>"$LOG")
    venv/bin/python scripts/gen_keyframe.py --seed $((200+i)) \
      --prefix "${work}_kf/night_s${i}" --prompt "${style}${desc}" --negative "$NEG" >>"$LOG" 2>&1 \
      || say "  ③ s${i} 키프레임 실패"
  done
  kf=$(ls output/${work}_kf/night_s*.png 2>/dev/null | wc -l)
  [ "$kf" -eq "$N" ] || { say "  ③ 키프레임 $kf/$N — 큐 유지(다음 밤 이어감)"; continue; }
  say "  ③ 키프레임 $N장"

  # ── ④ 크롭 → I2V ──
  for i in $(seq 1 "$N"); do
    grace_ok || break
    [ -s "output/${work}_i2v/night_s${i}_00001_.mp4" ] && continue
    src=$(ls output/${work}_kf/night_s${i}_*.png 2>/dev/null | head -1)
    [ -z "$src" ] && continue
    # 크롭은 scripts/crop_keyframe.py 가 한다 — 여백을 재서 자막을 잘라낸다.
    venv/bin/python scripts/crop_keyframe.py --src "$src" \
      --dst "ComfyUI/input/night_${work}_${i}.png" >>"$LOG" 2>&1
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "output/tts/${work}_night_s${i}.wav")
    # 감속 1.5배 상한을 지키는 최소 프레임 수를 4n+1 로 **올림**한다.
    # 내림하면 프레임이 모자라 감속이 1.5배를 살짝 넘는다(실측 1.52~1.54).
    fr=$(python3 -c "
import math
d=$d; f=max(81, math.ceil(d*24/1.5))
f = f + (4 - (f-1) % 4) % 4
# 121프레임에서 첫 프레임 번짐 실측 — 117(4n+1)로 상한. 최장 문장은 감속이
# 1.5를 살짝 넘을 수 있으나 번짐보다 낫다.
print(min(f, 117))")
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
    # ⑦ 보기 좋은 카테고리 발행 — /data/bard/video/<고전|현대>/<제목>/ (하드링크)
    venv/bin/python scripts/publish_final.py --work "$work" >>"$LOG" 2>&1 \
      && say "  ⑦ 발행 → /data/bard/video" || say "  ⑦ 발행 실패(수동 확인)"
  else
    say "  ⑤ 조립 검증 실패 — 큐 유지"
  fi
  rm -rf "$ASM"
done

finish 정상종료
