"""관리자 페이지 백엔드 (FastAPI).

설계 원칙: UI · cron · 에이전트가 **같은 REST API**를 쓴다.
UI 전용 로직을 만들면 나중에 자동화를 붙일 때 다시 짜야 한다.

실행:
  venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8010
"""
import datetime as _dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import db

BASE = Path(__file__).resolve().parent.parent
OUTPUT = BASE / "output"

app = FastAPI(title="aivideo admin API")
app.add_middleware(
    CORSMiddleware,
    # 사설망 어디서 열어도 통과시킨다 (내부 전용 서비스)
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):\d+",
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    db.init()
    db.reset_stuck()  # 워커가 죽은 채 남은 running 작업을 pending 으로 되돌린다


# ---------- 작업 큐 ----------

class JobIn(BaseModel):
    concept: str
    title: str = ""
    params: dict = {}
    source: str = "ui"


@app.post("/api/jobs")
def create_job(body: JobIn):
    return {"id": db.create(body.concept, body.params, body.title, body.source)}


@app.get("/api/jobs")
def list_jobs(limit: int = 100):
    return {"jobs": db.list_jobs(limit)}


@app.get("/api/jobs/{jid}")
def get_job(jid: str):
    j = db.get(jid)
    if not j:
        raise HTTPException(404, "job not found")
    return j


class JobPatch(BaseModel):
    status: str | None = None
    stage: str | None = None
    progress: int | None = None
    error: str | None = None
    video_path: str | None = None


@app.patch("/api/jobs/{jid}")
def patch_job(jid: str, body: JobPatch):
    if not db.get(jid):
        raise HTTPException(404, "job not found")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    db.update(jid, **fields)
    return db.get(jid)


# ---------- 작품 / 대본 검수 ----------

def _works():
    """output/<작품>/narration*.json 을 훑어 작품 목록을 만든다.
    별도 테이블 없이 파일시스템을 진실로 쓴다 -- 파이프라인이 파일로 돌기 때문."""
    out = []
    if not OUTPUT.exists():
        return out
    for d in sorted(p for p in OUTPUT.iterdir() if p.is_dir()):
        for f in sorted(d.glob("narration*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            out.append({
                "work": d.name,
                "version": f.stem,
                # 최종 수정시각. 버전 정렬·표기의 근거가 된다.
                "updated": _dt.datetime.fromtimestamp(
                    f.stat().st_mtime, _dt.timezone.utc
                ).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "title": data.get("title", d.name),
                "sentences": data.get("sentences", []),
                "passed": data.get("passed"),
                "issues": data.get("issues", []),
            })
    return out


@app.get("/api/works")
def list_works():
    return {"works": _works()}


class NarrationPatch(BaseModel):
    sentences: list[str]


def _revalidate(sents, title):
    """하네스의 검증기를 그대로 재사용한다 (규칙 중복 정의를 피한다)."""
    sys.path.insert(0, str(BASE / "scripts"))
    from write_script import ENDING_PLAN, narrative_issues, validate
    ending = f"소설 {title}에서 만날 수 있습니다"
    n = len(sents)
    issues = validate(sents, ending, [], plan=ENDING_PLAN[:n]) + narrative_issues(sents)
    return [f"S{i+1}: {m}" for i, m in issues]


@app.put("/api/works/{work}/{version}")
def update_narration(work: str, version: str, body: NarrationPatch):
    """대본 인라인 수정 후 재검증. 기계가 못 잡는 의미 왜곡을 사람이 고치는 경로."""
    if not re.fullmatch(r"[\w.\-]+", work) or not re.fullmatch(r"[\w.\-]+", version):
        raise HTTPException(400, "bad path")
    f = OUTPUT / work / f"{version}.json"
    if not f.is_file():
        raise HTTPException(404, "narration not found")
    data = json.loads(f.read_text(encoding="utf-8"))
    data["sentences"] = body.sentences
    issues = _revalidate(body.sentences, data.get("title", work))
    data["issues"] = issues
    data["passed"] = not issues
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


# ---------- 산출물 ----------

