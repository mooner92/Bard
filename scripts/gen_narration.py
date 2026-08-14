#!/usr/bin/env python3
"""Ollama 로 한국어 6문장 내레이션을 만들고, 2차 교정 패스까지 돌린다.

생성 -> 규칙 검증 -> (실패 시 피드백 재시도) -> 문법 교정 -> 재검증.
결과는 JSON 으로 저장한다.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ollama_util import ask  # noqa: E402

MIN_CH, MAX_CH = 30, 34

SPECS = {
    "mobydick": {
        "title": "모비딕",
        "ending": "는 소설 모비딕에서 만날 수 있습니다",
        "facts": """- 허먼 멜빌이 1851년에 쓴 소설 '모비딕'이다.
- 화자는 이슈메일이며, 그는 포경선 피쿼드호에 오른다.
- 선장 에이해브는 흰 향유고래 모비딕에게 한쪽 다리를 잃었고, 고래뼈로 만든 의족을 짚고 갑판을 걷는다.
- 에이해브는 복수심에 사로잡혀 배와 선원들을 사냥으로 몰아붙인다.
- 작살잡이 퀴퀘그를 비롯해 여러 나라에서 온 선원들이 함께 탄다.
- 사흘간의 추격 끝에 피쿼드호는 침몰하고, 이슈메일 혼자 살아남는다.
- 흰 고래는 인간이 끝내 헤아릴 수 없는 자연을 상징하고, 에이해브는 그것에 맞서는 인간의 집착을 상징한다.""",
        "extra": """- 작살은 반드시 '작살'이라고 써라. '목검' 같은 다른 무기는 절대 쓰지 마라.
- 이야기가 누가 봐도 모비딕임을 알 수 있어야 한다. 에이해브, 고래뼈 의족, 흰 고래, 집착이 반드시 드러나야 한다.
- 1번 문장은 질문이 아니라 구체적인 장면 묘사로 시작하라. (예: 갑판, 안개, 고래뼈 의족 소리 등)""",
        "must_include": [["에이해브", "에이하브"], ["고래뼈"], ["흰 고래", "흰고래", "흰 향유고래"]],
        "banned": ["목검", "칼", "검을"],
    },
    "kafka": {
        "title": "변신",
        "ending": "는 소설 변신에서 만날 수 있습니다",
        "facts": """- 프란츠 카프카가 1915년에 쓴 소설 '변신'이다.
- 외판원 그레고르 잠자는 어느 날 아침 흉측한 벌레로 변한 자신을 발견한다.
- 그는 기차를 놓친 걱정과 가족의 빚을 갚아야 한다는 걱정에 시달린다.
- 아버지, 어머니, 여동생 그레테는 처음에 충격을 받고 이내 혐오한다.
- 그레테는 처음에는 그에게 먹을 것을 가져다주지만 나중에는 등을 돌린다.
- 그레고르는 방에 갇히고, 아버지가 던진 사과에 상처를 입는다.
- 결국 그레고르는 죽고, 가족은 안도하며 시골로 나들이를 떠난다.""",
        "extra": """- 반드시 실제 대사를 1~2개 넣어라. 큰따옴표로 감싼 짧은 구어체 한국어 대사여야 한다.
  (예: 문 밖에서 가족이 부르는 말, 또는 그레고르의 속마음)
- 대사는 실제 사람이 말하듯 자연스럽고 생생해야 한다. 번역투를 피하라.
- 1번 문장은 질문이 아니라 구체적인 장면 묘사로 시작하라.
- 딱딱한 요약이 아니라 듣는 사람이 빠져들도록 흥미진진하게 써라.""",
        "must_include": [["그레고르"], ["벌레"], ["“", "\""]],
        "banned": [],
    },
}

GEN_TMPL = """너는 한국어 영상 내레이션 작가다. 아래 사실만 근거로 쓰고, 사실에 없는 내용은 절대 지어내지 마라.

[사실]
{facts}

[추가 지시]
{extra}

[형식 규칙]
- 정확히 6문장을 쓴다.
- 각 문장은 공백 포함 {minch}~{maxch}자여야 한다. 이 길이를 반드시 지켜라.
- 문장은 자연스러운 한국어 구어 내레이션 문체로 쓴다. 조사(은/는, 이/가, 을/를)를 정확히 써라.
- 자동사와 타동사를 구분하라. 예: 배가 '흔들린다'(O) / 배가 '흔든다'(X).
- 6번 문장은 반드시 정확히 이 글자열로 끝나야 한다: "{ending}."
  즉 바로 앞이 '-는'으로 끝나는 관형형 동사여야 한다.
  올바른 예: "...을 그리는 소설 ...에서 만날 수 있습니다." / "...을 보여주는 소설 ...에서 만날 수 있습니다."
  틀린 예: "...을 그린 소설 ...에서 만날 수 있습니다." (X, '그린'은 '-는'이 아니다)
  틀린 예: "...을 다룬 소설 ...에서 만날 수 있습니다." (X)
