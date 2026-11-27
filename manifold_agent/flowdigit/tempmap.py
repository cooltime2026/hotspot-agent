"""온도 그림(바닥면 또는 윗면, 4x4 칸 선이 보이는 그림) → 16칸의 평균·최고 온도.

  python flowdigit/tempmap.py <사진번호> <Tmax> [--tmin 20]
출력: 화면 기준 4x4 표 (위쪽 행 = 화면 위, 왼쪽 열 = 화면 왼쪽). 칸 이름(r_c)으로 바꾸는 방향은
      그림마다 다르므로(바닥면은 뒤집혀 보임) 따로 정해야 한다(--orient).
방법: 판 영역의 네 모서리를 찾아 원근 보정(호모그래피) → 칸마다 안쪽 76%를 표본 → 색상바 색과 가장 가까운 띠 값.
"""
from __future__ import annotations
import argparse, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from digitize import find_colorbars, lut_from_bar   # noqa: E402


def homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y, -u], [0, 0, 0, x, y, 1, -v * x, -v * y, -v]]
    _, _, vt = np.linalg.svd(np.array(A, float)); return vt[-1].reshape(3, 3)


def read(path, tmax, tmin=20.0, ref_lut=None):
    im = np.array(Image.open(path).convert("RGB")).astype(float); H, W, _ = im.shape
    bars = find_colorbars(im, min_rows=1)
    if not bars:
        raise RuntimeError("색상바 없음")
    bar = max(bars, key=lambda b: b[0])                     # 가장 아래 막대
    lut = lut_from_bar(im, bar)
    # 띠(색이 일정한 구간) 평균색과 값
    bands, i0 = [], 0
    for i in range(1, len(lut) + 1):
        if i == len(lut) or np.abs(lut[i] - lut[i0]).max() > 12:
            if i - i0 >= 3:
                bands.append((lut[i0:i].mean(0), ((i0 + i) / 2) / len(lut)))
            i0 = i
    if len(bands) < 15 and ref_lut is not None:              # 색상바가 잘린 그림: 다른 그림의 색상표를 빌림
        bands = ref_lut
    bc = np.array([b[0] for b in bands]); bf = np.array([b[1] for b in bands])
    bval = tmin + bf * (tmax - tmin)
    # 판 영역: 배경(밝은 회색 246 근처)이 아닌 것. 색상바·UI 아래쪽은 제외
    from scipy import ndimage
    sat = im.max(2) - im.min(2)
    col = (sat > 25) | (im.max(2) < 60)                      # 판의 색(검정~보라~노랑) + 검정 선
    col[bar[4] - 60:, :] = False
    lab, n = ndimage.label(col)
    if n == 0:
        raise RuntimeError("판 영역을 못 찾음")
    big = np.argmax(ndimage.sum(col, lab, range(1, n + 1))) + 1
    plate = ndimage.binary_fill_holes(lab == big)              # 가운데 흰 부분(최고온도)도 포함
    ys, xs = np.nonzero(plate)
    if len(xs) < 1000:
        raise RuntimeError("판 영역을 못 찾음")
    s, d = xs + ys, xs - ys
    TL = (xs[s.argmin()], ys[s.argmin()]); BR = (xs[s.argmax()], ys[s.argmax()])
    TR = (xs[d.argmax()], ys[d.argmax()]); BL = (xs[d.argmin()], ys[d.argmin()])
    Hm = homography([(0, 0), (1, 0), (1, 1), (0, 1)], [TL, TR, BR, BL])   # 단위 정사각형 → 화면
    mean = np.full((4, 4), np.nan); mx = np.full((4, 4), np.nan)
    g = np.linspace(0.12, 0.88, 25)
    for r in range(4):
        for c in range(4):
            vals = []
            for a in g:
                for b in g:
                    u, v = (c + a) / 4, (r + b) / 4
                    p = Hm @ np.array([u, v, 1.0]); x, y = int(round(p[0] / p[2])), int(round(p[1] / p[2]))
                    if 0 <= x < W and 0 <= y < H:
                        col = im[y, x]
                        if col.max() < 25:                       # 칸 경계 검정 선
                            continue
                        vals.append(bval[np.abs(bc - col).sum(1).argmin()])
            if vals:
                mean[r, c] = np.mean(vals); mx[r, c] = np.max(vals)
    return dict(lut=bands, mean=mean, max=mx, corners=(TL, TR, BR, BL), band=(tmax - tmin) / len(bands), n_bands=len(bands))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("img", type=int); ap.add_argument("tmax", type=float)
    ap.add_argument("--tmin", type=float, default=20.0); a = ap.parse_args()
    r = read(os.path.join(HERE, "..", "images", f"{a.img}.png"), a.tmax, a.tmin)
    print(f"색 띠 {r['n_bands']}개 (1띠 ≈ {r['band']:.1f} ℃), 판 모서리 {r['corners']}")
    print("칸 평균 온도 (화면 기준, 위 행부터):")
    for row in r["mean"]:
        print("  " + "  ".join(f"{x:6.1f}" for x in row))
    print("칸 최고 온도:")
    for row in r["max"]:
        print("  " + "  ".join(f"{x:6.1f}" for x in row))


if __name__ == "__main__":
    main()
