#!/usr/bin/env python3
"""Qwen-Image-Edit-2509 참조 편집 (ComfyUI API).

키프레임 간 피사체 일관성 확보용: 승인된 이미지(예: s2의 향유고래)를
참조로 넣고 다른 장면을 재생성하면 같은 개체가 유지된다.
텍스트 재생성 반복으로는 종이 바뀌는 문제(향유고래->흰수염고래)를
막을 수 없어서 이 방식이 필요하다.

사용:
  python gen_edit.py --ref whale.png --scene old_s6.png \
      --prompt "the same white sperm whale from image 1 diving deep..." \
      --prefix "mobydick_kf/s6edit"
"""
import argparse, json, sys, time, urllib.error, urllib.request, uuid

SERVER = "127.0.0.1:8188"


def build(ref, scene, prompt, negative, width, height, steps, cfg, shift, seed,
          denoise, prefix):
    g = {
        "1": {"class_type": "UnetLoaderGGUFMultiGPU",
              "inputs": {"unet_name": "qwen-image-edit-2509-Q4_K_M.gguf",
                         "device": "cuda:0"}},
        "2": {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"model": ["1", 0], "shift": shift}},
        "3": {"class_type": "CLIPLoaderMultiGPU",
              "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                         "type": "qwen_image", "device": "cuda:1"}},
        "8": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": ref}},
    }
    pos = {"clip": ["3", 0], "prompt": prompt, "vae": ["8", 0], "image1": ["10", 0]}
    neg = {"clip": ["3", 0], "prompt": negative, "vae": ["8", 0], "image1": ["10", 0]}
    if scene:
        g["11"] = {"class_type": "LoadImage", "inputs": {"image": scene}}
        pos["image2"] = ["11", 0]
        neg["image2"] = ["11", 0]
    g["4"] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": pos}
    g["5"] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": neg}
    g["6"] = {"class_type": "EmptySD3LatentImage",
              "inputs": {"width": width, "height": height, "batch_size": 1}}
    g["7"] = {"class_type": "KSampler",
              "inputs": {"model": ["2", 0], "positive": ["4", 0], "negative": ["5", 0],
                         "latent_image": ["6", 0], "seed": seed, "steps": steps,
                         "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
                         "denoise": denoise}}
    g["9"] = {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["8", 0]}}
    g["12"] = {"class_type": "SaveImage",
               "inputs": {"images": ["9", 0], "filename_prefix": prefix}}
    return g


def run(graph):
    body = json.dumps({"prompt": graph, "client_id": str(uuid.uuid4())}).encode()
    req = urllib.request.Request(f"http://{SERVER}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req, timeout=60))["prompt_id"]
    except urllib.error.HTTPError as e:
        print("제출 거부:", e.read().decode()[:2500], file=sys.stderr)
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
    p.add_argument("--ref", required=True, help="참조 피사체 이미지 (ComfyUI/input/)")
    p.add_argument("--scene", default=None, help="선택: 장면 구도 참조 이미지")
    p.add_argument("--prompt", required=True)
    p.add_argument("--negative", default="photorealistic, photograph, 3d render, cgi, "
                   "glossy, humpback whale, blue whale, caption, letters, text, "
                   "watermark, blurry, deformed")
    p.add_argument("--width", type=int, default=720)
    p.add_argument("--height", type=int, default=1280)
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--cfg", type=float, default=2.5)
    p.add_argument("--shift", type=float, default=3.1)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--denoise", type=float, default=1.0)
    p.add_argument("--prefix", default="edit/out")
    a = p.parse_args()
    g = build(a.ref, a.scene, a.prompt, a.negative, a.width, a.height, a.steps,
              a.cfg, a.shift, a.seed, a.denoise, a.prefix)
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
