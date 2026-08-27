#!/usr/bin/env python3
"""Qwen3-TTS 로 낭독을 합성한다 (Azure 대체).

왜 바꿨나: Azure 한국어 음성 10종은 **감정 스타일이 하나도 없다**(실측: 전부
StyleList 가 비어 있다). 그래서 다양성이라고는 목소리를 고르는 것뿐이었고,
어조·속도·높낮이를 손댈 방법이 없었다. Qwen3-TTS 의 VoiceDesign 은 원하는
목소리를 **문장으로 적어** 지정한다.

    "차분하고 낮은 여성 목소리로, 감정을 절제하고 담담하게 읽어 내려가듯"

사양(실측, Quadro RTX 6000 / Turing sm_75):
  - bf16 텐서코어가 없고 FlashAttention 도 Ampere 이상 전용이라
    fp16 + sdpa 로 올린다. 모델은 스스로 순수 PyTorch 로 폴백한다.
  - 적재 3.7초, 6초 문장 합성에 약 20초.
  - Azure 보다 0.85배로 짧게 말한다 → 길이는 atempo 로 맞춘다(음높이 유지).

이 파일은 venv-tts 로 돌린다. 파이프라인이 쓰는 venv 에 qwen-tts 를 넣으면
transformers 가 갈리면서 밤 배치가 깨진다.

사용:
  venv-tts/bin/python scripts/qwen_voice.py --narration output/x/narration_night.json \\
      --tone 서늘 --prefix output/tts/x_night_s --target 52
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

MODEL_DIR = "/data/bard/models/qwen3-tts-customvoice"

# 세 후보(담담·조곤·여운)를 들어 보고 고른 것. 모든 작품의 바탕이 된다.
INSTRUCT_BASE = "차분하고 낮은 여성 목소리로, 감정을 절제하고 담담하게 읽어 내려가듯"

# 톤은 바탕 위에 한 겹만 얹는다. 여성 화자와 차분한 결은 어느 작품에서도 지키고
# 작품 성격만 미세하게 바꾼다 — 목소리가 작품마다 딴사람이 되면 채널이 흩어진다.
#
# 속도를 건드리는 말은 넣지 않는다. "조금 더 느리게" 한 마디에 춘향전이 54초에서
# 69초로 늘어졌고, 되돌리느라 1.28배로 당기니 말이 쫓기듯 들렸다(실측). 길이는
# 지시문이 아니라 atempo 로 맞추고, 지시문은 결만 정한다.
TONE_HINT = {
    "서늘": ", 조금 더 낮게",
    "긴장": ", 숨을 조금 죽이고 단단하게",
    "생동": ", 조금 더 밝고 또렷하게",
    "담담": "",
}


def instruct_for(tone: str) -> str:
    return INSTRUCT_BASE + TONE_HINT.get((tone or "").strip(), "")


# ── 목소리 하나로 고정한다 ────────────────────────────────────────────────
#
# VoiceDesign 은 부를 때마다 목소리를 **새로 만든다**. 그래서 여덟 문장이 조금씩
# 다른 화자가 되고 그중 몇은 늘어졌다(실측: 춘향전에서 몇 문장이 처졌다).
#
# 한동안 CustomVoice 의 이름 있는 화자(sohee)로 피했는데, 그러면 흔들림은 잡히나
# **고른 목소리 자체가 달라진다** — 지시문만 옮기고 성대를 바꾼 셈이었다.
# 씨앗을 고정하면 VoiceDesign 이 같은 목소리를 재현한다(실측: 같은 씨앗·같은
# 문장에서 파형이 일치했다). 고른 목소리를 지키면서 흔들림도 없앤다.
# 씨앗마다 성대가 다르다. 고른 목소리를 낸 씨앗을 음색 유사도로 되찾았다
# (실측: 99 가 0.966, 31337 이 0.971, 처음 쓰던 20260827 은 0.877 로 딴사람이었다).
SPEAKER = "sohee"   # CustomVoice 의 유일한 한국어 여성 화자
SEED = 99
# 감정을 얹는 말은 넣지 않는다. "부드럽게 이어 가듯" 한 마디에 걱정하는 어조가
# 실렸다(실측). 한 톤으로 눌러 두면 이야기는 그림과 문장이 낸다.
VOICE = "처음부터 끝까지 한 톤으로, 감정을 싣지 말고 낮고 담담하게 책을 읽어 내려가듯"


def pick_device() -> str:
    """여유가 가장 큰 카드를 고른다.

    카드를 못 박아 두면 두 작업이 같은 카드를 다툰다 — 기존작 음성을 교체하는
    동안 밤 배치의 TTS 가 GPU1 여유 2GB 앞에서 0/8 로 실패했다(실측).
    """
    import torch
    if not torch.cuda.is_available():
        return "cpu"
    free = [(torch.cuda.mem_get_info(i)[0], i) for i in range(torch.cuda.device_count())]
    return f"cuda:{max(free)[1]}"


def load_model(device: str = "auto"):
    import torch
    from qwen_tts import Qwen3TTSModel
    if device in ("", "auto"):
        device = pick_device()
    return Qwen3TTSModel.from_pretrained(
        MODEL_DIR, device_map=device,
        dtype=torch.float16,           # Turing 에는 bf16 텐서코어가 없다
        attn_implementation="sdpa",    # FlashAttention 은 sm_80 이상 전용
    )


def synth(model, sentences, tone: str = ""):
    """문장마다 (파형, 표본율). 실패한 문장은 None 으로 남긴다.

    기준 음성을 복제해서 만든다 — 톤 인자는 남겨 두었으나 쓰지 않는다.
    목소리는 works/voices 의 둘로 고정하고, 작품 성격은 그림과 문장이 낸다.
    """
    import torch
    out = []
    for s in sentences:
        try:
            torch.manual_seed(SEED)       # 문장마다 같은 자리에서 시작해야 같은 목소리다
            wavs, sr = model.generate_custom_voice(
                text=s.strip(), speaker=SPEAKER, language="Korean", instruct=VOICE)
            out.append((wavs[0], sr))
        except Exception as e:            # 한 문장 때문에 편 전체를 버리지 않는다
            print(f"  ! 합성 실패: {s[:20]}… {e}", file=sys.stderr)
            out.append(None)
    return out


def dur(path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def write_wavs(pairs, prefix: str, speed: float = 1.0, pad: float = 0.0) -> list:
    """prefix{i}.wav 로 쓴다. speed<1 이면 느리게 늘리고, pad 초만큼 뒤에 숨을 둔다.

    Qwen 은 Azure 보다 빠르게 말해서 그대로 두면 영상이 목표 길이에 못 미친다.
    atempo 는 음높이를 건드리지 않으므로 목소리는 그대로고 속도만 바뀐다.

    다만 말을 늘리는 데는 한계가 있다 — 소희 화자는 원본보다 한참 빨라서 억지로
    맞추면 늘어져 들린다(실측: 춘향전이 53초 목표에 43초로 나왔다). 모자라는
    길이는 문장 뒤에 **숨**으로 채운다. 낭독에서 문장 사이의 여백은 원래 있는
    것이라 늘어진 말보다 훨씬 자연스럽다.
    """
    import numpy as np
    import soundfile as sf
    made = []
    for i, pair in enumerate(pairs, 1):
        if pair is None:
            continue
        wav, sr = pair
        if pad > 0:
            wav = np.concatenate([wav, np.zeros(int(sr * pad), dtype=wav.dtype)])
        out = Path(f"{prefix}{i}.wav")
        out.parent.mkdir(parents=True, exist_ok=True)
        if abs(speed - 1.0) < 0.02:
            sf.write(out, wav, sr)
        else:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
                raw = t.name
            sf.write(raw, wav, sr)
            subprocess.run(["ffmpeg", "-y", "-i", raw, "-filter:a", f"atempo={speed:.4f}",
                            "-ar", str(sr), str(out)], capture_output=True)
            Path(raw).unlink(missing_ok=True)
        made.append(out)
    return made


def main():
    p = argparse.ArgumentParser(description="Qwen3-TTS 낭독 합성")
    p.add_argument("--narration", required=True)
    p.add_argument("--prefix", required=True, help="output/tts/<작품>_night_s")
    p.add_argument("--tone", default="담담")
    p.add_argument("--target", type=float, default=0.0,
                   help="맞출 전체 길이(초). 0 이면 있는 그대로 둔다")
    p.add_argument("--device", default="auto")
    a = p.parse_args()

    sents = json.loads(Path(a.narration).read_text(encoding="utf-8"))["sentences"]
    model = load_model(a.device)
    pairs = synth(model, sents, a.tone)
    ok = [x for x in pairs if x]
    if len(ok) != len(sents):
        sys.exit(f"합성 {len(ok)}/{len(sents)} — 중단")

    total = sum(len(w) / sr for w, sr in ok)
    speed = 1.0
    if a.target > 0:
        speed = max(0.85, min(1.15, total / a.target))
    write_wavs(pairs, a.prefix, speed)
    print(json.dumps({"sentences": len(ok), "raw_sec": round(total, 1),
                      "speed": round(speed, 3),
                      "final_sec": round(total / speed, 1)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
