#!/usr/bin/env python3
"""트리트먼트 — 여덟 문장을 하나의 이야기 줄기에 꿰는 단계.

이 단계가 없을 때 무슨 일이 일어났나(실측, 「날개」):
  1) 어둠 속에서 구르고 꿈의 바다에 잠기었습니다      <- 방
  3) 환전소를 떠난 지폐들이 거리 틈새로 스며들어       <- 거리
  4) 빗속에 쓰러진 그를 보고 **우리는** 서 있었다      <- 시점이 바뀜
  6) 옥상에는 푸른 바다만이 남아 있었다               <- 옥상
줄거리 요약에서 장면만 여덟 개 뽑으니 파편이 됐다. 문장이 흩어지면 그림도
다락방·잠든 남자·책 읽는 노인으로 제각각 나온다.

그래서 대본을 쓰기 전에 **하나의 사건 줄기**를 먼저 정한다.
  - 작품 안에서 이야기 하나를 고른다(전체 요약이 아니라).
  - 여덟 박자로 나누되 장소·인물이 이어지게 한다.
  - 결말은 감춘다. 마지막 박자는 답이 아니라 질문으로 남긴다.
  - 시각 앵커(인물 생김새·팔레트)를 정해 모든 장면 그림에 같은 문장을 넣는다.

자료가 얇으면 웹 검색으로 보강한다. 검색이 막히면 있는 자료로 진행한다.

사용:
  venv/bin/python scripts/treatment.py --title 날개 --author 이상 \
      --facts facts/auto_nalgae.txt --out output/nalgae/treatment.json
"""
import argparse
import html
import os
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3.6:27b"                     # 이 서버 ollama (대체 경로)
VLLM = os.environ.get("BARD_VLLM", "http://192.168.1.105:8003/v1/chat/completions")
VLLM_MODEL = os.environ.get("BARD_VLLM_MODEL", "qwen3.8-27b")
UA = "bard-treatment/1.0 (internal literary shorts pipeline)"
BEATS = 8
ATTEMPTS = 6      # 검사가 여섯 겹이다. 시도가 적으면 고전이 줄기 없이 넘어간다
EXAMPLES_FILE = Path(__file__).resolve().parent.parent / "works" / "plot_examples.json"
# 사람이 사람에게 가하는 물리적 강제. 규칙만으로는 안 걸린다(실측: 채식주의자에서
# "남편이 어깨를 잡고 억지로 몸을 돌려" 가 결정적 사건으로 뽑혔다 — 그림으로 그리면
# 남자가 여자를 붙잡는 장면이 된다). 박자 텍스트에 이게 있으면 그 시도를 버린다.
COERCION = re.compile(
    r"억지로|강제로|때리|후려|붙잡아|움켜|밀치|끌고 가|끌어당|목을 조"
    r"|입에 (?:넣|밀어)|입으로 가져|입 앞에|먹이려|먹이는|폭력")


def ask(prompt: str, temperature: float = 0.7, ctx: int = 8192) -> str:
    """사내망 105 서버(qwen3.8)를 먼저 쓰고, 닿지 않으면 이 서버 ollama 로 돌아간다.

    105 쪽이 한 번에 43초로 훨씬 빠르고 형식 지시를 잘 지킨다(실측: 방향 규칙을
    여덟 컷 모두 지켰다). 다만 창작 규칙은 여전히 어긴다 — 감자에서 도착점을
    "목에서 흐르는 피"로 잡고 시신까지 그렸다. 모델을 바꿔도 하네스는 그대로 쓴다.
    """
    if VLLM:
        try:
            body = json.dumps({
                "model": VLLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature, "max_tokens": 2400,
                "chat_template_kwargs": {"enable_thinking": False},
            }).encode()
            req = urllib.request.Request(VLLM, data=body,
                                         headers={"Content-Type": "application/json"})
            t = json.load(urllib.request.urlopen(req, timeout=300))
            t = t["choices"][0]["message"]["content"]
            return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()
        except Exception as e:      # 사내망 단절·모델 교체 — 로컬로 이어 간다
            print(f"  · 105 호출 실패({type(e).__name__}) — 로컬 모델로 대체", file=sys.stderr)
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "think": False,
                       "options": {"temperature": temperature, "num_ctx": ctx}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    t = json.load(urllib.request.urlopen(req, timeout=1800)).get("response", "")
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()


