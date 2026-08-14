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


def usage_analysis(isbn13: str) -> dict:
    """정보나루 이용분석: 키워드·독자층·함께 빌린 책·대출 추이.

    출판사 소개문은 100자 남짓이라 8문장을 쓰기엔 얇다(실측: 그 얇음이
    "수상작의 빛이 되네요" 같은 빈 문장을 만들었다). 여기서 나오는 숫자와
    목록은 전부 검증 가능한 사실이라 환각 없이 살을 붙일 수 있다.
    """
    key = _env("DATA4LIBRARY_KEY")
    if not key or not isbn13:
        return {}
    q = urllib.parse.urlencode({"authKey": key, "isbn13": isbn13, "format": "json"})
    try:
        d = json.loads(_get(f"https://data4library.kr/api/usageAnalysisList?{q}"))["response"]
    except Exception as e:
        print(f"  ! 정보나루 이용분석 실패 {isbn13}: {type(e).__name__}: {e}", file=sys.stderr)
        return {}
    out = {}
    kw = [k["keyword"]["word"] for k in (d.get("keywords") or [])][:6]
    if kw:
        out["keywords"] = kw
    grps = [g["loanGrp"] for g in (d.get("loanGrps") or [])][:3]
    if grps:
        out["readers"] = [f"{g['age']} {g['gender']}" for g in grps]
    # coLoanBooks 는 책에 따라 {"books":[...]} 이기도 하고 그냥 [...] 이기도 하다.
    raw_co = d.get("coLoanBooks") or []
    raw_co = raw_co.get("books", []) if isinstance(raw_co, dict) else raw_co
    co = [(b.get("book") or {}).get("bookname", "").split(":")[0].strip()
          for b in raw_co if isinstance(b, dict)][:4]
    if any(co):
        out["together"] = [c for c in co if c]
    hist = [h["loan"] for h in (d.get("loanHistory") or [])]
    if hist:
        top = max(hist, key=lambda h: int(h.get("loanCnt") or 0))
        out["peak"] = f"{top['month']} 전국 {int(top['loanCnt']):,}회 대출"
    return out


def _wiki_extract(title: str) -> str:
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


def wikipedia_summary(title: str, author: str = "") -> str:
    """한국어 위키백과 첫 문단. 없거나 **다른 주제면** 빈 문자열을 준다.

    제목이 일반명사면 엉뚱한 문서가 잡힌다. 실측: '모순' -> 논리학 개념 문서가
    와서 대본에 "진리값", "논리적 비약"이 소설 내용인 양 실렸다. 그래서
    저자 이름이 본문에 있는지 확인하고, 없으면 자료로 쓰지 않는다.
    """
    for t in ([f"{title} (소설)", title] if author else [title]):
        txt = _wiki_extract(t)
        if not txt:
            continue
        if not author:
            return txt
        names = [author, author.replace(" ", "")] + author.split()
        if any(n and n in txt for n in names):
            return txt
    return ""


def wikipedia_plot(title: str, author: str = "") -> str:
    """퍼블릭 도메인 고전용: 위키백과의 줄거리·배경 절을 통째로 가져온다.

    고전은 저작권이 만료돼 각색이 자유롭고, 위키백과에 세계를 그릴 재료가
    충분하다(장소·계절·사물). 현대서의 홍보문 소개와 질이 다르다.
    """
    import time as _time
    for t in ([f"{title} (소설)", title] if author else [title]):
        pages = {}
        # 연속 조회에서 maxlag·타임아웃이 잦다(실측: 12작품 일괄 적재 시 다수 실패).
        # 한 번 쉬고 재시도하면 대부분 살아난다.
        for attempt in range(3):
            try:
                u = "https://ko.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
                    "action": "query", "format": "json", "prop": "extracts",
                    "explaintext": 1, "redirects": 1, "maxlag": 5, "titles": t,
                })
                pages = json.loads(_get(u, 60)).get("query", {}).get("pages", {})
                break
            except Exception as e:
                print(f"  ! 위키 본문 실패 {t} ({attempt+1}/3): {type(e).__name__}", file=sys.stderr)
                _time.sleep(3 * (attempt + 1))
        if not pages:
            continue
        for p in pages.values():
            txt = (p.get("extract") or "").strip()
            if len(txt) < 200:
                continue
            if author and not any(n and n in txt for n in [author] + author.split()):
                continue
            # "== 줄거리 ==" 같은 절 표제로 잘라 필요한 절만 남긴다
            parts = re.split(r"\n==+\s*([^=\n]+?)\s*==+\n", "\n" + txt)
            head = parts[0].strip()
            want, out = ("줄거리", "내용", "배경", "설정", "등장인물"), []
            for i in range(1, len(parts) - 1, 2):
                if any(w in parts[i] for w in want):
                    out.append(f"[{parts[i].strip()}]\n{parts[i+1].strip()}")
            body = "\n".join([head] + out) if out else head
            return re.sub(r"\n{2,}", "\n", body)[:2500]
    return ""


