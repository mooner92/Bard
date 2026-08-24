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

# 큐에서 한 줄을 지운다.
#
# 예전 코드는 grep -vxF ... && mv 였는데, 큐에 지울 그 한 줄만 남으면 grep 이
# 아무것도 못 골라 종료코드 1 을 낸다. 그러면 && 뒤의 mv 가 건너뛰어지고 큐가
# 그대로 남는다 — 마지막 작품이 완성·발행을 끝없이 되풀이한다(실측: 삼총사가
# 2분마다 같은 영상을 여덟 번 재발행했고, "5회 연속 진척 없음" 안전장치마저
# 같은 코드라 함께 무력화됐다). 큐가 비는 것은 정상이므로 실패로 보지 않는다.
dequeue() {
  grep -vxF "$1" "$Q" >"$Q.t" || true
  mv "$Q.t" "$Q"
}
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
  # 같은 작품이 진척 없이 반복되면 큐에서 내린다. 무한 재시도로 밤을 통째로
  # 날린 사고가 있었다(실측: 클립 9/8 불일치로 초당 수십 회 재시도).
  if [ "$work" = "${last_work:-}" ]; then
    stuck=$((${stuck:-0} + 1))
  else
    stuck=0
  fi
  last_work="$work"
  if [ "$stuck" -ge 5 ]; then
    say "  !! $work 이 5회 연속 진척 없음 — 큐에서 내리고 다음 작품으로"
    printf '%s\t%s\tstuck\n' "$(date +%FT%T)" "$line" >>"$FAIL"
    dequeue "$line"
    failed=$((failed+1)); stuck=0; continue
  fi
  facts=$(echo "$line" | cut -f2)
  ending=$(echo "$line" | cut -f3)
  style=$(echo "$line" | cut -f4); [ -z "$style" ] && style="$STYLE_DEFAULT"
  tone=$(echo "$line" | cut -f5); [ -z "$tone" ] && tone="담담"
  NAR="output/$work/narration_night.json"
  RATE_DELTA=0                      # 사람이 쓴 대본은 이 값으로 길이를 맞춘다
  TRE="output/$work/treatment.json"
  # 대본이 있으면 이미 착수한 작품이다 — 시각과 무관하게 마무리한다.
  if [ ! -s "$NAR" ] && ! start_ok; then
    say "08:00 이후 — 새 작품($work)은 시작하지 않는다. 오늘 밤 이어감"
    break
  fi
  say "▶ $work (톤 $tone)"

  mkdir -p "output/$work" "output/${work}_kf" "output/${work}_i2v"
  # 사람이 쓴 원고는 works/handwritten 이 원본이다(output 은 git 이 무시한다).
  # 작업 디렉터리에 없을 때만 채워 넣는다 — 진행 중인 산출물을 덮어쓰지 않는다.
  for f in treatment.json narration_night.json; do
    [ -s "works/handwritten/$work/$f" ] && [ ! -s "output/$work/$f" ] \
      && cp "works/handwritten/$work/$f" "output/$work/$f"
  done
  # 원고를 다시 쓴 작품은 옛 그림이 남아 있으면 그걸 그대로 재사용해 버린다
  # (실측: 상록수가 새 낭독 + 8월 20일 폐기본 그림으로 2분 만에 "완성"됐다).
  # 낭독이 키프레임보다 새것이면 옛 산출물을 지우고 처음부터 만든다.
  newest_kf=$(ls -t "output/${work}_kf"/night_s*.png 2>/dev/null | head -1)
  if [ -n "$newest_kf" ] && [ "output/$work/narration_night.json" -nt "$newest_kf" ]; then
    say "  원고가 그림보다 새것 — 옛 산출물을 버리고 다시 만든다"
    rm -f "output/${work}_kf"/*.png "output/${work}_i2v"/*.mp4 \
          output/tts/"${work}"_night_s*.wav "output/$work/final_night.mp4"
  fi
  ok=1

  # ── ①-0 트리트먼트 (이야기 줄기) ──
  # 이 단계가 없으면 여덟 문장이 서로 무관한 파편이 된다(실측: 방·거리·옥상이 따로 놀았다).
  if [ ! -s "$TRE" ] && [ -f "$facts" ]; then
    venv/bin/python scripts/treatment.py --title "$work" --facts "$facts" \
      --out "$TRE" >>"$LOG" 2>&1
    # 3 = 소개형(저작권 보호작). 고장이 아니라 설계다 — 줄거리를 지어내지 않는다.
    case $? in
      0) say "  ①-0 이야기 줄기 준비됨" ;;
      3) say "  ①-0 소개형 — 줄거리 없이 작품의 세계로 쓴다" ;;
      *) say "  ①-0 트리트먼트 실패 — 큐 유지, 30초 후 재시도"
         # 각색형에서 줄기 없이 만든 대본은 매번 품질 미달이었다(실측: 상록수 —
         # 한자 혼입·결말 노출). 진행하지 말고 재시도한다. 반복되면 위의
         # stuck 한도(5회)가 큐에서 내린다 — 죄와 벌이 그 경로로 내려갔다.
         sleep 30; continue ;;
    esac
  fi
  TRE_ARG=""; [ -s "$TRE" ] && TRE_ARG="--treatment $TRE"
  # 문장 길이 목표. 되먹임 루프가 바꾸면 관문도 같은 값을 봐야 한다 — 값이 갈리면
  # 생성과 검증이 서로 싸운다(실측: 46자로 쓰라 해놓고 38자 기준으로 반려).
  LENF="output/$work/.lenmax"
  cur_max=$( [ -s "$LENF" ] && cat "$LENF" || echo 38 )
  cur_min=$(( cur_max - 11 )); [ "$cur_min" -lt 20 ] && cur_min=20
  # 38자 상한은 0.206초/자(쉼표 잦은 모델 문장) 기준이다. 사람이 쓴 문장은
  # 0.156초/자로 읽혀 44자라도 6.8초 — 117프레임 안에 들어온다. 상한이 문체와
  # 어긋나면 멀쩡한 대본이 반려된다. 실제 제약(오디오 7.3초)에 맞춰 올린다.
  if grep -q '"author": "hand"' "$NAR" 2>/dev/null; then cur_max=41; cur_min=30; fi

  # ── ① 대본 (관문 통과할 때까지 다시 쓴다) ──
  # 하네스가 문제를 찾아도 수리에 실패하면 대본을 그대로 남긴다. 그 대본으로 그림을
  # 그리면 두 시간이 버려지므로(실측: 규칙 코드가 1번 문장에 박힌 채 진행될 뻔했다)
  # 여기서 막고 다시 쓴다.
  if [ ! -f "$facts" ]; then
    say "  ① 사실파일 없음($facts) — 영구 실패"; ok=0
  else
    # 모델 초안이 새 구조(질문 위치)를 시도당 절반쯤 놓친다. 3회면 작품이 통째로
    # 내려간다(실측: 인간 문제·혈의 누가 10분 간격으로 탈락). 6회면 대부분 통과한다.
    for try in 1 2 3 4 5 6; do
      if [ -s "$NAR" ]; then
        gate=$(venv/bin/python scripts/gate_script.py --narration "$NAR" \
                 --ending "$ending" --maxlen "$cur_max" 2>&1)
        if [ $? -eq 0 ]; then
          say "  ① 대본 $( [ "$try" = 1 ] && echo 준비됨 || echo "재작성 $((try-1))회 후 통과" )"
          break
        fi
        say "  ① $gate"
        mv "$NAR" "${NAR%.json}.rej${try}.json" 2>/dev/null
      fi
      [ "$try" = 6 ] && { say "  ① 관문 6회 불합격 — 큐에서 내림"; ok=0; break; }
      venv/bin/python scripts/write_script.py --title "$work" --facts "$facts" \
        --scenes 8 --minlen "$cur_min" --maxlen "$cur_max" --tone "$tone" --emphasis $TRE_ARG \
        --ending "$ending" --out "$NAR" >>"$LOG" 2>&1
      [ -s "$NAR" ] || { say "  ① 대본 생성 실패"; ok=0; break; }
    done
  fi
  if [ "$ok" != 1 ]; then
    printf '%s\t%s\tscript-gate\n' "$(date +%FT%T)" "$line" >>"$FAIL"
    dequeue "$line"
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
  # 길이는 글자 수로 예측할 수 없다. 쉼표마다 호흡이 붙어 같은 글자 수라도 크게 달라진다
  # (실측 0.168~0.219초/자). 그래서 **합성해서 재고**, 벗어나면 목표를 고쳐 다시 쓴다.
  for tts_try in 1 2 3; do
    if [ "$(ls output/tts/${work}_night_s*.wav 2>/dev/null | wc -l)" -ne "$N" ]; then
      # 한국어 음성은 감정 스타일을 하나도 지원하지 않는다(실측: 10개 전부 StyleList 비어
      # 있다). 그래서 다양성은 prosody 가 아니라 **목소리 선택**에서 나온다. 작품이
      # 트리트먼트에 voice 를 들고 있으면 그걸 쓰고, 없으면 tts_render 기본값으로 간다.
      vc=$(venv/bin/python -c "
import json
try: print(json.load(open('$TRE')).get('voice','') or '')
except Exception: print('')" 2>/dev/null)
      VOICE_ARG=""; [ -n "$vc" ] && VOICE_ARG="--voice $vc"
      venv/bin/python scripts/tts_render.py --narration "$NAR" --tone "$tone" --arc 산형 \
        --rate-delta "$RATE_DELTA" $VOICE_ARG \
        --prefix "output/tts/${work}_night_s" >>"$LOG" 2>&1
    fi
    got=$(ls output/tts/${work}_night_s*.wav 2>/dev/null | wc -l)
    [ "$got" -eq "$N" ] || { say "  ② TTS $got/$N — 일시 실패, 큐 유지"; break; }

    read -r total newmin newmax <<<"$(python3 -c "
import glob, json, subprocess
fs = sorted(glob.glob('output/tts/${work}_night_s*.wav'),
            key=lambda p: int(p.rsplit('_s',1)[1].split('.')[0]))
d = sum(float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
        '-of','csv=p=0',f], capture_output=True, text=True).stdout or 0) for f in fs)
ch = sum(len(x) for x in json.load(open('$NAR'))['sentences'])
rate = d/ch if ch else 0.2
t = int(55/rate/8)                      # 55초를 8문장으로 나눈 목표 글자 수
# 문장 상한은 38자에 묶는다. 그 이상이면 음성이 7.3초를 넘어 클립 프레임 상한(117)
# 안에서 감속 1.5배를 지킬 수 없다(실측: 48자 문장에서 1.53배). 하한만 올려 총 길이를 맞춘다.
print(f'{d:.1f} {max(20,min(t-1,36))} 38')   # 모델이 범위 아래쪽으로 쓴다 — 하한을 바짝 올린다")"
    say "  ② TTS $N개 · 낭독 ${total}초"
    ok_len=$(python3 -c "print(1 if 50 <= $total <= 59 else 0)")
    [ "$ok_len" = 1 ] && break
    [ "$tts_try" = 3 ] && { say "  ② 길이 ${total}초 — 3회 조정 실패, 그대로 진행"; break; }
    # 사람이 쓴 대본은 덮어쓰지 않는다. 길이 몇 초를 맞추자고 모델에게 다시 시키면
    # 문장이 무너진다(실측: "돼지들의 통 이동이 우유를 구해" 같은 문장이 관문을 통과했다).
    # 길이는 **모든 대본**을 속도로 맞춘다. 모델 대본만 옛 경로(문장을 다시 쓰며 상한을
    # 45자까지 올림)를 타게 두었더니 48자 문장이 나와 감속이 1.83배까지 갔다(실측:
    # 타임머신). 글자를 건드리는 순간 프레임 상한과 싸우게 된다.
    if true; then
      # 산문은 고치지 않고 **발화 속도**로 맞춘다. 낭독 시간은 글자 수에 비례하지 않는다 —
      # 문장마다 도입 호흡·끝 여운이 고정으로 붙어 시간 = 고정분 + 글자수x기울기 이고,
      # 기울기도 톤마다 다르다(실측: 담담 0.14, 생동 0.103초/자. 같은 320자가 50.6초와
      # 46.8초로 갈렸다). 속도는 1%p 당 약 1.07% 늘어난다(실측).
      # 겨냥은 55 가 아니라 52초다. 55 로 늘리면 문장이 7.3초를 넘어 117프레임 안에서
      # 감속 1.5배를 못 지킨다(실측: 54.6초로 맞췄더니 S8 이 7.74초, 감속 1.59배).
      # 하한이 -15 면 빠른 톤에서 모자란다(실측: 긴장 톤 벙어리 삼룡이가 42.7초에서
      # 49.5초까지만 늘어나 멈췄다). 톤 자체가 +8% 를 갖고 있어 -15 를 더해도 순 -7%
      # 뿐이다. -24 까지 열어 둔다 — 순 속도로는 -16% 라 낭독이 무너지지 않는다.
      # SSML 의 rate 는 **양수가 빠름**이다. 낭독을 늘리려면 음수를 줘야 한다
      # (실측: 부호를 반대로 줬다가 46.8초짜리가 42.7초로 더 짧아졌다).
      rd=$(python3 -c "print(max(-24, min(10, $RATE_DELTA - round((52/$total - 1)/0.0107))))")
      if [ "$tts_try" = 3 ] || [ "$rd" = "$RATE_DELTA" ]; then
        say "  ② 길이 ${total}초 — 속도 조정 한계(${RATE_DELTA}%p), 그대로 진행"; break
      fi
      say "  ② 길이 ${total}초 — 발화 속도 ${rd}%p 로 다시 합성"
      RATE_DELTA=$rd
      rm -f output/tts/${work}_night_s*.wav
      continue
    fi
    say "  ② 길이 ${total}초 — 목표 밖. 문장 ${newmin}~${newmax}자로 대본 다시 씀"
    echo "$newmax" > "$LENF"; cur_max=$newmax; cur_min=$newmin
    mv "$NAR" "${NAR%.json}.len${tts_try}.json" 2>/dev/null
    rm -f output/tts/${work}_night_s*.wav
    venv/bin/python scripts/write_script.py --title "$work" --facts "$facts" \
      --scenes 8 --minlen "$newmin" --maxlen "$newmax" --tone "$tone" --emphasis $TRE_ARG \
      --ending "$ending" --out "$NAR" >>"$LOG" 2>&1
    [ -s "$NAR" ] || { say "  ② 대본 재작성 실패"; break; }
  done
  [ "$(ls output/tts/${work}_night_s*.wav 2>/dev/null | wc -l)" -eq "$N" ] || { sleep 30; continue; }

  # ── ③ 키프레임 ──
  for i in $(seq 1 "$N"); do
    grace_ok || break
    ls output/${work}_kf/night_s${i}_*.png >/dev/null 2>&1 && continue
    # 그림 프롬프트는 **영어로만** 만든다. 한글을 넣으면 Qwen-Image 가 그 글자를
    # 그림 안에 써 넣는다(실측: 화면 상단에 뭉개진 한글 자막).
    desc=$(venv/bin/python scripts/scene_prompt.py --narration "$NAR" --index "$i" \
             --context "$ctx" $TRE_ARG 2>>"$LOG")
    # 무엇이 들어갔는지 남긴다. 남기지 않으면 이상한 그림이 나와도 원인을 재구성해야
    # 한다(실측: 모비딕에서 앵커가 모든 장면에 갑판을 밀어 넣은 것을 뒤늦게 찾았다).
    venv/bin/python -c "
import json, pathlib, sys
f = pathlib.Path('output/${work}_kf/prompts.json')
d = json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}
d[sys.argv[1]] = {'image': sys.argv[2], 'motion': ''}
f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
" "$i" "${style}${desc}" 2>/dev/null
    venv/bin/python scripts/gen_keyframe.py --seed $((200+i)) \
      --prefix "${work}_kf/night_s${i}" --prompt "${style}${desc}" --negative "$NEG" >>"$LOG" 2>&1 \
      || say "  ③ s${i} 키프레임 실패"
  done
  kf=$(ls output/${work}_kf/night_s*.png 2>/dev/null | sed -E 's/.*night_s([0-9]+)_.*/\1/' | sort -u | wc -l)
  [ "$kf" -eq "$N" ] || { say "  ③ 키프레임 $kf/$N — 큐 유지(다음 밤 이어감)"; sleep 30; continue; }
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
    # 여덟 컷이 같은 문장으로 움직이면 전부 똑같이 흔들린다. 트리트먼트가 박자마다
    # 무엇이 움직이는지 들고 있으면 그걸 쓴다 (없으면 같은 기본값으로 돌아간다).
    mot=$(venv/bin/python scripts/scene_prompt.py --motion --index "$i" $TRE_ARG 2>>"$LOG")
    [ -z "$mot" ] && mot="gentle continuous motion in the scene, slow camera drift"
    venv/bin/python -c "
import json, pathlib, sys
f = pathlib.Path('output/${work}_kf/prompts.json')
d = json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}
d.setdefault(sys.argv[1], {})['motion'] = sys.argv[2]
f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
" "$i" "$mot" 2>/dev/null
    venv/bin/python scripts/gen_i2v.py --image "night_${work}_${i}.png" \
      --prefix "${work}_i2v/night_s${i}" --length "$fr" --seed 42 \
      --prompt "$mot" \
      --negative "$MOTION_NEG" >>"$LOG" 2>&1 || say "  ④ s${i} I2V 실패"
  done
  cl=$(ls output/${work}_i2v/night_s*.mp4 2>/dev/null | sed -E 's/.*night_s([0-9]+)_.*/\1/' | sort -u | wc -l)
  [ "$cl" -eq "$N" ] || { say "  ④ 클립 $cl/$N — 큐 유지(다음 밤 이어감)"; sleep 30; continue; }
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
    dequeue "$line"
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
