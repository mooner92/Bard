#!/usr/bin/env python3
"""완성본을 /data/bard/video 아래 사람이 보기 좋은 구조로 내보낸다.

파이프라인 저장소(output/ = /data/bard/pipeline)는 기계용 평면 구조라 찾기 어렵다.
완성될 때마다 카테고리·한글 제목으로 정리된 사본을 만든다 — 같은 파일시스템이므로
**하드링크**라 용량을 더 쓰지 않는다.

  /data/bard/video/
    고전/날개/날개_48초_20260814.mp4
    현대/불편한 편의점/불편한 편의점_45초_20260814.mp4

카테고리는 사실파일의 [포맷] 선언에서 나온다(각색형=고전, 소개형=현대).
한글 제목은 [서지] 줄의 첫 항목이다. 원본이 재인코딩되면 링크가 낡으므로
같은 이름이 있으면 지우고 다시 건다.

사용:
  venv/bin/python scripts/publish_final.py --work nalgae
  venv/bin/python scripts/publish_final.py --all
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "output"
DEST = Path("/data/bard/video")
# 사실파일 이전 시대(수동 제작) 작품의 한글 제목
LEGACY_TITLES = {"tolstoy": "사람은 무엇으로 사는가", "mobydick": "모비딕", "kafka": "변신"}


def work_meta(work: str) -> tuple:
    """사실파일에서 (카테고리, 한글 제목)을 뽑는다. 없으면 구작 규칙."""
    f = BASE / "facts" / f"auto_{work}.txt"
    cat, title = "기타", work
    if f.exists():
        t = f.read_text(encoding="utf-8")
        if "[포맷] 각색형" in t:
            cat = "고전"
        elif "[포맷] 소개형" in t:
            cat = "현대"
        m = re.search(r"^\[서지\]\s*([^/\n]+)", t, re.M)
        if m and m.group(1).strip():
            title = m.group(1).strip()
    else:
        nar = OUT / work / "narration_night.json"
        if not nar.exists():
            cands = sorted((OUT / work).glob("narration*.json")) if (OUT / work).exists() else []
            nar = cands[-1] if cands else nar
        if nar.exists():
            title = json.loads(nar.read_text(encoding="utf-8")).get("title", work)
        cat = "고전"   # 사실파일 없는 구작(모비딕·카프카·톨스토이)은 전부 고전 라인
        title = LEGACY_TITLES.get(work, title)
    return cat, re.sub(r'[\\/:*?"<>|]', " ", title).strip()


def publish(work: str) -> str:
    src = OUT / work / "final_night.mp4"
    if not src.exists():
        cands = sorted((OUT / work).glob("final*.mp4")) if (OUT / work).exists() else []
        cands = [c for c in cands if "compressed" not in c.name]
        if not cands:
            return f"– {work}: 완성본 없음"
        src = cands[-1]
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(src)], capture_output=True, text=True)
    sec = int(float(r.stdout.strip() or 0))
    cat, title = work_meta(work)
    day = datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y%m%d")
    d = DEST / cat / title
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f"{title}_{sec}초_{day}.mp4"
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)          # 같은 파일시스템 — 용량 0 추가
    except OSError:
        import shutil
        shutil.copy2(src, dst)     # 파일시스템이 갈라지면 복사로 대체
    return f"+ {cat}/{title}/{dst.name}"


def main():
    p = argparse.ArgumentParser(description="완성본 카테고리 발행")
    p.add_argument("--work")
    p.add_argument("--all", action="store_true")
    a = p.parse_args()
    if a.all:
        works = sorted({d.parent.name for d in OUT.glob("*/final*.mp4")
                        if not d.parent.name.startswith("_")})
    else:
        works = [a.work] if a.work else []
    if not works:
        sys.exit("--work 또는 --all")
    for w in works:
        print(publish(w))


if __name__ == "__main__":
    main()
