"""SimScale 바닥 온도 사진 → 판(칩)만 네모 반듯하게 펴기 + 그 사진의 색상바 아래 붙이기.
  square_photo(n) → PIL.Image
판 찾기: 색이 진한 곳(채도 높음) 또는 아주 어두운 곳(격자선)을 묶어 가장 큰 덩어리 = 판, 꼭짓점 4개 = x+y, x−y 극값 → 원근 변환.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]


def _mask(a):
    a = a.astype(float) / 255; mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / (mx + 1e-6)
    return (sat > .28) | (mx < .3)


def square_photo(n, size=600, bar=True):
    im = Image.open(ROOT / f"images/{n}.png").convert("RGB"); a = np.array(im)
    m = ndi.binary_opening(_mask(a), iterations=2)
    lab, k = ndi.label(m); sizes = ndi.sum(m, lab, range(1, k + 1)); order = np.argsort(sizes)[::-1] + 1
    plate = ndi.binary_fill_holes(lab == order[0])
    ys, xs = np.nonzero(plate)
    s, d = xs + ys, xs - ys
    tl = (xs[s.argmin()], ys[s.argmin()]); br = (xs[s.argmax()], ys[s.argmax()])
    tr = (xs[d.argmax()], ys[d.argmax()]); bl = (xs[d.argmin()], ys[d.argmin()])
    quad = (*tl, *bl, *br, *tr)            # PIL QUAD: 왼위, 왼아래, 오른아래, 오른위
    sq = im.transform((size, size), Image.QUAD, quad, resample=Image.BICUBIC)
    if not bar:
        return sq
    # 색상바: 판 아래쪽에서 가로로 긴 덩어리
    cb = None
    a2 = a.astype(float) / 255; sat = (a2.max(2) - a2.min(2)) / (a2.max(2) + 1e-6)
    m2 = (sat > .45) & (a2.max(2) > .15); m2[:max(bl[1], br[1]) + 3] = False      # 색만 (검은 작업표시줄 빼려고), 판 아래쪽만
    lab2, k2 = ndi.label(m2); sz2 = ndi.sum(m2, lab2, range(1, k2 + 1))
    for j in (np.argsort(sz2)[::-1] + 1)[:8]:
        yy, xx = np.nonzero(lab2 == j)
        w, h = xx.max() - xx.min(), yy.max() - yy.min()
        if w > 5 * max(h, 1) and w > 150 and h > 4:
            cb = (xx.min(), yy.min(), xx.max(), yy.max()); break
    if cb is None:
        return sq
    x0, y0, x1, y1 = cb
    strip = im.crop((max(x0 - 45, 0), max(y0 - 32, 0), min(x1 + 90, im.width), min(y1 + 4, im.height)))
    strip = strip.resize((size, int(strip.height * size / strip.width)))
    out = Image.new("RGB", (size, size + strip.height + 6), "white"); out.paste(sq, (0, 0)); out.paste(strip, (0, size + 6))
    return out


if __name__ == "__main__":
    import sys
    for n in sys.argv[1:]:
        square_photo(int(n)).save(f"/tmp/sq_{n}.png")
