"""관리자 페이지 백엔드 (FastAPI).

설계 원칙: UI · cron · 에이전트가 **같은 REST API**를 쓴다.
UI 전용 로직을 만들면 나중에 자동화를 붙일 때 다시 짜야 한다.

실행:
  venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8010
  (127.0.0.1 에만 묶는다 — 시청 호스트의 신원 헤더를 Next 미들웨어만 쓸 수 있게)
"""
import collections
import datetime as _dt
import hashlib
import html as _html
import hmac
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import db

BASE = Path(__file__).resolve().parent.parent
OUTPUT = BASE / "output"

# ---------- 시청 호스트(외부 공개) ----------
# Next 미들웨어(admin/middleware.ts)가 호스트를 보고 x-bard-mode(watch|admin)와
# x-bard-viewer(Cloudflare Access 가 확인한 이메일)를 채워 넘긴다. 백엔드는 127.0.0.1 에만
# 묶여 있어야 이 헤더를 미들웨어만 쓸 수 있다(0.0.0.0 이면 사내망에서 위조 가능).
#
# 영상 URL 은 이메일에 묶어 서명한다 — 링크를 남에게 보내도 그 사람의 Access 이메일과
# 맞지 않아 403. 요청은 logs/access.log 에 남겨 폭주 시 누구인지 특정한다.
VIEW_TTL = 3 * 3600            # 서명 URL 유효 시간. 재생 중 Range 요청이 이어지므로 넉넉히
RATE_N, RATE_WIN = 60, 600     # 이메일당 10분에 영상 요청 60회(Range 포함) 넘으면 429
ACCESS_LOG = BASE / "logs" / "access.log"
BLOCK_FILE = BASE / "works" / "blocked_viewers.txt"   # 한 줄에 이메일 하나 — 즉시 차단
_rate: dict = collections.defaultdict(collections.deque)
_block_cache: tuple = (0.0, frozenset())


def _sign_secret() -> str:
    return os.environ.get("BARD_SIGN_SECRET") or _env("BARD_SIGN_SECRET")


def _viewer(request: Request) -> tuple:
    """(mode, email). mode 는 'watch' 또는 'admin'."""
    return (request.headers.get("x-bard-mode", "admin"),
            (request.headers.get("x-bard-viewer") or "").strip().lower())


def _sign(email: str, work: str, name: str, exp: int) -> str:
    msg = f"{email}|{work}|{name}|{exp}".encode()
    return hmac.new(_sign_secret().encode(), msg, hashlib.sha256).hexdigest()[:32]


def _signed_url(email: str, work: str, name: str) -> str:
    exp = int(time.time()) + VIEW_TTL
    return f"/api/files/video/{work}/{name}?e={exp}&s={_sign(email, work, name, exp)}"


