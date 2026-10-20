#!/usr/bin/env python3
"""백카탈로그 옛 크롭 피해 조사.

야간 로그의 크롭 기록 `{"src": …, "top": …, "bottom": …}` 줄(= 그 클립을 만들 때 실제로
적용된 절단)을 src 별로 마지막 것만 모아, 지금의 판정(crop_keyframe.content_bounds)과
대조한다. '심한 컷' = 위 250행 이상 절단 또는 남은 높이 80% 미만 — 클립 재생성 대상.

사용:
  venv/bin/python scripts/crop_survey.py [--before 2026-09-06] [--md 출력.md] [--json 출력.json]
"""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from crop_keyframe import content_bounds  # noqa: E402

TOP_SEVERE = 250
KEEP_MIN = 0.80
CUT_RE = re.compile(r"night_s(\d+)_")


def load_log_crops() -> dict:
    """src 경로 → 마지막 크롭 기록. 파일명 순(=날짜 순)으로 읽어 나중 기록이 이긴다."""
    last = {}
    for lf in sorted(glob.glob("logs/night/2026-*.log")):
        with open(lf, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                if not ln.startswith('{"src"'):
                    continue
                try:
                    d = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                last[d["src"]] = d
    return last


def by_work_cut(crops: dict) -> dict:
    """(work, cut) → 기록. 같은 컷의 파일명(00001/00002)이 달라도 잡히게."""
    out = {}
    for src, d in crops.items():
        m = re.match(r"output/(.+)_kf/night_s(\d+)_", src)
        if m:
            out[(m.group(1), int(m.group(2)))] = d
    return out


def published(before: str) -> list:
    seen, works = {}, []
    for ln in open("works/done.txt", encoding="utf-8"):
        cols = ln.rstrip("\n").split("\t")
        if len(cols) < 2:
            continue
        day, work = cols[0][:10], cols[1]
        if work not in seen:
            seen[work] = day
            works.append(work)
    return [w for w in works if seen[w] < before]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--before", default="2026-09-06", help="이 날짜 전에 처음 발행된 작품만")
    p.add_argument("--md", default="")
    p.add_argument("--json", default="")
    a = p.parse_args()

    crops = load_log_crops()
    wc = by_work_cut(crops)
    rows = []
    for work in published(a.before):
        kfs = sorted(glob.glob(f"output/{work}_kf/night_s[0-9]*_*.png"),
                     key=lambda s: int(CUT_RE.search(s).group(1)))
        if not kfs:
            continue
        cuts = []
        for kf in kfs:
            i = int(CUT_RE.search(kf).group(1))
            clip = f"output/{work}_i2v/night_s{i}_00001_.mp4"
            if not Path(clip).is_file():
                continue
            old = crops.get(kf) or wc.get((work, i))
            g = np.asarray(Image.open(kf).convert("L"), dtype=np.float32)
            h = g.shape[0]
            nt, nb = content_bounds(g)
            rec = {"cut": i, "h": h, "new_top": nt, "new_bottom": nb}
            if old:
                ot, ob = old["top"], old["bottom"]
                keep = (ob - ot + 1) / h
                rec.update(old_top=ot, old_bottom=ob, keep=round(keep, 3),
                           severe=bool(ot >= TOP_SEVERE or keep < KEEP_MIN),
                           same=bool(abs(nt - ot) <= 20 and abs(nb - ob) <= 20))
            else:
                rec.update(old_top=None, old_bottom=None, keep=None, severe=False, same=None)
            cuts.append(rec)
        n_clips = len(cuts)
        n_logged = sum(1 for c in cuts if c["old_top"] is not None)
        sev = [c for c in cuts if c["severe"]]
        rows.append({"work": work, "clips": n_clips, "logged": n_logged,
                     "severe": len(sev), "severe_cuts": [c["cut"] for c in sev],
                     "cuts": cuts})

    rows.sort(key=lambda r: (-r["severe"], r["work"]))
    tot_sev = sum(r["severe"] for r in rows)
    tot_works = sum(1 for r in rows if r["severe"])
    lines = [f"# 옛 크롭 피해 조사 — {a.before} 이전 발행 {len(rows)}편",
             "", f"심한 컷 {tot_sev}개 / {tot_works}편 (위 {TOP_SEVERE}행 이상 절단 또는 잔존 {int(KEEP_MIN*100)}% 미만)",
             "", "| 작품 | 클립 | 기록 | 심한 컷 | 컷(옛 top/잔존%) → 새 top |", "|---|---|---|---|---|"]
    for r in rows:
        if not r["severe"]:
            continue
        det = ", ".join(f"S{c['cut']}({c['old_top']}/{int(c['keep']*100)}%)→{c['new_top']}"
                        for c in r["cuts"] if c["severe"])
        lines.append(f"| {r['work']} | {r['clips']} | {r['logged']} | {r['severe']} | {det} |")
    lines += ["", "## 심한 컷 없는 작품", "",
              ", ".join(f"{r['work']}({r['clips']}/{r['logged']})" for r in rows if not r["severe"])]
    unlogged = [r["work"] for r in rows if r["logged"] < r["clips"]]
    if unlogged:
        lines += ["", "## 크롭 기록이 클립 수보다 적은 작품(로그 없음 — 옛 판정 불명)", "", ", ".join(unlogged)]
    md = "\n".join(lines)
    print(md)
    if a.md:
        Path(a.md).write_text(md + "\n", encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