def build(title: str, author: str, isbn13: str = "", fmt: str = "intro") -> tuple:
    """사실 텍스트와 KEI 소장 판정을 만든다. 반환: (facts_text, holding_dict)."""
    import sys
    sys.path.insert(0, str(BASE / "scripts"))
    from kei_holdings import first_author, lookup

    a1 = first_author(author)
    book = data4library_detail(isbn13)
    # 고전(각색형)은 줄거리·배경 절까지 가져온다. 현대서(소개형)는 첫 문단만.
    wiki = wikipedia_plot(title, a1) if fmt == "narrative" else wikipedia_summary(title, a1)
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
        # 청구기호·대출상태는 넣지 않는다. 모델이 "KEI 도서관 CB 1999" 처럼
        # 그대로 낭독해 버린다(실측). 서가 위치는 영상에 쓸 정보가 아니다.
        lines.append(f"[소장] KEI 도서관 {kind}")
    if book.get("description"):
        lines += ["[출판사 소개]", book["description"].strip()]
    if wiki:
        lines += ["[줄거리와 배경]" if fmt == "narrative" else "[백과 설명]", wiki]
    # 대출 통계·독자층·키워드는 사실파일에 넣지 않는다.
    # 재료가 얇을 때 이걸로 채웠더니 모델이 작품 내용으로 착각해
    # "대출 241회", "30대 여성 독자가 꾸준히" 를 낭독했다(실측). 영상이
    # 책 속 세계가 아니라 도서관 통계 소개가 돼 버린다. 재료가 얇은 책은
    # 통계로 때우지 말고 큐에서 빼는 것이 맞다(refill_queue.py 의 자료 하한).
    if fmt == "narrative":
        lines += [
            "[집필 지침] 위 줄거리에 있는 사건과 사물만 쓴다. 여덟 장면으로 나누되",
            "설명하지 말고 보여줘라. 결말은 밝히지 말고 질문으로 닫는다.",
        ]
    if fmt == "intro":
        lines += [
            "[집필 지침] 위 자료에 적힌 배경만 쓴다. 줄거리를 순서대로 옮기거나 결말을 밝히지 않는다.",
            "책·작가·출판 이야기가 아니라, 작품이 놓인 장소와 시간, 그 안의 사물과 공기를 그린다.",
        ]
    return "\n".join(lines), hold


# 작품 '속 세계'를 그릴 수 있는지 판별하는 단서. 출판사 소개문이 작가 홍보문
# ("젊은 거장의 신작", "베일에 가려져 있던")뿐이면 그릴 세계가 없다 — 실측:
# 그런 책에서 대본이 도서관 통계 낭독으로 흘렀다.
WORLD_CUES = [
    "시", "구", "동", "읍", "면", "리", "마을", "거리", "골목", "도시", "섬", "바다", "산",
    "강", "숲", "들판", "학교", "병원", "편의점", "서점", "카페", "식당", "공장", "역",
    "아파트", "하숙", "집", "방", "복도", "계단", "옥상", "지하", "정원", "시장",
    "봄", "여름", "가을", "겨울", "새벽", "아침", "저녁", "밤", "눈", "비", "바람",
    "년대", "세기", "전쟁", "식민", "조선", "고향",
]


def world_material(text: str) -> int:
    """사실 텍스트에 세계를 그릴 단서가 몇 개나 있는지 센다.

    [출판사 소개]·[백과 설명] 본문만 본다. 서지 줄의 출판지("파주")가
    장소 단서로 잘못 잡히면 홍보문뿐인 책이 통과해 버린다.
    """
    body = []
    keep = False
    for line in text.splitlines():
        if line.startswith("["):
            keep = line.startswith(("[출판사 소개]", "[백과 설명]", "[줄거리와 배경]", "[줄거리]"))
            continue
        if keep:
            body.append(line)
    joined = " ".join(body)
    return sum(1 for c in WORLD_CUES if c in joined)


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