@app.get("/api/works/{work}/keyframes")
def keyframes(work: str):
    d = OUTPUT / f"{work}_kf"
    return {"images": [f.name for f in sorted(d.glob("*.png"))] if d.exists() else []}


def _duration(path: Path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=20)
        return round(float(r.stdout.strip()), 2)
    except (subprocess.SubprocessError, ValueError):
        return None


def _classify(name: str) -> tuple[str, str]:
    """파일명에서 (종류, 버전)을 뽑는다.
    s1_00001_.mp4 -> ("scene", "s1") / final_v3_2.mp4 -> ("final", "v3.2")"""
    m = re.match(r"^s(\d+)[_.]", name)
    if m:
        return "scene", f"s{m.group(1)}"
    v = re.search(r"v(\d+(?:[._]\d+)*)", name)
    ver = "v" + v.group(1).replace("_", ".") if v else "\ucd08\ud310"
    if "compressed" in name:
        ver += " (\uc555\ucd95)"
    return ("final" if name.startswith("final") else "other"), ver


@app.get("/api/works/{work}/videos")
def videos(work: str):
    d = OUTPUT / work
    if not d.exists():
        return {"videos": []}
    out = []
    for f in sorted(d.glob("*.mp4")):
        kind, ver = _classify(f.name)
        st = f.stat()
        out.append({
            "name": f.name, "size": st.st_size, "duration": _duration(f),
            "kind": kind, "version": ver,
            "updated": _dt.datetime.fromtimestamp(
                st.st_mtime, _dt.timezone.utc
            ).isoformat(timespec="seconds").replace("+00:00", "Z"),
        })
    out.sort(key=lambda x: (x["kind"] != "final", x["updated"]))
    return {"videos": out}


@app.get("/api/files/{kind}/{work}/{name}")
def get_file(kind: str, work: str, name: str):
    """kind: keyframe | video. 경로 조작 방지를 위해 단순 파일명만 허용한다."""
    if not re.fullmatch(r"[\w.\-가-힣]+", name) or not re.fullmatch(r"[\w.\-]+", work):
        raise HTTPException(400, "bad name")
    p = (OUTPUT / f"{work}_kf" / name) if kind == "keyframe" else (OUTPUT / work / name)
    if kind not in ("keyframe", "video"):
        raise HTTPException(400, "bad kind")
    if not p.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(p)


@app.get("/api/works/{work}/review")
def work_review(work: str):
    """완성본 자가점검 결과. scripts/review_output.py 의 판정을 그대로 쓴다 —
    UI 가 따로 기준을 갖게 하면 배치와 화면이 서로 다른 말을 하게 된다."""
    if not re.fullmatch(r"[\w.\-]+", work):
        raise HTTPException(400, "bad work")
    sys.path.insert(0, str(BASE / "scripts"))
    from review_output import review
    try:
        return review(work)
    except Exception as e:
        raise HTTPException(500, f"점검 실패: {type(e).__name__}")


@app.get("/api/health")
def health():
    return {"ok": True, "jobs": len(db.list_jobs(1000)), "works": len(_works())}


# ---------- 도서 (정보나루 인기대출도서) ----------
# 매뉴얼: docs/reference/data4library_API_manual.pdf
# 승인된 인증키는 .env 의 DATA4LIBRARY_KEY 에서만 읽고 응답에 넣지 않는다.

_BOOK_CACHE: dict = {}


def _env(key: str) -> str:
    f = BASE / ".env"
    if not f.exists():
        return ""
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


