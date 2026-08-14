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
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3.6:27b"
UA = "bard-treatment/1.0 (internal literary shorts pipeline)"
BEATS = 8


def ask(prompt: str, temperature: float = 0.7, ctx: int = 8192) -> str:
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
 "protagonist": "이름 없이 부르는 말 (예: 골방에 사는 젊은 남자)",
 "setting": "장소와 시대 (예: 1930년대 경성의 셋방과 그 골목)",
 "anchor": "English visual anchor for the person and place, 10-18 words",
 "palette": "English palette and light, 8-14 words",
 "beats": [
   {"n": 1, "beat": "그 장면에서 눈에 보이는 사건 하나 (한국어, 40자 이내)",
    "visual": "English shot description, 12-22 words"}
 ],
 "withheld": "결말에서 밝혀지는 것 — 대본에 절대 쓰지 않는다"
}"""


def build(facts: str, extra: str) -> dict:
    prompt = f"""너는 문학 작품을 짧은 영상으로 옮기는 구성작가다.
아래 자료에서 **이야기 하나**를 골라 여덟 박자짜리 트리트먼트를 만들어라.

[자료]
{facts}
{("[검색 자료]" + chr(10) + extra) if extra else ""}

[규칙]
- 작품 전체를 요약하지 마라. 인물 한 명이 겪는 **하나의 사건 줄기**를 고른다.
- 여덟 박자는 이어져야 한다. 장소가 바뀌면 어떻게 옮겨갔는지 앞 박자에 드러나야 한다.
- 시점을 바꾸지 마라. 처음부터 끝까지 같은 인물을 따라간다.
- 결말·반전의 정답은 절대 쓰지 마라. withheld 에 따로 적고 beats 에서는 감춘다.
- 반전 박자는 **그 직전에서 멈춘다**. 무엇을 보았는지 쓰지 말고, 보고 난 뒤의 행동만 적어라
  (나쁜 예: "아내와 내객을 보고 도망친다" / 좋은 예: "문틈으로 무언가를 보고 뒤돌아 달린다").
- logline 에도 결정적 사건을 적지 마라. 무엇이 걸려 있는지만 말한다.
- 1번 박자는 눈앞의 동작 하나로 연다. 설명하지 마라.
- 중반(4~5번)에 판이 뒤집히는 순간을 하나 둔다.
- 8번 박자는 답이 아니라 **질문**으로 닫는다.
- 자료에 없는 사건·인물·지명을 지어내지 마라.
- visual 은 영어로, 카메라가 보는 것만. 글자·간판·책·종이를 넣지 마라.
- anchor 와 palette 는 모든 장면에 그대로 붙일 문장이다. 인물 생김새와 빛을 고정한다.

[출력] 아래 JSON 하나만. 설명·코드펜스 금지. beats 는 정확히 {BEATS}개.
{SCHEMA_HINT}"""
    for attempt in range(3):
        raw = ask(prompt, temperature=0.7 + 0.1 * attempt)
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            continue
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        beats = d.get("beats") or []
        if len(beats) == BEATS and all(b.get("beat") and b.get("visual") for b in beats):
            for i, b in enumerate(beats, 1):
                b["n"] = i
            return d
        print(f"  ! 트리트먼트 형식 불량({len(beats)}박자) — 재시도", file=sys.stderr)
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
