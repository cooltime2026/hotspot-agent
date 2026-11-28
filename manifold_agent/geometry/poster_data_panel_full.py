"""포스터 '② SimScale 해석 데이터와 머신러닝 모델' 칸 전체 (세로 칸 비율) → out/poster_icons/data_panel_full.png/svg
  그래프 (a)(b) + 숫자 상자 4개 + SimScale 바닥 온도 사진 4장 + 글 5줄
"""
from pathlib import Path
import pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
from matplotlib import font_manager as _fm
for _f in Path("/usr/share/fonts/truetype/nanum").glob("NanumSquareRound*.ttf"):   # 포스터 글씨체 (나눔스퀘어라운드, apt fonts-nanum-extra)
    _fm.fontManager.addfont(str(_f))
matplotlib.rcParams.update({"font.family": ["NanumSquareRound", "WenQuanYi Zen Hei", "DejaVu Sans"], "svg.fonttype": "none", "axes.unicode_minus": False,
                            "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#b3b3b3", "axes.grid": True,
                            "grid.color": "#ececec", "axes.axisbelow": True, "xtick.color": "#666", "ytick.color": "#666", "font.size": 8})
TXT, PUR, PINK, LP = "#333333", "#6b3a7d", "#e0457b", "#f1e9f3"
SER = [("M0", "매니폴드 없음", "#9a9a9a", "s"), ("M1", "중앙 집중 빗살형", "#3f7fd8", "^"), ("M3", "V자 빗살형", "#5b2a6e", "o")]
HS = "2_1+2_2"
d = pd.read_csv(ROOT / "data/ml/thermal.csv"); d = d[(d.augmented == "original") & (d.hotspot == HS)]
s5 = d[d.design == "S5"].iloc[0]
PH = [(261, (80, 45, 690, 740), "매니폴드 없음", "M0"), (733, (45, 40, 640, 732), "중앙 집중 빗살형", "M1"),
      (413, (135, 45, 800, 758), "V자 빗살형", "M3"), (1323, (55, 40, 679, 742), "자동 설계", "S5")]

fig = plt.figure(figsize=(7.6, 9.6))
# ---- (a)(b) 그래프 ----
a1 = fig.add_axes([.09, .72, .38, .18]); a2 = fig.add_axes([.60, .72, .38, .18])
for k, nm, c, m in SER:
    g = d[d.design == k].sort_values("Q_mLmin")
    a1.plot(g.Q_mLmin, g.Tmax_C, "-", color=c, lw=1.8, marker=m, ms=5, mec="white", mew=1, label=nm)
    a2.plot(g.Q_mLmin, g.p_max_Pa / 1000, "-", color=c, lw=1.8, marker=m, ms=5, mec="white", mew=1, label=nm)
for ax, v in [(a1, s5.Tmax_C), (a2, s5.p_max_Pa / 1000)]:
    ax.plot(55, v, marker="*", ms=13, color=PINK, mec="white", mew=.8, ls="", label="자동 설계 (V자 빗살)", zorder=5)
a1.annotate(f"{s5.Tmax_C:.1f} °C", (55, s5.Tmax_C), xytext=(7, -9), textcoords="offset points", fontsize=7.5, color=PINK, weight="bold")
for ax, t, yl in [(a1, "(a) 유량별 칩 최고 온도", "칩 최고 온도 (°C)"), (a2, "(b) 유량별 압력 강하", "압력 강하 (kPa)")]:
    ax.set_title(t, fontsize=9, loc="left", color=TXT, weight="bold", pad=4); ax.set_xlabel("총 유량 (mL/min)", fontsize=7.5); ax.set_ylabel(yl, fontsize=7.5)
    ax.set_xticks([30, 55, 75, 100]); ax.tick_params(labelsize=7)
a1.legend(frameon=False, fontsize=6.6, loc="upper right", handlelength=1.6); a2.legend(frameon=False, fontsize=6.6, loc="upper left", handlelength=1.6)
# 핫스팟 위치 그림 (글자 대신): 칩 바닥 4 × 4 칸, 빨간 2칸 = 핫스팟. 사진과 같은 방향(바닥에서 봄: 1행이 위)
from matplotlib.patches import Rectangle
mp = fig.add_axes([.035, .93, .075, .075 * 7.6 / 9.6]); mp.set_xlim(0, 4); mp.set_ylim(4, 0); mp.set_aspect("equal"); mp.axis("off"); mp.add_patch(Rectangle((0, 0), 4, 4, fill=False, ec="#8a7a92", lw=1.2, zorder=5))
hot = {(int(c.split("_")[0]), int(c.split("_")[1])) for c in HS.split("+")}
for r in range(1, 5):
    for c in range(1, 5):
        mp.add_patch(Rectangle((c - 1, r - 1), 1, 1, fc="#e8463c" if (r, c) in hot else "#ebe3ee", ec="white", lw=1.5))
fig.text(.125, .965, "칩 바닥(12 × 12 mm)을 4 × 4 칸으로 나눔 → 빨간 두 칸 = 핫스팟 (300 W/cm²)", fontsize=8.3, color=TXT, weight="bold", va="center")
fig.text(.125, .942, "아래 그래프 · 사진은 모두 이 같은 핫스팟 위치에서 SimScale 로 해석한 값", fontsize=7.5, color="#666", va="center")

# ---- 숫자 상자 4개 ----
bg = fig.add_axes([0, 0, 1, 1]); bg.axis("off"); bg.set_xlim(0, 1); bg.set_ylim(0, 1); bg.set_zorder(-1)
for i, (big, small) in enumerate([("238건", "SimScale 해석"), ("37종", "매니폴드 형상"), ("20가지", "핫스팟 위치"), ("5단계", "유량 30~100 mL/min")]):
    x = .035 + i * .2425
    bg.add_patch(FancyBboxPatch((x, .595), .222, .075, boxstyle="round,pad=0,rounding_size=0.012", fc=LP, ec="none"))
    bg.text(x + .111, .643, big, ha="center", va="center", fontsize=15, color=PUR, weight="bold")
    bg.text(x + .111, .607, small, ha="center", va="center", fontsize=7.3, color=TXT)

# ---- SimScale 사진 4장 ----
bg.text(.035, .578, "SimScale 칩 바닥 온도 (55 mL/min · 흰색이 가장 뜨거운 곳 · 사진마다 색 범위 다름)", fontsize=8.5, color=TXT, weight="bold", va="center")
for i, (n, box, nm, key) in enumerate(PH):
    im = Image.open(ROOT / f"images/{n}.png").convert("RGB").crop(box)
    ax = fig.add_axes([.035 + i * .2425, .33, .222, .185]); ax.imshow(im); ax.set_xticks([]); ax.set_yticks([])
    best = key == "S5"
    for s in ax.spines.values(): s.set_visible(best); s.set_edgecolor(PINK); s.set_linewidth(2)
    t = d[(d.design == key) & (d.inlet_v_mps.round(3) == .912)].Tmax_C.iloc[0]
    ax.set_title(f"{nm}\n{t:.1f} °C", fontsize=7.8, color=PINK if best else TXT, weight="bold", linespacing=1.15, pad=3)

out = ROOT / "out/poster_icons"
from matplotlib.transforms import Bbox
bb = Bbox.from_extents(0, .31 * 9.6, 7.6, 9.6)        # 아래 글(해석 조건 등)은 뺌 — PPT 에서 직접 씀
fig.savefig(out / "data_panel_full.png", dpi=300, facecolor="white", bbox_inches=bb); fig.savefig(out / "data_panel_full.svg", facecolor="white", bbox_inches=bb)
print("저장")
