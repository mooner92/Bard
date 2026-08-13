#!/usr/bin/env python3
"""도서 사실파일 자동 생성 — 정보나루 상세 + 위키백과 + KEI 소장.

대본 하네스(write_script.py)는 [원작 사실] 텍스트만 근거로 쓴다. 지금까지
이 파일은 사람이 손으로 썼다. 인기대출도서를 야간 배치에 자동 투입하려면
이 단계가 자동이어야 해서 만든 스크립트다.

**현대서는 줄거리 각색을 하지 않는다** (docs/PLAN.md). 저작권이 살아 있는
작품의 줄거리 재구성은 2차적저작물 침해 소지가 있다. 그래서 사실파일 첫 줄에
`[포맷] 소개형` 을 박아 하네스가 "책이 던지는 질문" 포맷으로 쓰게 한다.
퍼블릭 도메인 고전은 `--format narrative` 로 기존 각색 포맷을 쓴다.

사용:
  venv/bin/python scripts/fetch_book_facts.py --isbn 9788936434120 \
      --title "소년이 온다" --author 한강 --out facts/auto_x.txt
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
UA = "bard-facts/1.0 (internal literary shorts pipeline; contact: library ops)"

CHO = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj",
       "ch", "k", "t", "p", "h"]
JUNG = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe",
        "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]
JONG = ["", "k", "k", "k", "n", "n", "n", "t", "l", "l", "l", "l", "l", "l", "l",
        "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"]


def slug(title: str, limit: int = 24) -> str:
    """한글 제목 -> ASCII 작업 ID. 파일명·ComfyUI 입력명으로 쓰이므로 ASCII 고정."""
    out = []
    for ch in title.strip():
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3:
            c = o - 0xAC00
            out.append(CHO[c // 588] + JUNG[(c % 588) // 28] + JONG[c % 28])
        elif ch.isalnum():
            out.append(ch.lower())
        elif out and out[-1] != "_":
            out.append("_")
    return re.sub(r"_+", "_", "".join(out)).strip("_")[:limit] or "book"


def _env(key: str) -> str:
    f = BASE / ".env"
    for line in (f.read_text(encoding="utf-8").splitlines() if f.exists() else []):
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def _get(url: str, timeout: int = 25) -> str:
    # Accept 를 application/json 으로 고정하면 정보나루가 406 을 낸다(실측).
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def data4library_detail(isbn13: str) -> dict:
    """정보나루 상세: 출판사 소개문·분류·발행연도."""
    key = _env("DATA4LIBRARY_KEY")
    if not key or not isbn13:
        return {}
    q = urllib.parse.urlencode({"authKey": key, "isbn13": isbn13, "format": "json"})
    try:
        d = json.loads(_get(f"https://data4library.kr/api/srchDtlList?{q}"))
    except Exception as e:
        # 조용히 넘기면 "자료 부족"으로 오인된다. 왜 비었는지 남긴다.
        print(f"  ! 정보나루 상세 실패 {isbn13}: {type(e).__name__}: {e}", file=sys.stderr)
        return {}
    detail = (d.get("response", d).get("detail") or [{}])[0]
    return detail.get("book", {}) or {}


def wikipedia_summary(title: str) -> str:
    """한국어 위키백과 첫 문단. 없으면 빈 문자열 — 없다고 실패시키지 않는다."""
    try:
        u = "https://ko.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "prop": "extracts",
            "exintro": 1, "explaintext": 1, "redirects": 1, "maxlag": 5,
            "titles": title,
        })
        pages = json.loads(_get(u)).get("query", {}).get("pages", {})
        for p in pages.values():
            txt = (p.get("extract") or "").strip()
            if len(txt) > 80:
                return re.sub(r"\n{2,}", "\n", txt)[:1200]
    except Exception:
        pass
    return ""


def build(title: str, author: str, isbn13: str = "", fmt: str = "intro") -> tuple:
    """사실 텍스트와 KEI 소장 판정을 만든다. 반환: (facts_text, holding_dict)."""
    import sys
    sys.path.insert(0, str(BASE / "scripts"))
    from kei_holdings import first_author, lookup

    a1 = first_author(author)
    book = data4library_detail(isbn13)
    wiki = wikipedia_summary(title)
    try:
        hold = lookup(title, a1)
    except Exception:
        hold = {"holding": "unknown", "paper": [], "ebook": []}

    held = (hold.get("paper") or hold.get("ebook") or [{}])[0]
    lines = [
        f"[포맷] {'소개형' if fmt == 'intro' else '각색형'}",
        f"[서지] {title} / {a1 or author} / "
        f"{book.get('publisher', '')} {book.get('publication_year', '')} / "
        f"{book.get('class_nm', '')}".strip(),
    ]
    if hold["holding"] in ("paper", "ebook", "both"):
        kind = {"paper": "종이책", "ebook": "전자책", "both": "종이책·전자책"}[hold["holding"]]
        lines.append(f"[소장] KEI 도서관 {kind}"
                     + (f" (청구기호 {held.get('callno')}, {held.get('status')})"
                        if held.get("callno") else ""))
    if book.get("description"):
        lines += ["[출판사 소개]", book["description"].strip()]
    if wiki:
        lines += ["[백과 설명]", wiki]
    if fmt == "intro":
        lines += [
            "[집필 지침] 위 자료에 적힌 사실만 쓴다. 줄거리를 재구성하거나 결말을 밝히지 않는다.",
            "책이 독자에게 던지는 질문과, 읽기 전에 알아두면 좋은 배경만 다룬다.",
        ]
    return "\n".join(lines), hold


def main():
    p = argparse.ArgumentParser(description="도서 사실파일 자동 생성")
    p.add_argument("--title", required=True)
    p.add_argument("--author", default="")
    p.add_argument("--isbn", default="")
    p.add_argument("--format", choices=["intro", "narrative"], default="intro")
    p.add_argument("--out", default="")
    a = p.parse_args()
    text, hold = build(a.title, a.author, a.isbn, a.format)
    out = Path(a.out) if a.out else BASE / "facts" / f"auto_{slug(a.title)}.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "holding": hold["holding"],
                      "chars": len(text), "slug": slug(a.title)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