- 설명이나 해설을 덧붙이지 말고 아래 형식 그대로만 출력하라.

[출력 형식]
S1: <문장>
S2: <문장>
S3: <문장>
S4: <문장>
S5: <문장>
S6: <문장>
"""

FIX_TMPL = """아래 한국어 문장들의 맞춤법, 조사, 자동사/타동사 오류만 고쳐라.

[절대 규칙]
- 의미를 바꾸지 마라. 새로운 내용을 추가하지 마라.
- 각 문장의 길이를 공백 포함 {minch}~{maxch}자 범위 안에 유지하라.
- 6번 문장의 끝맺음 "{ending}."는 그대로 두어라.
- 큰따옴표로 된 대사가 있으면 그대로 살려라.
- 아무 설명도 쓰지 말고 S1~S6 형식으로만 출력하라.

[교정할 문장]
{sentences}
"""

LINE_RE = re.compile(r"^\s*S([1-6])\s*[:.]\s*(.+?)\s*$", re.M)


def parse(text):
    found = {}
    for m in LINE_RE.finditer(text):
        found[int(m.group(1))] = m.group(2).strip().strip("*").strip()
    return [found[i] for i in range(1, 7)] if len(found) == 6 else None


def validate(sents, spec):
    errs = []
    for i, s in enumerate(sents, 1):
        n = len(s)
        if not (MIN_CH <= n <= MAX_CH):
            errs.append(f"S{i} 길이 {n}자 (필요: {MIN_CH}~{MAX_CH}자): {s}")
        if re.search(r"[A-Za-z]{3,}", s):
            errs.append(f"S{i} 에 영문이 섞였다: {s}")
        if re.search(r"[一-鿿]", s):
            errs.append(f"S{i} 에 한자가 섞였다: {s}")
    if sents[0].rstrip().endswith("?"):
        errs.append("S1 이 질문으로 끝난다. 구체적인 장면 묘사여야 한다.")
    if not sents[5].rstrip().rstrip(".").endswith(spec["ending"]):
        errs.append(f"S6 이 \"{spec['ending']}.\" 로 끝나지 않는다: {sents[5]}")
    body = " ".join(sents)
    for group in spec["must_include"]:
        if not any(k in body for k in group):
            errs.append(f"필수 요소 누락: {group[0]}")
    for b in spec["banned"]:
        if b in body:
            errs.append(f"금지 단어 사용: {b}")
    return errs


def run(key, attempts=12, seed_temp=0.75):
    spec = SPECS[key]
    base = GEN_TMPL.format(facts=spec["facts"], extra=spec["extra"],
                           ending=spec["ending"], minch=MIN_CH, maxch=MAX_CH)
    prompt = base
    best, best_err = None, 10 ** 6
    for i in range(attempts):
        temp = seed_temp if i == 0 else 0.5
        raw = ask(prompt, temperature=temp, num_predict=900)
        sents = parse(raw)
        if not sents:
            print(f"[{key}] 시도 {i+1}: 형식 파싱 실패", flush=True)
            prompt = base + "\n\n반드시 S1~S6 여섯 줄만 출력하라."
            continue
        errs = validate(sents, spec)
        lens = [len(s) for s in sents]
        print(f"[{key}] 시도 {i+1}: 길이 {lens} 오류 {len(errs)}", flush=True)
        for e in errs:
            print("    -", e, flush=True)
        if not errs:
            best = sents
            break
        if best is None or len(errs) < best_err:
            best, best_err = sents, len(errs)
        prompt = (base + "\n\n[직전 시도]\n"
                  + "\n".join(f"S{j+1}: {s}" for j, s in enumerate(sents))
                  + "\n\n[직전 시도의 문제점 - 반드시 고쳐서 다시 써라]\n"
                  + "\n".join("- " + e for e in errs))
    if best is None:
        raise SystemExit(f"[{key}] 내레이션 생성 실패")
    return best, spec


def proofread(sents, spec):
    text = "\n".join(f"S{i+1}: {s}" for i, s in enumerate(sents))
    raw = ask(FIX_TMPL.format(sentences=text, ending=spec["ending"],
                              minch=MIN_CH, maxch=MAX_CH),
              temperature=0.2, num_predict=900)
    fixed = parse(raw)
    if not fixed:
        print("교정 패스 파싱 실패 -> 원문 유지", flush=True)
        return sents
    errs = validate(fixed, spec)
    if errs:
        print(f"교정본이 규칙 {len(errs)}건 위반 -> 원문 유지", flush=True)
        for e in errs:
            print("    -", e, flush=True)
        return sents
    return fixed


ONE_TMPL = """너는 한국어 영상 내레이션 작가다. 아래 문장 하나만 고쳐 쓴다.

