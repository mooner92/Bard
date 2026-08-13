#!/usr/bin/env python3
"""KEI 전자도서관(library.kei.re.kr) 소장 조회.

통합검색 화면이 내부적으로 쓰는 Pyxis JSON API 가 비로그인으로 열려 있어
브라우저(Playwright) 없이 이 API 를 그대로 쓴다. DOM 이 바뀌어도 깨지지 않는다.

  GET /pyxis-api/1/collections/{cid}/search?all=k|a|{검색어}&max=N&offset=0
    cid 1  = 통합검색 '소장자료' 탭 (종이책)
    cid 10 = 통합검색 'eBook' 탭 (전자책)

검색 인덱스는 출판사·주기사항까지 걸린다. 실측: '모비딕' 검색에
출판사가 '모비딕'(고양 소재)인 「로봇: 로숨의 유니버설 로봇」이 함께 나온다.
그래서 제목(정규화 부분일치)과, 저자가 주어졌으면 저자·표제 중 일치까지
확인해 의도에 맞는 결과만 남긴다. 번역서는 저자 표기가 원어(Melville)인
경우가 많아 표제("허먼 멜빌 장편소설")에서도 저자를 찾는다.

사용:
  venv/bin/python scripts/kei_holdings.py --title 모비딕 --author 멜빌
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request

HOST = "https://library.kei.re.kr"
COLLECTIONS = {"paper": 1, "ebook": 10}
UA = "bard-holdings/1.0 (internal pipeline)"


def _norm(s: str) -> str:
    """공백·문장부호를 걷어내고 소문자화 — '모비 딕(2)' 과 '모비딕' 을 잇는다."""
    return re.sub(r"[^0-9a-z가-힣]", "", (s or "").lower())


def first_author(s: str) -> str:
    """정보나루식 '허먼 멜빌 지음; 김석희 옮김' 에서 첫 저자만 뽑는다."""
    head = re.split(r"[;,/]", s or "")[0]
    head = re.sub(r"(지은이|지음|옮김|엮음|글|그림)", "", head).strip()
    return head


def _search(cid: int, query: str, max_n: int = 30) -> list:
    q = urllib.parse.quote(f"k|a|{query}")
    url = f"{HOST}/pyxis-api/1/collections/{cid}/search?all={q}&max={max_n}&offset=0"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    if not data.get("success"):
        raise RuntimeError(f"KEI API 오류: {data.get('message')}")
    return (data.get("data") or {}).get("list") or []


def _item(raw: dict) -> dict:
    bv = (raw.get("branchVolumes") or [{}])[0]
    return {
        "title": raw.get("titleStatement") or "",
        "author": raw.get("author") or "",
        "publication": raw.get("publication") or "",
        "type": (raw.get("biblioType") or {}).get("name") or "",
        "isbn": raw.get("isbn") or "",
        "callno": bv.get("volume") or "",
        "status": bv.get("cState") or "",
    }


def _match(it: dict, title: str, author: str) -> bool:
    """제목은 부분일치 필수. 저자는 토큰(≥2자) 하나라도 저자·표제에 보이면 통과.

    '프란츠 카프카' 로 물어도 서지에 '카프카'만 있으면 잡는다. 서지가
    원어(Kafka, Franz)뿐이고 질의가 한글뿐이면 놓친다 — 소장인데 none 으로
    보는 보수적 방향이라, 없는 책을 있다고 안내하는 사고는 나지 않는다.
    """
    if _norm(title) not in _norm(it["title"]):
        return False
    toks = [t for t in re.split(r"\s+", author or "") if len(_norm(t)) >= 2]
    if toks:
        hay = _norm(it["author"]) + _norm(it["title"])
        if not any(_norm(t) in hay for t in toks):
            return False
    return True


def lookup(title: str, author: str = "") -> dict:
    """제목(필수)·저자(선택)로 KEI 소장을 판별한다.

    holding: paper | ebook | both | none. 컬렉션 조회가 실패하면 해당
    kind 는 빈 리스트 + {kind}_error 로 남기고 판정은 나머지로 한다.
    """
    out = {"title": title, "author": author, "paper": [], "ebook": []}
    for kind, cid in COLLECTIONS.items():
        try:
            raw = _search(cid, title)
        except Exception as e:
            out[f"{kind}_error"] = f"{type(e).__name__}: {e}"
            continue
        out[kind] = [it for it in map(_item, raw) if _match(it, title, author)]
        time.sleep(0.3)  # 내부 도서관 서버 예의
    out["holding"] = (
        "both" if out["paper"] and out["ebook"]
        else "paper" if out["paper"]
        else "ebook" if out["ebook"]
        else "none"
    )
    return out


def main():
    ap = argparse.ArgumentParser(description="KEI 도서관 소장 조회")
    ap.add_argument("--title", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--raw", action="store_true", help="필터 전 소장자료 원본도 출력")
    a = ap.parse_args()
    res = lookup(a.title, first_author(a.author))
    if a.raw:
        res["_raw_paper"] = [_item(r) for r in _search(COLLECTIONS["paper"], a.title)]
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
