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
# 색·밝기·질감을 가리키는 말. 뒤쪽 박자에 나와도 그릴 사물이 아니다.
COLOUR = set("""
deep pale bone cold warm dark light dusty bright muted soft flat thin high low
white black grey gray gold gilt crimson indigo amber ochre green blue red brown
cream silver teal purple yellow orange pink violet scarlet olive rust sepia
hazy stark dim faint rich clear sharp heavy contrast shadow shadows shade tone
tones glow linework wash washes texture textures saturated overcast
""".split())

# 카메라가 볼 수 없는 사람의 상태. 모델은 이것을 그릴 수 있는 물건으로 바꾼다
# (실측: blind 라고 적었더니 눈에 검은 안대와 흰 천을 둘렀다). 보이는 것으로 적는다.
STATE = re.compile(r'\b(blind|deaf|mute|dumb|drunken|insane|grieving|'
                   r'lonely|anxious|frightened)\b', re.I)

# 관계를 말하는 표현. 모델은 '누구와 같다'를 실행할 수 없어 그냥 딴 사람을 그린다
# (실측: 거지 아이를 'with the same face' 로 적었더니 머리색부터 갈렸다).
# 닮게 하려면 두 배역에 같은 이목구비를 각각 적는다.
RELATIVE = re.compile(r'\b(same (?:face|hair|features)|identical|like the (?:other|first)|'
                      r'as (?:him|her|above))\b', re.I)

# 한 번에 끝나는 동작. 클립은 5~7초인데 모델은 지시한 동작을 대개 첫 1~2초에
# 해 버린다. 그런데 낭독은 그 말을 문장 중반에 한다 — 그림이 먼저, 말이 나중이
# 되어 어긋난다(실측: 잭과 콩나무에서 황금알이 구른 뒤에 그 문장이 나왔다).
# 지속되는 동작으로 적으면 어느 시점에 들어도 맞는다.
#   the egg rolls off and drops   →   the egg teeters at the edge, tipping
ONESHOT = re.compile(r'\b(drops?|slams?|strikes?|shuts?|lands?|bursts?|snaps?|'
                     r'topples?|scatters?|falls?|breaks?|catches?)\b', re.I)

EPISODIC = re.compile(r'\b(firelight|bonfire|campfire|torchlight|torch|fire)\b', re.I)

def _words(s): return set(re.findall(r"[가-힣]{2,}", s))
def _stem(w): return re.sub(r"(이|가|은|는|을|를|의|에|도|만|와|과|로|에서|으로|에게|까지|부터)$", "", w)
def _keys(s): return {_stem(w) for w in _words(s)} | _words(s)

def check(work: str) -> list:
    d = pathlib.Path("works/handwritten")/work
    bad = []
    T = json.loads((d/"treatment.json").read_text(encoding="utf-8"))
    beats = T.get("beats") or []

    # 팔레트는 여덟 컷 **전부**에 붙는다. 그러니 뒤쪽 박자에서야 나와야 할 것을
    # 여기 적으면 반전이 첫 컷부터 노출된다 — 흥부전의 박(6~8번)이 첫 컷 지붕에
    # 매달렸고, 심청전의 연꽃(7번)이 첫 컷에 피었다. 둘 다 색 이름에 숨어 있었다
    # ('lotus pink'). 그래서 낱말 목록이 아니라 **어느 박자에 나오는가**로 잡는다.
    #
    # 박자에 한 번도 안 나오는 낱말은 그릴 사물이 아니라 색·질감이므로 넘어간다
    # (hanji, bleached, storm grey…). 이 구분이 목록을 관리하는 것보다 정확했다.
    reveal = " ".join((b.get("visual", "") + " " + b.get("motion", ""))
                      for b in beats[5:]).lower()
    early = " ".join((b.get("visual", "") + " " + b.get("motion", ""))
                     for b in beats[:5]).lower()
    for w in re.findall(r"[a-z]{4,}", T.get("palette", "").lower()):
        stem = w.rstrip("s")
        if stem in COLOUR:
            continue          # 색말은 뒤쪽 박자에 나와도 사물이 아니다
        if stem in reveal and stem not in early:
            bad.append(f"팔레트의 '{w}' 가 뒤쪽 박자에만 나온다 — 반전이면 첫 컷부터 새어 나간다")

    # 움직임은 하나만 적는다. 셋을 적으면 셋 다 움직여 화면이 산만해진다
    # (실측: "구르고, 부딪히고, 튕겨 나간다"를 적었더니 전부 일어났다).
    for b in beats:
        mot = b.get("motion", "")
        if mot.count(",") >= 2:
            bad.append(f"S{b['n']} 움직임이 {mot.count(',')+1}가지 — 하나만 적는다")
        m = ONESHOT.search(mot)
        if m:
            bad.append(f"S{b['n']} 움직임이 한 번에 끝난다: {m.group()} — 지속형으로")

    # 한 장면에서만 나는 불도 같은 이유로 옮겨붙는다(십오 소년의 야자수가 탔다).
    m = EPISODIC.search(T.get("palette", ""))
    if m:
        word = m.group().lower().replace("light", "")
        seen = sum(1 for b in beats if word in (b.get("visual", "") + b.get("motion", "")).lower())
        if 1 <= seen <= 2:
            bad.append(f"팔레트에 일회성 불: {m.group()} ({seen}컷에만 등장)")

    for k, v in (T.get("personas") or {}).items():
        if NEG.search(v.get("desc", "")):
            bad.append(f"{k} 묘사에 부정어")
        if STATE.search(v.get("desc", "")):
            bad.append(f"{k} 묘사에 개념어: {STATE.search(v['desc']).group()}")
        if RELATIVE.search(v.get("desc", "")):
            bad.append(f"{k} 묘사에 관계 표현: {RELATIVE.search(v['desc']).group()}")

    # 배역만 고치고 박자를 놓치면 소용이 없다 — 심봉사의 안대는 배역 묘사를 고친
    # 뒤에도 돌아왔다. visual 에 'a blind old man' 이 그대로 남아 있었기 때문이다.
    for b in beats:
        for key in ("visual", "motion"):
            m = STATE.search(b.get(key, ""))
            if m:
                bad.append(f"S{b['n']} {key} 에 개념어: {m.group()}")
            r = RELATIVE.search(b.get(key, ""))
            if r:
                bad.append(f"S{b['n']} {key} 에 관계 표현: {r.group()}")

    n = d/"narration_night.json"
    if n.exists():
        N = json.loads(n.read_text(encoding="utf-8"))["sentences"]
        if len(N) >= 8 and len(beats) >= 8:
            drift = sum(1 for i in range(1, 7)
                        if len(_keys(N[i]) & _keys(beats[i-1]["beat"]))
                         > len(_keys(N[i]) & _keys(beats[i]["beat"])))
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
