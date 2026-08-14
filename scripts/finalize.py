#!/usr/bin/env python3
"""최종본을 deliverables 로 복사하고 30MiB 미만 공유용 압축본을 만든다."""
import argparse
import os
import shutil
import subprocess

LIMIT = 30 * 1024 * 1024


def probe(path, entries):
    return subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", entries,
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--destdir", required=True)
    ap.add_argument("--name", required=True, help="확장자 없는 한글 파일명")
    a = ap.parse_args()

    os.makedirs(a.destdir, exist_ok=True)
    dest = os.path.join(a.destdir, a.name + ".mp4")
    shutil.copy2(a.src, dest)

    comp = os.path.join(a.destdir, a.name + "_compressed.mp4")
    crf = 26
    while True:
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-i", a.src,
                        "-c:v", "libx264", "-profile:v", "high", "-preset", "slow",
                        "-crf", str(crf), "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
                        "-movflags", "+faststart", comp], check=True)
        if os.path.getsize(comp) < LIMIT or crf >= 34:
            break
        crf += 3
        print(f"  30MiB 초과 -> crf {crf} 로 재인코딩", flush=True)

    for p in (dest, comp):
        size = os.path.getsize(p) / 1024 / 1024
        print(f"{p}\n  길이 {float(probe(p, 'format=duration')):.2f}s  "
              f"{size:.1f}MiB  스트림 "
              f"{probe(p, 'stream=codec_type').replace(chr(10), '+')}")


if __name__ == "__main__":
    main()
