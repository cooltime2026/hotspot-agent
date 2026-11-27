"""채널층 온도 단면(Z 0.0003, Temperature) 사진 → 채널 22개 물 온도 + 사이 벽(핀) 온도.

  python flowdigit/chantemp.py <사진번호> <색상바최댓값> [--tmin 20] [--y0 1.5 --y1 10.5]

- 이 그림은 물(채널)과 금속 벽(핀)이 둘 다 색으로 보여서, 판 네 모서리로 원근 보정한 뒤
  형상 좌표로 위치를 정해서 읽는다: 채널 중심 x = 0.75 + 0.5·j, 핀 중심 = 채널 중심 + 0.25 (mm).
- 화면 방향: 화면 위 = y 0, 화면 왼쪽 = x 0 (바닥 온도 그림과 같은 규칙, 사진 570 축 표시 근거).
- 자기 점검: 같은 높이에서 물이 벽보다 차가워야 정상(위치가 맞는지 확인). '물<벽 비율'로 출력.
- 정확도: 색 띠 1개 = (최대−20)/20 ℃ (예: 162.5 ℃면 7 ℃). 채널 폭 0.25 mm = 사진에서 약 10~12 px.
"""
from __future__ import annotations
import argparse, os, sys, warnings
warnings.filterwarnings('ignore')
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from digitize import find_colorbars, lut_from_bar   # noqa: E402
from tempmap import homography                      # noqa: E402

CH_X = 0.75 + 0.5 * np.arange(22)


def read(path, tmax, tmin=20.0, y0=1.5, y1=10.5, dy=0.1):
    im = np.array(Image.open(path).convert("RGB")).astype(float); H, W, _ = im.shape
    bar = max(find_colorbars(im, min_rows=1), key=lambda b: b[0]); lut = lut_from_bar(im, bar)
    bands, i0 = [], 0
    for i in range(1, len(lut) + 1):
        if i == len(lut) or np.abs(lut[i] - lut[i0]).max() > 12:
            if i - i0 >= 3:
                bands.append((lut[i0:i].mean(0), ((i0 + i) / 2) / len(lut)))
            i0 = i
    bc = np.array([b[0] for b in bands]); bval = tmin + np.array([b[1] for b in bands]) * (tmax - tmin)
    from scipy import ndimage
    sat = im.max(2) - im.min(2)
    col = (sat > 25) | (im.max(2) < 60)
    col[bar[4] - 60:, :] = False
    lab, n = ndimage.label(col)
    big = np.argmax(ndimage.sum(col, lab, range(1, n + 1))) + 1
    plate = ndimage.binary_fill_holes(lab == big)
    ys, xs = np.nonzero(plate); s, d = xs + ys, xs - ys
    TL = (xs[s.argmin()], ys[s.argmin()]); BR = (xs[s.argmax()], ys[s.argmax()])
    TR = (xs[d.argmax()], ys[d.argmax()]); BL = (xs[d.argmin()], ys[d.argmin()])
    Hm = homography([(0, 0), (12, 0), (12, 12), (0, 12)], [TL, TR, BR, BL])   # mm → 화면

    def T_at(x, y):
        p = Hm @ np.array([x, y, 1.0]); u, v = int(round(p[0] / p[2])), int(round(p[1] / p[2]))
        if not (0 <= u < W and 0 <= v < H):
            return np.nan
        c = im[v, u]
        if c.max() < 25:
            return np.nan
        return bval[np.abs(bc - c).sum(1).argmin()]

    ygrid = np.arange(y0 + dy / 2, y1, dy)
    off = np.array([-0.05, 0.0, 0.05])                     # 채널 폭 0.25 중 가운데 0.1 mm만
    # 모서리 검출 오차(안내 상자·알림 창이 판을 가리는 경우) 보정: x 방향 이동·배율을 찾아
    # '물 − 옆 벽' 온도 차가 가장 크게(물이 가장 차갑게) 되는 위치로 맞춤
    yt = np.linspace(y0 + 0.5, y1 - 0.5, 12)
    def contrast(sc, dx):
        X = 6 + (CH_X - 6) * sc + dx
        f = np.array([[T_at(x, y) for y in yt] for x in X]); w = np.array([[T_at(x + 0.25 * sc, y) for y in yt] for x in X[:-1]])
        return np.nanmean(w - (f[:-1] + f[1:]) / 2)
    best = max(((contrast(sc, dx), sc, dx) for sc in (0.98, 0.99, 1.0, 1.01, 1.02)
                for dx in np.arange(-0.25, 0.26, 0.05)), key=lambda t: t[0] if np.isfinite(t[0]) else -1e9)
    _, sc, dx = best
    Xc = 6 + (CH_X - 6) * sc + dx
    fluid = np.array([[np.nanmean([T_at(x + o, y) for o in off]) for y in ygrid] for x in Xc])
    fin = np.array([[np.nanmean([T_at(x + 0.25 * sc + o, y) for o in off]) for y in ygrid] for x in Xc[:-1]])
    px_per_mm = np.hypot(TR[0] - TL[0], TR[1] - TL[1]) / 12
    return dict(shift=(sc, dx), y=ygrid, fluid=fluid, fin=fin, band=(tmax - tmin) / len(bands), n_bands=len(bands), px_per_mm=px_per_mm)


