"""포스터 '② SimScale 해석 데이터와 머신러닝 모델' 칸 그림 (우리 데이터)
  (a) 유량별 칩 최고 온도  (b) 유량별 압력 강하  — 핫스팟 2_1+2_2, 기본 형상 3종 5유량 + 자동 설계 V자 빗살형(S5)
  (c) SimScale 결과: 같은 핫스팟·55 mL/min 바닥 온도 사진 4장
  python geometry/poster_data_panel.py → out/poster_icons/data_panel.png/svg
"""
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
matplotlib.rcParams.update({"font.family": ["WenQuanYi Zen Hei", "DejaVu Sans"], "svg.fonttype": "none", "axes.unicode_minus": False,
                            "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#b3b3b3", "axes.grid": True,
                            "grid.color": "#ececec", "axes.axisbelow": True, "xtick.color": "#666", "ytick.color": "#666", "font.size": 9})
TXT, PUR, PINK = "#2b2b2b", "#5b2a6e", "#e0457b"
SER = [("M0", "매니폴드 없음", "#f47230", "s"), ("M1", "중앙 집중 빗살형", "#00b894", "^"), ("M3", "V자 빗살형 (헤더형)", "#257de0", "o")]
HS = "2_1+2_2"
d = pd.read_csv(ROOT / "data/ml/thermal.csv"); d = d[(d.augmented == "original") & (d.hotspot == HS)]
PH = [(261, (80, 45, 690, 740), "매니폴드 없음", "M0"), (733, (45, 40, 640, 732), "중앙 집중 빗살형", "M1"),
      (413, (135, 45, 800, 758), "V자 빗살형 (헤더형)", "M3"), (1323, (55, 40, 679, 742), "V자 빗살형 (자동 설계)", "S5")]

fig = plt.figure(figsize=(10, 7.4))
a1 = fig.add_axes([.07, .58, .40, .36]); a2 = fig.add_axes([.58, .58, .40, .36])
for k, nm, c, m in SER:
    g = d[d.design == k].sort_values("Q_mLmin")
    a1.plot(g.Q_mLmin, g.Tmax_C, "-", color=c, lw=2, marker=m, ms=6, mec="white", mew=1.2, label=nm)
    a2.plot(g.Q_mLmin, g.p_max_Pa / 1000, "-", color=c, lw=2, marker=m, ms=6, mec="white", mew=1.2, label=nm)
s5 = d[d.design == "S5"].iloc[0]
for ax, v in [(a1, s5.Tmax_C), (a2, s5.p_max_Pa / 1000)]:
    ax.plot(55, v, marker="*", ms=15, color=PINK, mec="white", mew=1, ls="", label="V자 빗살형 (자동 설계)", zorder=5)
a1.annotate(f"{s5.Tmax_C:.1f} °C", (55, s5.Tmax_C), xytext=(8, -10), textcoords="offset points", fontsize=8.5, color=PINK, weight="bold")
a1.set_title("(a) 유량별 칩 최고 온도", fontsize=10.5, loc="left", color=TXT, weight="bold"); a1.set_xlabel("총 유량 (mL/min)"); a1.set_ylabel("칩 최고 온도 (°C)")
a2.set_title("(b) 유량별 압력 강하", fontsize=10.5, loc="left", color=TXT, weight="bold"); a2.set_xlabel("총 유량 (mL/min)"); a2.set_ylabel("압력 강하 (kPa)")
a1.legend(frameon=False, fontsize=8, loc="upper right"); a2.legend(frameon=False, fontsize=8, loc="upper left")
for ax in (a1, a2):
    ax.set_xticks([30, 40, 55, 75, 100])
fig.text(.07, .975, f"핫스팟 {HS} (300 W/cm² 2칸), SimScale 해석값", fontsize=8.5, color="#666")

fig.text(.07, .495, "(c) SimScale 결과 : 같은 핫스팟 · 55 mL/min 칩 바닥 온도 (사진마다 색 범위가 다름, 숫자로 비교)", fontsize=10.5, color=TXT, weight="bold")
w = .225
for i, (n, box, nm, key) in enumerate(PH):
    im = Image.open(ROOT / f"images/{n}.png").convert("RGB").crop(box)
    ax = fig.add_axes([.04 + i * (w + .015), .03, w, .35]); ax.imshow(im); ax.axis("off")
    t = d[(d.design == key) & (d.inlet_v_mps.round(3) == .912)].Tmax_C.iloc[0]
    best = key == "S5"
    ax.set_title(f"{nm}\n최고 {t:.1f} °C", fontsize=9, color=PINK if best else TXT, weight="bold", linespacing=1.2)
    if best:
        for s in ax.spines.values(): s.set_visible(True); s.set_edgecolor(PINK); s.set_linewidth(2.5)
        ax.axis("on"); ax.set_xticks([]); ax.set_yticks([])
out = ROOT / "out/poster_icons"
fig.savefig(out / "data_panel.png", dpi=300, transparent=False, facecolor="white"); fig.savefig(out / "data_panel.svg", facecolor="white")
print("저장")
