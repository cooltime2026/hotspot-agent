"""위에서 본 수평 단면(채널층을 x-y로 자른 Velocity Magnitude 그림) → 채널 22개의 길이 방향 속도 분포.

  python flowdigit/planview.py <사진번호> <vmax> [--y0 1.5 --y1 10.5]
출력: 채널별 y 위치마다 속도(그 높이의 단면 속도, 채널 평균 유속과 비례), 채널별 평균, 균일값 대비 비율.

주의: 수평 단면 높이(z)의 속도라서 채널 단면 평균 유속과 크기는 다르다(비율만 사용).
채널 단면 사진(digitize.py)과 같은 위치(y=6)의 비율을 비교해 검증할 것.
"""
from __future__ import annotations
import argparse, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from digitize import find_colorbars, lut_from_bar   # noqa: E402


def hue(c):
    c = np.asarray(c, float); mx = c.max(-1); mn = c.min(-1); d = np.maximum(mx - mn, 1e-6)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return np.where(h > 300, h - 360, h)


def read(path, vmax, y0=1.5, y1=10.5, vmin=0.0):
    im = np.array(Image.open(path).convert("RGB")).astype(float)
    bars = [b for b in find_colorbars(im, min_rows=1) if b[3] == "rainbow"]
    if not bars:
        raise RuntimeError("속도 색상바 없음")
    bar = bars[-1]; lut = lut_from_bar(im, bar)
    hb = hue(lut); frac = (np.arange(len(lut)) + 0.5) / len(lut)
    bands, i0 = [], 0
    for i in range(1, len(hb) + 1):
        if i == len(hb) or abs(hb[i] - hb[i0]) > 2:
            if i - i0 >= 3:
                bands.append((hb[i0:i].mean(), frac[i0:i].mean()))
            i0 = i
    bh = np.array([b[0] for b in bands]); bf = np.array([b[1] for b in bands])
    hp = hue(im); sat = im.max(2) - im.min(2)
    val = vmin + bf[np.abs(hp[..., None] - bh[None, None, :]).argmin(-1)] * (vmax - vmin)
    fluid = (sat > 50) & (hp >= -10) & (hp <= 250)
    fluid[bar[4] - 40:, :] = False                          # 색상바 아래 제외
    # 판(유체 영역) 세로 범위: 채널이 있는 행 = 가로로 색 띠가 20개 이상 끊겨 나오는 행
    rows = []
    for y in range(fluid.shape[0]):
        r = fluid[y]; n = np.sum(r[1:] & ~r[:-1])
        if n >= 20:
            rows.append(y)
    rows = np.array(rows)
    ya, yb = rows.min(), rows.max()
    ypix = np.arange(ya, yb + 1)
    ymm = y0 + (ypix - ya) / max(yb - ya, 1) * (y1 - y0)      # 채널 구간 y0~y1 에 선형 대응(근사)
    prof = np.full((22, len(ypix)), np.nan)
    # 행마다 색 띠(채널)를 다시 찾음 → 화면이 조금 돌아가 있어도 채널을 따라감
    def runs_of(row):
        xs = np.nonzero(row)[0]
        if len(xs) == 0:
            return []
        out, s0 = [], xs[0]
        for a_, b_ in zip(xs[:-1], xs[1:]):
            if b_ != a_ + 1:
                out.append((s0, a_)); s0 = b_
        out.append((s0, xs[-1]))
        return out
    allw = [b - a + 1 for y in ypix[::5] for a, b in runs_of(fluid[y])]
    mw = np.median(allw); ok_rows = 0; cx = None
    for k, y in enumerate(ypix):
        rr = [(a, b) for a, b in runs_of(fluid[y]) if 0.75 * mw <= b - a + 1 <= 1.4 * mw]
        if len(rr) != 22:
            continue
        ok_rows += 1
        for j, (a, b) in enumerate(rr):
            c = (a + b) // 2; hw = max(1, int(0.25 * (b - a + 1)))
            m = fluid[y, c - hw:c + hw + 1]
            if m.any():
                prof[j, k] = val[y, c - hw:c + hw + 1][m].mean()
        if cx is None and k > len(ypix) // 2:
            cx = [(a + b) / 2 for a, b in rr]
    if ok_rows < 0.3 * len(ypix):
        raise RuntimeError(f"채널 22개가 보이는 행이 너무 적음 ({ok_rows}/{len(ypix)})")
    return dict(ymm=ymm, prof=prof, cx=cx, rows=(ya, yb), n_bands=len(bands))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("img", type=int); ap.add_argument("vmax", type=float)
    ap.add_argument("--vmin", type=float, default=0.0, help="색상바 최솟값 (압력 그림이면 음수 가능)")
    ap.add_argument("--y0", type=float, default=1.5); ap.add_argument("--y1", type=float, default=10.5)
    a = ap.parse_args()
    r = read(os.path.join(HERE, "..", "images", f"{a.img}.png"), a.vmax, a.y0, a.y1, a.vmin)
    P = r["prof"]; ym = r["ymm"]
    core = (ym > a.y0 + 1.0) & (ym < a.y1 - 1.0)              # 헤더 근처 1 mm 제외
    mean = np.nanmean(P[:, core], 1); s = mean / np.nanmean(mean)
    print(f"색상 띠 {r['n_bands']}개, 채널 행 {r['rows']}")
    print("채널 평균(헤더 근처 제외) / 균일값:", " ".join(f"{x:.2f}" for x in s))
    if a.vmin != 0:   # 압력 그림: 채널마다 양 끝(헤더 근처 1 mm 안쪽) 압력 차 = 채널 압력강하
        lo = (ym > a.y0 + 0.3) & (ym < a.y0 + 1.0); hi = (ym > a.y1 - 1.0) & (ym < a.y1 - 0.3)
        dp = np.nanmean(P[:, lo], 1) - np.nanmean(P[:, hi], 1)
        print("채널별 압력 차 (화면 위쪽 끝 − 아래쪽 끝, 양 끝 0.3~1 mm 안쪽 평균) [Pa]:", " ".join(f"{x:.0f}" for x in dp))
    i6 = np.argmin(np.abs(ym - 6.0)); s6 = P[:, i6] / np.nanmean(P[:, i6])
    print("y=6 행 / 균일값:            ", " ".join(f"{x:.2f}" for x in s6))
    out = os.path.join(HERE, "..", "data", f"planview_{a.img}.csv")
    with open(out, "w") as f:
        f.write("y_mm," + ",".join(f"ch{j}" for j in range(22)) + "\n")
        for k in range(0, len(ym)):
            f.write(f"{ym[k]:.3f}," + ",".join("" if np.isnan(v) else f"{v:.4f}" for v in P[:, k]) + "\n")
    print("저장:", os.path.relpath(out))


if __name__ == "__main__":
    main()