def summary(r):
    F, P = r["fluid"], r["fin"]
    nb = np.nanmean((F[:-1] + F[1:]) / 2 < P + 1e-9)       # 양옆 물 평균 < 사이 벽 이면 정상
    core = (r["y"] > 2.5) & (r["y"] < 9.5)
    inv = np.nanmean((((F[:-1] + F[1:]) / 2) > P + 0.5 * r["band"])[:, core])   # 물이 벽보다 분명히 뜨거움 = 위치 틀림
    return dict(fluid_max_C=float(np.nanmax(F)), fluid_mean_C=float(np.nanmean(F)), fin_max_C=float(np.nanmax(P)),
                fluid_below_fin_ratio=float(nb), inversion_ratio=float(inv), band_C=r["band"], px_per_mm=r["px_per_mm"],
                hottest_channel=int(np.nanargmax(np.nanmax(F, 1))), hottest_y_mm=float(r["y"][np.nanargmax(np.nanmax(F, 0))]))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("img", type=int); ap.add_argument("tmax", type=float)
    ap.add_argument("--tmin", type=float, default=20.0)
    ap.add_argument("--y0", type=float, default=1.5); ap.add_argument("--y1", type=float, default=10.5)
    a = ap.parse_args()
    r = read(os.path.join(HERE, "..", "images", f"{a.img}.png"), a.tmax, a.tmin, a.y0, a.y1)
    s = summary(r)
    print(f"위치 보정: 배율 {r['shift'][0]:.2f}, x 이동 {r['shift'][1]:+.2f} mm")
    print(f"색 띠 {r['n_bands']}개 (1띠 ≈ {s['band_C']:.1f} ℃), 1 mm ≈ {s['px_per_mm']:.0f} px")
    print("채널별 물 평균 [℃]:", " ".join(f"{x:.0f}" for x in np.nanmean(r['fluid'], 1)))
    print("채널별 물 최고 [℃]:", " ".join(f"{x:.0f}" for x in np.nanmax(r['fluid'], 1)))
    print(f"물 최고 {s['fluid_max_C']:.1f} ℃ (채널 {s['hottest_channel']}, y≈{s['hottest_y_mm']:.1f}), 벽 최고 {s['fin_max_C']:.1f} ℃")
    print(f"자기 점검: 물이 옆 벽보다 차가운 비율 {s['fluid_below_fin_ratio']*100:.0f}%, 역전(물이 벽보다 반 띠 이상 뜨거움) {s['inversion_ratio']*100:.1f}% (2% 넘으면 위치 의심)")
    out = os.path.join(HERE, "..", "data", f"chantemp_{a.img}.csv")
    with open(out, "w") as f:
        f.write("y_mm," + ",".join(f"ch{j}" for j in range(22)) + "\n")
        for k, y in enumerate(r["y"]):
            f.write(f"{y:.2f}," + ",".join("" if np.isnan(v) else f"{v:.1f}" for v in r["fluid"][:, k]) + "\n")
    print("저장:", os.path.relpath(out))


if __name__ == "__main__":
    main()
