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
        out[int(m.group(1))] = m.group(2).strip().strip('"*')
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
    return "명사종결"


# 문장별 목표 어미 계열. 모델에게 다양성을 맡기면 한 계열로 쏠리므로
# (한다체 금지 -> 전부 합니다체가 된 실측) 계열을 미리 배정해 강제한다.
# 마지막 문장은 마무리 문구("~있습니다") 때문에 합니다체 고정.
ENDING_PLAN = ["합니다체", "구어체", "명사종결", "합니다체", "구어체", "합니다체"]
CLASS_HINT = {
    "합니다체": "~습니다 / ~었습니다 로 끝내라",
    "구어체": "~었죠 / ~인데요 / ~네요 로 끝내라",
    "명사종결": "서술어 없이 명사로 끝내라 (예: '...만이 남은 검은 바다.')",
}


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
        if not (22 <= len(s) <= 42):
            issues.append((i, f"길이 {len(s)}자 (22~42 벗어남)"))
        for b in banned:
            if b in s:
                issues.append((i, f"금지어 '{b}'"))
        # 한글 본문 검사: 사고 텍스트("Here's a thinking...") 오염 차단
        if s and (re.search(r"[A-Za-z]", s) or
                  len(re.findall(r"[가-힣]", s)) < len(s) * 0.4):
            issues.append((i, "한국어 문장이 아님(라틴 문자/한글 비율)"))
    if ending_phrase and not sents[-1].rstrip(".!? ").endswith(ending_phrase.rstrip(".")):
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
    p.add_argument("--max-repair", type=int, default=4)
    a = p.parse_args()
    facts = open(a.facts, encoding="utf-8").read()
    banned = [b for b in a.banned.split(",") if b]
    n = a.scenes

    base_rules = f"""너는 한국어 낭독 대본 작가다. 아래 [원작 사실]의 내용만 사용하라. 없는 내용을 지어내지 마라.

[원작 사실]
{facts}

[문체 규칙 — 반드시 지켜라]
- 전체를 차분한 낭독체(~습니다체 계열)로 쓰되, 종결 형태를 문장마다 다르게 하라.
  허용 예: ~습니다 / ~었죠 / ~인데요 / ~것입니다 / 명사로 끝나는 문장 / 짧은 대사 인용.
- 같은 종결어미를 연이어 쓰지 마라. "~한다"체 금지.
- 문장별 종결 계열 배정을 정확히 따르라:
  S1 ~습니다 / S2 ~었죠·~인데요 / S3 명사로 끝냄 / S4 ~습니다 / S5 ~었죠·~네요 / S6 ~있습니다(고정)
- 문장 길이를 일부러 들쭉날쭉하게: 짧은 문장(22~28자)과 긴 문장(32~42자)을 섞어라.
- 첫 문장은 질문이 아니라 구체적 장면으로 시작한다.
- 각 문장은 장면 하나를 그린다. 요약하지 말고 보여줘라.
- 마지막 {n}번 문장은 반드시 "{a.ending}"로 끝난다.
- 금지어: {', '.join(banned)}"""

    draft = ask(base_rules + f"""

[출력 형식] S1: ~ S{n}: 만 출력. 설명 금지.
""")
    sents = parse_sentences(draft, n)

    # 스타일 패스: 리듬 관점 재작성 (길이 규칙을 반드시 포함 -- 빼면 문장이 부풀어 오른다)
    styled = ask(f"""아래 낭독 대본을 리듬 관점에서 고쳐 써라. 내용과 장면 순서는 유지하고,
종결어미 반복을 없애고, 문장 길이에 강약을 만들어라. 마지막 문장의 "{a.ending}" 마무리는 유지.
각 문장은 공백 포함 22~42자를 절대 넘기지 마라. 42자를 넘으면 실패다.
S1:~S{n}: 형식만 출력.

""" + "\n".join(f"S{i+1}: {s}" for i, s in enumerate(sents)))
    cand = parse_sentences(styled, n)
    if all(cand):
        sents = cand

    # 검증 -> 문장 단위 재수정 루프 (전체 재작성은 파싱이 불안정해 문장별로 처리)
    for attempt in range(a.max_repair):
        issues = validate(sents, a.ending, banned, plan=ENDING_PLAN[:n])
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
    proofed = ask("아래 문장들의 맞춤법과 어색한 표현(비문)만 고쳐라. 종결어미와 뜻은 유지하고, S1:~S%d: 형식으로만 출력하라.\n\n" % n
                  + "\n".join(f"S{i+1}: {s}" for i, s in enumerate(sents)), temperature=0.3)
    cand = parse_sentences(proofed, n)
    for i in range(n):
        if cand[i] and not validate([cand[i]], "", banned, plan=[ENDING_PLAN[i]]):
            sents[i] = cand[i]

    issues = validate(sents, a.ending, banned, plan=ENDING_PLAN[:n])
    result = {"title": a.title, "sentences": sents,
              "endings": [ending_of(s) for s in sents],
              "passed": not issues, "issues": [f"S{i+1}: {m}" for i, m in issues]}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    sys.exit(0 if not issues else 2)


if __name__ == "__main__":
    main()
