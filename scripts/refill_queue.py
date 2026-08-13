#!/usr/bin/env python3
"""인기대출도서 -> 야간 제작 큐 자동 적재.

정보나루 인기대출 목록 중 **KEI 도서관 소장본**만 골라 사실파일을 만들고
works/queue.txt 에 TSV 한 줄씩 붙인다. 야간 배치는 큐의 첫 줄부터 소비한다.

제외 규칙
  - KEI 미소장: 마무리 문구("우리 도서관에 있습니다")가 거짓이 된다.
  - 이미 큐/완료/제작 중인 작품: 중복 제작 방지.
  - 실존 참사·실존 인물을 다룬 작품(SENSITIVE): 무인 생성 이미지로 재현하면
    사실 왜곡과 피해자 존엄 훼손 위험이 있다. 사람이 검수한 트리트먼트로만 만든다.
  - 아동·학습만화 등 영상 포맷이 맞지 않는 분류.

사용:
  venv/bin/python scripts/refill_queue.py --limit 20 --max-add 6
  venv/bin/python scripts/refill_queue.py --limit 20 --max-add 6 --dry-run
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from fetch_book_facts import build, slug  # noqa: E402

QUEUE = BASE / "works" / "queue.txt"
DONE = BASE / "works" / "done.txt"
API = "http://127.0.0.1:8010/api/books/popular"

# 실존 참사/실존 인물 소재 — 무인 자동 제작에서 제외한다.
SENSITIVE = ["소년이 온다", "작별하지 않는다", "제주 4·3", "세월호", "5·18"]
# 영상 포맷이 맞지 않는 분류
SKIP_CLASS = ["학습만화", "그림책", "만화", "문제집", "수험서"]

# 현대 한국문학 기본 화풍: 사건 재연이 아니라 사물·공간 정물로 간다.
STYLE_MODERN = (
    "quiet contemporary Korean editorial illustration, still life of everyday objects "
    "and empty interiors, soft window light, muted paper palette with one warm accent, "
    "gentle grain texture, no crowds, no violence, no text. "
)
ENDING_KEI = "이 책은 KEI 도서관에서 만나볼 수 있습니다"


def popular(limit: int) -> list:
    with urllib.request.urlopen(f"{API}?limit={limit}", timeout=120) as r:
        return json.loads(r.read().decode("utf-8")).get("books", [])


def existing_ids() -> set:
    """큐·완료 기록·제작 산출물에서 이미 다룬 작품 ID 를 모은다."""
    ids = set()
    if QUEUE.exists():
        for line in QUEUE.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                ids.add(line.split("\t")[0].strip())
    if DONE.exists():
        for line in DONE.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")  # 완료 기록은 앞에 타임스탬프가 붙는다
            if len(parts) > 1:
                ids.add(parts[1].strip())
    for p in (BASE / "output").glob("*/narration_night.json"):
        ids.add(p.parent.name)
    return ids


def reason_to_skip(b: dict, have: set) -> str:
    """조회 전에 거를 수 있는 사유만 본다. 소장 여부는 build() 로 직접 확인한다
    (목록의 holding 은 백그라운드 채움 중이라 unknown 일 수 있다)."""
    t = b.get("title", "")
    if any(s in t for s in SENSITIVE):
        return "민감 소재 — 사람 검수 필요"
    if any(s in t + b.get("author", "") for s in SKIP_CLASS):
        return "영상 포맷 부적합"
    if slug(t) in have:
        return "이미 큐/완료됨"
    return ""


def main():
    p = argparse.ArgumentParser(description="인기대출도서를 야간 큐에 적재")
    p.add_argument("--limit", type=int, default=20, help="인기대출 상위 N권 조회")
    p.add_argument("--max-add", type=int, default=6, help="이번에 추가할 최대 편수")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    have = existing_ids()
    added, rows = 0, []
    for b in popular(a.limit):
        if added >= a.max_add:
            break
        why = reason_to_skip(b, have)
        if why:
            print(f"– {b['rank']:>2} {b['title'][:18]:20} 건너뜀: {why}")
            continue
        wid = slug(b["title"])
        text, hold = build(b["title"], b.get("author", ""), b.get("isbn", ""), "intro")
        if hold["holding"] not in ("paper", "ebook", "both"):
            print(f"– {b['rank']:>2} {b['title'][:18]:20} 건너뜀: KEI 미소장")
            continue
        if len(text) < 220:  # 소개문·백과 둘 다 빈약하면 환각 위험이 크다
            print(f"– {b['rank']:>2} {b['title'][:18]:20} 건너뜀: 자료 부족({len(text)}자)")
            continue
        rows.append((BASE / "facts" / f"auto_{wid}.txt", text,
                     "\t".join([wid, f"facts/auto_{wid}.txt", ENDING_KEI, STYLE_MODERN])))
        have.add(wid)
        added += 1
        print(f"+ {b['rank']:>2} {b['title'][:18]:20} → {wid} ({hold['holding']}, {len(text)}자)")

    if a.dry_run:
        print(f"\n[dry-run] {len(rows)}건 추가 예정 — 파일은 쓰지 않았다")
        return
    for path, text, _ in rows:
        path.write_text(text + "\n", encoding="utf-8")
    if rows:
        with QUEUE.open("a", encoding="utf-8") as f:
            for _, _, row in rows:
                f.write(row + "\n")
    left = len([x for x in QUEUE.read_text(encoding="utf-8").splitlines() if x.strip()])
    print(f"\n큐 적재 {len(rows)}건 · 현재 큐 {left}줄")


if __name__ == "__main__":
    main()