def _blocked(email: str) -> bool:
    global _block_cache
    try:
        mt = BLOCK_FILE.stat().st_mtime
    except FileNotFoundError:
        return False
    if mt != _block_cache[0]:
        emails = frozenset(
            ln.strip().lower() for ln in BLOCK_FILE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#"))
        _block_cache = (mt, emails)
    return email in _block_cache[1]


def _rate_ok(email: str) -> bool:
    now = time.time()
    q = _rate[email]
    while q and q[0] < now - RATE_WIN:
        q.popleft()
    if len(q) >= RATE_N:
        return False
    q.append(now)
    return True


def _log_access(request: Request, email: str, work: str, name: str, status: int):
    rec = {
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "email": email,
        "ip": request.headers.get("cf-connecting-ip")
              or (request.client.host if request.client else ""),
        "work": work, "name": name, "status": status,
        "range": request.headers.get("range", ""),
        "ua": (request.headers.get("user-agent") or "")[:80],
    }
    try:
        ACCESS_LOG.parent.mkdir(exist_ok=True)
        with ACCESS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass

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

def _display_title(work: str, fallback: str) -> str:
    """narration 의 title 이 ASCII 작업ID 그대로면(야간 배치가 --title $work 로 넘긴 실측:
    kafka·nalgae) 사실파일 [서지]·구작 표에서 한글 제목을 찾는다."""
    if re.search(r"[가-힣]", fallback):
        return fallback
    sys.path.insert(0, str(BASE / "scripts"))
    try:
        from publish_final import work_meta
        t = work_meta(work)[1]
        return t if t else fallback
    except Exception:
        return fallback


def _categories() -> dict:
    """작품별 권역·갈래. 전체보기 화면 왼쪽 필터가 쓴다.

    발행 분류(고전/현대)는 발행작이 사실상 전부 '고전'이라 필터가 되지 못하고,
    작가 이름은 한글로 음차되어 있어 국적을 자동으로 가를 수 없다. 그래서
    works/categories.json 에 사람이 적어 둔다."""
    try:
        return json.loads((BASE / "works" / "categories.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _blurbs() -> dict:
    """작품별 한 줄 설명과 분위기 묶음. 카드가 미끼 문장과 폰트 클래스를 얻는다."""
    try:
        return json.loads((BASE / "works" / "blurbs.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _seasons() -> dict:
    """작품별 계절과 추천 한 줄. 계절 추천관이 쓴다 — 뚜렷한 작품만 실려 있다."""
    try:
        return json.loads((BASE / "works" / "seasons.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _countries() -> dict:
    """작품별 나라(이름·ISO3·숫자 id). 세계 문학 전집과 나라별 지도가 쓴다 — works/countries.json."""
    try:
        d = json.loads((BASE / "works" / "countries.json").read_text(encoding="utf-8"))
        d.pop("_note", None)
        return d
    except Exception:
        return {}


def _era(work: str) -> tuple[str, bool]:
    """(시대, KEI 소장 여부). 사실파일 첫 줄이 '[포맷] 소개형'이면 저작권이 살아 있는
    현대소설이다 — 추천작품의 '현대소설' 칸이 이것으로 고전과 갈린다. 소장 여부는
    [소장] 줄에 '미소장'이 없으면 참."""
    for name in (f"auto_{work}.txt", f"{work}.txt"):
        f = BASE / "facts" / name
        if f.is_file():
            try:
                lines = f.read_text(encoding="utf-8").splitlines()
            except OSError:
                break
            modern = bool(lines) and "소개형" in lines[0]
            held = next((("미소장" not in l) for l in lines if l.startswith("[소장]")), False)
            return ("현대" if modern else "고전"), held
    return "고전", False


def _works():
    """output/<작품>/narration*.json 을 훑어 작품 목록을 만든다.
    별도 테이블 없이 파일시스템을 진실로 쓴다 -- 파이프라인이 파일로 돌기 때문."""
    out = []
    cats = _categories()
    blurbs = _blurbs()
    seasons = _seasons()
    countries = _countries()
    if not OUTPUT.exists():
        return out
    for d in sorted(p for p in OUTPUT.iterdir() if p.is_dir()):
        era, kei = _era(d.name)
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
                "title": _display_title(d.name, data.get("title", d.name)),
                "sentences": data.get("sentences", []),
                "passed": data.get("passed"),
                "issues": data.get("issues", []),
                "region": (cats.get(d.name) or {}).get("region", "기타"),
                "genre": (cats.get(d.name) or {}).get("genre", "기타"),
                "blurb": (blurbs.get(d.name) or {}).get("blurb", ""),
                "mood": (blurbs.get(d.name) or {}).get("mood", ""),
                "season": (seasons.get(d.name) or {}).get("season", ""),
                "season_note": (seasons.get(d.name) or {}).get("note", ""),
                "country": (countries.get(d.name) or {}).get("country", ""),
                "country_code": (countries.get(d.name) or {}).get("code", ""),
                "country_num": (countries.get(d.name) or {}).get("num", ""),
                "era": era,
                "kei": kei,
            })
    return out


class ViewIn(BaseModel):
    work: str


@app.post("/api/stats/view")
def add_view(body: ViewIn):
    """재생 1회 기록. 실재하는 작품만 센다 — 아무 문자열이나 쌓이면 통계가 오염된다."""
    d = OUTPUT / body.work
    if not d.is_dir() or not list(d.glob("final*.mp4")):
        raise HTTPException(404, "없는 작품")
    db.add_view(body.work)
    return {"ok": True}


@app.get("/api/stats/summary")
def stats_summary():
    """작품별 누적·이달 조회수와 이달의 순위. 홈의 '이달의 인기작'과 관리자 통계가 쓴다."""
    st = db.view_stats()
    top = sorted(st["month"].items(), key=lambda x: -x[1])[:12]
    return {**st, "monthly_top": [{"work": w, "views": n} for w, n in top]}


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

@app.get("/api/works/{work}/prompts")
def prompts(work: str):
    """장면마다 실제로 들어간 그림·움직임 프롬프트. 이상한 그림이 나왔을 때
    무엇이 들어갔는지 바로 볼 수 있어야 원인을 재구성하지 않는다."""
    f = OUTPUT / f"{work}_kf" / "prompts.json"
    if not f.exists():
        return {"prompts": {}}
    try:
        return {"prompts": json.loads(f.read_text(encoding="utf-8"))}
    except (json.JSONDecodeError, OSError):
        return {"prompts": {}}


@app.get("/api/works/{work}/keyframes")
def keyframes(work: str):
    d = OUTPUT / f"{work}_kf"
    if not d.exists():
        return {"images": []}
    # 컷 번호 순. 문자열 정렬은 night_s10 을 night_s1 앞에 세워 카드 표지가 10번 컷이
    # 되었다(실측 2026-09-07 서동과 선화공주 — 세 팔 그림이 썸네일로). 번호 없는 파일은 뒤로.
    def cut_no(f: Path) -> tuple:
        m = re.search(r"_s(\d+)_", f.name)
        return (0, int(m.group(1)), f.name) if m else (1, 0, f.name)
    return {"images": [f.name for f in sorted(d.glob("*.png"), key=cut_no)]}


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
    # 야간 배치 산출물은 사람이 승인하기 전이라 공개 페이지에 내보내지 않는다
    # (SPEC §4). 관리자 화면에서는 "야간(승인 전)"으로 따로 보인다.
    if name.startswith("final_night"):
        return "night", ver
    return ("final" if name.startswith("final") else "other"), ver


@app.get("/api/works/{work}/videos")
def videos(work: str, request: Request):
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
    # 승인본(final) → 야간 산출물(night) → 나머지 순
    order = {"final": 0, "night": 1, "other": 2, "scene": 3}
    out.sort(key=lambda x: (order.get(x["kind"], 9), x["updated"]))
    mode, email = _viewer(request)
    if mode == "watch":
        if not email:
            raise HTTPException(403, "로그인이 필요합니다")
        for v in out:                      # 시청 호스트: 이메일에 묶인 서명 URL 로만 재생
            v["url"] = _signed_url(email, work, v["name"])
    return {"videos": out}


@app.get("/api/works/{work}/prev")
def prev_versions(work: str):
    """이전 판 목록 — output/<work>/prev/<도장>/ (scripts/archive_prev.py 가 만든다).
    도장별로 완성본·정지 화면(frames)·옛 키프레임(kf)·클립 수·옛 원고를 돌려준다."""
    if not re.fullmatch(r"[\w.\-]+", work):
        raise HTTPException(400, "bad path")
    root = OUTPUT / work / "prev"
    out = []
    if root.exists():
        for d in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True):
            finals = [f.name for f in sorted(d.glob("*.mp4"))]
            frames = [f"frames/{f.name}" for f in sorted((d / "frames").glob("*.png"))] if (d / "frames").exists() else []
            kfs = []
            if (d / "kf").exists():
                def cut_no(f):
                    m = re.search(r"_s(\d+)_", f.name)
                    return (0, int(m.group(1))) if m else (1, 0)
                kfs = [f"kf/{f.name}" for f in sorted((d / "kf").glob("*.png"), key=cut_no)]
            clips = len(list((d / "clips").glob("*.mp4"))) if (d / "clips").exists() else 0
            sents, title = None, None
            nar = d / "narration_night.json"
            if nar.exists():
                try:
                    j = json.loads(nar.read_text(encoding="utf-8"))
                    sents, title = j.get("sentences"), j.get("title")
                except (json.JSONDecodeError, OSError):
                    pass
            m = re.match(r"(\d{4})(\d{2})(\d{2})_?(\d{2})?(\d{2})?", d.name)
            when = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" + (f" {m.group(4)}:{m.group(5)}" if m and m.group(4) and m.group(5) else "") if m else d.name
            fin = d / finals[0] if finals else None
            out.append({
                "stamp": d.name, "when": when, "final": finals[0] if finals else None,
                "duration": _duration(fin) if fin else None, "size": fin.stat().st_size if fin else 0,
                "frames": frames, "keyframes": kfs, "clips": clips, "sentences": sents, "title": title,
                "has_treatment": (d / "treatment.json").exists(), "has_prompts": (d / "prompts.json").exists(),
            })
    return {"versions": out}


@app.get("/api/files/prev/{work}/{stamp}/{path:path}")
def get_prev_file(work: str, stamp: str, path: str):
    """이전 판 파일 — 완성본(.mp4)·정지 화면(frames/…)·옛 키프레임(kf/…)·클립(clips/…)."""
    if not re.fullmatch(r"[\w.\-]+", work) or not re.fullmatch(r"[\w.\-]+", stamp) \
            or not re.fullmatch(r"(frames/|kf/|clips/)?[\w.\-가-힣 ]+", path):
        raise HTTPException(400, "bad path")
    p = OUTPUT / work / "prev" / stamp / path
    if not p.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(p)


@app.get("/api/files/{kind}/{work}/{name}")
def get_file(kind: str, work: str, name: str, request: Request, e: int = 0, s: str = ""):
    """kind: keyframe | video. 경로 조작 방지를 위해 단순 파일명만 허용한다.

    시청 호스트의 영상은 서명(e=만료, s=HMAC(email|work|name|e))이 맞아야 준다.
    """
    if not re.fullmatch(r"[\w.\-가-힣]+", name) or not re.fullmatch(r"[\w.\-]+", work):
        raise HTTPException(400, "bad name")
    p = (OUTPUT / f"{work}_kf" / name) if kind == "keyframe" else (OUTPUT / work / name)
    if kind not in ("keyframe", "video"):
        raise HTTPException(400, "bad kind")
    mode, email = _viewer(request)
    if mode == "watch" and kind == "video":
        if not email or _blocked(email):
            _log_access(request, email, work, name, 403)
            raise HTTPException(403, "차단된 사용자입니다")
        if e < time.time() or not hmac.compare_digest(s, _sign(email, work, name, e)):
            _log_access(request, email, work, name, 403)
            raise HTTPException(403, "링크가 만료됐거나 다른 사람의 링크입니다")
        dest = request.headers.get("sec-fetch-dest")
        if dest and dest not in ("video", "audio"):   # 브라우저가 밝힌 용도가 재생이 아니면 거절
            _log_access(request, email, work, name, 403)
            raise HTTPException(403, "재생 요청만 받습니다")
        if not _rate_ok(email):
            _log_access(request, email, work, name, 429)
            raise HTTPException(429, "요청이 너무 잦습니다. 잠시 뒤 다시 시도하세요")
        _log_access(request, email, work, name, 200)
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


# ---------- 인기 작품 (공개 페이지 캐러셀) ----------
# 조회수 지표가 아직 없으므로 사람이 고른 순서를 파일로 둔다.
# 순서가 곧 노출 순서다. 없으면 공개 페이지가 승인본 최신순으로 대체한다.

FEATURED = BASE / "works" / "featured.json"


class FeaturedIn(BaseModel):
    works: list[str]


@app.get("/api/featured")
def get_featured():
    if not FEATURED.exists():
        return {"works": []}
    try:
        return {"works": json.loads(FEATURED.read_text(encoding="utf-8")).get("works", [])}
    except (json.JSONDecodeError, OSError):
        return {"works": []}


@app.put("/api/featured")
def put_featured(body: FeaturedIn):
    """작품 ID 목록. 실제 존재하는 작품만 남긴다 — 지워진 작품이 캐러셀에 남지 않게."""
    known = {w["work"] for w in _works()}
    picked = [w for w in body.works if w in known]
    FEATURED.parent.mkdir(exist_ok=True)
    FEATURED.write_text(json.dumps({"works": picked}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    return {"works": picked}


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


# 정보나루 호출은 한 곳으로 모은다: 키·JSON·디스크 캐시·장애 시 옛 응답으로 버티기.
def _d4l(path: str, params: dict, cache_name: str, ttl: int) -> dict:
    import urllib.parse
    import urllib.request
    key = _env("DATA4LIBRARY_KEY")
    if not key:
        raise HTTPException(503, "DATA4LIBRARY_KEY 미설정")
    _LOAN_DIR.mkdir(parents=True, exist_ok=True)
    f = _LOAN_DIR / f"{cache_name}.json"
    if f.exists() and time.time() - f.stat().st_mtime < ttl:
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    q = urllib.parse.urlencode({"authKey": key, "format": "json", **params})
    try:
        with urllib.request.urlopen(f"https://data4library.kr/api/{path}?{q}", timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        resp = data.get("response", data)
        if "error" in resp:
            raise RuntimeError(str(resp["error"]))
        f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
    except Exception as e:  # 하루 호출 상한·정보나루 장애·재기동 — 만료된 캐시라도 있으면 그걸로
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        raise HTTPException(502, f"정보나루 호출 실패: {type(e).__name__}")


def _clean_author(a: str) -> str:
    """'지은이: 한강 ;옮긴이: 양윤옥' → '한강'. 첫 사람만, 역할 접두어는 뗀다."""
    head = re.split(r"\s*;\s*", a or "")[0]
    head = re.sub(r"(지은이|지음|글·그림|글|그림|옮김|옮긴이|엮음|엮은이|저자|원작)\s*:?", "", head)
    return head.strip(" :·,")


def _norm_doc(b: dict, i: int) -> dict:
    cover = (b.get("bookImageURL") or "").replace("http://", "https://")
    cls = (b.get("class_nm") or "").split(">")[0].strip()
    return {
        "rank": int(b.get("ranking") or b.get("no") or i),
        # '종의 기원 =정유정 장편소설 /The origin…' 처럼 = / : 뒤는 부제·병기 — 앞만 쓴다
        "title": re.split(r"\s*[:=/]\s*", (b.get("bookname") or "").strip())[0].strip(),
        "author": _clean_author(b.get("authors") or ""),
        "publisher": b.get("publisher", ""),
        "year": str(b.get("publication_year") or ""),
        "isbn": b.get("isbn13", ""),
        "cover": cover,
        "cls": cls,
        "loans": int(b.get("loan_count") or 0),
        "holding": "unknown",
    }


def _attach_holdings(books: list) -> None:
    """KEI 소장: 캐시된 것은 즉시, 나머지는 백그라운드로 채워 같은 dict 를 갱신한다."""
    sys.path.insert(0, str(BASE / "scripts"))
    from kei_holdings import first_author
    _hold_load()
    pending = []
    for b in books:
        hit = _HOLD_CACHE.get(f"{b['title']}|{first_author(b['author'])}")
        if hit:
            _hold_fields(b, hit["res"])  # 만료된 값이라도 먼저 보여 주고
        if not hit or time.time() - hit["ts"] >= _HOLD_TTL:
            pending.append(b)           # 뒤에서 새로 받아 캐시를 갈아 둔다
    if pending:
        import threading
        def _fill():
            for b in pending:
                try:
                    _hold_fields(b, _kei_lookup(b["title"], first_author(b["author"])))
                except Exception:
                    pass  # 도서관 서버 장애 — unknown 으로 두고 다음 기회에
        threading.Thread(target=_fill, daemon=True).start()


def _last_month() -> tuple:
    end = _dt.date.today().replace(day=1) - _dt.timedelta(days=1)
    return end.replace(day=1).isoformat(), end.isoformat()


@app.get("/api/books/popular")
def popular_books(start: str = "", end: str = "", limit: int = 30,
                  kdc: str = "", age: str = "", refresh: bool = False):
    """인기대출도서. 지난달 전국 순위. age(0;6;8 어린이 / 14 청소년 / 20;30;40;50;60 어른),
    kdc(0~9 대주제, ; 로 여럿) 로 거른다. 하루 호출 상한이 있으므로 월·조건별로 디스크에 둔다."""
    if not end:
        start, end = _last_month()
    ck = f"{start}:{end}:{limit}:{kdc}:{age}"
    if not refresh and ck in _BOOK_CACHE:
        return _BOOK_CACHE[ck]
    # 권별 ISBN 이 따로 오는 시리즈(흔한남매 등)를 접으면 30줄이 12권으로 준다(실측
    # 2026-08). 접은 뒤에도 limit 권이 남도록 넉넉히 받는다.
    params = {"startDt": start, "endDt": end, "pageNo": 1, "pageSize": min(limit * 6, 200)}
    if kdc:
        params["kdc"] = kdc
    if age:
        params["age"] = age
    tag = f"{start}_{(age or 'all').replace(';', '-')}_{(kdc or 'all').replace(';', '-')}"
    data = _d4l("loanItemSrch", params, f"raw_{tag}", 40 * 24 * 3600)
    resp = data.get("response", data)
    books = [_norm_doc(row.get("doc", row), i) for i, row in enumerate(resp.get("docs", []), 1)]
    books = _dedupe_rank(books)[:limit]
    _attach_holdings(books)
    _bridge_attach(books)
    if not kdc and not age:
        _rank_delta(books, start)
    out = {"period": {"start": start, "end": end}, "kdc": kdc, "age": age, "books": books}
    _BOOK_CACHE[ck] = out
    return out


@app.get("/api/books/trend")
def trend_books():
    """대출 급상승(최근 7일 순위 급등). 정보나루가 검색일 포함 3일치를 주므로 가장 최근 날을 쓴다."""
    today = _dt.date.today().isoformat()
    ck = f"trend:{today}"
    if ck in _BOOK_CACHE:
        return _BOOK_CACHE[ck]
    data = _d4l("hotTrend", {"searchDt": today}, f"trend_{today}", 6 * 3600)
    resp = data.get("response", data)
    results = resp.get("results", [])
    best = None
    for r in results:
        r = r.get("result", r)
        if r.get("docs"):
            best = r
    books, date = [], ""
    if best:
        date = best.get("date", "")
        for i, row in enumerate(best["docs"], 1):
            b = row.get("doc", row)
            d = _norm_doc(b, i)
            d["rank"] = i
            d["difference"] = int(b.get("difference") or 0)
            d["base_rank"] = int(b.get("baseWeekRank") or 0)
            d["past_rank"] = int(b.get("pastWeekRank") or 0)
            books.append(d)
    books = _dedupe_rank(books)
    _attach_holdings(books)
    _bridge_attach(books)
    out = {"date": date, "books": books}
    _BOOK_CACHE[ck] = out
    return out


@app.get("/api/books/keywords")
def book_keywords(limit: int = 40):
    """이달의 키워드(정보나루가 대출 급상승 도서의 소개·서평에서 뽑은 낱말)."""
    start, _ = _last_month()
    month = start[:7]
    data = _d4l("monthlyKeywords", {"month": month}, f"keywords_{month}", 40 * 24 * 3600)
    resp = data.get("response", data)
    words = []
    for k in resp.get("keywords", []):
        k = k.get("keyword", k)
        w = (k.get("word") or "").strip()
        if w and len(w) >= 2:
            words.append({"word": w, "weight": int(float(k.get("weight") or 0))})
    words.sort(key=lambda x: -x["weight"])
    return {"month": month, "keywords": words[:limit]}


@app.get("/api/books/search")
def search_books(q: str, limit: int = 24):
    """제목·저자·키워드로 전국 대출 데이터에서 책을 찾고 KEI 소장을 얹는다."""
    q = (q or "").strip()
    if len(q) < 2:
        raise HTTPException(400, "두 글자 이상")
    ck = f"search:{q}:{limit}"
    if ck in _BOOK_CACHE:
        return _BOOK_CACHE[ck]
    tag = hashlib.md5(q.encode("utf-8")).hexdigest()[:12]
    data = _d4l("srchBooks", {"keyword": q, "pageNo": 1, "pageSize": min(limit * 2, 100),
                              "sort": "loan", "order": "desc"}, f"search_{tag}", 24 * 3600)
    resp = data.get("response", data)
    books = [_norm_doc(row.get("doc", row), i) for i, row in enumerate(resp.get("docs", []), 1)]
    books = _dedupe_rank(books)[:limit]
    _attach_holdings(books)
    _bridge_attach(books)
    out = {"q": q, "found": int(resp.get("numFound") or len(books)), "books": books}
    _BOOK_CACHE[ck] = out
    return out


def _hold_fields(b: dict, res: dict) -> None:
    """소장 여부에서 멈추지 말고 실제로 빌릴 수 있는지까지 알려 준다.
    청구기호와 대출 상태는 Pyxis 조회에 이미 들어 있는데 버리고 있었다."""
    b["holding"] = res.get("holding", "unknown")
    item = (res.get("paper") or res.get("ebook") or [{}])[0]
    b["callno"] = item.get("callno", "")
    b["status"] = item.get("status", "")


def _dedupe_rank(books: list) -> list:
    """같은 책이 권별 ISBN 으로 여러 줄 나온다(흔한남매 실측). 접고 번호를 다시 매긴다 —
    접기만 하고 두면 1,2,3…9,11,13,19 처럼 튀어 고장으로 보인다."""
    seen, out = set(), []
    series = []
    if _BRIDGE_FILE.exists():
        try:
            series = json.loads(_BRIDGE_FILE.read_text(encoding="utf-8")).get("_series", [])
        except (json.JSONDecodeError, OSError):
            series = []
    for b in books:
        k = b["title"].replace(" ", "")
        # 시리즈(흔한남매 …)는 권·부제가 달라도 한 줄로 접는다 — 30위 안에 넷이 앉는다(실측 2026-08).
        for pre in series:
            if k.startswith(pre.replace(" ", "")):
                k = pre
                break
        if k in seen:
            continue
        seen.add(k)
        b["rank"] = len(out) + 1
        out.append(b)
    return out


_BRIDGE_FILE = BASE / "works" / "bridge.json"


def _bridge_attach(books: list) -> None:
    """인기 도서를 우리가 가진 고전 한 편으로 잇는다.

    목록의 책은 전부 저작권 보호작이라 영상으로 만들 수 없다. 이어 주지 않으면
    방문자는 볼 수 없는 책만 보고 나간다 — 목록에서 나갈 길이 없다.
    """
    if not _BRIDGE_FILE.exists():
        return
    try:
        table = json.loads(_BRIDGE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    for b in books:
        hit = table.get(b["title"].replace(" ", ""))
        if hit:
            b["bridge"] = hit


_LOAN_DIR = BASE / "data" / "loans"


def _rank_delta(books: list, start: str) -> None:
    """이번 달 순위를 저장하고 지난달과 비교한다.

    순위 스냅샷만으로는 읽을 것이 없다. 오르내림이 있어야 이야기가 된다.
    첫 달에는 비교 대상이 없으므로 delta 가 붙지 않는다 — 다음 달부터 보인다.
    """
    import datetime as _dt
    _LOAN_DIR.mkdir(parents=True, exist_ok=True)
    cur = {b["title"]: b["rank"] for b in books}
    (_LOAN_DIR / f"{start}.json").write_text(
        json.dumps(cur, ensure_ascii=False), encoding="utf-8")
    try:
        d = _dt.date.fromisoformat(start)
        prev = (d - _dt.timedelta(days=1)).replace(day=1).isoformat()
    except ValueError:
        return
    f = _LOAN_DIR / f"{prev}.json"
    if not f.exists():
        return
    try:
        before = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    for b in books:
        was = before.get(b["title"])
        b["delta"] = (was - b["rank"]) if was else None   # None = 지난달에 없던 책


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


_OURS_FILE = BASE / "data" / "loans" / "ours.json"
_NOAUTH = re.compile(r"미상|전래|설화|민담|해동염사|작자|원류")


@app.get("/api/books/ours")
def our_books():
    """책방 = 우리 영상이 있는 책만. 작품마다 정보나루 전국 대출 순위(지난달, 가장 많이 읽힌 판
    기준 — scripts/our_ranks.py 가 달마다 굽는 data/loans/ours.json)와 KEI 소장을 붙인다.
    급상승·키워드·'이어지는 고전' 같은 억지 연결은 두지 않는다(사용자 지시 09-10)."""
    try:
        data = json.loads(_OURS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(503, "순위 파일 없음 — scripts/our_ranks.py 를 먼저 돌리세요")
    books = []
    for w, r in data.get("works", {}).items():
        author = re.sub(r"\(.*?\)", "", r.get("author") or "").strip()
        b = {
            "work": w, "title": r.get("title", w), "author": author,
            "isbn": r.get("isbn") or "", "edition_title": r.get("edition_title") or "",
            "edition_author": _clean_author(r.get("edition_author") or ""),
            "publisher": r.get("publisher") or "", "year": r.get("year") or "",
            "cover": r.get("cover") or "",
            # 정보나루 설명에는 &lt;망원동 브라더스&gt; 같은 엔티티와 태그가 섞여 온다
            "description": re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", r.get("description") or ""))).strip(),
            "rank": r.get("rank"), "rank_month": r.get("rank_month") or "",
            "month_loans": r.get("month_loans") or 0, "total_loans": r.get("total_loans") or 0,
            "history": r.get("history") or [], "editions": r.get("editions") or 0,
            "edition_kind": r.get("edition_kind") or "",
            "holding": "unknown",
        }
        b["kei_author"] = "" if _NOAUTH.search(author) else author
        books.append(b)
    # KEI 조회 키는 title|author — 미상·전래 저자는 저자 없이 제목만으로 묻는다
    probe = [{"title": b["title"], "author": b["kei_author"]} for b in books]
    _attach_holdings(probe)
    for b, pr in zip(books, probe):
        for k in ("holding", "callno", "status"):
            b[k] = pr.get(k, "" if k != "holding" else "unknown")
        b.pop("kei_author", None)
    books.sort(key=lambda b: (b["rank"] is None, b["rank"] or 0, -b["total_loans"]))
    m = re.match(r"(\d{4})년 (\d{2})월", data.get("month", ""))
    stamp = _OURS_FILE.parent / "books_updated.txt"     # scripts/books_daily.sh 가 매일 09:00 적는다
    try:
        updated = stamp.read_text(encoding="utf-8").strip()
    except OSError:
        updated = data.get("built", "")
    return {"month": f"{m.group(1)}년 {int(m.group(2))}월" if m else data.get("month", ""),
            "built": data.get("built", ""), "updated": updated, "count": len(books),
            "ranked": sum(1 for b in books if b["rank"]), "books": books}