def web_snippets(query: str, limit: int = 8) -> str:
    """검색 요약문을 긁는다. 키 없이 되는 경로만 쓰고, 막히면 빈 문자열."""
    try:
        u = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        req = urllib.request.Request(u, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            page = r.read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"  ! 웹 검색 실패({type(e).__name__}) — 있는 자료로 진행", file=sys.stderr)
        return ""
    out = []
    for m in re.finditer(r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S):
        txt = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        if len(txt) > 40:
            out.append(txt)
        if len(out) >= limit:
            break
    return "\n".join(out)[:2500]


def research(title: str, author: str, facts: str) -> str:
    """줄거리 재료가 얇으면 검색으로 보탠다."""
    body = "\n".join(x for x in facts.splitlines() if x and not x.startswith("["))
    if len(body) >= 900:
        return ""
    add = web_snippets(f"{title} {author} 소설 줄거리 주요 장면")
    if add:
        print(f"  + 웹 검색으로 {len(add)}자 보강", file=sys.stderr)
    return add


SCHEMA_HINT = """{
 "logline": "이 이야기를 한 문장으로 (스포일러 없이)",
 "destination": "여덟 박자가 향하는 한 지점 (예: 집 문 앞 — 하루 종일 미뤄온 귀가)",
 "protagonist": "이름 없이 부르는 말 (예: 골방에 사는 젊은 남자)",
 "setting": "장소와 시대 (예: 1930년대 경성의 셋방과 그 골목)",
 "anchor": "English visual anchor for the person and place, 10-18 words",
 "palette": "English palette and light, 8-14 words",
 "beats": [
   {"n": 1, "beat": "그 장면에서 눈에 보이는 사건 하나 (한국어, 40자 이내)",
    "visual": "English shot description, 12-22 words",
    "motion": "English, 6-14 words. one moving thing + its direction (up the slope, toward the camera)"}
 ],
 "withheld": "결말에서 밝혀지는 것 — 대본에 절대 쓰지 않는다"
}"""


def examples() -> str:
    """정답셋(works/plot_examples.json)을 프롬프트에 넣을 형태로 읽는다.

    규칙 문장만 주면 모델은 '증상의 나열'을 쓴다 (실측: 채식주의자 — 고기 밀어냄 /
    남편이 화냄 / 침대에 누움 / 병원 채혈… 박자끼리 인과가 없고 도착점도 없었다).
    잘 짜인 줄기를 **보여주면** 그 구조를 흉내 낸다. 파일이 없으면 규칙만으로 간다.
    """
    if not EXAMPLES_FILE.exists():
        return ""
    try:
        ex = json.loads(EXAMPLES_FILE.read_text(encoding="utf-8")).get("examples", [])
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ! 정답셋을 읽지 못했다 ({e}) — 규칙만으로 진행", file=sys.stderr)
        return ""
    out = []
    for e in ex:
        beats = "\n".join(f"  {i}) {b}" for i, b in enumerate(e.get("beats", []), 1))
        out.append(f"《{e['title']}》\n  도착점: {e['destination']}\n"
                   f"  이게 좋은 이유: {e['why']}\n{beats}")
    return "\n\n".join(out)


