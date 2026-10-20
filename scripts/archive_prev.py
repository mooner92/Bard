#!/usr/bin/env python3
"""이전 버전 보관 — output/<작품>/prev/<도장>/ 에 옛 완성본·원고·그림을 남긴다.

배치는 원고가 그림보다 새로우면 옛 키프레임·클립·완성본을 지우고 다시 굽는다(night_batch_v2.sh).
그러면 관리자 화면에서 이전 판을 볼 수 없어 새 판과 비교가 안 된다(사용자 지적 09-11
"이전버전을 삭제하지말고 남겨두어야 전에거랑 비교가 되지"). 두 경로로 보관한다:

  --current <work>   지금 output 에 있는 산출물(kf·클립·완성본·원고·프롬프트·점검)을
                     prev/<완성본 날짜시각>/ 로 옮긴다. 배치가 지우기 직전에 부른다.
  --held [<work>]    /data/bard/video/_보류/<제목>_<초>초_<날짜>.mp4 (발행 때 밀려난 옛
                     완성본)를 prev/<날짜>_<초>s/ 에 하드링크로 들이고, 컷별 정지 화면을
                     뽑아 frames/ 에 둔다(옛 키프레임은 이미 지워졌으므로 대신 보는 용도).
                     스크래치 remake_old/<work>/ 에 옛 원고가 있으면 가장 최근 옛 판에 붙인다.

보관 폴더 구조:
  output/<work>/prev/<stamp>/
    final.mp4                (또는 원래 이름 그대로의 .mp4 하나)
    narration_night.json     있으면
    treatment.json           있으면
    prompts.json             있으면
    review.md                있으면
    kf/night_s*.png          --current 때만
    clips/night_s*.mp4       --current 때만
    frames/f01.png …         --held 때 완성본에서 뽑은 정지 화면
"""
import argparse, json, os, re, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "output"
HOLD = Path("/data/bard/video/_보류")
SCRATCH_OLD = Path(os.environ.get("REMAKE_OLD", "/tmp/claude-1000/-home-mooner92-aivideo/eaaf2866-ffc9-4a27-90d7-e8d83d21e029/scratchpad/remake_old"))
sys.path.insert(0, str(BASE / "scripts"))


def title_of(work: str) -> str:
    from publish_final import work_meta
    return work_meta(work)[1]


def duration(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def link_or_copy(src: Path, dst: Path):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def extract_frames(final: Path, dest: Path, n: int):
    """완성본에서 n 컷의 중간 지점 정지 화면을 뽑는다(옛 키프레임 대용)."""
    dest.mkdir(parents=True, exist_ok=True)
    d = duration(final)
    if d <= 0:
        return 0
    seg = d / n
    for i in range(n):
        t = seg * i + seg * 0.5
        out = dest / f"f{i+1:02d}.png"
        if out.exists():
            continue
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(final), "-frames:v", "1",
                        "-vf", "scale=540:-2", str(out)], capture_output=True)
    return n


def archive_current(work: str) -> str:
    """배치가 옛 산출물을 지우기 직전에 부른다. 완성본이 없으면 kf 만 있어도 보관한다."""
    wd = OUT / work
    final = wd / "final_night.mp4"
    kfs = sorted((OUT / f"{work}_kf").glob("night_s*.png"))
    clips = sorted((OUT / f"{work}_i2v").glob("night_s*.mp4"))
    if not final.exists() and not kfs:
        return f"– {work}: 보관할 산출물 없음"
    ref = final if final.exists() else kfs[-1]
    stamp = datetime.fromtimestamp(ref.stat().st_mtime).strftime("%Y%m%d_%H%M")
    dest = wd / "prev" / stamp
    if dest.exists():
        stamp += "_" + datetime.now().strftime("%S")
        dest = wd / "prev" / stamp
    dest.mkdir(parents=True, exist_ok=True)
    if final.exists():
        shutil.move(str(final), str(dest / "final.mp4"))
    if kfs:
        (dest / "kf").mkdir(exist_ok=True)
        for f in kfs:
            shutil.move(str(f), str(dest / "kf" / f.name))
    if clips:
        (dest / "clips").mkdir(exist_ok=True)
        for f in clips:
            shutil.move(str(f), str(dest / "clips" / f.name))
    for name, src in (("narration_night.json", wd / "narration_night.json"), ("treatment.json", wd / "treatment.json"),
                      ("prompts.json", OUT / f"{work}_kf" / "prompts.json"), ("review.md", BASE / "logs" / "review" / f"{work}.md")):
        if src.exists():
            shutil.copy2(src, dest / name)
    return f"+ {work}: prev/{stamp} (kf {len(kfs)}, clips {len(clips)}, final {'yes' if (dest/'final.mp4').exists() else 'no'})"


