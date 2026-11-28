"""지금까지 돌린 SimScale Run 정리: 모양 × 핫스팟 × 유량 → out/charts/7_run_matrix.png, run_matrix.csv

  python ml/run_matrix.py
"""
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "out" / "charts"
matplotlib.rcParams.update({"font.family": ["WenQuanYi Zen Hei", "DejaVu Sans"], "axes.unicode_minus": False})
d = pd.read_csv(ROOT / "data/ml/thermal.csv"); d = d[d.augmented == "original"].copy()
d["Q"] = d.inlet_v_mps.round(3).map({0.497: 30, 0.663: 40, 0.912: 55, 1.243: 75, 1.658: 100})
order = sorted(d.design.unique(), key=lambda k: ("MDABCLEFS".index(k[0]), int(k[1:])))
hs = d.groupby("hotspot").size().sort_values(ascending=False).index.tolist()
g = d.groupby(["design", "hotspot"]).Q.apply(lambda s: sorted(set(s))).unstack()
g = g.reindex(index=order, columns=hs)
txt = g.map(lambda q: "" if not isinstance(q, list) else ("30~100" if len(q) == 5 else "·".join(map(str, q))))
cnt = g.map(lambda q: len(q) if isinstance(q, list) else 0)
txt.to_csv(OUT / "run_matrix.csv", encoding="utf-8-sig")

fig, ax = plt.subplots(figsize=(17, 13.5))
cmap = matplotlib.colors.ListedColormap(["#ffffff", "#d6e6fa", "#9cc3f2", "#6aa3ea", "#3f86e3", "#257de0"])
ax.imshow(cnt.values, cmap=cmap, vmin=0, vmax=5, aspect="auto")
for i in range(len(order)):
    for j in range(len(hs)):
        t = txt.iat[i, j]
        if t:
            ax.text(j, i, t, ha="center", va="center", fontsize=7.6, color="white" if cnt.iat[i, j] >= 4 else "#191919")
ax.set_xticks(range(len(hs)), [f"{h}\n({(d.hotspot == h).sum()})" for h in hs], fontsize=8.5)
lab = {"M0": "M0 매니폴드 없음", "M1": "M1 중앙 빗살", "M3": "M3 V자 빗살", "M4": "M4 직상부 공급", "D0": "D0 이중 바람개비", "D1": "D1 말굽",
       "L1": "L1 국소 개방", "E1": "E1 가장자리 급수(실패)", "F1": "F1 핫스팟 줄 전용 입구", "S7": "S7 (=S6 같은 모양)"}
ax.set_yticks(range(len(order)), [f"{lab.get(k, k)}  ({(d.design == k).sum()})" for k in order], fontsize=8.5)
ax.xaxis.tick_top()
ax.set_xticks(np.arange(-.5, len(hs)), minor=True); ax.set_yticks(np.arange(-.5, len(order)), minor=True)
ax.grid(which="minor", color="#e6e6e6", lw=0.8); ax.tick_params(which="minor", length=0)
for s in ax.spines.values(): s.set_visible(False)
# 가족 구분선
for k in ["D0", "A1", "B1", "C1", "L1", "S1"]:
    ax.axhline(order.index(k) - .5, color="#888888", lw=1.2)
n_shape = d.design.nunique() - 1   # S6 = S7
ax.set_title(f"지금까지 돌린 SimScale Run {len(d)}개 — 모양 {n_shape}종 (이름 {d.design.nunique()}개, S6=S7) · 핫스팟 위치 {len(hs)}곳 · 유량 5단계\n"
             "칸 안 숫자 = 돌린 유량(mL/min), 30~100 = 5단계 전부 · 괄호 = Run 수 · 진할수록 유량을 많이 돌림",
             fontsize=12, weight="bold", pad=48)
fig.savefig(OUT / "7_run_matrix.png", dpi=140, bbox_inches="tight"); plt.close(fig)
print("저장", OUT / "7_run_matrix.png")
q = d.groupby("Q").size(); print(q.to_string())
