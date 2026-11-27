"""SimScale 에서 바닥면(아래)을 볼 때와 같은 방향으로 핫스팟 칸·포트 위치 그림.
  아래에서 올려다보면: x 는 오른쪽으로 커지고, y 는 아래쪽으로 커짐 (위에서 본 그림을 위아래로 뒤집은 것).
  python geometry/plot_bottom_view.py
"""
import json, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrow
matplotlib.rcParams["font.family"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
RUNS = [("S4", "1_3,1_4", "S4.step"), ("S5", "2_1,2_2", "S5.step"), ("S6", "3_3,3_4", "S6.step"), ("S7", "2_2,3_2", "S6.step (S6과 같은 모양)")]
fig, axs = plt.subplots(1, 4, figsize=(24, 8.2))
for ax, (k, hs, stp) in zip(axs, RUNS):
    m = json.load(open(f"out/step_v17/{k}_mask.json")); HOT = [tuple(map(int, c.split("_"))) for c in hs.split(",")]
    for r in range(1, 5):
        for c in range(1, 5):
            hot = (r, c) in HOT
            ax.add_patch(Rectangle(((c-1)*3, (r-1)*3), 3, 3, fc="#e8452c" if hot else "#fde9b0", ec="k", lw=1.3))
            ax.text((c-.5)*3, (r-.5)*3, f"{r}_{c}\n{'300' if hot else '50'} W/cm²", ha="center", va="center",
                    fontsize=13 if hot else 9, weight="bold" if hot else "normal", color="white" if hot else "#777")
    for (x, y) in m["pin"]:
        ax.add_patch(Circle((x, y), .45, fill=False, ec="#1f4fd8", lw=2, ls="--")); ax.text(x, y, "입", ha="center", va="center", fontsize=9, color="#1f4fd8", weight="bold")
    for (x, y) in m["pout"]:
        ax.add_patch(Circle((x, y), .45, fill=False, ec="#c0301a", lw=2, ls="--")); ax.text(x, y, "출", ha="center", va="center", fontsize=9, color="#c0301a", weight="bold")
    ax.set_xlim(0, 12); ax.set_ylim(12, 0)          # ← 아래에서 본 방향: y 가 아래로 커짐
    ax.set_aspect("equal"); ax.set_xticks(range(0, 13, 3)); ax.set_yticks(range(0, 13, 3))
    ax.set_xlabel("x [mm] →", fontsize=11); ax.set_ylabel("↓ y [mm]", fontsize=11)
    ax.set_title(f"{k}  ·  핫스팟 {hs.replace(',', ' + ')}\nSTEP: {stp}", fontsize=13, weight="bold")
fig.suptitle("바닥면(아래)에서 본 방향 — x 는 오른쪽, y 는 아래쪽으로 커짐.  빨간 칸 = 핫스팟 300 W/cm², 나머지 50 W/cm².  점선 원 = 윗면 포트 위치(참고)", fontsize=14, weight="bold")
fig.text(.5, .02, "방향 맞추기: SimScale 화면 구석의 좌표축(x 빨강, y 초록)을 보고 x·y 방향을 이 그림과 맞추세요. 화면에 따라 90° 돌아가 보일 수 있습니다.", ha="center", fontsize=12)
fig.tight_layout(rect=(0, .05, 1, .93)); fig.savefig("out/step_v17/batch_S4-S7_bottom.png", dpi=100)
print("저장 out/step_v17/batch_S4-S7_bottom.png")