def archive_held(work: str) -> list:
    """_보류 의 옛 완성본을 prev/ 로 들인다. 같은 (초, 날짜) 는 한 번만."""
    title = title_of(work)
    pat = re.compile(re.escape(title) + r"_(\d+)초_(\d{8})\.mp4$")
    wd = OUT / work
    old_scripts = SCRATCH_OLD / work
    done, msgs = [], []
    files = sorted((f for f in HOLD.glob(f"{title}_*초_*.mp4") if pat.search(f.name)),
                   key=lambda f: (pat.search(f.name).group(2), int(pat.search(f.name).group(1))))
    # 발행 때 이름만 바뀐 같은 파일(하드링크)이 여럿 남아 있다 — 내용(inode)별로 가장 늦은 이름 하나만
    by_inode = {}
    for f in files:
        by_inode[f.stat().st_ino] = f
    files = sorted(by_inode.values(), key=lambda f: (pat.search(f.name).group(2), int(pat.search(f.name).group(1))))
    for f in files:
        m = pat.search(f.name)
        sec, day = int(m.group(1)), m.group(2)
        stamp = f"{day}_{sec}s"
        dest = wd / "prev" / stamp
        if (dest / f.name).exists() or (dest / "final.mp4").exists():
            done.append(stamp); continue
        dest.mkdir(parents=True, exist_ok=True)
        link_or_copy(f, dest / f.name)
        # 옛 원고: 문장 수를 알면 그만큼, 모르면 8컷(옛 규격)로 정지 화면을 뽑는다
        n = 8
        nar = old_scripts / "narration_night.json"
        if nar.exists():
            try:
                n = len(json.loads(nar.read_text(encoding="utf-8")).get("sentences", [])) or 8
            except Exception:
                pass
        extract_frames(dest / f.name, dest / "frames", n)
        done.append(stamp); msgs.append(f"+ {work}: prev/{stamp} ({f.name})")
    # 스크래치의 옛 원고는 가장 최근 옛 판에 붙인다
    if files and old_scripts.exists():
        last = wd / "prev" / done[-1]
        for name in ("narration_night.json", "treatment.json"):
            src = old_scripts / name
            if src.exists() and not (last / name).exists():
                shutil.copy2(src, last / name)
    return msgs or [f"– {work}: 보류함에 옛 완성본 없음"]


def archive_final_only(work: str) -> str:
    """재조립 직전: 완성본과 점검만 prev/ 로 옮긴다(kf·클립은 재조립에 쓰므로 둔다).
    같은 경로에 덮어쓰면 발행 하드링크(_보류 포함)까지 새 내용이 되어 옛 판이 사라진다(실측 봄봄 S1 재조립)."""
    wd = OUT / work
    final = wd / "final_night.mp4"
    if not final.exists():
        return f"– {work}: 완성본 없음"
    stamp = datetime.fromtimestamp(final.stat().st_mtime).strftime("%Y%m%d_%H%M")
    dest = wd / "prev" / stamp
    if dest.exists() and (dest / "final.mp4").exists():
        stamp += "_" + datetime.now().strftime("%S")
        dest = wd / "prev" / stamp
    dest.mkdir(parents=True, exist_ok=True)
    shutil.move(str(final), str(dest / "final.mp4"))
    for name, src in (("narration_night.json", wd / "narration_night.json"), ("treatment.json", wd / "treatment.json"),
                      ("prompts.json", OUT / f"{work}_kf" / "prompts.json"), ("review.md", BASE / "logs" / "review" / f"{work}.md")):
        if src.exists():
            shutil.copy2(src, dest / name)
    kfs = sorted((OUT / f"{work}_kf").glob("night_s*.png"))
    if kfs:   # 그림은 하드링크로 곁에 둔다(용량 0) — 이 판이 어떤 그림으로 만들어졌는지
        (dest / "kf").mkdir(exist_ok=True)
        for f in kfs:
            link_or_copy(f, dest / "kf" / f.name)
    return f"+ {work}: prev/{stamp} (final only, kf link {len(kfs)})"


def archive_deliverables() -> list:
    """초기 수동 제작본(deliverables/<work>/*.mp4, deliverables/_old/<work>_*.mp4)을 들인다."""
    msgs = []
    dl = BASE / "deliverables"
    cands = []
    for d in dl.iterdir():
        if d.is_dir() and d.name != "_old":
            cands += [(d.name, f) for f in d.glob("*.mp4") if "압축" not in f.name]
    old = dl / "_old"
    if old.exists():
        for f in old.rglob("*.mp4"):
            if "압축" in f.name or "benchmark" in str(f):
                continue
            m = re.match(r"(kafka|mobydick|tolstoy)", f.name) or re.match(r"(kafka|mobydick|tolstoy)", f.parent.name)
            if m:
                cands.append((m.group(1), f))
    for work, f in cands:
        sec = int(duration(f))
        stamp = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y%m%d") + f"_{sec}s_" + re.sub(r"[^\w]", "", f.stem)[:24]
        dest = OUT / work / "prev" / stamp
        if dest.exists():
            continue
        dest.mkdir(parents=True, exist_ok=True)
        link_or_copy(f, dest / f.name)
        extract_frames(dest / f.name, dest / "frames", 6)
        msgs.append(f"+ {work}: prev/{stamp} ({f.name})")
    return msgs or ["– deliverables: 새로 들일 것 없음"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current", metavar="WORK")
    ap.add_argument("--final-only", metavar="WORK")
    ap.add_argument("--deliverables", action="store_true")
    ap.add_argument("--held", nargs="?", const="__all__", metavar="WORK")
    a = ap.parse_args()
    if a.current:
        print(archive_current(a.current))
    elif a.final_only:
        print(archive_final_only(a.final_only))
    elif a.deliverables:
        for m in archive_deliverables():
            print(m)
    elif a.held:
        works = [a.held] if a.held != "__all__" else sorted(
            d.name for d in OUT.iterdir() if d.is_dir() and not d.name.startswith("_")
            and not d.name.endswith(("_kf", "_i2v", "_sheets")) and d.name not in ("tts", "ab_motion"))
        for w in works:
            for m in archive_held(w):
                print(m, flush=True)
    else:
        ap.error("--current WORK | --final-only WORK | --deliverables | --held [WORK]")


if __name__ == "__main__":
    main()
