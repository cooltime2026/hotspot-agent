"""v17 자동 모양 SimScale 설정 그림: 바닥 핫스팟 칸 + 관통층·덮개 홈 + 입구/출구 좌표.
  python geometry/plot_v17_setup.py out/step_v17/S2_mask.json S2 2_2,3_2
"""
import json, sys
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
matplotlib.rcParams["font.family"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
src, name, hs = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
m = json.load(open(src)); HOT = [tuple(map(int, c.split("_"))) for c in hs]
cav = np.array(m["cav"]).reshape(240, 240); gro = np.array(m["gro"]).reshape(240, 240)
fig, axs = plt.subplots(1, 3, figsize=(18, 7))
ax = axs[0]
for r in range(1, 5):
    for c in range(1, 5):
        hot = (r, c) in HOT
        ax.add_patch(Rectangle(((c-1)*3, (r-1)*3), 3, 3, fc="#e8452c" if hot else "#fde9b0", ec="k", lw=1.2))
        ax.text((c-.5)*3, (r-.5)*3+.4, f"{r}_{c}", ha="center", va="center", fontsize=14 if hot else 11, weight="bold", color="white" if hot else "#555")
        ax.text((c-.5)*3, (r-.5)*3-.4, "300 W/cm²" if hot else "50", ha="center", va="center", fontsize=10 if hot else 8, color="white" if hot else "#888")
ax.set_title(f"① 바닥면: 핫스팟 {' + '.join(hs)} = 300 W/cm²\n나머지 = 50 W/cm²", fontsize=12)
for a, A, t in [(axs[1], cav, "② 관통층 (z 0.5~1.0)"), (axs[2], gro, "③ 덮개 홈층 (z 1.0~1.35) + 포트")]:
    img = np.ones((240, 240, 3))*.95; img[A == 1] = (.25, .45, .85); img[A == 2] = (.85, .3, .25)
    a.imshow(img, origin="lower", extent=[0, 12, 0, 12])
    for (r, c) in HOT: a.add_patch(Rectangle(((c-1)*3, (r-1)*3), 3, 3, fill=False, ec="orange", lw=2.5))
    for k in range(5): a.axhline(3*k, c="k", lw=.3); a.axvline(3*k, c="k", lw=.3)
    a.set_title(t + "\n파랑 = 입구 쪽 유로, 빨강 = 출구 쪽 유로, 주황 = 핫스팟", fontsize=11)
for (x, y) in m["pin"]:
    for a in axs[1:]: a.add_patch(Circle((x, y), .4, fc="white", ec="#1f4fd8", lw=2.5))
    axs[2].text(x+.55, y+.15, f"입구 ({x:g}, {y:g})\n0.912 m/s", fontsize=10, color="#1f4fd8", weight="bold")
for (x, y) in m["pout"]:
    for a in axs[1:]: a.add_patch(Circle((x, y), .4, fc="gold", ec="#c0301a", lw=2.5))
    axs[2].text(x+.55, y-.75, f"출구 ({x:g}, {y:g})\n0 Pa", fontsize=10, color="#c0301a", weight="bold")
for a in axs:
    a.set_xlim(0, 12); a.set_ylim(0, 12); a.set_aspect("equal"); a.set_xticks(range(0, 13, 3)); a.set_yticks(range(0, 13, 3)); a.set_xlabel("x [mm]"); a.set_ylabel("y [mm]")
fig.suptitle(f"{name}: {m.get('base','')} — 위에서 내려다본 방향, 입구 2개 각 0.912 m/s (합 55 mL/min)", fontsize=13, weight="bold")
fig.tight_layout(rect=(0, 0, 1, .95)); fig.savefig(f"out/step_v17/{name}_setup.png", dpi=110)
print("저장", f"out/step_v17/{name}_setup.png")
