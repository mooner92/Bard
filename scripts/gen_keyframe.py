#!/usr/bin/env python3
"""Qwen-Image 키프레임 생성 (ComfyUI API).

이미지 우선 파이프라인의 1단계: 스타일 블록을 고정한 키프레임을 뽑고,
선별된 이미지를 Wan 2.2 I2V의 start_image로 넘긴다.

GPU 배분: unet은 cuda:0, 텍스트 인코더는 cuda:1 (MultiGPU 로더).
동시 실행 없음 -- 배치 1로 순차 생성해 24GB를 넘지 않는다.

사용:
  python gen_keyframe.py --prompt "..." --prefix "mobydick_kf/s1" [--seed 7]
"""
import argparse, json, sys, time, urllib.error, urllib.request, uuid

SERVER = "127.0.0.1:8188"


def build(prompt, negative, width, height, steps, cfg, shift, seed, prefix):
    return {
        "1": {"class_type": "UnetLoaderGGUFMultiGPU",
              "inputs": {"unet_name": "qwen-image-Q4_K_M.gguf", "device": "cuda:0"}},
        "2": {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"model": ["1", 0], "shift": shift}},
        "3": {"class_type": "CLIPLoaderMultiGPU",
              "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                         "type": "qwen_image", "device": "cuda:1"}},
        "4": {"class_type": "TextEncodeQwenImageEdit",
              "inputs": {"clip": ["3", 0], "prompt": prompt}},
        "5": {"class_type": "TextEncodeQwenImageEdit",
              "inputs": {"clip": ["3", 0], "prompt": negative}},
        "6": {"class_type": "EmptySD3LatentImage",
              "inputs": {"width": width, "height": height, "batch_size": 1}},
        "7": {"class_type": "KSampler",
              "inputs": {"model": ["2", 0], "positive": ["4", 0], "negative": ["5", 0],
                         "latent_image": ["6", 0], "seed": seed, "steps": steps,
                         "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
                         "denoise": 1.0}},
        "8": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["8", 0]}},
        "10": {"class_type": "SaveImage",
               "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


def run(graph):
    body = json.dumps({"prompt": graph, "client_id": str(uuid.uuid4())}).encode()
    req = urllib.request.Request(f"http://{SERVER}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req, timeout=60))["prompt_id"]
    except urllib.error.HTTPError as e:
        print("제출 거부:", e.read().decode()[:2000], file=sys.stderr)
        raise
    t0 = time.time()
    while time.time() - t0 < 1800:
        time.sleep(3)
        h = json.load(urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=30))
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("completed") or st.get("status_str") in ("success", "error"):
                return time.time() - t0, h[pid]
    raise TimeoutError


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", required=True)
    p.add_argument("--negative", default="photorealistic, photograph, 3d render, cgi, "
                   "glossy, text, watermark, blurry, deformed")
    p.add_argument("--width", type=int, default=720)
    p.add_argument("--height", type=int, default=1280)
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--cfg", type=float, default=2.5)
    p.add_argument("--shift", type=float, default=3.1)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--prefix", default="keyframes/kf")
    a = p.parse_args()
    g = build(a.prompt, a.negative, a.width, a.height, a.steps, a.cfg, a.shift,
              a.seed, a.prefix)
    el, entry = run(g)
    st = entry.get("status", {})
    if st.get("status_str") == "error":
        print(f"실패 ({el:.0f}s)")
        for m in st.get("messages", [])[-4:]:
            print("  ", json.dumps(m, ensure_ascii=False)[:400])
        sys.exit(1)
    outs = [f.get("filename") for o in entry.get("outputs", {}).values()
            for f in o.get("images", [])]
    print(f"완료 {el:.0f}s -> {outs}")


if __name__ == "__main__":
    main()
