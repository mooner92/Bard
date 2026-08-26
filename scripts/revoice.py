#!/usr/bin/env python3
"""이미 만든 작품의 낭독만 Qwen3-TTS 로 갈아 끼우고 영상을 다시 조립한다.

영상은 **다시 만들지 않는다.** 조립 단계가 음성 길이에 맞춰 클립을 늘리는
구조라(night_batch_v2.sh ⑤), 음성만 바꾸고 그 단계만 되돌리면 된다.
발행작 67편 전부 클립이 남아 있는 것을 확인하고 짠 방식이다.

  키프레임 + 클립  2시간 20분  →  건너뜀
  낭독 8문장                     약 2분
  조립·발행                      약 1분

원본 Azure 음성은 output/tts/azure_backup/ 에 남긴다 — 되돌릴 수 있어야 한다.

venv-tts 로 돌린다(qwen-tts 가 거기 있다). 발행 스크립트만 본 venv 로 부른다.

사용:
  venv-tts/bin/python scripts/revoice.py --works chunhyangjeon
  venv-tts/bin/python scripts/revoice.py --all --skip-queued
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qwen_voice import dur, load_model, synth, write_wavs  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "output"
TTS = OUT / "tts"
BACKUP = TTS / "azure_backup"
VENV = BASE / "venv" / "bin" / "python"      # 발행 스크립트는 본 venv 로 돈다


def tone_of(work: str) -> str:
    """작품의 톤. 발행 기록에 큐 줄이 통째로 남아 있다(6번째 칸)."""
    f = BASE / "works" / "done.txt"
    if not f.exists():
        return "담담"
    for line in f.read_text(encoding="utf-8").splitlines():
        p = line.split("\t")
        if len(p) >= 6 and p[1] == work:
            return p[5].strip() or "담담"
    return "담담"


def narration_of(work: str):
    for p in (OUT / work / "narration_night.json",
              BASE / "works" / "handwritten" / work / "narration_night.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))["sentences"]
    return None


def has_clips(work: str, n: int) -> bool:
    return all((OUT / f"{work}_i2v" / f"night_s{i}_00001_.mp4").exists()
               for i in range(1, n + 1))


def assemble(work: str, n: int) -> float:
    """night_batch_v2.sh ⑤ 와 같은 방식으로 조립한다. 완성 길이를 낸다.

    클립을 음성 길이에 맞춰 늘리고(setpts), 1080x1920 으로 키운 뒤 이어 붙이고,
    음량을 -14 LUFS 로 맞춘다. 숫자는 배치와 글자 그대로 같게 두었다 — 여기만
    달라지면 새로 만든 작품과 결이 어긋난다.
    """
    asm = Path(tempfile.mkdtemp(prefix=f"revoice_{work}_"))
    vlist, alist = asm / "v.txt", asm / "a.txt"
    for i in range(1, n + 1):
        a = TTS / f"{work}_night_s{i}.wav"
        c = OUT / f"{work}_i2v" / f"night_s{i}_00001_.mp4"
        cd = dur(c)
        if cd <= 0:
            shutil.rmtree(asm, ignore_errors=True)
            return 0.0
        f = dur(a) / cd
        v = asm / f"v{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-i", str(c),
                        "-vf", f"setpts={f:.6f}*PTS,scale=1080:1920:flags=lanczos",
                        "-r", "24", "-c:v", "libx264", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-an", str(v)], capture_output=True)
        with vlist.open("a") as fh:
            fh.write(f"file '{v}'\n")
        with alist.open("a") as fh:
            fh.write(f"file '{a.resolve()}'\n")
    for lst, o in ((vlist, asm / "v.mp4"), (alist, asm / "a.wav")):
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", str(o)], capture_output=True)
    dest = OUT / work / "final_night.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", str(asm / "v.mp4"), "-i", str(asm / "a.wav"),
                    "-c:v", "libx264", "-crf", "20", "-profile:v", "high",
                    "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", str(dest)], capture_output=True)
    shutil.rmtree(asm, ignore_errors=True)
    return dur(dest)


def revoice(model, work: str, publish: bool = True) -> str:
    sents = narration_of(work)
    if not sents:
        return "낭독 없음"
    n = len(sents)
    if not has_clips(work, n):
        return "클립 부족 — 건너뜀"

    # 먼저 원본을 챙긴다. 되돌릴 수 있어야 하고, 목표 길이의 기준이기도 하다.
    BACKUP.mkdir(parents=True, exist_ok=True)
    for i in range(1, n + 1):
        src = TTS / f"{work}_night_s{i}.wav"
        dst = BACKUP / src.name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    # 목표는 **원본(Azure)** 길이다. 지금 파일에서 읽으면 두 번째 돌릴 때 이미
    # 바꿔 놓은 짧은 음성을 기준으로 삼아 편마다 조금씩 더 짧아진다(실측:
    # 춘향전이 53초 → 43초 → 그대로 굳었다). 원본은 백업에만 남는다.
    def _sum(folder):
        return sum(dur(folder / f"{work}_night_s{i}.wav") for i in range(1, n + 1))
    target = _sum(BACKUP) or _sum(TTS)
    if target <= 0:
        return "기존 음성 없음"

    pairs = synth(model, sents, tone_of(work))
    if any(p is None for p in pairs):
        return "합성 실패 — 원본 유지"
    # 길이는 맞추지 않는다. 소희 화자는 Azure 보다 빠르게 읽어서 억지로 늘리면
    # 늘어지고, 숨으로 채우면 여백이 과해진다. 이미 만든 작품은 조금 짧아져도
    # 두기로 했다 — 대신 앞으로 만들 작품은 대본을 늘려 50초를 맞춘다.
    raw = sum(len(w) / sr for w, sr in pairs)
    write_wavs(pairs, str(TTS / f"{work}_night_s"))

    sec = assemble(work, n)
    if sec < 10:
        return "조립 실패"
    if publish:
        subprocess.run([str(VENV), str(BASE / "scripts" / "publish_final.py"),
                        "--work", work], capture_output=True)
    chars = sum(len(s) for s in sents)
    return f"{sec:.0f}초 (원본 {target:.0f}초 · {chars}자 · {raw/chars:.3f}초/자)"


def main():
    p = argparse.ArgumentParser(description="발행작의 낭독을 Qwen 으로 교체")
    p.add_argument("--works", nargs="*", default=[])
    p.add_argument("--all", action="store_true")
    p.add_argument("--skip-queued", action="store_true",
                   help="큐에 있는 작품은 건드리지 않는다(밤 배치와 충돌 방지)")
    p.add_argument("--no-publish", action="store_true")
    p.add_argument("--device", default="cuda:1")
    a = p.parse_args()

    works = list(a.works)
    if a.all:
        works = sorted({d.name for d in OUT.iterdir()
                        if d.is_dir() and (d / "final_night.mp4").exists()})
    if a.skip_queued:
        q = BASE / "works" / "queue.txt"
        queued = ({l.split("\t")[0] for l in q.read_text(encoding="utf-8").splitlines() if l.strip()}
                  if q.exists() else set())
        works = [w for w in works if w not in queued]
    if not works:
        sys.exit("대상 없음")

    print(f"대상 {len(works)}편", flush=True)
    model = load_model(a.device)
    done = fail = 0
    for i, w in enumerate(works, 1):
        try:
            r = revoice(model, w, publish=not a.no_publish)
        except Exception as e:
            r = f"오류: {type(e).__name__} {e}"
        ok = "초 (" in r
        done += ok
        fail += not ok
        print(f"  [{i}/{len(works)}] {w}: {r}", flush=True)
    print(f"완료 {done}편 · 실패 {fail}편")


if __name__ == "__main__":
    main()
