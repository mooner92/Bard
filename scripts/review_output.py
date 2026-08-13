#!/usr/bin/env python3
"""완성작 자가점검 — 기계가 잴 수 있는 것만 재서 표로 남긴다.

사람이 눈으로 볼 시간은 짧다. 그 전에 숫자로 걸러낼 수 있는 결함
(길이 미달, 감속 과다, 음량 이탈, 트랙 누락, 대본 검증 실패)을 먼저 잡는다.

판정 기준
  길이   45초 ±3 (docs/PLAN.md 45초 명세)
  감속   클립 감속 1.5배 이하 — 넘으면 화면이 늘어져 보인다
  음량   -16 ~ -12 LUFS (유튜브 -14 기준), 트루피크 -1.0 dBTP 이하
  대본   하네스 검증 통과, 문장 길이 편차 4자 이상(리듬)

사용:
  venv/bin/python scripts/review_output.py --work tolstoy
  venv/bin/python scripts/review_output.py --all
"""
import argparse
import json
import re
import statistics
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "output"
REVIEW = BASE / "logs" / "review"
SPEC_SEC, SPEC_TOL, MAX_SLOWDOWN = 45.0, 3.0, 1.5


def probe(path: Path, entries: str) -> str:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries,
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return r.stdout.strip()


def dur(path: Path) -> float:
    try:
        return float(probe(path, "format=duration") or 0)
    except ValueError:
        return 0.0


