#!/usr/bin/env python3
"""클립 + 내레이션 -> 최종 세로 영상.

각 클립은 해당 문장 오디오 길이에 맞춰 생성되지만 4n+1 반올림 때문에
최대 ±0.08초 오차가 난다. 오디오 쪽에 무음 패딩을 넣어 클립 길이에
정확히 맞춘 뒤 이어붙여, 나레이션과 화면이 어긋나지 않게 한다.
"""
import argparse
import json
import os
import subprocess

FF = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]


def run(cmd):
    subprocess.run(cmd, check=True)


def probe(path, entries):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", entries,
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--clipdir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", required=True)
    a = ap.parse_args()

    with open(a.plan, encoding="utf-8") as f:
        plan = json.load(f)
    os.makedirs(a.work, exist_ok=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)

    vlist, alist = [], []
    for c in plan["clips"]:
        i = c["idx"]
        src = os.path.join(a.clipdir, f"s{i}_00001_.mp4")
        if not os.path.exists(src):
            raise SystemExit(f"클립 없음: {src}")
        vlist.append(os.path.abspath(src))

        # 오디오를 클립 길이에 맞춰 패딩(짧으면 무음 추가, 길면 자름)
        target = c["clip_secs"]
        pad = os.path.join(a.work, f"a{i}.wav")
        run(FF + ["-i", c["wav"], "-af",
                  f"apad=whole_dur={target},atrim=0:{target}",
                  "-ar", "48000", "-ac", "2", pad])
        alist.append(os.path.abspath(pad))

    vtxt = os.path.join(a.work, "video_concat.txt")
    atxt = os.path.join(a.work, "audio_concat.txt")
    with open(vtxt, "w") as f:
        f.write("".join(f"file '{p}'\n" for p in vlist))
    with open(atxt, "w") as f:
        f.write("".join(f"file '{p}'\n" for p in alist))

    narration = os.path.join(a.work, "narration.wav")
    run(FF + ["-f", "concat", "-safe", "0", "-i", atxt, "-c", "copy", narration])

    run(FF + ["-f", "concat", "-safe", "0", "-i", vtxt, "-i", narration,
              "-vf", "scale=1080:1920:flags=lanczos,format=yuv420p",
              "-r", "24",
              "-c:v", "libx264", "-profile:v", "high", "-preset", "slow",
              "-b:v", "8M", "-maxrate", "10M", "-bufsize", "16M",
              "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
              "-movflags", "+faststart", "-shortest", a.out])

    dur = probe(a.out, "format=duration")
    streams = probe(a.out, "stream=codec_type")
    size = os.path.getsize(a.out) / 1024 / 1024
    print(f"완성: {a.out}\n  길이 {float(dur):.2f}s  크기 {size:.1f}MiB")
    print("  스트림:", streams.replace("\n", ", "))


if __name__ == "__main__":
    main()
