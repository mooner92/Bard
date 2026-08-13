#!/usr/bin/env python3
"""내레이션 대본 하네스: 초안 -> 스타일 패스 -> 기계 검증 -> 문장별 재수정.

단조로운 종결어미("~한다" 반복)를 코드가 정량 판정해 되돌린다.
LLM에게 "다양하게 써라"는 지시만으로는 강제가 안 되므로,
검증기가 불합격 문장을 찾아 해당 문장만 다시 쓰게 한다.

검증 규칙:
  - 같은 종결어미 연속 2회 초과 금지
  - 전체 문장의 50% 초과가 같은 어미면 불합격
  - 문장 길이 22~42자 (TTS ~6.5자/초 기준 3.4~6.5초)
  - 마지막 문장은 지정 문구로 끝나야 함
  - 금지어(목검 등 오역 단어) 포함 시 불합격

사용:
  python write_script.py --title 모비딕 --facts facts.txt \
      --ending "소설 모비딕에서 만날 수 있습니다" --out narration.json
"""
import argparse, json, re, sys, urllib.request

OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3.6:27b"


def ask(prompt, temperature=0.8):
    # think=False: qwen3.6 이 <think> 태그 없이 사고 텍스트를 흘리는 경우가 있어
    # 아예 생성 단계에서 꺼버린다 (태그 제거 정규식만으로는 못 막는다).
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "think": False,
                       "options": {"temperature": temperature, "num_ctx": 8192}}).encode()
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    t = json.load(urllib.request.urlopen(req, timeout=1800)).get("response", "")
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()


def parse_sentences(text, n):
    """S1: / **S1:** / S1. / 1. 등 형식 편차를 허용해 파싱한다."""
    out = {}
    for m in re.finditer(r"^\**\s*S?([1-9])\s*[:.)\]]\**\s*(.+)$", text, flags=re.M):
        s = m.group(2).strip().strip('"*')
        # 꺾쇠·서명 괄호는 문장에서 원천 제거: SSML(XML)에 <변신> 이 들어가면
        # 태그로 해석돼 TTS 합성이 깨진다.
        s = re.sub(r"[<>《》〈〉「」『』]", "", s)
        out[int(m.group(1))] = s
    return [out.get(i, "") for i in range(1, n + 1)]


def ending_of(s):
    """종결어미 지문: 마지막 어절의 끝 2글자."""
    s = s.rstrip(".!?」』\" ")
    return s[-2:] if len(s) >= 2 else s


def ending_class(s):
    """어미의 문법 계열 판별. 표면 글자 비교로는 '낸다/춘다/는다'가
    전부 달라 보이지만 모두 같은 한다체라 별도 분류가 필요하다."""
    t = s.rstrip(".!?」』\" ")
    if re.search(r"니다$|니까$", t):
        return "합니다체"
    if re.search(r"[죠요]$", t):
        return "구어체"
    if t.endswith("다"):
        return "한다체"
    # ~노라/~도다/~구나/~로다: 고어체 서술 어미. 명사종결로 오분류되면
    # ("바라보았노라" 실측) 낭독 톤이 깨진 채 통과된다.
    if re.search(r"(노라|도다|구나|로다)$", t):
        return "고어체"
    return "명사종결"


# 문장별 목표 어미 계열. 모델에게 다양성을 맡기면 한 계열로 쏠리므로
# (한다체 금지 -> 전부 합니다체가 된 실측) 계열을 미리 배정해 강제한다.
# 마지막 문장은 마무리 문구("~있습니다") 때문에 합니다체 고정.
LEN_MIN, LEN_MAX = 22, 42
ENDING_PLAN = ["합니다체", "구어체", "명사종결", "합니다체", "구어체", "명사종결", "구어체", "합니다체"]
CLASS_HINT = {
    "합니다체": "~습니다 / ~었습니다 로 끝내라",
    "구어체": "~었죠 / ~인데요 / ~네요 로 끝내라",
    "명사종결": "서술어 없이 명사로 끝내라 (예: '...만이 남은 검은 바다.')",
}



# ---------- 서사 검증층 (docs/NARRATIVE.md 의 H1~X2 규칙) ----------
CAUSAL = ["그래서", "그러자", "따라서", "결국", "탓에", "때문에", "덕분에"]
ADVERS = ["그런데", "하지만", "그러나", "사실", "정작", "오히려", "그렇지만", "반면", "그때"]
ADDITIVE = ["그리고", "그러고는", "이윽고", "그런 다음", "또한", "며칠 뒤"]
STATIVE_END = ["있습니다", "있죠", "섭니다", "보입니다", "디딥니다", "놓입니다",
               "펼쳐집니다", "나타납니다", "있었죠", "보이죠"]
