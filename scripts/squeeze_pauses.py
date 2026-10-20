#!/usr/bin/env python3
"""이미 만든 문장 wav 의 안쪽 긴 쉼을 줄인다(qwen_voice.squeeze_pauses 와 같은 규칙).
  venv-tts/bin/python scripts/squeeze_pauses.py output/tts/<work>_night_s*.wav
"""
import sys
from pathlib import Path
import numpy as np, soundfile as sf
sys.path.insert(0, str(Path(__file__).parent))
from qwen_voice import squeeze_pauses
for f in sys.argv[1:]:
    x, sr = sf.read(f, dtype="float32")
    if x.ndim > 1: x = x[:, 0]
    y = squeeze_pauses(x, sr)
    sf.write(f, y, sr)
    print(f"{Path(f).name}: {len(x)/sr:.2f}s -> {len(y)/sr:.2f}s")
