#!/usr/bin/env python3
"""우리 작품(발행작)마다 정보나루에서 대표 판(가장 많이 대출된 ISBN)을 찾고, 그 판의
지난 12개월 월별 대출·전국 순위·책소개를 받아 data/loans/ours.json 에 모은다.
책방 탭(/api/books/ours)이 이 파일을 읽는다. 호출 상한이 있어 결과를 ISBN·작품별로
디스크에 두고, 이미 있는 것은 다시 부르지 않는다. 매달 1일 뒤 한 번 돌리면 된다.
  venv/bin/python scripts/our_ranks.py [--force]
"""
import argparse, json, re, sys, time, urllib.parse, urllib.request, datetime as dt
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
D = BASE / "data" / "loans"; D.mkdir(parents=True, exist_ok=True)
OUT = D / "ours.json"
KEY = next((l.split("=", 1)[1].strip() for l in (BASE / ".env").read_text().splitlines() if l.startswith("DATA4LIBRARY_KEY=")), "")

def d4l(path, cache, ttl, **p):
    f = D / f"{cache}.json"
    if f.exists() and time.time() - f.stat().st_mtime < ttl:
        return json.loads(f.read_text(encoding="utf-8"))
    q = urllib.parse.urlencode({"authKey": KEY, "format": "json", **p})
    with urllib.request.urlopen(f"https://data4library.kr/api/{path}?{q}", timeout=60) as r:
        data = json.load(r)
    resp = data.get("response", data)
    if "error" in resp:
        raise RuntimeError(resp["error"])
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.6)   # 정보나루에 몰아치지 않는다
    return data

def clean_title(s): return re.split(r"\s*[:=/]\s*", (s or "").strip())[0].strip()
def norm(s): return re.sub(r"[^0-9a-z가-힣]", "", (s or "").lower())

def title_author(work, facts):
    try: t = (BASE / facts).read_text(encoding="utf-8")
    except OSError: t = ""
    m = re.search(r"\[서지\]\s*([^/\n]+)/\s*([^/\n]+)", t)
    if m: return m.group(1).strip(), m.group(2).strip()
    m = re.search(r"^([^『\n]+)『([^』]+)』", t)
    if m: return m.group(2).strip(), m.group(1).strip()
    try: return json.load(open(BASE / "works" / "handwritten" / work / "narration_night.json", encoding="utf-8"))["title"], ""
    except Exception: return work, ""

def surname(author):
    a = re.sub(r"\(.*?\)", "", author or "").strip()
    toks = [t for t in re.split(r"[\s·,]+", a) if t]
    if not toks: return ""
    # 서양 이름은 성이 뒤(허먼 멜빌 → 멜빌), 한국 이름은 통째(현진건)
    return toks[-1] if len(toks) > 1 and re.fullmatch(r"[가-힣]{2,4}", toks[0]) is None or len(toks) > 1 and len(toks[0]) <= 3 and len(a) > 4 else toks[0]

ALIAS = {  # 우리 제목 → 정보나루 서지에서 더 흔한 표기
    "십오 소년 표류기": ["15소년 표류기", "15소년 표류기"], "알라딘과 요술 램프": ["알라딘"],
    "신드바드의 모험": ["신드바드"], "잭과 콩나무": ["잭과 콩나무"], "금도끼 은도끼": ["금도끼 은도끼"],
}
NOAUTH = re.compile(r"미상|전래|설화|민담|해동염사|작자|원류")

KIDS_PUBS = ("은하수미디어", "대한교과서", "그레이트북스", "그레이트kids", "그레이트키즈", "삼성출판사", "교원", "프뢰벨",
             "여원미디어", "문공사", "크레용하우스", "학산문화사", "대교", "파랑새", "스푼북", "예림아이", "웅진씽크빅", "한국헤르만헤세",
             "톨스토이", "지경사", "효리원", "꿈소담이", "글송이", "삼성당", "계림", "능인", "아이세움", "주니어", "키즈")

def tier(x):
    """어떤 판인가. ISBN 부가기호 첫 자리(0·1·2·9 교양/실용/전문, 4 청소년, 7 아동, 6 초등학습)와
    둘째 자리(7 = 그림책·만화)로 가른다. 0 원작(완역) < 1 청소년 < 2 알 수 없음 < 3 어린이 글판 < 4 그림책·만화.
    사용자 지시 09-10: "왜 죄다 만화책이지? 원작 소설 표지로" — 대출 1위 판은 거의 초등 만화판이었다."""
    a = (x.get("addition_symbol") or "").strip()
    r, f = (a[0] if a else ""), (a[1] if len(a) > 1 else "")
    au = x.get("authors") or ""; pub = x.get("publisher") or ""; t_ = x.get("bookname") or ""
    comic = f == "7" or "만화" in t_ or "그림" in au or "엮은이" in au or "다시 씀" in au
    kids = any(k in pub for k in KIDS_PUBS) or "초등" in t_ or "어린이" in t_
    if r in ("0", "1", "2", "9") and not comic and not kids: return 0
    if r == "4" and not comic: return 1
    if r == "" and not comic and not kids: return 2
    if r in ("0", "1", "2", "4", "7", "9") and not comic: return 3
    return 4

