#!/usr/bin/env python3
"""키프레임에서 가짜 자막을 잘라내고 I2V 입력 규격(480×848)으로 맞춘다.

Qwen-Image 는 문장을 그리라고 하면 종이 여백에 **뭉개진 한글 자막**을 얹는 버릇이 있다.
네거티브로도 완전히 막히지 않고, 고정 비율 크롭으로도 못 잡는다 — 자막이 앉는 높이가
그림마다 다르기 때문이다(실측: 상단 3%, 9~15%, 16% 아래 모두 나왔다).

그래서 그림이 실제로 시작하는 줄을 찾아서 자른다. 여백은 행 분산이 거의 0이고,
자막은 그 여백 위의 고립된 분산 봉우리다. 분산이 충분히 높은 상태로 길게 이어지는
첫 줄이 그림의 시작이다.

사용:
  venv/bin/python scripts/crop_keyframe.py --src output/x_kf/night_s1_0001.png \
      --dst ComfyUI/input/night_x_1.png
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

W, H = 480, 848          # I2V 입력 규격
BG_TOL = 30              # 종이 배경으로 볼 밝기 허용 오차 (종이 질감 때문에 넉넉히)
BG_FRAC = 0.78           # 이 비율 이상이 배경색이면 여백(자막 포함)으로 본다
RUN_FRAC = 0.04          # 그림 시작 판정에 필요한 연속 길이 (전체 높이 대비)
SEARCH_FRAC = 0.30       # 상하 각각 이 비율까지만 자막을 찾는다
MARGIN = 4               # 찾은 경계에서 조금 더 안쪽으로


def content_bounds(gray: np.ndarray) -> tuple:
    """그림이 시작·끝나는 행을 찾는다. 반환: (top, bottom) 행 인덱스.

    자막은 종이 여백 위의 가는 획이라 그 행의 대부분이 여전히 배경색이다.
    분산으로 보면 여러 줄짜리 자막이 '그림'으로 오인되므로(실측) 배경 비율로 가른다.
    """
    h = gray.shape[0]
    # 네 귀퉁이에서 종이색을 추정한다 (그림은 가운데에 온다)
    corners = np.concatenate([gray[:20, :40].ravel(), gray[:20, -40:].ravel(),
                              gray[-20:, :40].ravel(), gray[-20:, -40:].ravel()])
    bg = float(np.median(corners))
    bg_frac = (np.abs(gray - bg) <= BG_TOL).mean(axis=1)

    limit = int(h * SEARCH_FRAC)

    # '첫 그림 줄'이 아니라 '마지막 여백 줄' 을 기준으로 자른다.
    # 자막이 여러 줄이면 줄마다 굵기가 달라 어떤 줄은 그림으로 오인된다(실측:
    # 세 줄 중 마지막 줄만 살아남았다). 여백으로 보이는 마지막 줄 아래에서 시작하면
    # 그 사이에 낀 자막까지 함께 사라진다.
    head = np.where(bg_frac[:limit] >= BG_FRAC)[0]
    top = int(head[-1]) + MARGIN if len(head) else 0
    tail = np.where(bg_frac[h - limit:] >= BG_FRAC)[0]
    bottom = h - limit + int(tail[0]) - MARGIN if len(tail) else h - 1
    return max(0, min(top, limit)), min(h - 1, max(bottom, h - 1 - limit))


def crop(src: Path, dst: Path) -> dict:
    im = Image.open(src).convert("RGB")
    g = np.asarray(im.convert("L"), dtype=np.float32)
    top, bottom = content_bounds(g)
    im = im.crop((0, top, im.width, bottom + 1))

    # 목표 비율로 자르기. 세로가 남으면 위쪽을 조금 더 남긴다(하늘·지붕이 위에 온다).
    tw, th = im.width, im.height
    want = W / H
    if tw / th > want:
        nw = int(round(th * want))
        im = im.crop(((tw - nw) // 2, 0, (tw - nw) // 2 + nw, th))
    else:
        nh = int(round(tw / want))
        off = int((th - nh) * 0.35)
        im = im.crop((0, off, tw, off + nh))

    im = im.resize((W, H), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)
    return {"src": str(src), "dst": str(dst), "top": int(top), "bottom": int(bottom)}


def main():
    p = argparse.ArgumentParser(description="키프레임 크롭 (가짜 자막 제거)")
    p.add_argument("--src", required=True)
    p.add_argument("--dst", required=True)
    a = p.parse_args()
    print(json.dumps(crop(Path(a.src), Path(a.dst)), ensure_ascii=False))


if __name__ == "__main__":
    main()
