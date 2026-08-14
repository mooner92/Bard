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


def gate(nar: dict, ending: str, maxlen: int) -> list:
    """치명 결함 목록. 비어 있으면 통과."""
    sents = nar.get("sentences") or []
    bad = []
    if len(sents) != 8 or not all(s.strip() for s in sents):
        return [f"문장 {len([s for s in sents if s.strip()])}/8"]

    for i, m in leak_issues(sents):
        bad.append(f"S{i+1} {m.split('—')[0].strip()}")

    over = [(i + 1, len(s)) for i, s in enumerate(sents) if len(s) > maxlen + 5]
    if over:
        bad.append("길이 초과 " + ", ".join(f"S{i}({n}자)" for i, n in over))

    total = sum(len(s) for s in sents)
    if not BUDGET_MIN - 15 <= total <= BUDGET_MAX + 15:
        bad.append(f"전체 {total}자 (예산 {BUDGET_MIN}~{BUDGET_MAX})")

    if ending:
        norm = re.sub(r"[<>《》〈〉「」『』()\[\]]", "", sents[-1]).rstrip(".!? ")
        e = ending.rstrip(".!? ")
        if not norm.endswith(e):
            bad.append("마무리 문구 누락")
        elif norm.count(e[:8]) > 1 or norm.count(e[-8:]) > 1:
            bad.append("마무리 문구 중복")

    for i, s in enumerate(sents):
        core = re.sub(r"\b[A-Z]{2,5}\b", "", s)
        if core and len(re.findall(r"[가-힣]", core)) < len(core) * 0.4:
            bad.append(f"S{i+1} 한국어 문장 아님")
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
    bad = gate(json.loads(f.read_text(encoding="utf-8")), a.ending, a.maxlen)
    if bad:
        print("관문 불합격: " + " / ".join(bad))
        sys.exit(1)
    print("관문 통과")


if __name__ == "__main__":
    main()