KIND = {0: "원작", 1: "청소년판", 2: "원작", 3: "어린이판", 4: "그림책·만화판"}

ALIAS = {  # 우리 제목 → 정보나루 서지에서 더 흔한 표기
    "십오 소년 표류기": ["15소년 표류기"], "알라딘과 요술 램프": ["알라딘"],
    "신드바드의 모험": ["신드바드"],
}
NOAUTH = re.compile(r"미상|전래|설화|민담|해동염사|작자|원류")

def pick_editions(title, author, n=14):
    """제목(+저자)으로 찾아 (판 등급, 대출 많은 순) 후보 n 개. 저자가 '미상·전래…' 이면 제목만으로.
    한 판에 대출 이력이 비어 있는 일이 있어(09-10 실측 신데렐라) 후보를 여럿 돌려준다."""
    if NOAUTH.search(author or ""): author = ""
    sur = surname(author)
    seen, found = set(), []
    for t in [title] + ALIAS.get(title, []):
        for params in ({"title": t, "author": sur} if sur else {"title": t}, {"title": t}):
            tag = "srch50_" + norm(t) + "_" + norm(params.get("author", ""))
            try: data = d4l("srchBooks", tag, 60 * 24 * 3600, sort="loan", order="desc", pageSize=50, **params)
            except Exception as e: print("  srchBooks 실패", t, e); continue
            docs = [x.get("doc", x) for x in data.get("response", {}).get("docs", [])]
            docs = [x for x in docs if norm(t) in norm(clean_title(x.get("bookname")))]
            if sur: docs = [x for x in docs if norm(sur) in norm(x.get("authors", ""))]
            for x in docs:
                if x.get("isbn13") and x["isbn13"] not in seen:
                    seen.add(x["isbn13"]); found.append(x)
            if found: break
        if found: break
    return sorted(found, key=lambda x: (tier(x), -int(x.get("loan_count") or 0)))[:n]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true"); ap.add_argument("--retry", action="store_true", help="순위 못 찾은 작품만 다시"); a = ap.parse_args()
    month = (dt.date.today().replace(day=1) - dt.timedelta(days=1)).strftime("%Y년 %m월")
    works = {}
    for line in (BASE / "works" / "done.txt").read_text(encoding="utf-8").splitlines():
        c = line.split("\t")
        if len(c) >= 3: works[c[1]] = c[2]
    out = {"month": month, "built": "", "works": {}}
    if OUT.exists() and not a.force:
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
            if old.get("month") == month: out = old
        except Exception: pass
    for i, (w, facts) in enumerate(works.items(), 1):
        if w in out["works"] and out["works"][w].get("month") == month and not (a.retry and (not out["works"][w].get("rank") or out["works"][w].get("provisional"))): continue
        title, author = title_author(w, facts)
        cands = pick_editions(title, author)
        rec = {"work": w, "title": title, "author": author, "month": month}
        ed = None
        for ed in cands:
            isbn = ed.get("isbn13", "")
            try:
                u = d4l("usageAnalysisList", f"usage_{isbn}_{month[:4]}{month[6:8]}", 40 * 24 * 3600, isbn13=isbn).get("response", {})
            except Exception as e:
                rec["error"] = f"usage: {type(e).__name__}"; continue
            b = u.get("book", {}); hist = [x.get("loan", x) for x in u.get("loanHistory", [])]
            last = hist[-1] if hist else {}
            fields = {"isbn": isbn, "edition_title": clean_title(b.get("bookname") or ed.get("bookname")),
                      "edition_author": (b.get("authors") or ed.get("authors") or ""), "publisher": b.get("publisher") or ed.get("publisher", ""),
                      "year": str(b.get("publication_year") or ed.get("publication_year") or ""),
                      "cover": (b.get("bookImageURL") or ed.get("bookImageURL") or "").replace("http://", "https://"),
                      "description": re.sub(r"\s+", " ", (b.get("description") or "")).strip()[:600],
                      "total_loans": int(b.get("loanCnt") or ed.get("loan_count") or 0),
                      "rank": int(last.get("ranking") or 0) or None, "month_loans": int(last.get("loanCnt") or 0),
                      "rank_month": last.get("month", ""),
                      "history": [{"month": x.get("month"), "loans": int(x.get("loanCnt") or 0), "rank": int(x.get("ranking") or 0) or None} for x in hist][-12:],
                      "editions": len(cands), "edition_kind": KIND[tier(ed)]}
            if fields["rank"] or "isbn" not in rec:  # 순위 있는 판을 우선, 없으면 첫 판이라도 서지는 남긴다
                rec.update(fields); rec.pop("error", None)
            if fields["rank"]: break
        if not cands:
            rec["error"] = "판 못 찾음"
        out["works"][w] = rec
        out["built"] = dt.datetime.now().isoformat(timespec="seconds")
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{i:>3}/{len(works)} {w}: {title} / {author} → {rec.get('rank') and '전국 '+format(rec['rank'],',')+'위' or rec.get('error')} · 누적 {rec.get('total_loans','-')}", flush=True)
    print("끝", OUT)

if __name__ == "__main__":
    main()
