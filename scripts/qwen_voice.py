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
import re
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
# 승인된 문구다. 손대지 말 것 — "차분히"를 빼고 "낮고 담담하게"로 바꿨더니
# 오히려 급하고 높아졌다(실측). 미세 조정도 이 문장 구조 안에서만 한다.
VOICE = "처음부터 끝까지 한 톤으로, 감정을 싣지 말고 책을 차분히 읽어 내려가듯"


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
    for s in strip_lines(sentences):
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


def trim_silence(wav, sr, keep: float = 0.15):
    """말 앞뒤의 무음을 깎는다. 양 끝에 keep 초만 남긴다.

    Qwen 은 문장마다 앞뒤에 무음을 붙여 내놓는다(실측: 미녀와 야수 51.3초 중
    8.5초가 무음이었다). 문장을 이어 붙이면 앞 문장의 뒤 무음과 다음 문장의 앞
    무음이 겹쳐 1.5초씩 침묵이 생긴다 — 말하다 멈춘 것처럼 들린다.
    Azure 파이프라인에는 이걸 깎는 코드가 있었는데 갈아타면서 빠뜨렸다.
    """
    import numpy as np
    loud = np.abs(wav) > 0.02
    if not loud.any():
        return wav
    i = max(0, int(loud.argmax()) - int(sr * keep))
    j = min(len(wav), len(wav) - int(loud[::-1].argmax()) + int(sr * keep))
    return wav[i:j]


# ── 인물 대사 한마디 ────────────────────────────────────────────────────
#
# 낭독 문장 끝에 [역할·감정] "대사" 를 붙이면 그 대사만 다른 목소리로 읽는다(사용자 요청
# 09-08: "그때 한 아이가 소리쳤습니다 '애들아 조심해!' — 성별·나이·감정에 맞는 음성").
#   예) 층층대 밑에서 싸늘한 손이 눈을 가렸습니다. [소녀·장난] "내가 누구게요?"
# 규칙: 대사는 문장 **끝**에 하나만, 앞에 지문(누가 말했는지)이 있어야 한다. 대사 ≤16자.
# 목소리는 VoiceDesign(자연어 묘사 → 새 목소리)으로 만들고 역할마다 씨앗을 고정해
# 같은 역할은 작품 안에서 같은 목소리가 나오게 한다. 낭독(소희)과 음량을 맞춘 뒤
# 0.25초 숨을 두고 잇는다.
VD_MODEL_DIR = "/data/bard/models/qwen3-tts-voicedesign"
# 목소리 묘사는 **영어**로 적는다. 한국어 묘사는 성별·나이를 거꾸로 냈다(실측 09-08:
# "열 살 여자아이" → 130Hz 남자 소리, "큰 짐승 같은 남자" → 348Hz). 영어 묘사는
# 소녀 440Hz·소년 381Hz·짐승 176Hz·할아버지 98Hz 로 의도대로 나왔다. 말은 한국어(language).
# (묘사, 씨앗, 목표 F0[Hz]). 씨앗은 09-08 여섯 후보 중 담담한 문장에서 목표 음높이에 가장
# 가까운 것. 감정 문구가 붙으면 추첨이 달라지므로 synth_line 이 음높이를 재서 벗어나면
# 다음 씨앗(+17)으로 다시 뽑는다(최대 4회).
ROLE_DESC = {
    "소년": ("A ten-year-old Korean boy, high clear childlike voice", 1186, 330),
    "소녀": ("A ten-year-old Korean girl, high light childlike voice", 1102, 380),
    "아이": ("A six-year-old Korean child, small sweet toddler-like voice", 1188, 400),
    "청년": ("A Korean man in his early twenties, bright clear youthful voice", 1104, 150),
    "처녀": ("A Korean woman in her early twenties, clear light youthful voice", 1122, 250),
    "남자": ("A Korean man in his forties, deep bass firm mature voice", 1157, 120),
    "여자": ("A Korean woman in her forties, warm calm mature voice", 1192, 200),
    "할아버지": ("An old Korean man in his seventies, very deep bass slow husky voice", 1176, 100),
    "할머니": ("An old Korean woman in her seventies, thin slow gentle voice", 1177, 190),
    "짐승": ("A huge monster with an extremely deep bass, gravelly, rumbling voice, far below a normal man", 1161, 105),
}
ROLE_ALIAS = {"어린이": "아이", "남자아이": "소년", "여자아이": "소녀", "노인": "할아버지",
              "아저씨": "남자", "아주머니": "여자", "아가씨": "처녀", "호랑이": "짐승", "괴물": "짐승",
              "임금": "남자", "선생": "남자", "어머니": "여자", "아버지": "남자"}