def reveals_ending(t: dict) -> bool:
    """박자가 감춰야 할 결말을 드러내는지 모델에게 묻는다.

    규칙만으로는 안 막힌다(실측: withheld 가 "개츠비가 살해되는 결말"인데
    박자 6~8이 총을 꺼내고 겨누고 물에 가라앉는 장면이었다). 판정만 시킨다.
    """
    withheld = (t.get("withheld") or "").strip()
    if not withheld:
        return False
    # 박자 텍스트는 문턱에서 멈춰도 그림 묘사가 결말을 그대로 그리는 일이 있다
    # (실측: 박자는 "눈을 감는다"인데 visual 은 "the gun points directly at his...").
    # 두 필드를 함께 보여준다.
    beats = "\n".join(f"{b['n']}) {b['beat']}  [그림: {b.get('visual','')}]"
                      for b in t.get("beats", []))
    ans = ask(f"""아래 [감출 것]이 [박자]에 드러나 있는지 판정만 하라.

[감출 것]
{withheld}

[박자]
{beats}

판정 기준: 시청자가 이 박자와 그림만 보고 [감출 것]의 사건을 알아차릴 수 있으면 '노출'이다.
인물 이름을 안 썼어도, 그 사건이 일어나는 장면을 그리면 노출이다.
특히 그림에 흉기가 사람을 겨누거나, 죽음·시신·피가 보이면 노출이다.
'노출' 또는 '안전' 한 낱말만 출력하라.""", temperature=0.1)
    verdict = ans.strip().splitlines()[0] if ans.strip() else ""
    if "노출" in verdict:
        print(f"  ! 결말 노출 판정 — 재작성", file=sys.stderr)
        return True
    return False


def drifts(t: dict) -> bool:
    """박자들이 도착점 하나로 모이는지 모델에게 묻는다.

    흩어짐은 문장 하나의 결함이 아니라 **배열 전체**의 결함이라 규칙·정규식으로는
    안 걸린다(실측: 채식주의자 — 박자 여덟 개가 각각은 규칙을 다 지켰는데
    서로 무관한 증상들이라 무슨 이야기인지 알 수 없었다). 모이는지만 판정시킨다.
    """
    dest = (t.get("destination") or "").strip()
    if not dest:
        return True
    beats = "\n".join(f"{b['n']}) {b['beat']}" for b in t.get("beats", []))
    verdict = ask(f"""아래는 짧은 영상의 여덟 박자와 그것들이 향하는 도착점이다.

[도착점] {dest}

[박자]
{beats}

각 박자가 앞 박자의 결과로 일어나면서 도착점에 가까워지는가?
서로 무관한 장면이 나열돼 있거나 도착점과 상관없는 박자가 둘 이상이면 '흩어짐'이다.
'모임' 또는 '흩어짐', 한 단어로만 답하라.""", temperature=0.2)
    return "흩어" in verdict


