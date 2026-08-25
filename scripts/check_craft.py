"""손으로 쓴 원고가 작법 규칙을 지키는지 본다.

내가 docs/PROMPTCRAFT.md 에 적어 놓고도 스스로 어긴 것들이라 검사로 바꾼다:
부정어 'no fire' 가 다락방에 불을 피웠고, 팔레트의 'giant gourds' 가 반전을
첫 컷에 노출했고, 훅이 전제를 말해 여덟 컷이 한 칸씩 밀렸다.
"""
import json, pathlib, re

NEG = re.compile(r'\b(no|without|not|never)\b', re.I)
# 팔레트·화풍에 와서는 안 되는 사물(빛·색이 아닌 것)
THING = re.compile(r'\b(hut|huts|hall|halls|sail|sails|gourd|gourds|swallow|swallows|'
                   r'ship|ships|tree|trees|house|houses|room|rooms|velvet|canvas)\b', re.I)

# 한 장면에서만 나는 불. 팔레트에 적으면 여덟 컷 모두로 옮겨붙는다
# (실측: 'firelight amber' 가 소년이 매달린 야자수를 태웠다).
# 등불·촛불 같은 시대 조명은 어느 컷에나 있어도 되므로 제외한다.
EPISODIC = re.compile(r'\b(firelight|bonfire|campfire|torchlight|torch|fire)\b', re.I)

def _words(s): return set(re.findall(r"[가-힣]{2,}", s))
def _stem(w): return re.sub(r"(이|가|은|는|을|를|의|에|도|만|와|과|로|에서|으로|에게|까지|부터)$", "", w)
def _keys(s): return {_stem(w) for w in _words(s)} | _words(s)

def check(work: str) -> list:
    d = pathlib.Path("works/handwritten")/work
    bad = []
    T = json.loads((d/"treatment.json").read_text(encoding="utf-8"))
    # 'bone white sail' · 'crimson velvet' 처럼 색 이름 안에 든 명사는 사물이 아니라
    # 색조다(실측: 모비딕·오페라의 유령이 이렇게 잘못 걸렸다). 앞에 색말이 붙으면 넘긴다.
    COLOUR = (r'(?:deep|pale|bone|cold|warm|dark|light|dusty|bright|muted|'
              r'white|black|grey|gray|gold|gilt|crimson|indigo|amber|ochre|'
              r'green|blue|red|brown|cream|silver)\s+')
    for m in THING.finditer(T.get("palette", "")):
        before = T["palette"][:m.start()]
        if not re.search(COLOUR + r'$', before, re.I):
            bad.append(f"팔레트에 사물: {m.group()}")
    # 단어만 보면 안 된다 — 중세 파리의 횃불은 그 시대의 기본 조명이라 어느 컷에나
    # 있어도 된다. 그 불이 실제로 몇 박자에 나오는지 세어, 두 컷 이하일 때만 잡는다.
    m = EPISODIC.search(T.get("palette", ""))
    if m:
        word = m.group().lower().replace("light", "")
        seen = sum(1 for b in (T.get("beats") or [])
                   if word in (b.get("visual", "") + b.get("motion", "")).lower())
        if seen <= 2:
            bad.append(f"팔레트에 일회성 불: {m.group()} ({seen}컷에만 등장)")
    for k, v in (T.get("personas") or {}).items():
        if NEG.search(v.get("desc", "")):
            bad.append(f"{k} 묘사에 부정어")
    n = d/"narration_night.json"
    if n.exists():
        N = json.loads(n.read_text(encoding="utf-8"))["sentences"]
        B = T.get("beats") or []
        if len(N) >= 8 and len(B) >= 8:
            drift = sum(1 for i in range(1, 7)
                        if len(_keys(N[i]) & _keys(B[i-1]["beat"]))
                         > len(_keys(N[i]) & _keys(B[i]["beat"])))
            if drift >= 3:
                bad.append(f"낭독이 박자보다 한 칸 밀림 ({drift}/6)")
    return bad

def check_all():
    out = {}
    for d in sorted(pathlib.Path("works/handwritten").iterdir()):
        if not (d/"treatment.json").exists(): continue
        b = check(d.name)
        if b: out[d.name] = b
    return out

if __name__ == "__main__":
    r = check_all()
    print(f"위반 {len(r)}편")
    for w, b in r.items(): print(f"  {w}: {', '.join(b)}")
