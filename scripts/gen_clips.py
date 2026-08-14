#!/usr/bin/env python3
"""계획(plan.json) + 영문 프롬프트(prompts.json)로 클립을 순차 생성한다.

이미 만들어진 클립은 건너뛴다 -> 중간에 끊겨도 이어서 돌릴 수 있다.
"""
import argparse
import json
import os
import subprocess
import sys
import time

NEG = ("photorealistic, photograph, live action, 3d render, cgi, text, letters, "
       "watermark, blurry, distorted, deformed anatomy, extra limbs, modern objects")

PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "venv", "bin", "python")
GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_t2v.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--width", type=int, default=480)
    ap.add_argument("--height", type=int, default=848)
    ap.add_argument("--steps", type=int, default=8)
    a = ap.parse_args()

    plan = json.load(open(a.plan, encoding="utf-8"))
    pdata = json.load(open(a.prompts, encoding="utf-8"))
    suffix = pdata["style_suffix"]
    prompts = pdata["prompts"]

    for c in plan["clips"]:
        i = c["idx"]
        out = f"output/{a.key}/s{i}_00001_.mp4"
        if os.path.exists(out):
            print(f"[s{i}] 이미 있음 -> 건너뜀", flush=True)
            continue
        prompt = prompts[str(i)] + suffix
        t0 = time.time()
        print(f"\n[s{i}] {c['frames']}프레임 시작 :: {prompts[str(i)][:90]}...",
              flush=True)
        r = subprocess.run([PY, GEN,
                            "--width", str(a.width), "--height", str(a.height),
                            "--length", str(c["frames"]),
                            "--steps", str(a.steps),
                            "--seed", str(1000 + i),
                            "--prefix", f"{a.key}/s{i}",
                            "--prompt", prompt,
                            "--negative", NEG])
        if r.returncode != 0:
            print(f"[s{i}] 실패", flush=True)
            sys.exit(1)
        print(f"[s{i}] 완료 {(time.time()-t0)/60:.1f}분", flush=True)
    print("\n전체 클립 완료", flush=True)


if __name__ == "__main__":
    main()
