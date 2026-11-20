"""다음 핫스팟 목록 그림 (형상별 입출구 포트와 같이) → out/plan/hotspot_plan.png
  python ml/plan_figure.py
"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
for f in font_manager.findSystemFonts():
    if "wqy-zenhei" in f:
        font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
LIST = [("2_1+2_2", "가로 붙음"), ("3_2+4_2", "세로 붙음"), ("2_3+3_4", "대각선"), ("1_1+3_1", "떨어짐"),
        ("1_3+1_4", "가로 붙음"), ("2_1+3_1", "세로 붙음"), ("3_3+4_4", "대각선"), ("1_2+4_3", "떨어짐")]
DES = ["M0", "M1", "M4"]
meta = json.loads((ROOT / "data/design_meta.json").read_text(encoding="utf-8"))
th = pd.read_csv(ROOT / "data/ml/thermal.csv")
fig, axs = plt.subplots(len(DES), len(LIST), figsize=(2.3 * len(LIST), 3.2 * len(DES)), gridspec_kw=dict(hspace=0.45))
for i, d in enumerate(DES):
    for j, (h, kind) in enumerate(LIST):
        ax = axs[i, j]; done = ((th.design == d) & (th.hotspot == h)).any()
        for r in range(1, 5):
            for c in range(1, 5):
                hot = f"{r}_{c}" in h.split("+")
                ax.add_patch(plt.Rectangle(((c-1)*3, (r-1)*3), 3, 3, fc=("#bbbbbb" if done else "#e8443a") if hot else "white", ec="black", lw=0.8))
                ax.text((c-0.5)*3, (r-0.5)*3, f"{r}_{c}", ha="center", va="center", fontsize=6.5, color="white" if hot else "#999999")
        for p in meta[d]["inlets"]:
            ax.add_patch(plt.Circle(p, 0.75, fc="#f5c400", ec="black", lw=0.8, zorder=5))
        for p in meta[d]["outlets"]:
            ax.add_patch(plt.Circle(p, 0.75, fc="#1f5fff", ec="black", lw=0.8, zorder=5))
        ax.set_xlim(-0.3, 12.3); ax.set_ylim(-0.3, 12.3); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); [s.set_visible(False) for s in ax.spines.values()]
        ax.set_title(f"#{j+1} {h}\n{kind}" + ("  (완료)" if done else ""), fontsize=9, color="#888888" if done else "black")
        if j == 0:
            ax.set_ylabel(d, fontsize=14, rotation=0, labelpad=22, va="center")
fig.suptitle("다음 핫스팟 목록 (빨강 = 300 W/cm² 두 칸, 회색 = 이미 돌림)   노랑 원 = 입구, 파랑 원 = 출구\n"
             "위에서 본 모습: x → 오른쪽, y → 위, 칸 이름 = 행_열 (1행 = 아래, 1열 = 왼쪽). SimScale 윗면 압력 화면의 포트 위치와 맞춰서 보세요.", fontsize=10)
fig.subplots_adjust(left=0.04, right=0.99, top=0.86, bottom=0.02, wspace=0.12)
out = ROOT / "out/plan/hotspot_plan.png"; fig.savefig(out, dpi=130); print(out)
