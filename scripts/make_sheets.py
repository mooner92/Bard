#!/usr/bin/env python3
"""인물 자산마다 캐릭터 시트를 1장 만든다 (§9 참조 체인의 1단계).

시트는 인물 하나만 담으므로 예산 경쟁이 없다 — 자산의 spec+상세 전문을
다 쓴다. 이미 있으면 건너뛴다(신선도: 자산을 고치면 시트 png 를 지운다).
"""
import argparse, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = str(ROOT / "venv" / "bin" / "python")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--treatment", required=True)
    ap.add_argument("--style", required=True)
    ap.add_argument("--out", required=True, help="output/<작품>_sheets")
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT / "scripts"))
    import scene_prompt
    tre = json.loads(pathlib.Path(a.treatment).read_text(encoding="utf-8"))
    assets = scene_prompt.load_assets(tre.get("assets_dir", ""))
    people = [(k, v) for k, v in assets.items() if v.get("kind") == "인물"]
    if not people:
        print("인물 자산 없음"); return
    outdir = pathlib.Path(a.out); outdir.mkdir(parents=True, exist_ok=True)
    for i, (name, v) in enumerate(sorted(people)):
        if list(outdir.glob(f"{name}_*.png")):
            print(f"시트 있음 -> {name}"); continue
        desc = ", ".join(x for x in [v.get("spec", ""), v.get("detail", "")] if x)
        prompt = (f"{a.style}a character sheet of a single figure on a plain warm "
                  f"cream background, full body, facing slightly left, "
                  f"the whole figure clearly visible: {desc}")
        r = subprocess.run([PY, str(ROOT / "scripts" / "gen_keyframe.py"),
                            "--seed", str(300 + i),
                            "--prefix", f"{pathlib.Path(a.out).name}/{name}",
                            "--prompt", prompt])
        if r.returncode != 0:
            sys.exit(f"시트 실패: {name}")
        print(f"시트 완료 -> {name}")

if __name__ == "__main__":
    main()
