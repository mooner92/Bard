#!/usr/bin/env python3
"""ComfyUI 를 다른 프로젝트와 나눠 쓴다(사용자 지시 09-08). 우리 작업을 넣기 전에
남의 작업이 큐(실행 중 + 대기)에 있으면 빌 때까지 기다린다.

구분: 큐 항목 워크플로의 filename_prefix. 우리 것은 "<work>_kf/…" "<work>_i2v/…"
"night_…" 꼴, 남의 것은 그 밖(예: "infog/…"). 우리 작업은 기다리지 않는다.
  venv/bin/python scripts/comfy_wait.py [--url http://127.0.0.1:8188] [--poll 20]
"""
import argparse, json, re, sys, time, urllib.request

OURS = re.compile(r"(^|/)(night_|[A-Za-z0-9_]+_(kf|i2v|sheets)/)")


def foreign_jobs(url: str, pending_only: bool = False) -> list:
    try:
        with urllib.request.urlopen(f"{url}/queue", timeout=30) as r:
            d = json.load(r)
    except Exception as e:                       # 응답이 없으면 "비었다"고 보지 않는다
        return [f"?({e.__class__.__name__})"]
    out = []
    for kind in (("queue_pending",) if pending_only else ("queue_running", "queue_pending")):
        for e in d.get(kind, []):
            wf = e[2] if len(e) > 2 and isinstance(e[2], dict) else {}
            prefixes = {n.get("inputs", {}).get("filename_prefix", "") for n in wf.values() if isinstance(n, dict)}
            prefixes.discard("")
            if prefixes and not any(OURS.search(p) for p in prefixes):
                out.append(sorted(prefixes)[0])
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8188")
    p.add_argument("--poll", type=int, default=20)
    p.add_argument("--max-pending", type=int, default=1,
                   help="남의 '대기' 작업이 이 수 이하면 제출한다(실행 중인 것은 세지 않음). "
                        "0 미만이면 옛 방식 — 남의 작업이 하나도 없을 때까지 기다린다")
    a = p.parse_args()
    waited = 0
    while True:
        # 남이 쉼 없이 넣으면 '빌 때까지' 는 굶는다(실측: infog 가 연속 제출). ComfyUI 큐는
        # 선입선출이므로 남의 대기가 적을 때 하나 넣으면 한 작업씩 번갈아 돈다 — 큐 구조.
        f = foreign_jobs(a.url, pending_only=a.max_pending >= 0)
        if len(f) <= max(a.max_pending, 0) and not any(x.startswith("?") for x in f):
            if waited:
                print(f"comfy_wait: 남의 작업 끝 — {waited}초 기다림", flush=True)
            return 0
        if waited % 300 == 0:
            print(f"comfy_wait: ComfyUI 에 남의 작업 {len(f)}건({f[0]}) — 기다림", flush=True)
        time.sleep(a.poll); waited += a.poll


if __name__ == "__main__":
    sys.exit(main())
