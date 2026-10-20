#!/usr/bin/env bash
# 옛 포맷 작품을 15컷 규격으로 다시 만들기 위해 새 원고를 검사하고 큐에 넣는다.
#   scripts/remake_queue.sh <work> "<화풍 문자열>" [톤]
# 검사: 비트 수 = 문장 수, author hand, cast 자산 존재, 관문(gate_script), check_craft 무결.
# 통과하면 treatment/narration 을 touch 해 배치가 옛 그림·클립을 버리고 새로 굽게 하고,
# works/queue.txt 에 한 줄 붙인다(타이머가 매시 :15 에 배치를 띄운다).
set -u
cd "$(dirname "$0")/.."
W=${1:?work}; STYLE=${2:?style}; TONE=${3:-담담}
D=works/handwritten/$W; TRE=$D/treatment.json; NAR=$D/narration_night.json
[ -s "$TRE" ] && [ -s "$NAR" ] || { echo "[$W] 원고 없음"; exit 2; }
FACTS=facts/auto_$W.txt; [ -s "$FACTS" ] || FACTS=facts/$W.txt
[ -s "$FACTS" ] || { echo "[$W] 사실파일 없음"; exit 2; }
END=$(python3 -c "import json;print(json.load(open('$TRE'))['destination'])")
python3 - "$TRE" "$NAR" <<'PY' || exit 3
import glob, json, os, sys
t = json.load(open(sys.argv[1])); n = json.load(open(sys.argv[2]))
b = t["beats"]; s = n["sentences"]; bad = []
if len(b) != len(s): bad.append(f"비트 {len(b)} ≠ 문장 {len(s)}")
if n.get("author") != "hand": bad.append('"author": "hand" 아님')
ad = t.get("assets_dir", ""); names = {os.path.basename(p)[:-3] for p in glob.glob(ad + "/*.md")}
if not names: bad.append(f"assets_dir 비었음: {ad}")
for i, x in enumerate(b, 1):
    if x.get("n") != i: bad.append(f"비트 n={x.get('n')} 가 {i}번째")
    for c in x.get("cast", []):
        if c not in names: bad.append(f"S{i} cast '{c}' 자산 없음")
    if len(x.get("visual", "")) < 200: bad.append(f"S{i} visual 너무 짧음({len(x.get('visual',''))}자)")
    if len(x.get("motion", "")) < 600: bad.append(f"S{i} motion 너무 짧음({len(x.get('motion',''))}자) — 09-10 A/B 뒤 800~1000자 규격")
if not t.get("withheld"): bad.append("withheld 없음")
# 대사(§13): 문장 끝 [역할·감정] "대사" 가 작품마다 1~3마디 있어야 한다(09-19 사용자 지적 — 45번부터 30편이 0이었다).
import re as _re3
_nd = sum(1 for x in s if _re3.search(r'\[[^\]\[]*\]\s*[“"「][^”"」]+[”"」]\s*$', x))
if _nd == 0: bad.append("대사가 없다 — 문장 끝에 [역할·감정] \"대사\" 를 1~3마디(지문 ≤26자·대사 ≤16자)")
# 분량이 예산 하한에 붙으면 영상이 짧아지고 그림 밀도가 떨어진다(사용자 지적 09-18:
# 낭독 451→397자로 흘러내리며 영상이 68→59초가 됐다). 관문은 395자만 넘으면 통과시키므로
# 여기서 **목표치**를 따로 막는다 — 낭독 440자 이상, 비주얼 평균 800자 이상, 동작은 컷마다 800자 이상.
nar_total = sum(len(x) for x in s)
if nar_total < 440: bad.append(f"낭독 {nar_total}자 — 440자 이상으로(예산 410~460, 하한에 붙으면 영상이 60초 밑으로 떨어진다)")
vis = [len(x.get("visual", "")) for x in b]
if vis and sum(vis)/len(vis) < 800: bad.append(f"비주얼 평균 {sum(vis)//len(vis)}자 — 800자 이상으로(그림 밀도)")
for x in b:
    if len(x.get("motion", "")) < 800: bad.append(f"S{x.get('n')} motion {len(x.get('motion',''))}자 — 800~1,000자 규격")