MOOD_DESC = {
    "다급": "urgent and hurried", "외침": "shouting loudly without raising the pitch", "놀람": "startled, gasping in surprise",
    "장난": "playful and giggly", "다정": "tender and gentle", "화남": "angry, growling low in the throat",
    "슬픔": "sad, voice trembling", "속삭임": "whispering softly", "으스댐": "boastful and proud",
    "겁": "frightened, voice shaking", "담담": "calm and plain", "웃음": "laughing warmly",
}
LINE_RE = re.compile(r'\s*\[([^\]\[]*)\]\s*[“"「]([^”"」]+)[”"」]\s*$')


def parse_line(sentence: str):
    """(지문, 대사, 역할, 감정). 대사가 없으면 (문장, None, None, None)."""
    m = LINE_RE.search(sentence)
    if not m:
        return sentence, None, None, None
    tag, line = m.group(1), m.group(2).strip()
    parts = [t.strip() for t in re.split(r"[·,/ ]+", tag) if t.strip()]
    role = ROLE_ALIAS.get(parts[0], parts[0]) if parts else "남자"
    mood = parts[1] if len(parts) > 1 else "담담"
    nar = sentence[:m.start()].strip()
    if nar and nar[-1] not in ".!?…":
        nar += "."
    return nar or line, line, role, mood


def strip_lines(sentences):
    """한 호흡 낭독에 넣을 지문만 남긴다."""
    return [parse_line(s)[0] for s in sentences]


_VD = {}


def synth_line(text: str, role: str, mood: str, device: str = "auto"):
    """대사 한마디를 역할·감정에 맞는 목소리로. (파형, 표본율)."""
    import torch
    from qwen_tts import Qwen3TTSModel
    if "model" not in _VD:
        dev = pick_device() if device in ("", "auto") else device
        _VD["model"] = Qwen3TTSModel.from_pretrained(
            VD_MODEL_DIR, device_map=dev, dtype=torch.float16, attn_implementation="sdpa")
    import numpy as np
    desc, seed, target = ROLE_DESC.get(role, ROLE_DESC["남자"])
    instruct = f"{desc}, {MOOD_DESC.get(mood, 'calm and plain')}, speaking Korean"
    best = None
    # 감정 문구를 넣은 묘사로 여섯 씨앗, 그래도 안 맞으면 감정 없는 묘사로 세 씨앗
    # (실측 09-08: "angry and harsh" 가 짐승을 247Hz 로 끌어올렸다 — 감정보다 성대가 먼저다).
    plans = [(instruct, seed + 17 * k) for k in range(6)] + \
            [(f"{desc}, calm and plain, speaking Korean", seed + 17 * k) for k in range(3)]
    for ins, sd in plans:
        torch.manual_seed(sd)
        wavs, sr = _VD["model"].generate_voice_design(text=text, language="Korean", instruct=ins)
        w = np.asarray(wavs[0] if isinstance(wavs, list) else wavs, dtype=np.float32).squeeze()
        f = _f0(w, sr)
        err = abs(np.log2(max(f, 1.0) / target))
        if best is None or err < best[0]:
            best = (err, w, sr, f, sd)
        if f and target * 0.75 <= f <= target * 1.35:
            break
    err, w, sr, f, used = best
    print(f"  대사 목소리 [{role}] {f:.0f}Hz (목표 {target}, 씨앗 {used})", flush=True)
    return w, sr