def loudness(path: Path) -> dict:
    """ffmpeg loudnorm 분석 패스. 통합 음량(LUFS)과 트루피크를 얻는다."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
        return {"lufs": float(d["input_i"]), "peak": float(d["input_tp"])}
    except Exception:
        return {}


def review(work: str) -> dict:
    w = {"work": work, "flags": [], "ok": True}
    nar_p = OUT / work / "narration_night.json"
    final = OUT / work / "final_night.mp4"

    if nar_p.exists():
        nar = json.loads(nar_p.read_text(encoding="utf-8"))
        lens = [len(s) for s in nar["sentences"]]
        sd = round(statistics.pstdev(lens), 1)
        w["script"] = {
            "passed": nar.get("passed"), "issues": len(nar.get("issues") or []),
            "tone": nar.get("tone", "-"), "sentences": len(lens),
            "len_min": min(lens), "len_max": max(lens), "len_sd": sd,
        }
        if not nar.get("passed"):
            w["flags"].append(f"대본 검증 불합격 {len(nar.get('issues') or [])}건")
        if sd < 4:
            w["flags"].append(f"문장 길이가 균일(편차 {sd}) — 리듬 부족")

    def idx(p):
        m = re.search(r"s(\d+)", p.name)
        return int(m.group(1)) if m else 0

    wavs = sorted((OUT / "tts").glob(f"{work}_night_s*.wav"), key=idx)
    clips = sorted((OUT / f"{work}_i2v").glob("night_s*.mp4"), key=idx)
    if wavs and clips:
        slows = []
        for a, v in zip(wavs, clips):
            cd = dur(v)
            slows.append(round(dur(a) / cd, 2) if cd else 0)
        w["clips"] = {"count": len(clips), "slowdown_max": max(slows), "slowdown": slows}
        over = [i + 1 for i, s in enumerate(slows) if s > MAX_SLOWDOWN]
        if over:
            w["flags"].append(f"감속 {MAX_SLOWDOWN}배 초과: S{', S'.join(map(str, over))}")

    w["keyframes"] = len(list((OUT / f"{work}_kf").glob("night_s*.png")))

    if final.exists():
        d = dur(final)
        streams = probe(final, "stream=codec_type").splitlines()
        wh = probe(final, "stream=width,height").splitlines()
        w["final"] = {"sec": round(d, 1), "size_mb": round(final.stat().st_size / 2**20, 1),
                      "streams": streams, "res": wh[0] if wh else "?"}
        if abs(d - SPEC_SEC) > SPEC_TOL:
            w["flags"].append(f"길이 {d:.1f}초 — 명세 {SPEC_SEC:.0f}±{SPEC_TOL:.0f}초 이탈")
        if "video" not in streams or "audio" not in streams:
            w["flags"].append("트랙 누락 — 영상/음성 확인 필요")
        ld = loudness(final)
        if ld:
            w["final"].update(ld)
            if not (-16 <= ld["lufs"] <= -12):
                w["flags"].append(f"음량 {ld['lufs']:.1f} LUFS — -14 기준에서 벗어남")
            if ld["peak"] > -1.0:
                w["flags"].append(f"트루피크 {ld['peak']:.1f} dBTP — 클리핑 위험")
    else:
        w["flags"].append("완성본 없음")

    w["ok"] = not w["flags"]
    return w


def fix_loudness(work: str) -> str:
    """음량만 -14 LUFS 로 다시 맞춘다. 영상 트랙은 복사라 재인코딩 손실이 없다."""
    src = OUT / work / "final_night.mp4"
    tmp = src.with_name("final_night.norm.mp4")
    r = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(tmp)],
        capture_output=True, text=True)
    types = probe(tmp, "stream=codec_type").splitlines() if tmp.exists() else []
    if r.returncode != 0 or "video" not in types or "audio" not in types:
        tmp.unlink(missing_ok=True)
        return f"음량 교정 실패: {r.stderr.strip()[:120]}"
    tmp.replace(src)
    return f"음량 교정 완료 → {loudness(src).get('lufs', 0):.1f} LUFS"


def to_md(w: dict) -> str:
    L = [f"# {w['work']} 자가점검", ""]
    s = w.get("script")
    if s:
        verdict = "통과" if s["passed"] else f"불합격 {s['issues']}건"
        L.append(f"- 대본: {verdict} · {s['sentences']}문장 · "
                 f"길이 {s['len_min']}~{s['len_max']}자(편차 {s['len_sd']}) · 톤 {s['tone']}")
    if w.get("clips"):
        L.append(f"- 클립: {w['clips']['count']}개 · 최대 감속 {w['clips']['slowdown_max']}배")
    L.append(f"- 키프레임: {w['keyframes']}장")
    f = w.get("final")
    if f:
        L.append(f"- 완성본: {f['sec']}초 · {f['res'].replace(chr(10), 'x')} · {f['size_mb']}MB"
                 + (f" · {f['lufs']:.1f} LUFS / 피크 {f['peak']:.1f} dBTP" if "lufs" in f else ""))
    L += ["", "## 판정", ""]
    L += ["합격 — 기계 점검에서 걸린 항목 없음"] if w["ok"] else [f"- {x}" for x in w["flags"]]
    return "\n".join(L) + "\n"


def main():
    p = argparse.ArgumentParser(description="완성작 자가점검")
    p.add_argument("--work")
    p.add_argument("--all", action="store_true")
    p.add_argument("--fix-loudness", action="store_true",
                   help="음량이 기준을 벗어나면 -14 LUFS 로 다시 맞춘다(영상 트랙은 복사)")
    a = p.parse_args()
    works = ([d.parent.name for d in OUT.glob("*/final_night.mp4")] if a.all
             else [a.work] if a.work else [])
    if not works:
        p.error("--work 또는 --all 이 필요하다")
    REVIEW.mkdir(parents=True, exist_ok=True)
    for name in sorted(works):
        w = review(name)
        if a.fix_loudness and any("음량" in f or "트루피크" in f for f in w["flags"]):
            print("  " + fix_loudness(name))
            w = review(name)  # 교정 후 다시 재서 기록한다
        (REVIEW / f"{name}.md").write_text(to_md(w), encoding="utf-8")
        print(f"[{'OK' if w['ok'] else '!!'}] {name}: " + (", ".join(w["flags"]) or "이상 없음"))
        print(json.dumps(w, ensure_ascii=False))


if __name__ == "__main__":
    main()