ABSTRACT = ["집착", "불가해", "운명", "본질", "진리", "실존", "소외", "숙명", "고독",
            "인간의", "자연의", "인간성"]
CONCRETE = ["관", "작살", "갑판", "고래", "다리", "의족", "금화", "돛대", "피", "뼈", "손",
            "눈", "불", "바다", "밤", "사과", "빵", "문", "침대", "눈보라", "벌레", "그림자",
            "촛불", "날개", "구두", "접시", "배", "돛", "칼", "종이", "편지"]
META = ["상징한", "그리는 ", "보여주", "담고 있", "명작", "걸작", "작품이", "이야기다", "묘사하"]
GAPWORD = ["왜", "무엇", "누구", "어떤", "한 ", "단 하나", "까닭", "이유", "무언가", "누군가"]


def narrative_issues(sents, persons=None):
    """서사 규칙 위반 목록 [(문장idx, 메시지)]. 전역 위반은 대표 문장에 귀속."""
    I = []
    n = len(sents)
    body = " ".join(sents)
    # C1: 인과/역접 전환 >=2, 나열 <=1
    tr = [any(m in x for m in CAUSAL + ADVERS) for x in sents[1:]]
    if sum(tr) < 2:
        I.append((3 if n > 3 else n - 1, "C1 인과/역접 접속(그래서/결국/그런데...)이 2개 미만 — 문장을 앞 문장의 결과나 반전으로 다시 써라"))
    if sum(any(m in x for m in ADDITIVE) for x in sents[1:]) > 1:
        I.append((1, "C1 나열 접속(그리고...) 과다 — 인과나 반전으로 바꿔라"))
    # A6: 중반 반전
    if not any(m in x for x in sents[2:n - 1] for m in ADVERS):
        I.append((2, "A6 중반(S3~)에 반전 표지(그런데/하지만/사실/오히려)가 없다"))
    # H1: S1 정지 서술 금지 + 구체 명사
    if any(sents[0].rstrip(".!?").endswith(v) for v in STATIVE_END):
        I.append((0, "H1 첫 문장이 정지 서술로 끝난다 — 지금 벌어지는 동작으로 바꿔라"))
    if not any(c in sents[0] for c in CONCRETE):
        I.append((0, "H1 첫 문장에 눈에 보이는 구체 사물이 없다"))
    # A8: 정보격차 장치
    if not any(g in sents[0] or g in sents[1] for g in GAPWORD):
        I.append((0, "A8 S1~S2에 유보 장치(한/어떤/왜/누군가...)가 없다"))
    # E1/A3: 추상어
    half = n // 2 + 1
    for i, x in enumerate(sents[:half]):
        if any(a in x for a in ABSTRACT):
            I.append((i, "A3 전반부에 추상어 — 구체 이미지로 바꿔라"))
    for i in range(half, n):
        x = sents[i]
        if any(a in x for a in ABSTRACT) and not any(c in x for c in CONCRETE):
            I.append((i, "A3 추상어에 구체 명사 미동반"))
    # A7: 메타 요약 어휘
    for i, x in enumerate(sents):
        if any(m in x for m in META):
            I.append((i, "A7 메타 요약 어휘(상징/그리는/명작...) 금지"))
    # C2: 리듬
    L = [len(x) for x in sents if x]
    if L:
        mu = sum(L) / len(L)
        sd = (sum((v - mu) ** 2 for v in L) / len(L)) ** 0.5
        if sd < 4.0:
            I.append((L.index(max(L)), f"C2 문장 길이가 균일(편차 {sd:.1f}) — 이 문장을 짧게 쪼개라"))
        if min(L) > 24:
            I.append((L.index(min(L)), "C2 24자 이하 펀치라인이 없다 — 이 문장을 압축하라"))
    # Q1: 인용 1개, 중간에
    q = body.count('"') + body.count("\u201c") + body.count("\u201d")
    if q != 2:
        I.append((1, "Q1 인용 대사가 정확히 1쌍이어야 한다 (짧은 구어 한 줄)"))
    elif '"' in sents[0] or '"' in sents[-1]:
        I.append((0 if '"' in sents[0] else n - 1, "Q1 인용은 중간 문장에만"))
    # A2: 인물 상한
    if persons:
        named = {p for p in persons if p in " ".join(sents[:n - 1])}
        if len(named) > 2:
            I.append((2, f"A2 인물 {len(named)}명({', '.join(sorted(named))}) — 2명 이하로 줄여라"))
    # X1: 마지막 문장 미해결 질문형
    if not re.search(r"(는지|이유|까닭|무엇|누구|왜)", sents[-1]):
        I.append((n - 1, "X1 마지막 문장이 미해결 질문형이 아니다 — '~한 이유는/누구인지는' 형태로"))
    # X2: 루프백. 한국어는 조사가 붙으므로("선원이" vs "선원을") 어간으로 비교한다.
    def stems(s):
        out = set()
        for w in re.findall(r"[가-힣]{2,}", s):
            out.add(w)
            w2 = re.sub(r"(이|가|은|는|을|를|의|에|도|만|와|과|로|에서|으로|에게|까지|부터)$", "", w)
            if len(w2) >= 2:
                out.add(w2)
        return out
    t1, tn = stems(sents[0]), stems(sents[-1])
    if not (t1 & tn):
        I.append((n - 1, "X2 마지막 문장이 첫 문장과 공유하는 단어가 없다 (루프백)"))
    return I
