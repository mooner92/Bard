#!/usr/bin/env python3
"""Wan 2.2 T2V 클립 생성 (ComfyUI API 제출 + 소요시간 측정).

Wan 2.2는 high-noise / low-noise 두 전문가로 나뉜 구조라,
KSamplerAdvanced 두 개로 스텝 구간을 나눠 태운다.
Lightning 4-step 증류 LoRA를 붙여 총 4스텝, CFG=1로 돈다.

사용:
  python gen_t2v.py --prompt "..." --width 720 --height 1280 --length 121
"""
import argparse, json, time, urllib.request, urllib.error, uuid, sys

SERVER = "127.0.0.1:8188"

NEG = ("blurry, low quality, distorted, watermark, text, logo, "
       "static, jpeg artifacts, oversaturated, deformed")


def build(prompt, negative, width, height, length, steps, shift, cfg,
          sampler, scheduler, seed, fps, prefix):
    """API 포맷 워크플로우 그래프를 만든다. 노드 키는 문자열 ID."""
    split = steps // 2  # high-noise -> low-noise 전환점
    return {
        # 디바이스 배치가 성능을 좌우한다. Turing(sm_75)은 FlashAttention을
        # 못 써서 활성화 메모리가 커진다 -- 720x1280x121은 어텐션 토큰이 약 11만
        # 개라 ComfyUI가 추론용으로 21GB를 예약하고 가중치엔 2.8GB만 남긴다.
        # 그러면 12GB unet이 부분 로드되어 매 스텝 CPU에서 스트리밍하며
        # 스텝당 400초대로 느려진다(실측 28.6분/클립).
        # -> 두 전문가를 각각 다른 카드에, 텍스트 인코더는 CPU로 보내
        #    각 unet이 거의 빈 24GB를 쓰게 한다.
        # ---- high-noise 전문가 (cuda:0) ----
        "1":  {"class_type": "UnetLoaderGGUFMultiGPU",
               "inputs": {"unet_name": "wan2.2_t2v_high_noise_Q6_K.gguf",
                          "device": "cuda:0"}},
        "2":  {"class_type": "LoraLoaderModelOnly",
               "inputs": {"model": ["1", 0], "strength_model": 1.0,
                          "lora_name": "wan2.2_t2v_high_noise_lightx2v_4step.safetensors"}},
        "3":  {"class_type": "ModelSamplingSD3",
               "inputs": {"model": ["2", 0], "shift": shift}},
        # ---- low-noise 전문가 (cuda:1) ----
        "4":  {"class_type": "UnetLoaderGGUFMultiGPU",
               "inputs": {"unet_name": "wan2.2_t2v_low_noise_Q6_K.gguf",
                          "device": "cuda:1"}},
        "5":  {"class_type": "LoraLoaderModelOnly",
               "inputs": {"model": ["4", 0], "strength_model": 1.0,
                          "lora_name": "wan2.2_t2v_low_noise_lightx2v_4step.safetensors"}},
        "6":  {"class_type": "ModelSamplingSD3",
               "inputs": {"model": ["5", 0], "shift": shift}},
        # ---- 텍스트 인코딩 (cpu: 프롬프트당 한 번만 도므로 GPU를 낭비할 이유가 없다) ----
        "7":  {"class_type": "CLIPLoaderMultiGPU",
               "inputs": {"clip_name": "umt5_xxl_fp16.safetensors", "type": "wan",
                          "device": "cpu"}},
        "8":  {"class_type": "CLIPTextEncode",
               "inputs": {"clip": ["7", 0], "text": prompt}},
        "9":  {"class_type": "CLIPTextEncode",
               "inputs": {"clip": ["7", 0], "text": negative}},
        # ---- 빈 latent ----
        "10": {"class_type": "EmptyHunyuanLatentVideo",
               "inputs": {"width": width, "height": height,
                          "length": length, "batch_size": 1}},
        # ---- 2단 샘플링 ----
        "11": {"class_type": "KSamplerAdvanced",
               "inputs": {"model": ["3", 0], "positive": ["8", 0],
                          "negative": ["9", 0], "latent_image": ["10", 0],
                          "add_noise": "enable", "noise_seed": seed,
                          "steps": steps, "cfg": cfg,
                          "sampler_name": sampler, "scheduler": scheduler,
                          "start_at_step": 0, "end_at_step": split,
                          "return_with_leftover_noise": "enable"}},
        "12": {"class_type": "KSamplerAdvanced",
               "inputs": {"model": ["6", 0], "positive": ["8", 0],
                          "negative": ["9", 0], "latent_image": ["11", 0],
                          "add_noise": "disable", "noise_seed": seed,
                          "steps": steps, "cfg": cfg,
                          "sampler_name": sampler, "scheduler": scheduler,
                          "start_at_step": split, "end_at_step": steps,
                          "return_with_leftover_noise": "disable"}},
        # ---- 디코드 & 저장 ----
        # A14B(T2V/I2V)는 Wan 2.1의 16채널 VAE를 쓴다.
        # 48채널 wan2.2_vae는 TI2V-5B 전용이라 여기 물리면 채널 불일치로 죽는다.
        "13": {"class_type": "VAELoaderMultiGPU",
               "inputs": {"vae_name": "wan_2.1_vae.safetensors",
                          "device": "cuda:1"}},
        "14": {"class_type": "VAEDecode",
               "inputs": {"samples": ["12", 0], "vae": ["13", 0]}},
        "15": {"class_type": "CreateVideo",
               "inputs": {"images": ["14", 0], "fps": float(fps)}},
        "16": {"class_type": "SaveVideo",
               "inputs": {"video": ["15", 0], "filename_prefix": prefix,
                          "format": "auto", "codec": "auto"}},
    }


