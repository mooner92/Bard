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


PERSONAS_FILE = Path(__file__).resolve().parent.parent / "works" / "personas.json"


def personas() -> dict:
    """인물·장소 생김새 사전. 없으면 빈 사전으로 돌아간다."""
    try:
        return json.loads(PERSONAS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _fit(parts, limit=1900) -> str:
    """쉼표 경계에서 자른다. 낱말 중간이 잘리면 모델이 엉뚱하게 읽는다.

    한도 1900: 영상 모델의 텍스트 창은 UMT5 512토큰(영문 약 2000자)이다.
    2600자로 조립하던 동안 두 번째 인물의 묘사가 반쯤 잘리고 화풍 접미가
    창 밖으로 밀려났다(실측: 빨간 모자 — 늑대의 귀가 소녀 머리에, 호박색
    눈이 베개의 털뭉치에 붙었다). 1900자 + 화풍 접미 ≈ 500토큰으로 창 안에 든다."""
    out = ""
    for p in parts:
        p = (p or "").rstrip(".").strip()
        if not p:
            continue
        nxt = p if not out else f"{out}, {p}"
        if len(nxt) > limit:
            break
        out = nxt
    return out


KIND_CAP = {"인물": 340, "소품": 180, "장소": 250, "지면": 220, "물": 220, "배경": 160}

def load_assets(d) -> dict:
    """작품 전용 자산(md) 사전. 서식은 docs/PROMPTCRAFT.md §8."""
    import pathlib, re as _re
    out = {}
    root = pathlib.Path(d)
    if not root.is_dir():
        return out
    for f in sorted(root.glob("*.md")):
        t = f.read_text(encoding="utf-8")
        m = _re.match(r"---\n(.*?)\n---\n?(.*)", t, _re.S)
        if not m:
            continue
        head, body = m.groups()
        meta = dict(_re.findall(r"^(\w+):\s*(.+)$", head, _re.M))
        meta.setdefault("name", f.stem)
        meta["detail"] = " ".join(body.split())
        out[meta["name"]] = meta
    return out


def from_treatment(tre: dict, index: int, v3: bool = False) -> str:
    """트리트먼트가 있으면 그 박자의 영어 묘사를 쓴다.

    장면마다 모델에게 새로 묘사를 시키면 인물 생김새와 빛이 매번 달라진다(실측:
    다락방·잠든 남자·책 읽는 노인). 앵커와 팔레트를 모든 장면에 그대로 붙여 고정한다.

    앵커는 주인공 **한 사람**을 적는 자리다. 두 번째 인물이 나오는 컷에서는 그를
    적을 칸이 없어 모델이 앵커를 그 사람에게도 입혔다 — 춘향전에서 이도령이
    댕기머리 처녀로 나와 여자 둘이 마주 앉았고, 묘사가 아예 없던 사또는 '조선
    관리'의 가장 흔한 그림인 임금이 되었다(붉은 곤룡포에 원형 금색 보).

    그래서 박자마다 cast 로 그 컷에 나오는 인물·장소를 열거하고 생김새는
    works/personas.json 에서 가져온다. cast 가 있으면 앵커 대신 그것을 쓴다 —
    cast 에는 주인공도 함께 적기 때문이다. cast 가 없는 옛 작품은 그대로 앵커로 간다.
    """
    beats = tre.get("beats") or []
    if not 1 <= index <= len(beats):
        return ""
    beat = beats[index - 1]
    shot = (beat.get("visual") or "").strip()
    if not shot or HANGUL.search(shot):
        return ""

    cast = beat.get("cast") or []
    if cast:
        # 작품 전용 배역은 트리트먼트에 personas 로 적는다. 같은 열쇠면 그쪽이 이긴다.
        book = {**personas(), **(tre.get("personas") or {})}
        assets = load_assets(tre.get("assets_dir", ""))
        who = []
        # 어떤 인물을 참조로 보낼지는 박자의 refs 가 정한다. 없으면 인물 전원.
        # 실측: 2인 참조는 확률적으로 한 명이 탈락한다(5컷 중 2컷 — 도둑이
        # 넥타이 차림 현대인으로) — 연약한 정체성은 참조 1장 + 텍스트가 안전.
        ref_set = set(beat.get("refs") or
                      [k for k in cast if (assets.get(k) or {}).get("kind") == "인물"])
        people_ref = False
        for key in cast:
            a = assets.get(key)
            if a:
                if v3 and a.get("kind") == "인물" and key in ref_set:
                    # 참조로 가는 인물만 글에서 뺀다(§9)
                    people_ref = True
                    continue
                cap = KIND_CAP.get(a.get("kind", ""), 250)
                spec = (a.get("spec") or "").strip().rstrip(".")
                det = _fit((a.get("detail") or "").split(", "), max(cap - len(spec) - 2, 0))
                who.append(f"{spec}, {det}" if det else spec)
                continue
            entry = book.get(key)
            if not entry:
                print(f"  ! 사전에 없는 배역: {key}", file=sys.stderr)
                continue
            d = (entry.get("desc") if isinstance(entry, dict) else str(entry)).strip()
            if d and not HANGUL.search(d):
                # 전문은 사전용이다. 컷에는 앞 340자(쉼표 경계)만 싣는다 —
                # 배역의 첫 340자에 실루엣·복색 핵심을 몰아 쓰는 이유.
                who.append(_fit(d.split(", "), 340))
        parts = [shot, *who, (tre.get("palette") or "").strip()]
        if v3 and people_ref:
            # 실측: 근접 컷에서 시트의 크림색 무지 배경이 장면을 밀어냈다 —
            # 배경 우선 절을 앞세워 참조에서는 인물 생김새만 가져오게 한다.
            parts.insert(1, "repaint the entire background and setting exactly as "
                            "described in this prompt — take from the reference images "
                            "only the characters' appearance, never their plain background")
    else:
        # 사람이 없어야 할 컷에까지 앵커를 붙이면 모델이 사람을 밀어 넣는다
        # (실측: "텅 빈 갑판"에 선원이 서 있었다). 그런 박자는 anchor: false 로 끈다.
        use_anchor = beat.get("anchor", True)
        parts = [shot,
                 (tre.get("anchor") or "").strip() if use_anchor else "",
                 (tre.get("palette") or "").strip()]
    return _fit(parts)


# 모든 장면에 같은 문장을 넣으면 여덟 컷이 똑같이 흔들린다. 박자마다 무엇이
# 움직이는지 적어야 화면이 산다. 트리트먼트에 없으면 이 값으로 돌아간다.
MOTION_DEFAULT = "gentle continuous motion in the scene, slow camera drift"


def motion_from_treatment(tre: dict, index: int) -> str:
    """그 박자의 움직임 지시. 없으면 빈 문자열."""
    beats = tre.get("beats") or []
    if not 1 <= index <= len(beats):
        return ""
    m = (beats[index - 1].get("motion") or "").strip()
    # 상세 작법(300자 안팎)이 잘리지 않게 여유를 둔다
    return "" if HANGUL.search(m) else m[:450]


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
    p.add_argument("--narration", default="")
    p.add_argument("--index", type=int, required=True, help="1부터")
    p.add_argument("--motion", action="store_true",
                   help="장면 묘사 대신 그 박자의 움직임 지시를 낸다 (I2V 용)")
    p.add_argument("--context", default="", help="작품 세계 한 줄 (선택)")
    p.add_argument("--treatment", default="", help="이야기 줄기 JSON (있으면 우선)")
    p.add_argument("--v3", action="store_true",
                   help="인물은 참조 이미지가 진다 — 글에서 인물 묘사를 뺀다(§9)")
    p.add_argument("--list-refs", action="store_true",
                   help="그 박자 cast 의 인물 시트 경로를 --ref 인자 형태로 낸다")
    p.add_argument("--sheets", default="", help="--list-refs 용 시트 폴더")
    a = p.parse_args()
    if a.list_refs:
        tre = json.loads(Path(a.treatment).read_text(encoding="utf-8"))
        assets = load_assets(tre.get("assets_dir", ""))
        beats = tre.get("beats") or []
        out = []
        if 1 <= a.index <= len(beats):
            beat = beats[a.index - 1]
            ref_set = set(beat.get("refs") or
                          [k for k in (beat.get("cast") or [])
                           if (assets.get(k) or {}).get("kind") == "인물"])
            for key in beat.get("cast") or []:
                aa = assets.get(key)
                if aa and aa.get("kind") == "인물" and key in ref_set:
                    f = Path(a.sheets) / f"{key}_00001_.png"
                    if f.exists():
                        out += ["--ref", str(f)]
        print(" ".join(out))
        return
    if a.motion:
        tre = (json.loads(Path(a.treatment).read_text(encoding="utf-8"))
               if a.treatment and Path(a.treatment).exists() else {})
        print(motion_from_treatment(tre, a.index) or MOTION_DEFAULT)
        return
    if not a.narration:
        sys.exit("--narration 이 필요하다")
    sents = json.loads(Path(a.narration).read_text(encoding="utf-8"))["sentences"]
    if not 1 <= a.index <= len(sents):
        sys.exit(f"index 범위 초과: {a.index}")
    scene = ""
    if a.treatment and Path(a.treatment).exists():
        scene = from_treatment(json.loads(Path(a.treatment).read_text(encoding="utf-8")),
                               a.index, v3=a.v3)
    if not scene:
        scene = to_scene(sents[a.index - 1], a.context)
    if not scene:
        # 실패해도 배치를 멈추지 않는다. 한글 없는 최소 프롬프트로 대체한다.
        print("  ! 장면 묘사 실패 — 기본 프롬프트 사용", file=sys.stderr)
        scene = FALLBACK
    print(scene)


if __name__ == "__main__":
    main()
