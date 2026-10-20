"""손으로 쓴 원고가 작법 규칙을 지키는지 본다.

내가 docs/PROMPTCRAFT.md 에 적어 놓고도 스스로 어긴 것들이라 검사로 바꾼다:
부정어 'no fire' 가 다락방에 불을 피웠고, 팔레트의 'giant gourds' 가 반전을
첫 컷에 노출했고, 훅이 전제를 말해 여덟 컷이 한 칸씩 밀렸다.
"""
import json, pathlib, re, sys

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

# 직유는 그려진다 — like a minister 가 관리를 세웠고 calligrapher's brush 가
# 인두를 붓으로 바꿨다(실측: 규중칠우 여섯 컷). 물리 묘사만 허용한다.
SIMILE = re.compile(r"\blike (?:a|an|the)\b|\bas if\b|\bas (?:one|a) (?:solid |single )?(?:wall|mass|block|sheet|curtain|carpet|blanket|tower|cliff)\b|\bstands? as a\b", re.I)   # 'as one solid wall' 이 돌담을 세웠다(80일간 S5)

EPISODIC = re.compile(r'\b(firelight|bonfire|campfire|torchlight|torch|fire)\b', re.I)

# 구조·지형 비유도 그려진다 — 'bedding tower' 가 창밖에 돌 망루를 세웠고
# 'striped cliff' 가 침실 안에 절벽을 들였고 'cloud upon cloud' 가 요 아래
# 구름을 깔았다(실측: 공주와 완두콩 6·7·8). 그 낱말이 자산 파일에 실물로
# 적혀 있을 때만(라푼젤의 탑) 통과시킨다.
METAPHOR = re.compile(r'\b(tower|towers|cliff|cliffs|mountain|mountains|cloud|clouds|'
                      r'sea|ocean|river|forest|waterfall|island|cave)\b', re.I)

# 맨살에 붙인 색은 옷이 된다 — 'bare feet red with cold' 가 빨간 양말을, 'reddened
# fingers' 가 빨간 장갑을 신기고 끼웠다(실측: 성냥팔이 소녀 2·3·4·5). 추위는
# pale·cold·stiff 로 적는다.
BODY_COLOUR = re.compile(r'\b(red|reddened|blue|purple|pink)\s+'
                         r'(feet|foot|toes|fingers|hands?|legs?|arms?)\b', re.I)

LIGHT_THING = re.compile(r'\b(candle|candles|flame|flames|fire|lamp|lamps|lantern|'
                         r'torch|sun|moon|stars?)\b', re.I)