def submit(graph, client_id):
    body = json.dumps({"prompt": graph, "client_id": client_id}).encode()
    req = urllib.request.Request(f"http://{SERVER}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))["prompt_id"]
    except urllib.error.HTTPError as e:
        # 검증 실패 시 ComfyUI가 어느 노드가 왜 틀렸는지 본문에 담아준다
        print("제출 거부됨:", e.read().decode()[:3000], file=sys.stderr)
        raise


def wait(prompt_id, poll=5, timeout=7200):
    """완료까지 대기. 반환: (소요초, 결과 히스토리 엔트리)"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(poll)
        h = json.load(urllib.request.urlopen(
            f"http://{SERVER}/history/{prompt_id}", timeout=30))
        if prompt_id in h:
            entry = h[prompt_id]
            status = entry.get("status", {})
            if status.get("completed") or status.get("status_str") in ("success", "error"):
                return time.time() - t0, entry
        print(f"  ... {time.time()-t0:6.0f}s 경과", flush=True)
    raise TimeoutError(f"{timeout}s 초과")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", required=True)
    p.add_argument("--negative", default=NEG)
    p.add_argument("--width", type=int, default=720)
    p.add_argument("--height", type=int, default=1280)
    p.add_argument("--length", type=int, default=121, help="프레임 수 (121 = 24fps 5초)")
    p.add_argument("--steps", type=int, default=4, help="Lightning 증류 LoRA 기준 4")
    p.add_argument("--shift", type=float, default=8.0)
    p.add_argument("--cfg", type=float, default=1.0, help="증류 모델은 CFG=1")
    p.add_argument("--sampler", default="euler")
    p.add_argument("--scheduler", default="simple")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--prefix", default="test/wan22")
    a = p.parse_args()

    g = build(a.prompt, a.negative, a.width, a.height, a.length, a.steps,
              a.shift, a.cfg, a.sampler, a.scheduler, a.seed, a.fps, a.prefix)

    secs_video = a.length / a.fps
    print(f"제출: {a.width}x{a.height}, {a.length}프레임 "
          f"({secs_video:.1f}초 @{a.fps}fps), {a.steps}스텝, seed={a.seed}")
    pid = submit(g, str(uuid.uuid4()))
    print(f"prompt_id={pid} — 대기 중")

    elapsed, entry = wait(pid)
    if entry.get("status", {}).get("status_str") == "error":
        print(f"\n실패 ({elapsed:.0f}s)")
        for m in entry["status"].get("messages", [])[-6:]:
            print("   ", json.dumps(m, ensure_ascii=False)[:600])
        sys.exit(1)

    outs = [f for o in entry.get("outputs", {}).values()
            for f in o.get("images", []) + o.get("videos", [])]
    print(f"\n완료: {elapsed:.1f}초 ({elapsed/60:.2f}분)")
    print(f"영상 1초당 생성시간: {elapsed/secs_video:.1f}초")
    for f in outs:
        print("  출력:", f.get("subfolder", ""), f.get("filename"))


if __name__ == "__main__":
    main()