def _f0(x, sr, fmin=70, fmax=450) -> float:
    """YIN 식 기본 주파수(중앙값). 목소리가 역할의 음높이에 맞게 뽑혔는지 재는 용도."""
    import numpy as np
    win = int(sr * 0.05); hop = int(sr * 0.02); tmax = int(sr / fmin); tmin = int(sr / fmax); vals = []
    for i in range(0, len(x) - win - tmax, hop):
        seg = x[i:i + win + tmax]
        if np.abs(seg[:win]).max() < 0.03:
            continue
        frame = seg[:win]
        d = np.array([0.0] + [float(np.dot(frame - seg[t:t + win], frame - seg[t:t + win])) for t in range(1, tmax + 1)])
        cum = np.cumsum(d[1:]); cmnd = np.ones(tmax + 1); cmnd[1:] = d[1:] * np.arange(1, tmax + 1) / np.maximum(cum, 1e-9)
        cand = [t for t in range(tmin, tmax + 1) if cmnd[t] < 0.15]
        if cand:
            vals.append(sr / cand[0])
    return float(np.median(vals)) if vals else 0.0


def splice_line(nar, line, sr, gap: float = 0.25):
    """지문 + 숨 + 대사. 대사 음량을 지문에 맞춘다(살짝 크게 — 앞으로 나오는 목소리)."""
    import numpy as np
    nar = trim_silence(nar, sr, keep=0.05)
    line = trim_silence(line, sr, keep=0.05)
    rn = float(np.sqrt(np.mean(nar ** 2)) + 1e-6)
    rl = float(np.sqrt(np.mean(line ** 2)) + 1e-6)
    line = line * min(3.0, rn * 1.15 / rl)
    peak = float(np.abs(line).max())
    if peak > 0.98:
        line = line * (0.98 / peak)
    return np.concatenate([nar, np.zeros(int(sr * gap), dtype=nar.dtype), line])


def attach_lines(pairs, sentences, device: str = "auto"):
    """문장 wav 목록에 대사를 끼운다. 대사 없는 문장은 그대로."""
    out = []
    for pair, s in zip(pairs, sentences):
        nar, line, role, mood = parse_line(s)
        if pair is None or not line:
            out.append(pair); continue
        try:
            lw, lsr = synth_line(line, role, mood, device)
            w, sr = pair
            if lsr != sr:
                import numpy as np
                t_old = np.arange(len(lw)) / lsr; t_new = np.arange(int(len(lw) * sr / lsr)) / sr
                lw = np.interp(t_new, t_old, lw).astype(np.float32)
            out.append((splice_line(w, lw, sr), sr))
            print(f"  대사 [{role}·{mood}] {line}", flush=True)
        except Exception as e:                    # 대사 하나 때문에 편 전체를 버리지 않는다
            print(f"  ! 대사 합성 실패({line[:12]}…): {e}", file=sys.stderr)
            out.append(pair)
    return out


