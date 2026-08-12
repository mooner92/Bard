#!/usr/bin/env python3
"""Wan 2.2 I2V 클립 생성 (키프레임 -> 영상).

이미지 우선 파이프라인의 2단계. 스타일은 이미 키프레임이 결정했으므로
프롬프트에는 모션과 카메라 움직임만 쓴다(Alibaba 공식 I2V 권장 방식).

GPU 배분: unet high/low 는 cuda:0, VAE 는 cuda:1, 텍스트 인코더는 cpu.
길이는 81프레임을 기본으로 한다 -- 121프레임은 첫 프레임이 타고
영상이 빨라 보이는 문제가 보고돼 있다.

사용:
  python gen_i2v.py --image kf1.png --prompt "slow dolly in, mist drifting" \
      --prefix "mobydick_i2v/s1" --length 81
"""
import argparse, json, sys, time, urllib.error, urllib.request, uuid

SERVER = "127.0.0.1:8188"
NEG = ("static, still, motionless, frozen, jittery, flickering, warping, morphing, "
       "text, watermark, blurry, distorted, deformed")


def build(image, prompt, negative, width, height, length, steps, shift, cfg,
          sampler, scheduler, seed, fps, prefix):
    split = steps // 2
    return {
        "1": {"class_type": "UnetLoaderGGUFMultiGPU",
              "inputs": {"unet_name": "wan2.2_i2v_high_noise_Q6_K.gguf",
                         "device": "cuda:0"}},
        "2": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0], "strength_model": 1.0,
                         "lora_name": "wan2.2_i2v_high_noise_lightx2v_4step.safetensors"}},
        "3": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["2", 0], "shift": shift}},
        "4": {"class_type": "UnetLoaderGGUFMultiGPU",
              "inputs": {"unet_name": "wan2.2_i2v_low_noise_Q6_K.gguf",
                         "device": "cuda:0"}},
        "5": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["4", 0], "strength_model": 1.0,
                         "lora_name": "wan2.2_i2v_low_noise_lightx2v_4step.safetensors"}},
        "6": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["5", 0], "shift": shift}},
        "7": {"class_type": "CLIPLoaderMultiGPU",
              "inputs": {"clip_name": "umt5_xxl_fp16.safetensors", "type": "wan",
                         "device": "cpu"}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["7", 0], "text": prompt}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["7", 0], "text": negative}},
        "10": {"class_type": "LoadImage", "inputs": {"image": image}},
        # A14B I2V 는 Wan 2.1 계열 16채널 VAE 를 쓴다 (48채널 wan2.2_vae 아님).
        "11": {"class_type": "VAELoaderMultiGPU",
               "inputs": {"vae_name": "wan_2.1_vae.safetensors", "device": "cuda:1"}},
        "12": {"class_type": "WanImageToVideo",
               "inputs": {"positive": ["8", 0], "negative": ["9", 0], "vae": ["11", 0],
                          "width": width, "height": height, "length": length,
                          "batch_size": 1, "start_image": ["10", 0]}},
        "13": {"class_type": "KSamplerAdvanced",
               "inputs": {"model": ["3", 0], "positive": ["12", 0], "negative": ["12", 1],
                          "latent_image": ["12", 2], "add_noise": "enable",
                          "noise_seed": seed, "steps": steps, "cfg": cfg,
                          "sampler_name": sampler, "scheduler": scheduler,
                          "start_at_step": 0, "end_at_step": split,
                          "return_with_leftover_noise": "enable"}},
        "14": {"class_type": "KSamplerAdvanced",
               "inputs": {"model": ["6", 0], "positive": ["12", 0], "negative": ["12", 1],
                          "latent_image": ["13", 0], "add_noise": "disable",
                          "noise_seed": seed, "steps": steps, "cfg": cfg,
                          "sampler_name": sampler, "scheduler": scheduler,
                          "start_at_step": split, "end_at_step": steps,
                          "return_with_leftover_noise": "disable"}},
        "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["11", 0]}},
        "16": {"class_type": "CreateVideo", "inputs": {"images": ["15", 0], "fps": float(fps)}},
        "17": {"class_type": "SaveVideo",
               "inputs": {"video": ["16", 0], "filename_prefix": prefix,
                          "format": "auto", "codec": "auto"}},
    }


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
    while time.time() - t0 < 3600:
        time.sleep(5)
        h = json.load(urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=30))
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("completed") or st.get("status_str") in ("success", "error"):
                return time.time() - t0, h[pid]
    raise TimeoutError


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image", required=True, help="ComfyUI/input/ 안의 파일명")
    p.add_argument("--prompt", required=True, help="모션·카메라만 기술 (스타일은 이미지가 결정)")
    p.add_argument("--negative", default=NEG)
    p.add_argument("--width", type=int, default=480)
    p.add_argument("--height", type=int, default=848)
    p.add_argument("--length", type=int, default=81, help="81 권장 (121은 첫 프레임 손상)")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--shift", type=float, default=8.0)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--sampler", default="euler")
    p.add_argument("--scheduler", default="simple")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--prefix", default="i2v/clip")
    a = p.parse_args()
    g = build(a.image, a.prompt, a.negative, a.width, a.height, a.length, a.steps,
              a.shift, a.cfg, a.sampler, a.scheduler, a.seed, a.fps, a.prefix)
    print(f"제출: {a.image} -> {a.width}x{a.height}, {a.length}프레임 "
          f"({a.length/a.fps:.1f}초), {a.steps}스텝")
    el, entry = run(g)
    st = entry.get("status", {})
    if st.get("status_str") == "error":
        print(f"실패 ({el:.0f}s)")
        for m in st.get("messages", [])[-5:]:
            print("  ", json.dumps(m, ensure_ascii=False)[:500])
        sys.exit(1)
    outs = [f.get("filename") for o in entry.get("outputs", {}).values()
            for f in o.get("videos", []) + o.get("images", [])]
    print(f"완료 {el:.0f}s ({el/60:.1f}분) -> {outs}")


if __name__ == "__main__":
    main()
