"""C1~C4 핫스팟 위치 그림 — 바닥에서 본 모습(SimScale BOTTOM: x→오른쪽, y→아래).  python geometry/plot_round3_hotspots.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle, Circle
from geometry import param_manifold as PM
for f in font_manager.findSystemFonts():
    if "wqy" in f.lower() or "nanum" in f.lower() or "noto" in f.lower() and "cjk" in f.lower():
        font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name(); break
R = json.loads(Path("out/step_param_v3/round3.json").read_text())
NAME = {"1_3+1_4": "③ 맨 위 줄, 오른쪽 두 칸", "2_2+3_2": "④ 왼쪽에서 두 번째 열, 가운데 두 칸(세로)",
        "3_3+3_4": "② 세 번째 줄, 오른쪽 두 칸", "2_1+2_2": "① 두 번째 줄, 왼쪽 두 칸"}
fig, axs = plt.subplots(1, 4, figsize=(22, 6.6))
for ax, (k, p) in zip(axs, R.items()):
    hs = p["aimed_hotspot"]; q = {kk: v for kk, v in p.items() if kk != "aimed_hotspot"}
    P = PM.masks(q)[0]                                   # P[iy, ix], y 위(위 시점)
    img = np.ones((*P.shape, 3)) * 0.93
    img[P == 1] = (0.45, 0.6, 0.9); img[P == 2] = (0.9, 0.45, 0.42)
    ax.imshow(img, extent=(0, 12, 0, 12), origin="lower")   # 축을 뒤집어 BOTTOM 시점(y 아래)
    ax.set_ylim(12, 0); ax.set_xlim(0, 12)
    for t in (3, 6, 9): ax.axhline(t, c="k", lw=1); ax.axvline(t, c="k", lw=1)
    for r in range(1, 5):
        for c in range(1, 5):
            ax.text(3 * c - 1.5, 3 * r - 1.5, f"{r}_{c}", ha="center", va="center", fontsize=11, color="0.25")
    for cell in hs.split("+"):
        r, c = map(int, cell.split("_"))
        ax.add_patch(Rectangle((3 * c - 3, 3 * r - 3), 3, 3, fc=(1, 0, 0, 0.35), ec="red", lw=3))
    for (x, y), lab, col in [((3, 1), "출구", "white"), ((3, 11), "출구", "white"), ((9, 1), "입구", "gold"), ((9, 11), "입구", "gold")]:
        ax.add_patch(Circle((x, y), 0.55, fc=col, ec="k", lw=1.5)); ax.text(x + (-1.3 if lab == "출구" else 1.3), y, lab, ha="center", va="center", fontsize=10)
    ax.set_xticks([]); ax.set_yticks([]); ax.add_patch(Rectangle((0, 0), 12, 12, fill=False, ec="k", lw=1.5))
    ax.set_title(f"{k}  핫스팟 {hs}\n{NAME[hs]}\n띠 {q['n']}개를 이 줄에 모음 (yf {q['yf']})", fontsize=12)
fig.suptitle("C1~C4 핫스팟 위치 — 바닥에서 본 모습 (SimScale BOTTOM: x→오른쪽, y→아래)\n빨간 칸 = 300 W/cm², 나머지 50 W/cm²   입구(노랑) 오른쪽, 출구(흰색) 왼쪽 = A·B와 같음", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.86]); fig.savefig("out/step_param_v3/C_hotspots_bottom.png", dpi=100); print("saved")
