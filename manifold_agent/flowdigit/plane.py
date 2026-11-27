"""채널층 수평 단면(z = 채널 높이 가운데) Velocity Magnitude 사진 → 채널 22개 유량(y 위치별).

사용: python flowdigit/plane.py <사진 번호> --vmax 0.7403 --design D1 --v 0.497 [--x-left] [--y-down]
  --x-left : 화면 왼쪽이 +x (SimScale 축 표시 x 빨간 화살표가 왼쪽)  → 왼쪽 첫 채널 = 21번
  --y-down : 화면 아래가 +y

방법
 1) 속도 색상바 → 20띠 hue 표 (digitize.py와 같은 방식)
 2) 채널 = 세로로 긴 색 덩어리 22개 (판 테두리 주황 고리는 폭이 커서 제외)
 3) 덩어리마다 중심선(x = a + b·y 직선)을 맞추고, 길이 방향을 채널 y 범위(형상별)로 대응
 4) y 0.1 mm 칸마다 폭 방향 평균 속도(가운데 높이) → 단면 평균 = K × 그 값 (직사각 층류 해석해)
    → 채널 유량 = 단면 평균 × 폭 0.25 × 높이 0.4 mm
"""
from __future__ import annotations
import argparse, csv, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from digitize import find_colorbars, lut_from_bar, components  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W_CH, H_CH, N_CH = 0.25e-3, 0.4e-3, 22
Y_RANGE = {"D": (0.6, 11.4), "M": (1.5, 10.5)}   # 채널 y 범위 [mm] (M0·M계열 채널 1.5~10.5, D계열 0.6~11.4)


def duct_K(w=0.25, h=0.4, nterm=60, n=401):
    """직사각 채널 완전발달 층류: 단면 평균 / (높이 가운데에서 폭 방향 평균) — 급수 해석해"""
    x = np.linspace(-w / 2, w / 2, n); z = np.linspace(0, h, n)
    X, Z = np.meshgrid(x, z)
    u = np.zeros_like(X)
    for k in range(nterm):
        m = 2 * k + 1; a = m * np.pi / h
        u += (1 / m ** 3) * (1 - np.cosh(a * X) / np.cosh(a * w / 2)) * np.sin(a * Z)
    return u.mean() / u[n // 2].mean()


def hue(c):
    c = np.asarray(c, float); mx = c.max(-1); mn = c.min(-1); d = np.maximum(mx - mn, 1e-6)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return np.where(h > 300, h - 360, h), (mx - mn) / np.maximum(mx, 1e-6)


def read_plane(path, vmax, design="D1", x_left=False, y_down=False):
    im = np.array(Image.open(path).convert("RGB")).astype(float)
    bars = [b for b in find_colorbars(im) if b[3] == "rainbow"]
    if not bars:
        raise RuntimeError("속도 색상바를 못 찾음")
    vbar = bars[-1]
    vl = lut_from_bar(im, vbar)
    hb, _ = hue(vl)
    frac = (np.arange(len(vl)) + 0.5) / len(vl)
    hq = np.round(hb).astype(int); bands = []; i0 = 0
    for i in range(1, len(hq) + 1):
        if i == len(hq) or abs(hq[i] - hq[i0]) > 2:
            if i - i0 >= 3:
                bands.append((hb[i0:i].mean(), frac[i0:i].mean()))
            i0 = i
    bh = np.array([b[0] for b in bands]); bf = np.array([b[1] for b in bands])
    hp, sp = hue(im)
    val = bf[np.abs(hp[..., None] - bh[None, None, :]).argmin(-1)] * vmax
    col = (sp > 0.45) & ((im.max(2) - im.min(2)) > 50)
    col[int(vbar[4]) - 40:, :] = False                       # 색상바 아래쪽 제외
    comps = components(col, min_n=200, max_n=10 ** 7)
    strips = []
    for p in comps:
        h = np.ptp(p[:, 0]) + 1; w = np.ptp(p[:, 1]) + 1
        if h > 300 and w < 0.2 * h:                       # 세로로 긴 덩어리 (기울어짐 포함)
            strips.append(p)
    if len(strips) != N_CH:
        raise RuntimeError(f"채널 {len(strips)}개 검출 (22개여야 함)")
    strips.sort(key=lambda p: p[:, 1].mean())
    y0, y1 = Y_RANGE[design[0]]
    ys = np.round(np.arange(y0, y1 + 1e-9, 0.1), 1)
    K = duct_K()
    out = []
    for k, p in enumerate(strips):
        j = N_CH - 1 - k if x_left else k
        r, c = p[:, 0].astype(float), p[:, 1].astype(float)
        b, a = np.polyfit(r, c, 1)                        # c = a + b·r (중심선)
        r_top, r_bot = r.min(), r.max()
        # 화면 위→아래 = y 큰→작은 (기본, y 위쪽) / --y-down 이면 반대
        t = (r - r_top) / (r_bot - r_top)                 # 0(위)~1(아래)
        ymm = y0 + t * (y1 - y0) if y_down else y1 - t * (y1 - y0)
        v = val[p[:, 0], p[:, 1]]
        # 폭 방향 가장자리 1px 제외(벽 섞인 색)
        off = c - (a + b * r)
        halfw = np.percentile(np.abs(off), 95)
        keep = np.abs(off) <= halfw - 1
        prof = []
        for yy in ys:
            m = keep & (np.abs(ymm - yy) <= 0.05)
            prof.append(v[m].mean() if m.sum() >= 3 else np.nan)
        prof = np.array(prof)
        q = prof * K * W_CH * H_CH * 6e7                  # m³/s → mL/min
        out.append(dict(ch=j, x_mm=0.75 + 0.5 * j, ys=ys, v_mid=prof, q=q,
                        width_px=2 * halfw, length_px=r_bot - r_top))
    out.sort(key=lambda d: d["ch"])
    return out, dict(K=K, n_bands=len(bands), vmax=vmax)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("img", type=int); ap.add_argument("--vmax", type=float, required=True)
    ap.add_argument("--design", default="D1"); ap.add_argument("--v", type=float, required=True)
    ap.add_argument("--x-left", action="store_true"); ap.add_argument("--y-down", action="store_true")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    res, info = read_plane(os.path.join(ROOT, "images", f"{a.img}.png"), a.vmax, a.design, a.x_left, a.y_down)
    print(f"  K = {info['K']:.4f} (단면평균/가운데높이 폭평균), 색상 띠 {info['n_bands']}개")
    ys = res[0]["ys"]
    for yy in (2.0, 4.0, 6.0, 8.0, 10.0):
        i = int(np.argmin(np.abs(ys - yy)))
        print(f"  y={yy:4.1f}: " + " ".join(f"{d['q'][i]:.2f}" for d in res))
    if a.save:
        dst = os.path.join(ROOT, "data", f"{a.design}_plane_z03_img{a.img}.csv")
        with open(dst, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["design", "inlet_v_mps", "img", "channel", "x_mm"] + [f"y{y:.1f}" for y in ys])
            for d in res:
                w.writerow([a.design, a.v, a.img, d["ch"], d["x_mm"]] + [f"{x:.4f}" for x in d["q"]])
        print("  저장:", dst)
    return res


if __name__ == "__main__":
    main()
