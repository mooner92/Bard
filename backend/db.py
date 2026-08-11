"""작업 큐 저장소 (SQLite).

UI, cron, Claude Cowork가 모두 같은 큐에 작업을 넣는다.
GPU 작업이 편당 20~30분이라 상태를 디스크에 남겨야
프로세스가 죽어도 진행 상황이 보존된다.
"""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "data" / "jobs.db"

# 파이프라인 단계. UI 진행률 표시와 워커 재개 지점에 함께 쓴다.
STAGES = ["queued", "script", "shotlist", "clips", "narration", "audio", "assemble", "done"]


def now() -> str:
    """ISO 8601 UTC. 문자열로 넣어도 사전순 = 시간순이 된다."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@contextmanager
def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    # 워커와 API가 동시에 붙으므로 WAL로 읽기/쓰기 경합을 줄인다.
    c.execute("PRAGMA journal_mode=WAL")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL DEFAULT '',
                concept     TEXT NOT NULL,
                params      TEXT NOT NULL DEFAULT '{}',
                source      TEXT NOT NULL DEFAULT 'ui',
                status      TEXT NOT NULL DEFAULT 'pending',
                stage       TEXT NOT NULL DEFAULT 'queued',
                progress    INTEGER NOT NULL DEFAULT 0,
                error       TEXT,
                video_path  TEXT,
                artifacts   TEXT NOT NULL DEFAULT '{}',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at)")


def create(concept: str, params: dict, title: str = "", source: str = "ui") -> str:
    jid = uuid.uuid4().hex[:12]
    t = now()
    with conn() as c:
        c.execute(
            "INSERT INTO jobs (id, title, concept, params, source, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (jid, title, concept, json.dumps(params, ensure_ascii=False), source, t, t),
        )
    return jid


def _row(r) -> dict:
    d = dict(r)
    for k in ("params", "artifacts"):
        try:
            d[k] = json.loads(d[k] or "{}")
        except json.JSONDecodeError:
            d[k] = {}
    return d


def get(jid: str):
    with conn() as c:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    return _row(r) if r else None


def list_jobs(limit: int = 100) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row(r) for r in rows]


def update(jid: str, **fields):
    if not fields:
        return
    if isinstance(fields.get("artifacts"), dict):
        fields["artifacts"] = json.dumps(fields["artifacts"], ensure_ascii=False)
    fields["updated_at"] = now()
    sets = ", ".join(f"{k}=?" for k in fields)
    with conn() as c:
        c.execute(f"UPDATE jobs SET {sets} WHERE id=?", (*fields.values(), jid))


def claim_next():
    """대기 중인 가장 오래된 작업 하나를 원자적으로 선점해 반환.

    워커를 GPU당 하나씩 띄울 것이므로, 두 워커가 같은 작업을 집지 않도록
    UPDATE ... WHERE status='pending' 의 rowcount로 선점 성공을 판정한다.
    """
    with conn() as c:
        r = c.execute(
            "SELECT id FROM jobs WHERE status='pending' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if not r:
            return None
        cur = c.execute(
            "UPDATE jobs SET status='running', stage='script', updated_at=? "
            "WHERE id=? AND status='pending'",
            (now(), r["id"]),
        )
        if cur.rowcount == 0:
            return None  # 다른 워커가 먼저 가져갔다
        row = c.execute("SELECT * FROM jobs WHERE id=?", (r["id"],)).fetchone()
    return _row(row)


def reset_stuck():
    """워커가 비정상 종료되면 running이 남는다. 기동 시 pending으로 되돌린다."""
    with conn() as c:
        c.execute(
            "UPDATE jobs SET status='pending', stage='queued', progress=0, updated_at=?"
            " WHERE status='running'",
            (now(),),
        )
