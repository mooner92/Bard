#!/usr/bin/env python3
"""Ollama HTTP API 헬퍼. stream=false 로만 호출하고 사고 과정(thinking)을 제거한다."""
import json
import re
import urllib.request

OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3.6:27b"

# 모델이 <think>...</think> 로 감싸거나, 그냥 "Here's a thinking process:" 로
# 평문 사고를 흘리는 경우가 둘 다 관측된다. 둘 다 걷어낸다.
THINK_TAG = re.compile(r"<think>.*?</think>", re.S)
THINK_OPEN = re.compile(r"<think>.*", re.S)


def strip_think(text: str) -> str:
    text = THINK_TAG.sub("", text)
    text = THINK_OPEN.sub("", text)
    return text.strip()


def ask(prompt: str, temperature: float = 0.7, num_predict: int = 1200,
        timeout: int = 900, think: bool = False) -> str:
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": think,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    out = data.get("response", "")
    if data.get("thinking"):
        # think=true 로 돌았을 때 별도 필드로 온다 -- 본문에는 섞이지 않는다.
        pass
    return strip_think(out)