@app.get("/api/books/popular")
def popular_books(start: str = "", end: str = "", limit: int = 20, refresh: bool = False):
    """인기대출도서. 하루 호출 상한이 있으므로 메모리에 캐시한다."""
    import datetime as _dt
    import urllib.parse
    import urllib.request

    if not end:
        end = _dt.date.today().replace(day=1) - _dt.timedelta(days=1)
        start = end.replace(day=1).isoformat()
        end = end.isoformat()
    ck = f"{start}:{end}:{limit}"
    if not refresh and ck in _BOOK_CACHE:
        return _BOOK_CACHE[ck]

    key = _env("DATA4LIBRARY_KEY")
    if not key:
        raise HTTPException(503, "DATA4LIBRARY_KEY 미설정")
    q = urllib.parse.urlencode({
        "authKey": key, "startDt": start, "endDt": end,
        "pageNo": 1, "pageSize": limit, "format": "json",
    })
    try:
        with urllib.request.urlopen(
            f"https://data4library.kr/api/loanItemSrch?{q}", timeout=30
        ) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # 외부 API 장애가 페이지 전체를 죽이지 않게 한다
        raise HTTPException(502, f"정보나루 호출 실패: {type(e).__name__}")

    resp = data.get("response", data)
    if "error" in resp:
        raise HTTPException(502, str(resp["error"]))

    books = []
    for i, row in enumerate(resp.get("docs", []), 1):
        b = row.get("doc", row)
        books.append({
            "rank": int(b.get("ranking") or i),
            "title": (b.get("bookname") or "").split(":")[0].strip(),
            "author": (b.get("authors") or "").replace("지은이:", "").strip(),
            "publisher": b.get("publisher", ""),
            "isbn": b.get("isbn13", ""),
            "loans": int(b.get("loan_count") or 0),
            "holding": "unknown",
        })

    # KEI 소장: 캐시된 것은 즉시 채우고, 나머지는 백그라운드로 조회해
    # 같은 dict 를 갱신한다(_BOOK_CACHE 가 참조를 들고 있어 다음 조회에 반영).
    sys.path.insert(0, str(BASE / "scripts"))
    from kei_holdings import first_author
    _hold_load()
    pending = []
    for b in books:
        hit = _HOLD_CACHE.get(f"{b['title']}|{first_author(b['author'])}")
        if hit and time.time() - hit["ts"] < _HOLD_TTL:
            b["holding"] = hit["res"]["holding"]
        else:
            pending.append(b)
    if pending:
        import threading

        def _fill():
            for b in pending:
                try:
                    b["holding"] = _kei_lookup(b["title"], first_author(b["author"]))["holding"]
                except Exception:
                    pass  # 도서관 서버 장애 — unknown 으로 두고 다음 기회에

        threading.Thread(target=_fill, daemon=True).start()

    out = {"period": {"start": start, "end": end}, "books": books}
    _BOOK_CACHE[ck] = out
    return out


# ---------- KEI 도서관 소장 확인 ----------
# scripts/kei_holdings.py (Pyxis JSON API) 를 24시간 파일 캐시로 감싼다.

_HOLD_CACHE: dict = {}
_HOLD_FILE = BASE / "data" / "kei_holdings.json"
_HOLD_TTL = 24 * 3600


def _hold_load():
    if not _HOLD_CACHE and _HOLD_FILE.exists():
        try:
            _HOLD_CACHE.update(json.loads(_HOLD_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass  # 캐시 파일 손상 — 새로 조회하며 다시 쌓는다


def _kei_lookup(title: str, author: str = "") -> dict:
    _hold_load()
    k = f"{title}|{author}"
    hit = _HOLD_CACHE.get(k)
    if hit and time.time() - hit["ts"] < _HOLD_TTL:
        return hit["res"]
    sys.path.insert(0, str(BASE / "scripts"))
    from kei_holdings import lookup
    res = lookup(title, author)
    _HOLD_CACHE[k] = {"ts": time.time(), "res": res}
    _HOLD_FILE.parent.mkdir(exist_ok=True)
    _HOLD_FILE.write_text(json.dumps(_HOLD_CACHE, ensure_ascii=False), encoding="utf-8")
    return res


@app.get("/api/books/holdings")
def book_holdings(title: str, author: str = ""):
    """KEI 소장 확인: holding = paper | ebook | both | none (24h 캐시)."""
    sys.path.insert(0, str(BASE / "scripts"))
    from kei_holdings import first_author
    try:
        return _kei_lookup(title.strip(), first_author(author))
    except Exception as e:
        raise HTTPException(502, f"KEI 조회 실패: {type(e).__name__}")
