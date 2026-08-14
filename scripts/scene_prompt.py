#!/usr/bin/env python3
"""한국어 내레이션 문장 -> 영어 장면 묘사(이미지 프롬프트).

Qwen-Image 는 프롬프트에 한글이 있으면 **그 글자를 그림 안에 써 넣는다**.
야간 배치가 내레이션 문장을 그대로 프롬프트로 넘기면서 화면에 뭉개진 한글 자막이
얹혔다(실측). 손으로 만들던 초기 작품들이 이 문제가 없던 이유는 영어 장면 묘사를
썼기 때문이다. 그래서 그림 프롬프트는 영어로만 만든다.

번역이 아니라 **보이는 것만** 뽑는다 — 장소·사물·빛·시간대·카메라. 내레이션의
서술이나 감정어는 그림에 옮길 수 없으므로 버린다.

사용:
  venv/bin/python scripts/scene_prompt.py --narration output/x/narration_night.json --index 3
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3.6:27b"

# 모델이 한글을 남기면 그림에 글자가 박힌다. 최후 방어선.
HANGUL = re.compile(r"[가-힣]")
FALLBACK = "quiet empty interior, soft daylight, weathered surfaces, still life"


def ask(prompt: str, temperature: float = 0.4) -> str:
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "think": False,
                       "options": {"temperature": temperature, "num_ctx": 4096}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    t = json.load(urllib.request.urlopen(req, timeout=600)).get("response", "")
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()


def from_treatment(tre: dict, index: int) -> str:
    """트리트먼트가 있으면 그 박자의 영어 묘사를 쓴다.

    장면마다 모델에게 새로 묘사를 시키면 인물 생김새와 빛이 매번 달라진다(실측:
    다락방·잠든 남자·책 읽는 노인). 앵커와 팔레트를 모든 장면에 그대로 붙여 고정한다.
    """
    beats = tre.get("beats") or []
    if not 1 <= index <= len(beats):
        return ""
    shot = (beats[index - 1].get("visual") or "").strip()
    if not shot or HANGUL.search(shot):
        return ""
    parts = [shot, (tre.get("anchor") or "").strip(), (tre.get("palette") or "").strip()]
    return ", ".join(x.rstrip(".") for x in parts if x)[:400]


def to_scene(sentence: str, context: str = "") -> str:
    """문장에서 그릴 수 있는 것만 영어로 뽑는다. 실패하면 빈 문자열."""
    s = sentence.replace("*", "").strip()
    out = ask(f"""Convert this Korean narration line into a short English image prompt.

Rules:
- Describe ONLY what a camera could see: place, objects, materials, light, time of day.
- Drop feelings, judgements, and anything abstract. Never translate word by word.
- No personal names. If a person appears, describe them plainly ("a man in a worn coat").
- 12~25 words, comma-separated fragments. No sentences, no quotes, no Korean.
- Never mention writing, letters, signs, captions, or paper with text.

{("Story world: " + context) if context else ""}
Korean line: {s}

Output the prompt only.""")
    line = next((x.strip() for x in out.splitlines() if x.strip()), "")
    line = line.strip('"').strip()
    if not line or HANGUL.search(line) or len(line) < 12:
        return ""
    return line[:300]


def main():
    p = argparse.ArgumentParser(description="문장 -> 영어 장면 묘사")
    p.add_argument("--narration", required=True)
    p.add_argument("--index", type=int, required=True, help="1부터")
    p.add_argument("--context", default="", help="작품 세계 한 줄 (선택)")
    p.add_argument("--treatment", default="", help="이야기 줄기 JSON (있으면 우선)")
    a = p.parse_args()
    sents = json.loads(Path(a.narration).read_text(encoding="utf-8"))["sentences"]
    if not 1 <= a.index <= len(sents):
        sys.exit(f"index 범위 초과: {a.index}")
    scene = ""
    if a.treatment and Path(a.treatment).exists():
        scene = from_treatment(json.loads(Path(a.treatment).read_text(encoding="utf-8")), a.index)
    if not scene:
        scene = to_scene(sents[a.index - 1], a.context)
    if not scene:
        # 실패해도 배치를 멈추지 않는다. 한글 없는 최소 프롬프트로 대체한다.
        print("  ! 장면 묘사 실패 — 기본 프롬프트 사용", file=sys.stderr)
        scene = FALLBACK
    print(scene)


if __name__ == "__main__":
    main()