# ---------- /서사 검증층 ----------


NARRATIVE_RULES = """[서사 규칙 — 지루한 줄거리 나열을 막는다]
- 첫 문장: 지금 눈앞에서 벌어지는 구체적 동작 하나. 주인공 이름을 쓰지 말고
  "한 선원이", "어떤 남자가" 처럼 감춰라. "~있습니다/서 있습니다" 같은 정지 서술 금지.
- 문장끼리 "그리고 다음엔"으로 잇지 마라. 최소 두 곳은 "그래서/결국" (결과) 또는
  "그런데/하지만/사실" (반전) 으로 이어라.
- 중반에 반드시 반전이 한 번 있어야 한다.
- 짧은 문장(22~24자) 하나를 반드시 섞어 리듬을 만들어라.
- 큰따옴표 대사는 정확히 한 번, 중간 문장에. 14자 이내의 짧은 구어로.
- 이름 있는 인물은 2명까지만.
- 추상어(집착·운명·본질·불가해) 금지. 눈에 보이는 사물로 말하라.
- 마지막 문장은 답을 주지 말고 질문을 남겨라: "~한 이유는", "~가 누구인지는".
  그리고 첫 문장에 나온 단어를 하나 다시 써서 처음으로 되돌아오게 하라."""

# 저작권 살아 있는 현대서용. 줄거리·결말을 재구성하지 않고 "이 책이 던지는 질문"만 다룬다.
INTRO_RULES = """[소개 규칙 — 줄거리 각색 금지]
- 이 책은 저작권이 살아 있다. 줄거리를 순서대로 옮기거나 결말·반전을 밝히면 실패다.
- 등장인물의 행동을 장면으로 재연하지 마라. 본문을 인용하지 마라.
- 대신 이렇게 쓴다: 이 책이 독자에게 던지는 질문, 책이 놓인 시대와 장소,
  읽기 전에 알아두면 좋은 배경, 이 책을 지금 읽는 의미.
- 첫 문장은 독자의 일상에서 출발하는 구체적 장면 하나로 연다(책 이야기부터 꺼내지 마라).
- 중간에 질문 형태의 문장을 두 개 이상 넣어라. 답은 주지 마라.
- 자료에 없는 인물·사건·수치를 지어내지 마라. 확실하지 않으면 쓰지 마라.
- 추상어(운명·본질·불가해) 금지. 눈에 보이는 사물과 상황으로 말하라.
- 마지막 문장은 지정 문구로 끝나되, 첫 문장에 나온 단어를 하나 다시 써라."""