# 팔레트의 색 이름이 사물이면 그 사물이 온다 — 'rose pink' 가 여섯 컷 구석마다
# 장미 덤불을 심었다(실측: 공주와 완두콩). 색은 색 이름으로만 적는다.
COLOUR_THING = re.compile(r'\b(rose|roses|cherry|peach|lemon|lime|olive|'
                          r'apricot|lavender|coral|salmon|chestnut|honey|'
                          r'snow|ice|frost)\b', re.I)   # 'snow white' 가 응접실 카펫에 눈을 깔았다(전나무 S8)

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
    k = max(4, round(len(beats) * 5 / 14))   # 컷 수가 늘면 경계도 비례
    reveal = " ".join((b.get("visual", "") + " " + b.get("motion", ""))
                      for b in beats[k:]).lower()
    early = " ".join((b.get("visual", "") + " " + b.get("motion", ""))
                     for b in beats[:k]).lower()
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
        # 상세 작법(150자 이상)은 한 동작의 시작→끝을 여러 절로 잇는다 — 쉼표가
        # 많아도 동작은 하나다. 짧은 움직임에서만 나열을 잡는다.
        if len(mot) < 150 and mot.count(",") >= 2:
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
    assets_text = " ".join(p.read_text(encoding="utf-8")
                           for p in (d/"assets").glob("*.md")) if (d/"assets").is_dir() else ""
    # 무대(setting)·앵커에 적힌 바다·숲은 그 이야기의 실물이다 — 보물섬의 sea.
    literal = {w.lower() for w in METAPHOR.findall(
        assets_text + " " + str(T.get("setting", "")) + " " + str(T.get("anchor", "")))}
    ct = COLOUR_THING.search(T.get("palette", ""))
    if ct:
        bad.append(f"팔레트에 사물 색 이름: {ct.group()}")
    # 광원 이름도 팔레트에 두면 초점이 빈 컷마다 그 광원을 세운다 — 'candle amber' 가
    # 유리장 속 완두콩 옆에 촛불을, 'matchstick-flame gold' 가 다 탄 다발 위에 불꽃을
    # 세웠다(실측: 공주와 완두콩 S13, 성냥팔이 소녀 S15). 팔레트엔 색 이름만 남긴다.
    lt = LIGHT_THING.search(T.get("palette", ""))
    if lt:
        bad.append(f"팔레트에 광원 이름: {lt.group()}")
    for b in beats:
        for key in ("visual", "motion"):
            sm = SIMILE.search(b.get(key, ""))
            if sm:
                bad.append(f"S{b['n']} {key} 에 직유: {sm.group()}")
            for mw in METAPHOR.findall(b.get(key, "")):
                if mw.lower() not in literal:
                    bad.append(f"S{b['n']} {key} 에 자산에 없는 구조·지형 낱말: {mw}")
            bc = BODY_COLOUR.search(b.get(key, ""))
            if bc:
                bad.append(f"S{b['n']} {key} 에 맨살 색 형용(옷이 된다): {bc.group()}")
            m = STATE.search(b.get(key, ""))
            if m:
                bad.append(f"S{b['n']} {key} 에 개념어: {m.group()}")
            r = RELATIVE.search(b.get(key, ""))
            if r:
                bad.append(f"S{b['n']} {key} 에 관계 표현: {r.group()}")
    for bc in BODY_COLOUR.finditer(assets_text):
        bad.append(f"자산에 맨살 색 형용(옷이 된다): {bc.group()}")

    # 카드의 한 줄 미끼·권역/갈래·계절은 자동 생성이 아니라 사람이 적는 파일이다.
    # 작품 네 편이 요약 없이 발행됐다(실측: 성냥팔이~눈의 여왕) — 큐에 올리기 전에 잡는다.
    for fname, label, keys in (("blurbs.json", "한줄요약(works/blurbs.json)", ("blurb", "mood")),
                               ("categories.json", "권역·갈래(works/categories.json)", ("region", "genre"))):
        try:
            entry = json.loads(pathlib.Path("works", fname).read_text(encoding="utf-8")).get(work)
        except Exception:
            entry = None
        if not isinstance(entry, dict) or not all(entry.get(k) for k in keys):
            bad.append(f"{label} 항목 없음")

    n = d/"narration_night.json"
    if n.exists():
        N = json.loads(n.read_text(encoding="utf-8"))["sentences"]
        if len(N) >= 8 and len(beats) >= 8:
            drift = sum(1 for i in range(1, 7)
                        if len(_keys(N[i]) & _keys(beats[i-1]["beat"]))
                         > len(_keys(N[i]) & _keys(beats[i]["beat"])))
            if drift >= 3:
                bad.append(f"낭독이 박자보다 한 칸 밀림 ({drift}/6)")

        # 이어짐. 컷이 열넷으로 늘면 마디 사이가 벌어져 "이게 뭔 내용이지" 가 나온다.
        # 앞 문장과 낱말을 하나도 공유하지 않으면 그 자리에서 이야기가 끊긴 것이다 —
        # 인물이든 장소든 사물이든 하나는 물고 넘어가야 눈이 따라간다.
        # 접속어(그런데·그러자·이윽고)만으로는 부족하다. 실제 대상이 이어져야 한다.
        JOIN = {"그런데", "그러자", "그리고", "그러던", "이윽고", "그날", "그때",
                "그러나", "그래서", "하지만", "며칠", "이튿날", "마침내", "다시"}
        # 바로 앞 문장만 보면 지나치게 깐깐하다. 한국어 낭독은 같은 대상을
        # 오누이 → 오빠 → 소년 처럼 바꿔 부르는데, 낱말이 글자 그대로 겹쳐야만
        # 통과시키면 문장이 단조로워진다(실측: 헨젤과 그레텔이 열한 곳에서 걸렸다).
        # 앞 **두 문장** 안에서 이어지면 눈이 따라간다 — 그 범위로 본다.
        for i in range(2, len(N) - 1):        # 마무리 문구는 뺀다
            near = _keys(N[i - 1]) | _keys(N[i - 2])
            if not (_keys(N[i]) & near) - JOIN:
                bad.append(f"S{i+1} 이 앞 두 문장과 이어지지 않는다")

        # 말투. "~지요" 만 열네 번 이어지면 낭독이 한 가락으로 굳는다(사용자 지적 09-08).
        # 자동 대본기와 같은 잣대 — 같은 계열 연속 2회 초과 금지, 한 계열이 절반 초과 금지.
        # 마지막 문장(마무리 문구)은 뺀다. 대사(따옴표 안)와 [역할·감정] 꼬리표는 어미 판정에서 지운다.
        try:
            sys.path.insert(0, str(pathlib.Path(__file__).parent))
            from write_script import ending_class
            body = [re.sub(r'\[[^\]]*\]|[“"「][^”"」]*[”"」]', "", x).strip() for x in N[:-1]]
            cls = [ending_class(x) for x in body if x]
            run = 1
            for a, b in zip(cls, cls[1:]):
                run = run + 1 if a == b else 1
                if run > 2:
                    bad.append(f"같은 말투가 셋 이상 이어진다({b})"); break
            if cls:
                top = max(set(cls), key=cls.count)
                if cls.count(top) * 2 > len(cls):
                    bad.append(f"말투가 {top} 로 쏠렸다({cls.count(top)}/{len(cls)})")
        except Exception:
            pass
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
