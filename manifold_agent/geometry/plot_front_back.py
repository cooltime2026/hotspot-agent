"""실행마다 두 그림: 왼쪽 = 앞면(윗면, 위에서 내려다봄)의 입구·출구 / 오른쪽 = 뒷면(바닥, 아래에서 올려다봄)의 핫스팟 칸.
  python geometry/plot_front_back.py
앞면: x 오른쪽, y 위쪽으로 커짐.  뒷면: x 오른쪽, y 아래쪽으로 커짐(위아래 뒤집힘).
"""
import json, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
matplotlib.rcParams["font.family"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
import sys
RUNS = [("S4", "1_3,1_4", "S4.step"), ("S5", "2_1,2_2", "S5.step"), ("S6", "3_3,3_4", "S6.step"), ("S7", "2_2,3_2", "S6.step (S6과 같은 모양)")]
if len(sys.argv) > 1:   # 예: S8:2_1,2_2 S9:3_3,3_4
    RUNS = [(a.split(":")[0], a.split(":")[1], a.split(":")[0] + ".step") for a in sys.argv[1:]]
fig, axs = plt.subplots(len(RUNS), 2, figsize=(13, 6.5 * len(RUNS)))
import numpy as _np
axs = _np.atleast_2d(axs)
for row, (k, hs, stp) in enumerate(RUNS):
    m = json.load(open(f"out/step_v17/{k}_mask.json")); HOT = [tuple(map(int, c.split("_"))) for c in hs.split(",")]
    a, b = axs[row]
    # 앞면: 입구·출구
    a.add_patch(Rectangle((0, 0), 12, 12, fc="#eef0f3", ec="k", lw=1.5))
    for (x, y) in m["pin"]:
        a.add_patch(Circle((x, y), .5, fc="white", ec="#1f4fd8", lw=3))
        a.text(x + .75, y, f"입구 ({x:.2f}, {y:.2f})\n0.912 m/s", va="center", fontsize=12, color="#1f4fd8", weight="bold")
    for (x, y) in m["pout"]:
        a.add_patch(Circle((x, y), .5, fc="gold", ec="#c0301a", lw=3))
        a.text(x - .75, y, f"출구 ({x:.2f}, {y:.2f})\n0 Pa", va="center", ha="right", fontsize=12, color="#c0301a", weight="bold")
    a.set_xlim(0, 12); a.set_ylim(0, 12); a.set_xlabel("x [mm] →"); a.set_ylabel("y [mm] ↑")
    a.set_title(f"{k} — 앞면(윗면): 입구·출구\n위에서 내려다봄 · STEP {stp}", fontsize=14, weight="bold")
    # 뒷면: 핫스팟
    for r in range(1, 5):
        for c in range(1, 5):
            hot = (r, c) in HOT
            b.add_patch(Rectangle(((c-1)*3, (r-1)*3), 3, 3, fc="#e8452c" if hot else "#fde9b0", ec="k", lw=1.3))
            b.text((c-.5)*3, (r-.5)*3, f"{r}_{c}\n{'300' if hot else '50'} W/cm²", ha="center", va="center",
                   fontsize=14 if hot else 10, weight="bold" if hot else "normal", color="white" if hot else "#777")
    b.set_xlim(0, 12); b.set_ylim(12, 0); b.set_xlabel("x [mm] →"); b.set_ylabel("y [mm] ↓")
    b.set_title(f"{k} — 뒷면(바닥): 핫스팟 {hs.replace(',', ' + ')}\n아래에서 올려다봄 (위아래 뒤집힘)", fontsize=14, weight="bold")
    for ax in (a, b):
        ax.set_aspect("equal"); ax.set_xticks(range(0, 13, 3)); ax.set_yticks(range(0, 13, 3))
fig.suptitle(f"{RUNS[0][0]} ~ {RUNS[-1][0]}: 왼쪽 = 앞면 입구·출구, 오른쪽 = 뒷면 핫스팟\n(SimScale 좌표축 x 빨강·y 초록으로 방향 확인)", fontsize=16, weight="bold")
fig.tight_layout(rect=(0, 0, 1, .95 if len(RUNS) < 4 else .97)); fig.savefig(f"out/step_v17/batch_{RUNS[0][0]}-{RUNS[-1][0]}_front_back.png", dpi=90)
print("저장")
