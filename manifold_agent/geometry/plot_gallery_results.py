"""매니폴드마다 [모양 | 바닥 온도 사진 | 유량 분포 사진] (SimScale 캡처, 0.912 m/s 에서 가장 좋았던 Run).
  python geometry/plot_gallery_results.py   → out/gallery_results_1.png …
유량 분포 = 채널층 온도 사진(찬 줄 = 물이 흐르는 채널). D0·D1·M0 은 유속 단면 사진.
"""
import csv, json, sys
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "geometry/plot_gallery.py").read_text(encoding="utf-8")
g = {"__file__": str(ROOT / "geometry/plot_gallery.py"), "__name__": "g"}
exec(compile(src[:src.index("ncol = 8")], "g", "exec"), g)      # 모양 목록(items, 같은 모양 합침 포함)
items, C_P, C_U, C_CH, C_PORT = g["items"], g["C_P"], g["C_U"], g["C_CH"], g["C_PORT"]
matplotlib.rcParams["font.family"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]

runs = pd.read_csv(ROOT / "data/direct_runs.csv"); runs["hs"] = runs.heat.str.split("at ").str[1].str.replace(",", "+")
cells = pd.read_csv(ROOT / "data/ml/cell_temps.csv"); chan = pd.read_csv(ROOT / "data/ml/channel_temps.csv"); sec = pd.read_csv(ROOT / "data/section_catalog.csv")
near = lambda a, b: abs(a - b) < 1e-3

def pick(names):
    """같은 모양 여러 이름 중 0.912 에서 최고온도가 가장 낮고 바닥 사진이 있는 Run → (이름, 핫스팟, Tmax, 바닥 사진, 유량 사진, 유량 사진 종류)"""
    best = None
    for d in names.split(" = "):
        r = runs[(runs.design == d) & runs.inlet_velocity_m_s.apply(lambda v: near(v, .912))]
        for _, x in r.sort_values("Tmax_bottom_C").iterrows():
            b = cells[(cells.design == d) & (cells.hotspot == x.hs) & cells.inlet_v_mps.apply(lambda v: near(v, .912))]
            if best is None or (len(b) and (best[3] is None or x.Tmax_bottom_C < best[2])):
                best = (d, x.hs, x.Tmax_bottom_C, int(b.img.iloc[0]) if len(b) else None)
            if len(b): break
    if best is None: return None
    d, hs = best[0], best[1]
    f, kind = None, ""
    order = [d] + [n for n in names.split(" = ") if n != d]
    cand = []   # (우선순위, 사진, 설명)
    for i, dd in enumerate(order):
        for _, c in chan[chan.design == dd].iterrows():
            pr = (i, 0 if c.hotspot == hs else 1, 0 if near(c.inlet_v_mps, .912) else 1)
            cand.append((pr, int(c.img), "채널층 온도 (찬 줄 = 물 흐름)", dd, c.hotspot, c.inlet_v_mps))
    if not cand:
        for _, c in sec[sec.design == d].iterrows():
            pr = (0, 0 if c.hotspot == hs else 1, 0 if near(c.inlet_v_mps, .912) else 1)
            cand.append((pr, int(c.img), "유속 단면 (채널별 흐름)", d, c.hotspot, c.inlet_v_mps))
    if cand:
        _, f, kind, dd, h2, v2 = min(cand, key=lambda x: x[0])
        if (dd, h2, round(v2, 3)) != (d, hs, .912):
            kind += f"\n({dd} · {h2} · {v2:g} m/s)"
    return (*best, f, kind)

def draw(ax, name, desc, P, U, ports, head):
    ax.add_patch(Rectangle((0, 0), 12, 12, fc="white", ec="#555", lw=1, zorder=0))
    y0, y1 = (1.5, 10.5) if head else (0.6, 11.4)
    for j in range(22): ax.add_patch(Rectangle((0.625 + 0.5 * j, y0), 0.25, y1 - y0, fc=C_CH, ec="none", zorder=1))
    if head:
        for a, b in [(0.5, 1.5), (10.5, 11.5)]: ax.add_patch(Rectangle((0.625, a), 10.75, b - a, fc=C_CH, ec="none", zorder=1))
    for A, col, z in [(U, C_U, 2), (P, C_P, 3)]:
        if A is None: continue
        A = np.asarray(A); img = np.zeros((*A.shape, 4)); img[A > 0] = (*matplotlib.colors.to_rgb(col), 1)
        ax.imshow(img, origin="lower", extent=[0, 12, 0, 12], interpolation="nearest", zorder=z)
    for (px, py) in ports: ax.add_patch(Circle((px, py), .45, fc="white", ec=C_PORT, lw=1.5, zorder=4))
    ax.set_xlim(-.3, 12.3); ax.set_ylim(-.3, 12.3); ax.set_aspect("equal"); ax.axis("off")

def photo(ax, n, title):
    ax.axis("off")
    if n is None:
        ax.text(.5, .5, "사진 파일 없음\n(그때 대화에 파일로 안 들어옴)", ha="center", va="center", fontsize=10, color="#999", transform=ax.transAxes); return
    p = ROOT / f"images/{n}.png"
    im = Image.open(p).convert("RGB"); ax.imshow(im); ax.set_title(f"{title} · 사진 {n}", fontsize=8.5, color="#333")

PER = 6                      # 한 장에 모양 6개 (줄 3 × 2 묶음)
pages = [items[i:i + PER] for i in range(0, len(items), PER)]
for pi, page in enumerate(pages, 1):
    fig, axs = plt.subplots(3, 6, figsize=(24, 13.5), gridspec_kw=dict(width_ratios=[1, 1.25, 1.25] * 2))
    for ax in axs.flat: ax.axis("off")
    for k, it in enumerate(page):
        name, desc = it[0], it[1]; r, c0 = k // 2, (k % 2) * 3
        draw(axs[r, c0], *it)
        info = pick(name)
        if info:
            d, hs, T, fb, ff, kind = info
            import textwrap; axs[r, c0].set_title("\n".join(textwrap.wrap(f"{name}  {desc}", 30)) + f"\n대표 Run: {d} · {hs} · 0.912 m/s · 최고 {T:.1f} ℃", fontsize=9, weight="bold")
            photo(axs[r, c0 + 1], fb, "바닥 온도"); photo(axs[r, c0 + 2], ff, kind or "유량 분포")
        else:
            axs[r, c0].set_title(f"{name}  {desc}", fontsize=9.5, weight="bold")
    fig.suptitle(f"매니폴드별 SimScale 결과 사진 ({pi}/{len(pages)})  —  왼쪽: 모양(보라 관통층·하늘색 덮개 홈·회색 채널·분홍 포트) | 가운데: 바닥 온도 | 오른쪽: 유량 분포",
                 fontsize=14, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, .96)); out = ROOT / f"out/gallery_results_{pi}.png"; fig.savefig(out, dpi=80); plt.close(fig)
    print("저장", out, [it[0] for it in page])
