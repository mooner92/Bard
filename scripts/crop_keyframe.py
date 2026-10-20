#!/usr/bin/env python3
"""키프레임에서 가짜 자막을 잘라내고 I2V 입력 규격(480×848)으로 맞춘다.

Qwen-Image 는 문장을 그리라고 하면 종이 여백에 **뭉개진 한글 자막**을 얹는 버릇이 있다.
네거티브로도 완전히 막히지 않고, 고정 비율 크롭으로도 못 잡는다 — 자막이 앉는 높이가
그림마다 다르기 때문이다(실측: 상단 3%, 9~15%, 16% 아래 모두 나왔다).

예전 판정("배경색 78% 이상인 마지막 행 아래부터 그림")은 옅은 하늘·담벼락이 위쪽에
오는 그림에서 그림 한가운데를 여백으로 오인해 인물의 머리를 잘랐다(실측 2026-09-06
피아노 S2: 위 27.7% 절단, S15 21.7%, S6 15.9%). 그래서 이렇게 바꿨다:

  1. '빈 행' = 종이색이 97% 이상인 행(진짜 여백). 옅은 그림 행은 나뭇가지·인물 몇
     픽셀만으로도 빈 행이 아니다.
  2. 자막 띠 = 빈 행 사이에 낀 얇은 띠(높이 10% 이하)로, 행마다 배경이 55% 이상
     남아 있고(가는 획) 가로로 획 전환이 많다(글줄; 달·새 같은 고립 사물은 전환이
     2~4번뿐). 자막 띠가 있으면 그 아래 빈 띠가 끝나는 곳(그림 시작)까지 자른다.
  3. 자막이 없으면 가장자리의 순수 여백만 최대 8% 자른다 — 하늘이 종이색과 같은
     그림에서도 구도가 크게 밀리지 않도록.

위·아래 모두 같은 규칙이다.

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
EMPTY_FRAC = 0.97        # 이 비율 이상이 종이색이면 '빈 행'(진짜 여백)
STROKE_FRAC = 0.55       # 자막 행: 배경이 이 비율 이상 남는 가는 획
SEARCH_FRAC = 0.30       # 상하 각각 이 비율까지만 자막을 찾는다
BAND_MAX_FRAC = 0.10     # 자막 띠의 최대 높이
GAP_MIN_FRAC = 0.012     # 자막 띠 아래에 있어야 하는 빈 띠의 최소 높이
MIN_TRANSITIONS = 8      # 글줄로 볼 행당 획 전환(배경↔획) 최소 횟수의 중앙값
SIDE_MARGIN_FRAC = 0.03  # 글줄은 좌우에 이만큼 여백이 있다 (지평선·나무 띠는 끝까지 이어진다)
PLAIN_MAX_FRAC = 0.08    # 자막이 없을 때 가장자리 순수 여백을 자르는 상한
PAPER_MIN = 160          # 종이색이 이보다 어두우면(밤 장면) 자막도 여백도 없다고 보고 자르지 않는다


def row_stats(gray: np.ndarray) -> tuple:
    """행별 (배경 비율, 획 전환 횟수)와 획 마스크. 네 귀퉁이에서 종이색을 추정한다."""
    corners = np.concatenate([gray[:20, :40].ravel(), gray[:20, -40:].ravel(),
                              gray[-20:, :40].ravel(), gray[-20:, -40:].ravel()])
    bg = float(np.median(corners))
    ink = np.abs(gray - bg) > BG_TOL
    bg_frac = 1.0 - ink.mean(axis=1)
    trans = (ink[:, 1:] != ink[:, :-1]).sum(axis=1)
    return bg, bg_frac, trans, ink


def edge_cut(bg_frac: np.ndarray, trans: np.ndarray, ink: np.ndarray) -> int:
    """배열의 시작 쪽에서 잘라낼 행 수. 아래쪽은 뒤집어서 같은 함수를 쓴다."""
    h = len(bg_frac)
    w = ink.shape[1]
    limit = int(h * SEARCH_FRAC)
    empty = bg_frac >= EMPTY_FRAC
    side = int(w * SIDE_MARGIN_FRAC)

    i = 0
    while i < limit and empty[i]:
        i += 1
    lead = i
    cut = min(lead, int(h * PLAIN_MAX_FRAC))

    pos = lead
    while pos < limit:
        j = pos
        while j < limit and not empty[j]:
            j += 1
        if j >= limit:          # 띠가 탐색 한계까지 이어진다 → 그림 본체
            break
        band_h = j - pos
        k = j
        while k < h and empty[k]:
            k += 1
        gap = k - j
        thin = (bg_frac[pos:j] >= STROKE_FRAC).mean() >= 0.9
        texty = float(np.median(trans[pos:j])) >= MIN_TRANSITIONS
        cols = ink[pos:j].any(axis=0)
        framed = not cols[:side].any() and not cols[w - side:].any()
        if band_h <= h * BAND_MAX_FRAC and gap >= h * GAP_MIN_FRAC and thin and texty and framed:
            cut = min(k, limit)  # 자막 띠와 그 아래 빈 띠까지 잘라 그림 시작에서 시작
            pos = k
        else:
            break
    return max(0, cut)


def content_bounds(gray: np.ndarray) -> tuple:
    """그림이 시작·끝나는 행을 찾는다. 반환: (top, bottom) 행 인덱스(포함)."""
    h = gray.shape[0]
    bg, bg_frac, trans, ink = row_stats(gray)
    if bg < PAPER_MIN:      # 어두운 화면: 귀퉁이가 그림이지 종이가 아니다 → 손대지 않는다
        return 0, h - 1
    top = edge_cut(bg_frac, trans, ink)
    bottom = h - 1 - edge_cut(bg_frac[::-1], trans[::-1], ink[::-1])
    return top, max(bottom, top + 1)


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
