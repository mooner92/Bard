#!/usr/bin/env python3
"""대본 관문 — 그림을 그리기 전에 통과 여부를 판정한다.

하네스는 문제를 **찾아내지만**, 수리에 실패해도 대본을 그대로 남긴다. 그 대본으로
배치가 키프레임·클립을 만들면 두 시간짜리 GPU 작업이 통째로 버려진다(실측:
"A8 S1~S2의 안전 밸브를 확인하세요"가 1번 문장으로 박힌 채 진행될 뻔했다).

그래서 ① 대본 뒤에 관문을 둔다. 여기서 막히면 배치가 대본을 지우고 다시 쓴다.
**치명적인 것만** 막는다 — 문체 잔여(어미 계열 불일치 등)는 아침 검수로 넘긴다.

치명 판정
  1. 지시어·규칙 코드 누출        (낭독될 문장이 아니다)
  2. 길이 상한 +5자 초과          (48자·80자 문장이 나온 실측)
  3. 전체 분량 예산 이탈           (영상이 60초를 넘거나 너무 짧아진다)
  4. 마무리 문구 중복·누락         (끝맺음이 깨진다)
  5. 문장 누락 / 한국어 아님

사용:
  venv/bin/python scripts/gate_script.py --narration output/x/narration_night.json \
      --ending "소설 X에서 만날 수 있습니다" --maxlen 38
"""
import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from write_script import leak_issues  # noqa: E402

BUDGET_MIN, BUDGET_MAX = 245, 275     # write_script 의 예산과 같은 값
# 예산은 글자 수로 적혀 있지만 재려는 것은 **길이**다. 245~275 는 0.206초/자를
# 전제로 잡은 값이고, 그건 쉼표가 잦은 모델 문장의 속도다. 사람이 쓴 문장은
# 호흡이 적어 0.169초/자로 읽힌다(실측: 동물농장 268자가 45.4초). 같은 55초를
# 채우려면 글자가 더 필요하므로 문체별로 예산을 나눈다.
# 마지막 문장이 안내만 맡게 되면서 전체 글자 수가 줄었다. 길이는 발화 속도가
# 맞추므로 여기서는 넓게만 잡는다 — 속도 레버가 닿는 범위면 충분하다.
# 소희(Qwen3-TTS)는 0.161초/자로 읽는다 — Azure(0.206)보다 한참 빠르다(실측:
# 같은 263자 대본이 54초에서 42초가 됐다). 50초를 채우려면 310자쯤 필요하다.
# 글자를 늘리는 것은 말을 늘어뜨리는 것과 다르다 — 이야기를 더 담으라는 뜻이다.
HAND_MIN, HAND_MAX = 300, 350


def spoiler_words(work_dir: Path) -> set:
    """트리트먼트가 감추기로 한 것에서 핵심 낱말을 뽑는다."""
    f = work_dir / "treatment.json"
    if not f.exists():
        return set()
    try:
        t = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    w = t.get("withheld", "")
    stop = {"결말", "사실", "이야기", "장면", "인물", "작품", "내용", "부분"}
    # 박자에 이미 나온 낱말은 감춰야 할 것이 아니다. 이걸 빼지 않으면 "그가",
    # "그림을" 같은 흔한 말이 스포일러로 잡혀 멀쩡한 대본이 반려된다(실측:
    # 폭풍의 언덕이 "그가, 돌아온" 두 낱말로 불합격했다).
    shown = set()
    for b in t.get("beats", []):
        shown |= set(re.findall(r"[가-힣]{2,}", b.get("beat", "")))
    return {x for x in re.findall(r"[가-힣]{2,}", w) if x not in stop and x not in shown}


def gate(nar: dict, ending: str, maxlen: int, spoil: set = frozenset()) -> list:
    """치명 결함 목록. 비어 있으면 통과."""
    sents = nar.get("sentences") or []
    bad = []
    # 8문장 고정에서 가변 조각으로 바뀌었다. 한 문장을 여러 컷에 나눠 실으면
    # 조각 수가 곧 컷 수가 된다 — 3~6초짜리 컷 12~14개를 겨눈다.
    if not 8 <= len(sents) <= 16 or not all(s.strip() for s in sents):
        return [f"조각 {len([s for s in sents if s.strip()])}개 (8~16)"]

    for i, m in leak_issues(sents):
        bad.append(f"S{i+1} {m.split('—')[0].strip()}")

    over = [(i + 1, len(s)) for i, s in enumerate(sents) if len(s) > maxlen + 5]
    if over:
        bad.append("길이 초과 " + ", ".join(f"S{i}({n}자)" for i, n in over))

    lo, hi = ((HAND_MIN, HAND_MAX) if nar.get("author") == "hand"
              else (BUDGET_MIN, BUDGET_MAX))
    total = sum(len(s) for s in sents)
    if not lo - 15 <= total <= hi + 15:
        bad.append(f"전체 {total}자 (예산 {lo}~{hi})")

    # 끝에서 두 번째는 질문, 마지막은 안내만. 트리트먼트에는 이 검사가 있는데
    # 대본 관문에 없어서 모델이 어겨도 통과했다(실측: 노트르담 끝-1 이
    # "저 손이 내미는 것 같았죠" — 질문 없이 발행됐다).
    if len(sents) >= 2 and not sents[-2].rstrip().rstrip('."').endswith("?"):
        bad.append("끝에서 두 번째가 질문이 아님")
    if len(sents) >= 1 and "?" in sents[-1]:
        bad.append("마지막 문장에 질문이 있음 — 안내만")

    if ending:
        norm = re.sub(r"[<>《》〈〉「」『』()\[\]]", "", sents[-1]).rstrip(".!? ")
        e = ending.rstrip(".!? ")
        if not norm.endswith(e):
            bad.append("마무리 문구 누락")
        elif norm.count(e[:8]) > 1 or norm.count(e[-8:]) > 1:
            bad.append("마무리 문구 중복")

    # 한자·가나가 한 글자라도 섞이면 낭독이 깨진다. 한글 비율만 보던 아래 검사는
    # 대부분이 한글인 문장을 통과시켰다(실측: 상록수 S1 의 "*青年教师*").
    for i, s in enumerate(sents):
        if re.search(r"[\u4e00-\u9fff\u3040-\u30ff]", s):
            bad.append(f"S{i+1} 한자·가나 혼입")

    for i, s in enumerate(sents):
        core = re.sub(r"\b[A-Z]{2,5}\b", "", s)
        if core and len(re.findall(r"[가-힣]", core)) < len(core) * 0.4:
            bad.append(f"S{i+1} 한국어 문장 아님")

    # 감추기로 한 결말이 대본에 새어 나왔는지 (트리트먼트 withheld 와 낱말 대조)
    body = " ".join(sents)
    hit = sorted(w for w in spoil if w in body)
    if len(hit) >= 2:
        bad.append(f"결말 노출 '{', '.join(hit[:3])}'")
    return bad


def main():
    p = argparse.ArgumentParser(description="대본 관문")
    p.add_argument("--narration", required=True)
    p.add_argument("--ending", default="")
    p.add_argument("--maxlen", type=int, default=38)
    a = p.parse_args()
    f = Path(a.narration)
    if not f.exists():
        print("대본 없음")
        sys.exit(1)
    bad = gate(json.loads(f.read_text(encoding="utf-8")), a.ending, a.maxlen,
               spoiler_words(f.parent))
    if bad:
        print("관문 불합격: " + " / ".join(bad))
        sys.exit(1)
    print("관문 통과")


if __name__ == "__main__":
    main()