def validate(sents, ending_phrase, banned, plan=None):
    """문제 목록 반환. 비어 있으면 합격."""
    issues = []
    ends = [ending_of(s) for s in sents]
    run = 1
    for i in range(1, len(ends)):
        run = run + 1 if ends[i] == ends[i - 1] else 1
        if run > 2:
            issues.append((i, f"종결어미 '{ends[i]}' 3연속"))
    for i, s in enumerate(sents):
        if not s:
            continue
        if ending_class(s) == "한다체":
            issues.append((i, f"한다체 종결('{ending_of(s)}') 금지"))
        elif plan and i < len(plan) and ending_class(s) != plan[i]:
            issues.append((i, f"어미 계열 불일치: {ending_class(s)} -> {CLASS_HINT[plan[i]]}"))
    for i, s in enumerate(sents):
        if not s:
            issues.append((i, "누락")); continue
        # 마지막 문장은 지정 마무리 문구를 통째로 담아야 한다. 문구가 27자인데
        # 상한이 33자면 앞에 무슨 말을 붙여도 초과라 수리 루프가 헛돈다.
        lmax = LEN_MAX
        if ending_phrase and i == len(sents) - 1:
            lmax = max(LEN_MAX, len(ending_phrase) + 12)
        if not (LEN_MIN <= len(s) <= lmax):
            issues.append((i, f"길이 {len(s)}자 ({LEN_MIN}~{lmax} 벗어남)"))
        for b in banned:
            if b in s:
                issues.append((i, f"금지어 '{b}'"))
        # 한글 본문 검사: 사고 텍스트("Here's a thinking...") 오염 차단.
        # KEI·ESG 같은 두문자어는 정상 한국어 문장에 섞이므로 검사 전에 뺀다.
        core = re.sub(r"\b[A-Z]{2,5}\b", "", s)
        if core and (re.search(r"[A-Za-z]", core) or
                     len(re.findall(r"[가-힣]", core)) < len(core) * 0.4):
            issues.append((i, "한국어 문장이 아님(라틴 문자/한글 비율)"))
    # 모델이 작품명에 꺾쇠·괄호를 붙이는 버릇(<변신>, 《모비딕》 실측)이 있어
    # 비교 전에 양쪽 모두 제거한다.
    def norm(x):
        return re.sub(r"[<>《》〈〉「」『』()\[\]]", "", x).rstrip(".!? ")
    if ending_phrase and not norm(sents[-1]).endswith(norm(ending_phrase)):
        issues.append((len(sents) - 1, f"마지막 문장이 '{ending_phrase}'로 끝나지 않음"))
    return issues


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--title", required=True)
    p.add_argument("--facts", required=True, help="원작 사실 텍스트 파일 (환각 방지용 근거)")
    p.add_argument("--scenes", type=int, default=6)
    p.add_argument("--ending", required=True, help="마지막 문장의 필수 마무리 문구")
    p.add_argument("--banned", default="목검", help="쉼표 구분 금지어")
    p.add_argument("--out", required=True)
    # 8문장 자동 생성은 4회로 수렴하지 않는다(실측: 톨스토이 야간 배치 11건 잔존).
    # 수리 1회는 27B 몇 초짜리라, 클립 한 편 7분에 비하면 훨씬 싸다.
    p.add_argument("--max-repair", type=int, default=8)
    p.add_argument("--persons", default="", help="쉼표 구분 인물명 목록 (2명 초과 검출용)")
    p.add_argument("--minlen", type=int, default=22)
    p.add_argument("--maxlen", type=int, default=42)
    a = p.parse_args()
    global LEN_MIN, LEN_MAX
    LEN_MIN, LEN_MAX = a.minlen, a.maxlen
    persons = [x for x in a.persons.split(",") if x]
    facts = open(a.facts, encoding="utf-8").read()
    banned = [b for b in a.banned.split(",") if b]
    n = a.scenes
    # 저작권이 살아 있는 현대서는 줄거리 각색 금지 (docs/PLAN.md).
    # 사실파일이 스스로 포맷을 선언한다 — 야간 배치 호출부를 건드리지 않기 위해서다.
    intro = "[포맷] 소개형" in facts

    base_rules = f"""너는 한국어 낭독 대본 작가다. 아래 [원작 사실]의 내용만 사용하라. 없는 내용을 지어내지 마라.

[원작 사실]
{facts}

[문체 규칙 — 반드시 지켜라]
- 전체를 차분한 낭독체(~습니다체 계열)로 쓰되, 종결 형태를 문장마다 다르게 하라.
  허용 예: ~습니다 / ~었죠 / ~인데요 / ~것입니다 / 명사로 끝나는 문장 / 짧은 대사 인용.
- 같은 종결어미를 연이어 쓰지 마라. "~한다"체 금지.
- 문장별 종결 계열 배정을 정확히 따르라:
  1번 ~습니다 / 2번 ~었죠·~인데요 / 3번 명사로 끝냄 / 4번 ~습니다 /\n  5번 ~었죠·~네요 / 6번 명사로 끝냄 / 7번 ~네요·~인데요 / 마지막 번호 ~있습니다(고정)
- 문장 길이를 일부러 들쭉날쭉하게: 짧은 문장(22~28자)과 긴 문장(32~42자)을 섞어라.
- 첫 문장은 질문이 아니라 구체적 장면으로 시작한다.
- 각 문장은 장면 하나를 그린다. 요약하지 말고 보여줘라.
- 마지막 {n}번 문장은 반드시 "{a.ending}"로 끝난다.
- 금지어: {', '.join(banned)}

{INTRO_RULES if intro else NARRATIVE_RULES}"""

    draft = ask(base_rules + f"""

[출력 형식] 아래처럼 번호와 괄호만 붙여 {n}줄 출력. 설명 금지.\n1) 첫 문장\n2) 두 번째 문장\n...
""")
    sents = parse_sentences(draft, n)

    # 스타일 패스: 리듬 관점 재작성 (길이 규칙을 반드시 포함 -- 빼면 문장이 부풀어 오른다)
    styled = ask(f"""아래 낭독 대본을 리듬 관점에서 고쳐 써라. 내용과 장면 순서는 유지하고,
종결어미 반복을 없애고, 문장 길이에 강약을 만들어라. 마지막 문장의 "{a.ending}" 마무리는 유지.
각 문장은 공백 포함 22~42자를 절대 넘기지 마라. 42자를 넘으면 실패다.
1) ~ {n}) 번호 형식만 출력.

""" + "\n".join(f"{i+1}) {s}" for i, s in enumerate(sents)))
    cand = parse_sentences(styled, n)
    if all(cand):
        sents = cand

    # 검증 -> 문장 단위 재수정 루프 (전체 재작성은 파싱이 불안정해 문장별로 처리)
    for attempt in range(a.max_repair):
        # 서사 검증층(반전·대사·루프백)은 각색형 전용이다. 소개형에 걸면
        # 있지도 않은 줄거리를 만들어내라고 모델을 떠미는 꼴이 된다.
        issues = validate(sents, a.ending, banned, plan=ENDING_PLAN[:n])
        if not intro:
            issues += narrative_issues(sents, persons)
        if not issues:
            break
        print(f"[검증 {attempt+1}] 불합격 {len(issues)}건: {issues}", file=sys.stderr)
        bad = {}
        for i, msg in issues:
            if i >= 0:
                bad.setdefault(i, []).append(msg)
        if not bad:
            break
        for i, msgs in bad.items():
            tail = f' 반드시 "{a.ending}"로 끝나야 한다.' if i == n - 1 else ""
            fixed = ask(f"""다음 한 문장을 고쳐라. 문제: {'; '.join(msgs)}.
규칙: 공백 포함 22~42자, 차분한 낭독체, 내용 유지.{tail}
고친 문장 한 줄만 출력하라. 번호나 설명 금지.

{sents[i]}""", temperature=0.9)
            # 첫 줄이 아니라 '한글이 실제로 들어 있는 첫 줄'을 채택한다
            line = next((l for l in fixed.strip().splitlines()
                         if re.search(r"[가-힣]", l)), "").strip().strip('"*')
            line = re.sub(r"^\**\s*S?[1-9]\s*[:.)\]]\**\s*", "", line)
            print(f"[수정 S{i+1}] ({len(line)}자) {line[:60]}", file=sys.stderr)
            if line:
                sents[i] = line

    # 비문 교정 패스: "침몰하느라고 합니다" 류의 어색한 문장을 정리.
    # 교정이 어미 계열을 깨면 해당 문장은 교정 전 버전을 유지한다.
    proofed = ask("아래 문장들의 맞춤법과 어색한 표현(비문)만 고쳐라. 종결어미와 뜻은 유지하고, 1) ~ %d) 번호 형식으로만 출력하라.\n\n" % n
                  + "\n".join(f"{i+1}) {s}" for i, s in enumerate(sents)), temperature=0.3)
    cand = parse_sentences(proofed, n)
    for i in range(n):
        if cand[i] and not validate([cand[i]], "", banned, plan=[ENDING_PLAN[i]]):
            sents[i] = cand[i]

    issues = validate(sents, a.ending, banned, plan=ENDING_PLAN[:n])
    if not intro:
        issues += narrative_issues(sents, persons)
    result = {"title": a.title, "sentences": sents,
              "endings": [ending_of(s) for s in sents],
              "passed": not issues, "issues": [f"S{i+1}: {m}" for i, m in issues]}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    sys.exit(0 if not issues else 2)


if __name__ == "__main__":
    main()
