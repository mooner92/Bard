#!/usr/bin/env python3
"""내레이션 톤 렌더러 — 말의 온도·텐션을 SSML 로 제어한다.

Azure 한국어 음성은 감정 스타일(mstts:express-as)을 **지원하지 않는다**
(실측: ko-KR 10개 음성 전부 StyleList 비어 있음). 그래서 감정은
prosody(속도·음높이·크기) + break(호흡) + emphasis(강세) 조합으로 만든다.

두 축으로 조절한다.
  톤(TONES)     : 전체 온도. 담담 / 따뜻 / 서늘 / 긴장 / 속삭임 / 생동
  텐션 곡선(ARCS): 문장별 기복. 한 편 안에서 오르내려야 낭독이 살아난다.

문장 안에 *별표*로 감싼 구절은 강세(emphasis)로 읽는다.

사용:
  venv/bin/python scripts/tts_render.py --narration output/tolstoy/narration_night.json \
      --tone 생동 --prefix output/tts/tolstoy_v2_s
  venv/bin/python scripts/tts_render.py --text "문장 하나" --tone 긴장 --out /tmp/a.wav
"""
import argparse
import html
import json
import re
import subprocess
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# rate/pitch/volume 은 SSML prosody 값. 백분율은 기본 발화 대비 증감.
TONES = {
    "담담": {"rate": "-3%", "pitch": "-2%", "volume": "+0%", "lead": 120,
             "desc": "차분한 다큐 내레이션. 기본값."},
    "따뜻": {"rate": "-6%", "pitch": "+2%", "volume": "-4%", "lead": 200,
             "desc": "낮고 부드럽게. 위로·회상 장면."},
    "서늘": {"rate": "-8%", "pitch": "-3%", "volume": "-2%", "lead": 260,
             "desc": "느리고 낮게. 불길함·거리감."},
    "긴장": {"rate": "+8%", "pitch": "+4%", "volume": "+3%", "lead": 60,
             "desc": "빠르고 높게. 추격·위기."},
    "속삭임": {"rate": "-10%", "pitch": "-2%", "volume": "-28%", "lead": 300,
               "desc": "작고 느리게. 비밀·고백."},
    "생동": {"rate": "+3%", "pitch": "+5%", "volume": "+4%", "lead": 90,
             "desc": "밝고 탄력 있게. 소개·추천."},
}

# 텐션 곡선: 문장 위치별 가감(퍼센트포인트). 도입은 눌러서 시작하고
# 중반에 올렸다가 마지막 두 문장에서 다시 내려 여운을 만든다.
ARCS = {
    "평탄": [0, 0, 0, 0, 0, 0, 0, 0],
    "상승": [-3, -2, 0, 2, 4, 5, 2, -2],
    "산형": [-2, 0, 3, 5, 3, 0, -2, -4],
    "하강": [4, 3, 1, 0, -1, -2, -3, -5],
}
# 고전 낭독 기본값: 차분한 남성 저음. 여성 음성(SunHi)은 --voice 로 계속 쓸 수 있다.
VOICE_DEFAULT = "ko-KR-InJoonNeural"


def _env(key: str) -> str:
    f = BASE / ".env"
    for line in (f.read_text(encoding="utf-8").splitlines() if f.exists() else []):
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def _shift(value: str, delta: int) -> str:
    """'-3%' 에 +4 를 더해 '+1%' 로. 곡선을 톤 위에 얹는다."""
    n = int(re.sub(r"[^0-9-]", "", value) or 0) + delta
    return f"{n:+d}%"


def build_ssml(sentence: str, tone: str, delta: int = 0, voice: str = VOICE_DEFAULT) -> str:
    t = TONES[tone]
    body = html.escape(sentence.strip())
    # *강조* -> emphasis. escape 이후에 치환해야 태그가 깨지지 않는다.
    body = re.sub(r"\*([^*]+)\*", r"<emphasis level='strong'>\1</emphasis>", body)
    # 쉼표 뒤 짧은 호흡. 이게 없으면 낭독이 기계적으로 들린다.
    body = body.replace(", ", ", <break time='140ms'/>")
    lead = f"<break time='{t['lead']}ms'/>" if t["lead"] else ""
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='ko-KR'>"
        f"<voice name='{voice}'>"
        f"<prosody rate='{_shift(t['rate'], delta)}' pitch='{_shift(t['pitch'], delta)}' "
        f"volume='{t['volume']}'>{lead}{body}</prosody>"
        "</voice></speak>"
    )


def synth(ssml: str, out: Path) -> float:
    """SSML -> wav. 반환값은 초 단위 길이(내레이션이 영상 길이의 기준이다)."""
    region, key = _env("AZURE_SPEECH_REGION"), _env("AZURE_SPEECH_KEY")
    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),
        headers={"Ocp-Apim-Subscription-Key": key,
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
                 "User-Agent": "bard-tts"},
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=60) as r:
        out.write_bytes(r.read())
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(out)], capture_output=True, text=True)
    return round(float(d.stdout.strip() or 0), 2)


def main():
    p = argparse.ArgumentParser(description="내레이션 톤 렌더링")
    p.add_argument("--narration", help="narration*.json 경로")
    p.add_argument("--text", help="문장 하나만 렌더링")
    p.add_argument("--tone", default="담담", choices=list(TONES))
    p.add_argument("--arc", default="산형", choices=list(ARCS))
    p.add_argument("--voice", default=VOICE_DEFAULT)
    p.add_argument("--prefix", default="", help="출력 접두사 (예: output/tts/work_v2_s)")
    p.add_argument("--out", default="", help="--text 용 단일 출력 경로")
    a = p.parse_args()

    if a.text:
        dst = Path(a.out or "/tmp/tone.wav")
        sec = synth(build_ssml(a.text, a.tone, voice=a.voice), dst)
        print(json.dumps({"out": str(dst), "sec": sec}, ensure_ascii=False))
        return

    nar = json.loads(Path(a.narration).read_text(encoding="utf-8"))
    sents = nar["sentences"]
    # 대본이 자기 톤을 들고 있으면 그걸 따른다 (write_script --tone 로 쓴 값).
    tone = a.tone if a.tone != "담담" else nar.get("tone", a.tone)
    if tone not in TONES:
        tone = a.tone
    a.tone = tone
    arc = ARCS[a.arc]
    files, durs = [], []
    for i, s in enumerate(sents):
        delta = arc[i] if i < len(arc) else 0
        out = Path(f"{a.prefix}{i+1}.wav")
        durs.append(synth(build_ssml(s, a.tone, delta, a.voice), out))
        files.append(str(out))
        print(f"  s{i+1} {a.tone}{delta:+d} {durs[-1]:>5.2f}초  {s[:28]}")
    print(json.dumps({"files": files, "durations": durs,
                      "total": round(sum(durs), 2)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