[대상 작품] {title}
[전체 내레이션 흐름]
{context}

[고쳐야 할 문장] (현재 {curlen}자)
{sentence}

[고쳐야 할 이유]
{problems}

[규칙]
- 뜻과 장면은 그대로 유지하되, 공백 포함 정확히 {target}자가 되도록 표현을 늘리거나 줄여라.
- 한자와 영문은 절대 쓰지 마라. 순한국어와 한글만 쓴다.
- 조사와 자동사/타동사를 정확히 써라.
- 큰따옴표 안의 대사가 있으면 자연스러운 구어체로 살려라.
- 설명 없이 고친 문장 한 줄만 출력하라. 번호나 따옴표로 감싸지 마라.
"""


def repair_one(sent, idx, problems, spec, sents, target=32, tries=6):
    ctx = "\n".join(f"S{j+1}: {s}" for j, s in enumerate(sents))
    best = sent
    for t in range(tries):
        raw = ask(ONE_TMPL.format(title=spec["title"], context=ctx,
                                  sentence=sent, curlen=len(sent),
                                  problems="\n".join("- " + p for p in problems),
                                  target=target),
                  temperature=0.4 + 0.1 * t, num_predict=300)
        cand = raw.strip().splitlines()[0].strip() if raw.strip() else ""
        cand = re.sub(r"^S?\d\s*[:.]\s*", "", cand).strip().strip('*').strip()
        if not cand:
            continue
        bad = []
        if not (MIN_CH <= len(cand) <= MAX_CH):
            bad.append(f"길이 {len(cand)}자")
        if re.search(r"[一-鿿]", cand):
            bad.append("한자 포함")
        if re.search(r"[A-Za-z]{3,}", cand):
            bad.append("영문 포함")
        if idx == 6 and not cand.rstrip().rstrip(".").endswith(spec["ending"]):
            bad.append("끝맺음 불일치")
        print(f"    repair S{idx} 시도 {t+1}: ({len(cand)}자) {cand}"
              + (f"  <- {', '.join(bad)}" if bad else "  <- OK"), flush=True)
        if not bad:
            return cand
        best = cand if abs(len(cand) - target) < abs(len(best) - target) else best
    return best


def repair(sents, spec, rounds=4):
    sents = list(sents)
    for r in range(rounds):
        errs = validate(sents, spec)
        if not errs:
            return sents
        print(f"\n[수리 라운드 {r+1}] 남은 오류 {len(errs)}", flush=True)
        for e in errs:
            print("  -", e, flush=True)
        # 문장별 문제 모으기
        per = {}
        for e in errs:
            m = re.match(r"S([1-6])", e)
            if m:
                per.setdefault(int(m.group(1)), []).append(e)
        # 문장에 매이지 않은 오류(필수 요소 누락 등)는 해당 요소가 들어갈
        # 만한 문장(가장 앞 문장)에 붙인다.
        for e in errs:
            if not re.match(r"S([1-6])", e):
                per.setdefault(1, []).append(e + " -> 이 문장에 반드시 넣어라")
        for idx in sorted(per):
            sents[idx - 1] = repair_one(sents[idx - 1], idx, per[idx],
                                        spec, sents)
    return sents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key", choices=sorted(SPECS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--repair-from", help="기존 JSON 을 읽어 수리만 수행")
    a = ap.parse_args()

    if a.repair_from:
        spec = SPECS[a.key]
        sents = json.load(open(a.repair_from, encoding="utf-8"))["sentences"]
        print("=== 수리 입력 ===")
        for s in sents:
            print(f"  ({len(s)}자) {s}")
        sents = repair(sents, spec)
        fixed = proofread(sents, spec)
        print("\n=== 최종 ===")
        ok = validate(fixed, spec)
        for s in fixed:
            print(f"  ({len(s)}자) {s}")
        print("남은 오류:", ok if ok else "없음")
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        json.dump({"key": a.key, "sentences": fixed},
                  open(a.out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print("저장:", a.out)
        return

    sents, spec = run(a.key)
    print("\n=== 1차 ===")
    for s in sents:
        print(f"  ({len(s)}자) {s}")
    sents = repair(sents, spec)
    fixed = proofread(sents, spec)
    print("\n=== 교정 후 ===")
    for s in fixed:
        print(f"  ({len(s)}자) {s}")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"key": a.key, "sentences": fixed}, f,
                  ensure_ascii=False, indent=2)
    print(f"\n저장: {a.out}")


if __name__ == "__main__":
    main()
