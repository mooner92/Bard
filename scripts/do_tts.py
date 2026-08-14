#!/usr/bin/env python3
"""내레이션 JSON -> 문장별 Azure TTS wav + 클립 프레임 수 계산.

프레임 수는 4n+1 형태여야 하므로 duration*24 에서 가장 가까운 4n+1 로 맞춘다.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts import synth, duration, load_env  # noqa: E402

FPS = 24


def nearest_4n1(frames: int) -> int:
    n = round((frames - 1) / 4)
    return max(4 * n + 1, 33)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--narration", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--out", required=True, help="계획 JSON 경로")
    ap.add_argument("--rate", default="0%")
    a = ap.parse_args()

    with open(a.narration, encoding="utf-8") as f:
        sents = json.load(f)["sentences"]
    env = load_env()

    plan = []
    total = 0.0
    for i, s in enumerate(sents, 1):
        wav = f"output/tts/{a.key}_s{i}.wav"
        # 마침표가 없으면 TTS가 문장을 끝맺지 않고 어색하게 이어 읽는다.
        spoken = s if s[-1] in ".!?…" else s + "."
        if os.path.exists(wav):
            d = duration(wav)
        else:
            d = synth(spoken, wav, env=env, rate=a.rate)
        frames = nearest_4n1(round(d * FPS))
        clip_secs = frames / FPS
        total += d
        plan.append({"idx": i, "text": s, "chars": len(s), "wav": wav,
                     "audio_secs": round(d, 3), "frames": frames,
                     "clip_secs": round(clip_secs, 3)})
        print(f"S{i} {len(s):>2}자 오디오 {d:6.2f}s -> {frames}프레임 "
              f"({clip_secs:.2f}s)", flush=True)

    clip_total = sum(p["clip_secs"] for p in plan)
    print(f"\n오디오 합계 {total:.2f}s / 영상 합계 {clip_total:.2f}s")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"key": a.key, "fps": FPS, "audio_total": round(total, 3),
                   "clip_total": round(clip_total, 3), "clips": plan},
                  f, ensure_ascii=False, indent=2)
    print("저장:", a.out)


if __name__ == "__main__":
    main()