# 팔레트의 붉은색은 옷·벽·산울타리에 핏자국처럼 내려앉는다(정글북·로빈 후드·마지막 잎새·
# 올리버 트위스트에서 되풀이). 컷에서 정말 붉어야 하는 것은 visual 에 "dull red brick" 처럼
# 그 자리에만 적는다. 화풍 문자열(works/queue.txt)도 같은 팔레트를 쓰므로 여기서 한 번에 막는다.
import re as _re2
if _re2.search(r"\b(red|crimson|scarlet|maroon)\b", t.get("palette", ""), _re2.I):
    bad.append("팔레트에 붉은색 — 옷·벽·풀에 핏자국처럼 번진다(PROMPTCRAFT §7). 색이 필요한 곳은 컷의 visual 에만 적어라")
# 조립 예산: visual + cast 자산(kind 상한) + 팔레트 가 1900 을 넘으면 scene_prompt._fit 이
# 뒤쪽 자산·팔레트를 통째로 떨군다(09-12 실측: 추월색 S13 2298 — 칼·공원·팔레트 탈락).
import re as _re
CAP = {"인물": 340, "소품": 180, "장소": 250, "지면": 220, "물": 220, "배경": 160}
def _fit(parts, limit):
    out = ""
    for q in parts:
        q = (q or "").rstrip(".").strip()
        if not q: continue
        nxt = q if not out else f"{out}, {q}"
        if len(nxt) > limit: break
        out = nxt
    return out
A = {}
for f in glob.glob(ad + "/*.md"):
    m = _re.search(r"^---\n(.*?)\n---\n(.*)$", open(f, encoding="utf-8").read(), _re.S)
    if not m: continue
    h = dict(l.split(": ", 1) for l in m.group(1).splitlines() if ": " in l)
    A[h.get("name", "")] = (h.get("kind", ""), h.get("spec", ""), m.group(2).strip())
for x in b:
    who = []
    for c in x.get("cast", []):
        if c not in A: continue
        kind, spec, det = A[c]; cap = CAP.get(kind, 250); spec = spec.strip().rstrip(".")
        d = _fit(det.split(", "), max(cap - len(spec) - 2, 0)); who.append(f"{spec}, {d}" if d else spec)
    parts = [x.get("visual", ""), *who, t.get("palette", "")]
    total = sum(len(q.rstrip(".").strip()) for q in parts) + 2 * (len(parts) - 1)
    if total > 1850: bad.append(f"S{x.get('n')} 조립 {total}자 > 1850 — visual 을 줄이거나 cast 를 빼라(팔레트가 떨어진다)")
print("\n".join(bad)); sys.exit(1 if bad else 0)
PY
G=$(venv/bin/python scripts/gate_script.py --narration "$NAR" --ending "$END" --maxlen 36 2>&1 | tail -n 1)
echo "[$W] gate: $G"; echo "$G" | grep -q 통과 || exit 4
C=$(venv/bin/python scripts/check_craft.py 2>/dev/null | grep -E "^  $W:")
[ -z "$C" ] && echo "[$W] craft: 통과" || { echo "[$W] craft:$C" | sed 's/, /\n    /g'; exit 5; }
touch "$TRE" "$NAR"
if grep -qP "^$W\t" works/queue.txt 2>/dev/null; then echo "[$W] 이미 큐에 있음"; exit 0; fi
printf '%s\t%s\t%s\t%s\t%s\n' "$W" "$FACTS" "$END" "$STYLE" "$TONE" >> works/queue.txt
sed -i "s/^\($W\t[^\t]*\t[^\t]*\t\)[^\t]*$/\1큐/" works/remake_order.txt 2>/dev/null
echo "[$W] 큐 추가 ($TONE) — 큐 $(wc -l < works/queue.txt)편"
