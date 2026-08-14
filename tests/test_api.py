#!/usr/bin/env python3
"""SPEC §7 운영 인터페이스 확인 — 백엔드가 문서대로 응답하는지 본다.

백엔드(:8010)가 떠 있어야 한다. 외부 도서 API(정보나루·KEI)는 네트워크가
불안정하면 건너뛰고 경고만 남긴다 — 그 실패로 릴리스를 막지는 않는다.
실행: venv/bin/python tests/test_api.py
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "http://127.0.0.1:8010"
FAIL, WARN = [], []


def get(path, timeout=60):
    with urllib.request.urlopen(f"{API}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def check(name, cond, detail=""):
    print(f"  {'OK ' if cond else '!! '}{name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAIL.append(f"{name}: {detail}")


def warn(name, detail):
    print(f"  -- {name} 건너뜀 — {detail}")
    WARN.append(name)


print("[상태]")
try:
    h = get("/api/health", 20)
except Exception as e:
    print(f"  !! 백엔드 무응답: {e}")
    print("  venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8010")
    sys.exit(1)
check("health 응답", h.get("ok") is True, str(h))
check("작품 수 노출", isinstance(h.get("works"), int), str(h))

print("\n[작품·산출물]")
works = get("/api/works")["works"]
check("작품 목록", bool(works), "0건")
w = works[0]["work"]
for key in ("work", "version", "title", "sentences", "passed", "issues", "updated"):
    check(f"작품 필드 {key}", key in works[0])

vids = get(f"/api/works/{w}/videos")["videos"]
kinds = {v["kind"] for v in vids}
check("영상 종류가 명세 집합 안", kinds <= {"final", "night", "scene", "other"}, str(kinds))
check("키프레임 응답", "images" in get(f"/api/works/{w}/keyframes"))

night = [v for v in vids if v["kind"] == "night"]
if night:
    check("야간 산출물은 final 이 아니다", all(v["kind"] != "final" for v in night))

print("\n[자가점검]")
rev = get(f"/api/works/{w}/review", 180)
for key in ("work", "ok", "flags", "keyframes"):
    check(f"점검 필드 {key}", key in rev, str(list(rev)))
check("판정이 불리언", isinstance(rev.get("ok"), bool))
check("위반 목록이 리스트", isinstance(rev.get("flags"), list))

print("\n[도서]")
try:
    b = get("/api/books/popular?limit=5", 180)
    check("인기대출 목록", bool(b.get("books")), str(b)[:120])
    if b.get("books"):
        for key in ("rank", "title", "author", "isbn", "loans", "holding"):
            check(f"도서 필드 {key}", key in b["books"][0])
        check("소장 판정값이 명세 집합 안",
              {x["holding"] for x in b["books"]} <= {"paper", "ebook", "both", "none", "unknown"},
              str({x["holding"] for x in b["books"]}))
except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
    warn("정보나루 인기대출", str(e)[:80])

try:
    q = urllib.parse.urlencode({"title": "모비딕", "author": "허먼 멜빌"})
    hold = get(f"/api/books/holdings?{q}", 120)
    check("소장 조회 판정", hold.get("holding") in ("paper", "ebook", "both", "none"),
          str(hold.get("holding")))
    check("소장 목록 구조", isinstance(hold.get("paper"), list))
except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
    warn("KEI 소장 조회", str(e)[:80])

print("\n" + "=" * 60)
if WARN:
    print(f"경고 {len(WARN)}건(외부 API): {', '.join(WARN)}")
if FAIL:
    print(f"불합격 {len(FAIL)}건")
    for x in FAIL:
        print(" -", x)
    sys.exit(1)
print("인터페이스 확인 전부 통과")