def squeeze_pauses(wav, sr, max_pause: float = 0.55, thresh: float = 0.02):
    """문장 **안**의 긴 쉼을 max_pause 초로 줄인다. 양 끝은 건드리지 않는다(trim_silence 몫).

    한 호흡 생성은 절 사이("…밝고 | 이야기는…")에서 1.1~1.3초를 쉰다(실측 09-08 홍학의
    자리 S1·S2·S13). 쉼표를 빼도 그대로였다 — 문장 부호가 아니라 생성 버릇이다. 사용자는
    이것을 "뚝뚝 끊김"으로 듣는다. 0.55초면 숨은 남고 끊김은 사라진다.
    """
    import numpy as np
    loud = np.abs(wav) > thresh
    if not loud.any():
        return wav
    first, last = int(loud.argmax()), len(wav) - int(loud[::-1].argmax())
    keep = int(sr * max_pause)
    out, i = [wav[:first]], first
    while i < last:
        if loud[i]:
            j = i
            while j < last and loud[j]:
                j += 1
            out.append(wav[i:j]); i = j
        else:
            j = i
            while j < last and not loud[j]:
                j += 1
            run = wav[i:j]
            out.append(run if len(run) <= keep else np.concatenate([run[:keep // 2], run[-(keep - keep // 2):]]))
            i = j
    out.append(wav[last:])
    return np.concatenate(out)


def _align_bounds_whisper(w, sr, sentences):
    """낭독 원문을 아는 채로 음성인식 단어 시각에 맞춰 문장 경계를 찍는다.

    함정 실측: numpy 배열을 그대로 넘기면 whisper 가 16kHz 로 가정한다 —
    24kHz 음원의 시각이 1.5배로 늘어나 경계가 음원 밖을 가리켰다(77.5초
    음원에 116초 시각). 반드시 16kHz 로 리샘플해 넘긴다. 매핑은 전사
    오차에 강한 문자 단위 정렬(difflib)로 한다.
    """
    import re, difflib, numpy as np
    from faster_whisper import WhisperModel
    x = np.asarray(w, dtype=np.float32)
    if sr != 16000:
        t_old = np.arange(len(x)) / sr
        t_new = np.arange(int(len(x) * 16000 / sr)) / 16000
        x = np.interp(t_new, t_old, x).astype(np.float32)
    m = WhisperModel("base", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(x, language="ko", word_timestamps=True,
                           beam_size=1, condition_on_previous_text=False)
    words = [wd for sg in segs for wd in (sg.words or [])]
    if len(words) < len(sentences) * 2:
        raise RuntimeError("단어 시각 부족")
    norm = lambda t: re.sub(r"[^가-힣0-9]", "", t)
    src = "".join(norm(t) for t in sentences)
    tr_chars, char2word = [], []
    for wi, wd in enumerate(words):
        for ch in norm(wd.word):
            tr_chars.append(ch); char2word.append(wi)
    tr = "".join(tr_chars)
    sm = difflib.SequenceMatcher(None, src, tr, autojunk=False)
    if sm.ratio() < 0.55:
        raise RuntimeError(f"전사 일치율 낮음 {sm.ratio():.2f}")
    ops = sm.get_opcodes()
    def map_pos(sp):
        for tag, a1, a2, b1, b2 in ops:
            if a1 <= sp < a2:
                if a2 > a1:
                    return b1 + int((sp - a1) / (a2 - a1) * max(b2 - b1, 1))
                return b1
        return len(tr) - 1
    cum = np.cumsum([len(norm(t)) for t in sentences])[:-1]
    total = len(w) / sr
    gap = lambda k: words[k + 1].start - words[k].end
    # whisper 의 낱말 시각은 앞뒤 무음을 낱말에 붙여 늘리는 일이 잦아 낱말 틈만으로는
    # 경계가 한 낱말 앞뒤로 어긋난다(실측: 이상한 샘물 s4/s5, s8/s9 가 "돌아왔지요"
    # "살았지요" 앞에서 잘림). 정확한 자리는 파형에서 잡는다 — 추정 경계 ±1.5초 안의
    # 무음 골짜기 중 가장 긴 것(문장 사이 쉼 1.5~2.5초, 쉼표 쉼은 0.5초 미만)의 한가운데.
    hop = int(sr * 0.02)
    env = np.array([np.abs(w[i:i + hop]).max() for i in range(0, len(w) - hop, hop)])
    quiet = env < 0.02
    runs, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        if not q and start is not None:
            runs.append((start * 0.02, i * 0.02)); start = None
    if start is not None:
        runs.append((start * 0.02, len(quiet) * 0.02))

    def snap(b0):
        near = [(a, e) for a, e in runs if e - a >= 0.3 and a - 1.5 <= b0 <= e + 1.5]
        if not near:
            return b0
        a, e = max(near, key=lambda r: (r[1] - r[0]) - 0.2 * abs((r[0] + r[1]) / 2 - b0))
        return (a + e) / 2

    bounds, prev = [], -1
    for sp in cum:
        # sp 는 **다음 문장 첫 글자**의 자리다. 예전엔 그 글자가 든 낱말 뒤에서 잘라
        # 다음 문장의 첫 낱말이 앞 문장 wav 꼬리에 붙었다(실측 2026-09-07: 09-01 이후
        # 24편에서 문장당 10~14개가 "문장 + 2초 쉼 + 다음 문장 첫말"로 잘려 뚝뚝 끊김).
        # 경계는 이 문장 마지막 글자(sp-1)가 든 낱말과 그 다음 낱말 사이에 놓는다.
        tp = min(map_pos(int(sp) - 1), len(tr) - 1)
        wi = max(char2word[tp], prev + 1)
        wi = min(wi, len(words) - 2)
        # 전사가 한 낱말쯤 어긋나도 문장 사이 쉼(한 호흡 녹음에선 1.5~2.5초)은 낱말
        # 사이 틈(0.5초 미만)보다 훨씬 길다 — 이웃한 틈 셋 중 가장 긴 것을 고른다.
        cands = [k for k in (wi - 1, wi, wi + 1) if prev + 1 <= k <= len(words) - 2]
        wi = max(cands, key=gap)
        prev = wi
        b = (words[wi].end + words[wi + 1].start) / 2
        b = snap(b)
        if bounds and b <= bounds[-1] + 0.5:   # 골짜기가 앞 경계와 겹치면 낱말 틈 자리로
            b = (words[wi].end + words[wi + 1].start) / 2
        bounds.append(min(b, total - 0.2))
    if any(b2 - b1 < 1.0 for b1, b2 in zip(bounds, bounds[1:])):
        raise RuntimeError("경계 간격 이상")
    return bounds


def synth_onebreath(model, sentences, tone: str = ""):
    """전체 낭독을 한 호흡으로 생성해 문장 경계 무음에서 가른다.

    문장마다 따로 생성하면 화자는 같아도 억양·템포가 문장마다 새로 뽑혀
    영상 안에서 목소리가 계속 바뀐다(실측: 문장 간 음색 유사도 최저 0.665,
    사용자 "계속 바뀌어 왜"). 한 번에 생성하면 하나의 억양 흐름이 전체를
    관통한다. 경계는 글자 수 누적 비율로 예상 위치를 잡고, 그 근처에서
    가장 길고 가까운 무음 골짜기를 고른다(쉼표 호흡과 문장 경계를 구별).
    매칭 신뢰가 약하면 문장별 방식으로 물러난다.
    """
    import numpy as np, torch
    sentences = strip_lines(sentences)             # 대사는 뒤에서 따로 읽어 붙인다
    full = "\n".join(x.strip() for x in sentences)
    torch.manual_seed(SEED)
    wavs, sr = model.generate_custom_voice(
        text=full, speaker=SPEAKER, language="Korean", instruct=VOICE)
    w = np.asarray(wavs[0] if isinstance(wavs, list) else wavs,
                   dtype=np.float32).squeeze()
    try:
        bounds = _align_bounds_whisper(w, sr, sentences)
        cuts = [0.0] + bounds + [len(w) / sr]
        pairs = []
        for i in range(len(sentences)):
            seg = w[int(cuts[i] * sr):int(cuts[i + 1] * sr)]
            pairs.append((trim_silence(seg, sr), sr))
        print("  한 호흡 + 원문 정렬", flush=True)
        return pairs
    except Exception as e:
        print(f"  원문 정렬 불가({e}) — 골짜기 매칭으로", flush=True)
    hop = int(sr * 0.02)
    env = np.array([np.abs(w[i:i + hop]).max()
                    for i in range(0, len(w) - hop, hop)])
    quiet = env < 0.02
    runs, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        if not q and start is not None:
            runs.append((start * 0.02, i * 0.02)); start = None
    gaps = [(a, b) for a, b in runs if (b - a) >= 0.22 and a > 0.5]
    chars = [len(x) for x in sentences]
    cum = np.cumsum(chars)[:-1] / sum(chars)
    total = len(w) / sr
    # 전역 최적 배정: 경계는 단조 증가해야 하고, 탐욕 선택은 뒤 경계를
    # 궁지로 몬다(실측: 조인 창에서 문장별로 물러났다). DP 로 전체 비용을
    # 최소화한다 — 비용 = 예상 위치와의 거리 - 골짜기 길이 보너스.
    mids = [(a + b) / 2 for a, b in gaps]
    lens = [b - a for a, b in gaps]
    targets = [float(f) * total for f in cum]
    NB, NG = len(targets), len(mids)
    INF = 1e18
    cost = [[INF] * (NG + 1) for _ in range(NB + 1)]
    back = [[-1] * (NG + 1) for _ in range(NB + 1)]
    for j in range(NG + 1):
        cost[0][j] = 0.0
    for i in range(1, NB + 1):
        for j in range(i, NG + 1):
            take = cost[i - 1][j - 1] + abs(mids[j - 1] - targets[i - 1]) - lens[j - 1] * 0.5
            skip = cost[i][j - 1]
            if take < skip:
                cost[i][j] = take; back[i][j] = 1
            else:
                cost[i][j] = skip; back[i][j] = 0
    if cost[NB][NG] >= INF / 2:
        print("  한 호흡 경계 매칭 불가 — 문장별로 물러남", flush=True)
        return synth(model, sentences, tone)
    bounds, i, j = [], NB, NG
    while i > 0:
        if back[i][j] == 1:
            bounds.append(mids[j - 1]); i -= 1; j -= 1
        else:
            j -= 1
    bounds.reverse()
    worst = max(abs(b - t) for b, t in zip(bounds, targets))
    if worst > 2.6:
        print(f"  한 호흡 경계 최대 이탈 {worst:.1f}s — 문장별로 물러남", flush=True)
        return synth(model, sentences, tone)
    cuts = [0.0] + bounds + [total]
    pairs = []
    for i in range(len(sentences)):
        seg = w[int(cuts[i] * sr):int(cuts[i + 1] * sr)]
        pairs.append((trim_silence(seg, sr), sr))
    return pairs


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
        wav = squeeze_pauses(trim_silence(wav, sr), sr)
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
    p.add_argument("--mode", default="onebreath", choices=["onebreath", "sentence"],
                   help="onebreath: 한 호흡 생성 + 원문 정렬(기본). 정렬 불가 시 자동 폴백")
    p.add_argument("--target", type=float, default=0.0,
                   help="맞출 전체 길이(초). 0 이면 있는 그대로 둔다")
    # 침묵을 0.12초까지 깎았더니 문장이 꼬리를 물고 이어져 쫓기듯 들렸다(실측:
    # "긴급한 듯한 목소리"). 낭독의 차분함은 어조만큼 **문장 사이 호흡**이 만든다.
    p.add_argument("--pad", type=float, default=0.35,
                   help="문장 뒤 호흡(초)")
    p.add_argument("--device", default="auto")
    a = p.parse_args()

    sents = json.loads(Path(a.narration).read_text(encoding="utf-8"))["sentences"]
    model = load_model(a.device)
    pairs = (synth_onebreath(model, sents, a.tone) if a.mode == "onebreath"
             else synth(model, sents, a.tone))
    if any(parse_line(x)[1] for x in sents):
        pairs = attach_lines(pairs, sents, a.device)
    ok = [x for x in pairs if x]
    if len(ok) != len(sents):
        sys.exit(f"합성 {len(ok)}/{len(sents)} — 중단")

    total = sum(len(w) / sr for w, sr in ok)
    speed = 1.0
    if a.target > 0:
        speed = max(0.85, min(1.15, total / a.target))
    write_wavs(pairs, a.prefix, speed, a.pad)
    print(json.dumps({"sentences": len(ok), "raw_sec": round(total, 1),
                      "speed": round(speed, 3),
                      "final_sec": round(total / speed, 1)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