def build(facts: str, extra: str) -> dict:
    # 소개형(저작권 보호작)은 자료에 줄거리가 없고 "재구성 금지"가 적혀 있다. 그런데도
    # 여덟 박자를 만들라고 하면 모델은 장면을 **지어낸다**(실측: 채식주의자에서 소설상
    # 아버지가 한 행동을 남편이 한 것으로 만든 식탁 폭력 장면이 나왔다). 줄기를 만들지
    # 않고 물러난다 — 대본 단계가 줄거리 대신 작품의 세계를 쓰는 길로 간다.
    if re.search(r"\[포맷\]\s*소개형", facts):
        print("  · 소개형 — 줄거리 재구성 금지. 트리트먼트 없이 진행한다.", file=sys.stderr)
        return {}
    good = examples()
    prompt = f"""너는 문학 작품을 짧은 영상으로 옮기는 구성작가다.
아래 자료에서 **이야기 하나**를 골라 여덟 박자짜리 트리트먼트를 만들어라.

[자료]
{facts}
{("[검색 자료]" + chr(10) + extra) if extra else ""}
{("[잘 짜인 예 — 이 구조를 그대로 따라라]" + chr(10) + good) if good else ""}

[규칙]
- 작품 전체를 요약하지 마라. 인물 한 명이 겪는 **하나의 사건 줄기**를 고른다.
- 먼저 **도착점**을 하나 정하라. 여덟 박자는 전부 그 한 지점을 향해 밀려가야 한다.
  도착점이 없으면 장면들이 따로 놀고, 보는 사람은 무슨 이야기인지 알 수 없다.
- 박자와 박자는 **'그래서' 또는 '그런데'** 로 이어져야 한다. 앞 박자가 뒤 박자의
  원인이 되어야 한다. '그리고 다음엔' 으로 이어붙인 나열은 실패다.
  (나쁜 예: 고기를 밀어낸다 / 침대에 눕는다 / 병원에서 피를 뽑힌다 — 서로 무관한 증상들)
- 아무 대목이나 고르지 마라. **그 작품이 기억되는 결정적 사건**을 골라야 한다.
  독자가 그 작품을 떠올릴 때 가장 먼저 생각나는 장면, 제목이 가리키는 사건,
  마지막에 뒤집히는 것 — 그 줄기를 따라간다. 곁가지 일화는 안 된다.
- 그 사건을 향해 **기대를 쌓아라**. 1번은 평범해 보이는 시작, 중반은 어긋나는 징후,
  7~8번은 문턱 앞. 무슨 일이 일어날지 궁금하게 만들되 답은 주지 않는다.
- 여덟 박자는 이어져야 한다. 장소가 바뀌면 어떻게 옮겨갔는지 앞 박자에 드러나야 한다.
- 시점을 바꾸지 마라. 처음부터 끝까지 같은 인물을 따라간다.
- 결말·반전의 정답은 절대 쓰지 마라. withheld 에 따로 적고 beats 에서는 감춘다.
- 반전 박자는 **그 직전에서 멈춘다**. 무엇을 보았는지 쓰지 말고, 보고 난 뒤의 행동만 적어라
  (나쁜 예: "아내와 내객을 보고 도망친다" / 좋은 예: "문틈으로 무언가를 보고 뒤돌아 달린다").
- logline 에도 결정적 사건을 적지 마라. 무엇이 걸려 있는지만 말한다.
- 1번 박자는 눈앞의 동작 하나로 연다. 설명하지 마라.
- 중반(4~5번)에 판이 뒤집히는 순간을 하나 둔다.
- **끝에서 두 번째** 박자를 질문으로 닫는다. 마지막 박자는 질문이 아니라
  사람이 없는 **여운의 정물**이다(빈 인력거, 창불 하나, 남겨진 물건).
  마지막 낭독 문장이 안내 문구라 그 자리에 절정 그림이 붙으면 낭비된다.
- anchor 에는 **생김새만** 적는다. 소품이나 장소를 넣으면 그것이 모든 컷에 강제로
  끼어든다(실측: "회중시계를 든"이 코끼리 타는 장면까지 따라갔다).
- motion 에는 **진행 방향**을 반드시 적는다. 없으면 아무 쪽으로나 움직인다.
- 자료에 없는 사건·인물·지명을 지어내지 마라. 누가 그 행동을 했는지 자료대로 써라.
- **사람이 사람에게 물리적으로 강제하거나 해치는 장면은 고르지 마라** — 때리기,
  붙잡아 끌기, 억지로 먹이기, 밀치기. 그 작품의 결정적 사건이 폭력이라면 폭력 자체가
  아니라 **그 직전의 결심** 이나 **그 뒤에 남은 정적** 을 도착점으로 삼아라.
- visual 은 영어로, 카메라가 보는 것만. 글자·간판·책·종이를 넣지 마라.
- **그림도 결말을 그리면 안 된다.** 흉기가 사람을 겨누는 구도, 죽음·시신·피는 금지다.
  박자 텍스트가 문턱에서 멈췄어도 그림이 다 보여주면 같은 위반이다.
- anchor 와 palette 는 모든 장면에 그대로 붙일 문장이다. 인물 생김새와 빛을 고정한다.

[출력] 아래 JSON 하나만. 설명·코드펜스 금지. beats 는 정확히 {BEATS}개.
{SCHEMA_HINT}"""
    for attempt in range(ATTEMPTS):
        raw = ask(prompt, temperature=0.7 + 0.08 * attempt)
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            continue
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        beats = d.get("beats") or []
        # qwen3.6 이 한국어에 중국어를 흘린다. 박자만 검사하다 로그라인으로 샜다
        # (실측: 박자 "거리로走出去", 로그라인 "가족의餐桌을 무너뜨리고").
        # 낭독·대본의 근거가 되는 한국어 필드를 전부 본다.
        ko_fields = [d.get(k) or "" for k in
                     ("logline", "destination", "protagonist", "setting", "withheld")]
        ko_fields += [b.get("beat") or "" for b in beats]
        ko_ok = not any(re.search(r"[\u4e00-\u9fff\u3040-\u30ff]", t) for t in ko_fields)
        if len(beats) == BEATS and d.get("destination") and ko_ok and all(
                b.get("beat") and b.get("visual") for b in beats):
            for i, b in enumerate(beats, 1):
                b["n"] = i
            if reveals_ending(d):
                continue
            if drifts(d):
                print("  ! 박자가 도착점으로 모이지 않는다 — 재시도", file=sys.stderr)
                continue
            # 박자를 막았더니 도착점 쪽으로 샜다(실측: 도착점 "거절이 폭력으로
            # 전환되는 문턱"). 줄기 전체가 폭력을 향하면 그림도 그리 간다.
            if any(COERCION.search(t) for t in
                   [b["beat"] for b in beats] + [d.get("destination") or ""]):
                print("  ! 물리적 강제를 향하는 줄기 — 재시도", file=sys.stderr)
                continue
            # 8번은 질문으로 닫으라는 규칙을 모델이 자주 흘린다(실측: "침묵이
            # 식탁을 짓누르며 남편의 표정이 굳어진다"). 여운이 질문이어야 다음이 궁금해진다.
            # 질문은 **끝에서 두 번째**다. 마지막은 여운의 정물 — 프롬프트와 이 검사가
            # 어긋나 있으면 모델이 뭘 내놔도 반려된다(실측: 여섯 번 다 떨어졌다).
            # 모델이 옛 버릇대로 질문을 마지막에 두는 일이 가장 잦다. 반려하지 말고
            # 끝 두 박자를 맞바꾸면 원하는 모양(질문 -2, 여운 -1)이 된다 — 반려 여섯 번의
            # 대부분이 이 하나였다(실측: 만무방·금수회의록·인간 문제).
            if (beats[-1]["beat"].rstrip().endswith("?")
                    and not beats[-2]["beat"].rstrip().endswith("?")):
                beats[-1], beats[-2] = beats[-2], beats[-1]
                for i, b in enumerate(beats, 1):
                    b["n"] = i
            if not all((b.get("motion") or "").strip() for b in beats):
                print("  ! motion 이 빠진 박자가 있다 — 재시도", file=sys.stderr)
                continue
            if re.search(r"\b(moving|walking|through|aboard|inside|holding|carrying|landscape|street|room)\b",
                         d.get("anchor", ""), re.I):
                print("  ! 앵커에 장소·동작이 들었다 — 재시도", file=sys.stderr)
                continue
            if not beats[-2]["beat"].rstrip().endswith("?"):
                print("  ! 끝에서 두 번째가 질문이 아니다 — 재시도", file=sys.stderr)
                continue
            if beats[-1]["beat"].rstrip().endswith("?"):
                print("  ! 마지막 박자는 여운이어야 한다 — 재시도", file=sys.stderr)
                continue
            return d
        why = []
        if len(beats) != BEATS:
            why.append(f"박자 {len(beats)}개")
        if not d.get("destination"):
            why.append("도착점 없음")
        if not ko_ok:
            why.append("외국어 혼입")
        if not all(b.get("beat") and b.get("visual") for b in beats):
            why.append("빈 박자/그림")
        print(f"  ! 트리트먼트 불량({', '.join(why) or '알 수 없음'}) — 재시도", file=sys.stderr)
    return {}


def main():
    p = argparse.ArgumentParser(description="이야기 줄기 트리트먼트 생성")
    p.add_argument("--title", required=True)
    p.add_argument("--author", default="")
    p.add_argument("--facts", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--no-web", action="store_true", help="웹 검색 보강을 쓰지 않는다")
    a = p.parse_args()

    facts = Path(a.facts).read_text(encoding="utf-8")
    # 소개형은 여기서 끝낸다. build() 도 같은 판정을 하지만, 그 전에 도는 웹 검색이
    # 쓸데없이 붙고 배치 로그에는 "실패"로 남아 없는 고장을 쫓게 된다.
    if re.search(r"\[포맷\]\s*소개형", facts):
        print("소개형 — 줄거리 재구성 금지. 줄기 없이 진행한다.")
        sys.exit(3)
    extra = "" if a.no_web else research(a.title, a.author, facts)
    t = build(facts, extra)
    if not t:
        sys.exit("트리트먼트 생성 실패")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"out": str(out), "logline": t.get("logline", ""),
                      "beats": len(t.get("beats", []))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
