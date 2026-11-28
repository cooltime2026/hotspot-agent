"""보내준 SimScale 자료를 표·그래프로 정리 → out/charts/

  python ml/data_charts.py

1 같은 유량(0.912 m/s)에서 핫스팟별 모양 순위
2 유량을 올리면: 최고온도 / 압력 (2_1+2_2, M0·M1·M3)
3 온도 vs 압력 (2_2+3_2, 0.912 m/s) — 시원한데 압력도 낮은 모양
4 머신러닝 예측(사진 보기 전) vs 실측
5 16칸 평균 온도 지도 — 핫스팟별 1등 모양
6 채널 22개 유량 나눠짐 (M0·D0·D1, 0.912 m/s)
+ 표: out/charts/summary_by_hotspot.csv
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "charts"; OUT.mkdir(parents=True, exist_ok=True)
matplotlib.rcParams.update({
    "font.family": ["WenQuanYi Zen Hei", "DejaVu Sans"], "axes.unicode_minus": False,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#b3b3b3",
    "axes.labelcolor": "#191919", "xtick.color": "#666666", "ytick.color": "#666666",
    "axes.grid": True, "grid.color": "#ececec", "grid.linewidth": 0.8, "axes.axisbelow": True,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "figure.facecolor": "white",
})
TXT, TXT2, MUTED = "#191919", "#666666", "#c9c9c9"
C1, C2, C3 = "#257de0", "#f47230", "#00b894"      # 범주 1~3 (검사 통과, 대비 낮은 2·3 은 글자 표시를 같이 붙임)
V = 0.912

d = pd.read_csv(ROOT / "data/ml/thermal.csv")
d = d[d.augmented == "original"].copy()
d["v"] = d.inlet_v_mps.round(3)


def fam(k):
    if k[0] in "MD":
        return "기본 모양 (M·D)"
    if k[0] == "S":
        return "머신러닝 v17 (S)"
    return "띠 가족·발명 (A·B·C·L·F·E)"


FAMC = {"기본 모양 (M·D)": C2, "띠 가족·발명 (A·B·C·L·F·E)": C3, "머신러닝 v17 (S)": C1}
FAMM = {"기본 모양 (M·D)": "s", "띠 가족·발명 (A·B·C·L·F·E)": "^", "머신러닝 v17 (S)": "o"}


def save(fig, name):
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight"); plt.close(fig); print("저장", OUT / name)


# ---------- 1. 핫스팟별 순위 ----------
def chart_rank():
    a = d[d.v == V]
    hs = [h for h, n in a.groupby("hotspot").design.nunique().sort_values(ascending=False).items() if n >= 4]
    fig, axs = plt.subplots(1, len(hs), figsize=(4.0 * len(hs), 6.2), sharex=True)
    for ax, h in zip(np.atleast_1d(axs), hs):
        g = a[a.hotspot == h].groupby("design").Tmax_C.min().sort_values()
        y = np.arange(len(g))[::-1]
        cols = [C1 if i == 0 else MUTED for i in range(len(g))]
        ax.barh(y, g.values, color=cols, height=0.72, edgecolor="white", linewidth=2)
        ax.set_yticks(y, g.index); ax.grid(axis="y", visible=False)
        for yy, (k, t) in zip(y, g.items()):
            ax.text(t + 2, yy, f"{t:.1f}", va="center", fontsize=8.5, color=TXT if k == g.index[0] else TXT2,
                    weight="bold" if k == g.index[0] else "normal")
        ax.set_title(f"핫스팟 {h}\n1등 {g.index[0]} {g.iloc[0]:.1f} ℃  (모양 {len(g)}개)")
        ax.set_xlabel("최고온도 (℃)"); ax.set_xlim(0, max(a.Tmax_C.max(), 210) * 1.08)
    fig.suptitle(f"같은 유량(입구 {V} m/s, 55 mL/min)에서 모양별 최고온도 — 파랑이 1등, 짧을수록 좋음", fontsize=13, weight="bold", y=1.01)
    save(fig, "1_rank_by_hotspot.png")


# ---------- 2. 유량 효과 ----------
def chart_flow():
    h = "2_1+2_2"; ks = [("M0", C2, "s"), ("M1", C3, "^"), ("M3", C1, "o")]
    nm = {"M0": "M0 매니폴드 없음", "M1": "M1 중앙 집중 빗살", "M3": "M3 V자 빗살"}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
    for k, c, m in ks:
        g = d[(d.hotspot == h) & (d.design == k)].sort_values("Q_mLmin")
        a1.plot(g.Q_mLmin, g.Tmax_C, "-", color=c, lw=2, marker=m, ms=7, mec="white", mew=1.5)
        a2.plot(g.Q_mLmin, g.p_max_Pa / 1000, "-", color=c, lw=2, marker=m, ms=7, mec="white", mew=1.5)
        a1.annotate(nm[k], (g.Q_mLmin.iloc[-1], g.Tmax_C.iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=TXT)
        a2.annotate(nm[k], (g.Q_mLmin.iloc[-1], g.p_max_Pa.iloc[-1] / 1000), xytext=(6, {"M3": 8, "M1": -8}.get(k, 0)), textcoords="offset points", va="center", fontsize=9, color=TXT)
    a1.set_title(f"유량 ↑ → 최고온도 ↓  (핫스팟 {h})"); a1.set_xlabel("전체 유량 (mL/min)"); a1.set_ylabel("최고온도 (℃)")
    a2.set_title("유량 ↑ → 압력 ↑ (세로축 로그)"); a2.set_xlabel("전체 유량 (mL/min)"); a2.set_ylabel("입구 압력 (kPa)"); a2.set_yscale("log"); a2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    a2.yaxis.set_minor_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}" if v in (2, 5, 20) else ""))
    for ax in (a1, a2):
        ax.set_xlim(25, 135); ax.axvline(55, color="#999999", ls=":", lw=1)
        ax.text(55, ax.get_ylim()[1], " 55 mL/min (비교 기준)", fontsize=8, color=TXT2, va="top")
    fig.suptitle("55 → 100 mL/min 으로 올리면 온도는 19~23 ℃ 내려가지만 압력은 2.6~3배 — 같은 유량이면 모양 차이가 더 큼", fontsize=12, weight="bold", y=1.02)
    fig.tight_layout(); save(fig, "2_flow_effect.png")


# ---------- 3. 온도 vs 압력 ----------
def chart_tradeoff():
    h = "2_2+3_2"
    g = d[(d.hotspot == h) & (d.v == V)].dropna(subset=["p_max_Pa"]).sort_values("Tmax_C").drop_duplicates("design")
    fig, ax = plt.subplots(figsize=(9.5, 6))
    for f, gg in g.groupby(g.design.map(fam)):
        ax.scatter(gg.p_max_Pa / 1000, gg.Tmax_C, s=70, color=FAMC[f], marker=FAMM[f], edgecolor="white", linewidth=2, label=f, zorder=3)
    for _, r in g.iterrows():
        ax.annotate(r.design, (r.p_max_Pa / 1000, r.Tmax_C), xytext=(6, 4), textcoords="offset points", fontsize=9, color=TXT,
                    weight="bold" if r.design == g.design.iloc[0] else "normal")
    ax.set_xlabel("입구 압력 (kPa) — 왼쪽일수록 펌프가 편함"); ax.set_ylabel("최고온도 (℃) — 아래일수록 시원")
    ax.set_title(f"핫스팟 {h}, {V} m/s: 왼쪽 아래가 좋은 모양  (1등 {g.design.iloc[0]} {g.Tmax_C.iloc[0]:.1f} ℃ · {g.p_max_Pa.iloc[0]/1000:.1f} kPa)")
    ax.legend(frameon=False, loc="lower left")
    save(fig, "3_temp_vs_pressure.png")
    return g


# ---------- 4. 예측 vs 실측 ----------
BLIND = [  # (모양, 핫스팟, ML 예측 ℃, 실측 ℃)  — data/runs_log.md, 사진 보기 전 칸 모델(+보정) 예측
    ("F1", "1_3+1_4", 129.3, 111.6), ("E1", "1_3+1_4", 112.5, 201.5), ("S4", "1_3+1_4", 97.8, 116.3),
    ("S5", "2_1+2_2", 79.9, 88.82), ("S6", "3_3+3_4", 88.3, 92.22), ("S7", "2_2+3_2", 89.6, 89.83),
    ("S8", "2_1+2_2", 85.8, 95.79), ("S9", "3_3+3_4", 99.8, 94.18)]


def chart_blind():
    b = pd.DataFrame(BLIND, columns=["design", "hotspot", "pred", "real"])
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12.5, 5.4), gridspec_kw=dict(width_ratios=[1, 1.15]))
    lo, hi = 70, 210
    ax.plot([lo, hi], [lo, hi], color="#999999", lw=1, ls="--"); ax.fill_between([lo, hi], [lo - 10, hi - 10], [lo + 10, hi + 10], color="#f2f2f2", zorder=0)
    ax.text(185, 172, "±10 ℃", color=TXT2, fontsize=8)
    for _, r in b.iterrows():
        c = MUTED if r.design == "E1" else C1
        ax.scatter(r.pred, r.real, s=70, color=c, edgecolor="white", linewidth=2, zorder=3)
        off = dict(S5=(-22, -4), S6=(8, 6), S7=(8, -10), S8=(-20, 6)).get(r.design, (6, 3))
        ax.annotate(r.design, (r.pred, r.real), xytext=off, textcoords="offset points", fontsize=9, color=TXT)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
    ax.set_xlabel("머신러닝 예측 (℃, 사진 보기 전)"); ax.set_ylabel("SimScale 실측 (℃)")
    ax.set_title("점선 위 = 예측보다 뜨거웠음")
    b["err"] = b.real - b.pred
    bb = b.iloc[::-1]
    cols = [MUTED if k == "E1" else (C2 if e > 0 else C1) for k, e in zip(bb.design, bb.err)]
    bx.barh(bb.design, bb.err, color=cols, height=0.65, edgecolor="white", linewidth=2)
    bx.axvline(0, color="#999999", lw=1); bx.grid(axis="y", visible=False)
    for i, (k, e) in enumerate(zip(bb.design, bb.err)):
        bx.text(e + (2 if e >= 0 else -2), i, f"{e:+.1f}", va="center", ha="left" if e >= 0 else "right", fontsize=9, color=TXT)
    bx.set_xlabel("실측 − 예측 (℃)  · 주황 = 실제가 더 뜨거움, 파랑 = 더 시원"); bx.set_xlim(-30, 100)
    ok = b[b.design != "E1"]
    bx.set_title(f"E1 빼고 평균 틀림 {ok.err.abs().mean():.1f} ℃ (E1 = 지름길 실패 모양, 지금은 학습에서 뺌)")
    fig.suptitle("머신러닝이 사진 보기 전에 맞힌 값 vs 실제 (0.912 m/s)", fontsize=13, weight="bold", y=1.02)
    fig.tight_layout(); save(fig, "4_ml_prediction_vs_real.png")
    return b


# ---------- 5. 16칸 온도 지도 ----------
def chart_cells():
    c = pd.read_csv(ROOT / "data/ml/cell_temps.csv"); c = c[c.inlet_v_mps.round(3) == V]
    hs = ["2_2+3_2", "2_1+2_2", "3_3+3_4", "1_3+1_4", "4_3+4_4"]
    rows = []
    for h in hs:
        g = c[c.hotspot == h].dropna(subset=["Tmean_1_1"])
        if len(g):
            rows.append(g.loc[g.Tmax_C.idxmin()])
    fig, axs = plt.subplots(1, len(rows), figsize=(3.3 * len(rows), 3.9))
    vmin, vmax = 20.0, max(float(r[[f"Tmean_{i}_{j}" for i in range(1, 5) for j in range(1, 5)]].max()) for r in rows)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", ["#fff3e8", "#fbb27e", "#f47230", "#b8461a", "#6e2a0f"])
    for ax, r in zip(np.atleast_1d(axs), rows):
        M = np.array([[float(r[f"Tmean_{i}_{j}"]) for j in range(1, 5)] for i in range(4, 0, -1)])
        ax.imshow(M, cmap=cmap, vmin=vmin, vmax=vmax)
        hot = set(r.hotspot.split("+"))
        for ii in range(4):
            for jj in range(4):
                cell = f"{4-ii}_{jj+1}"; v = M[ii, jj]
                ax.text(jj, ii, f"{v:.0f}", ha="center", va="center", fontsize=10, color="white" if v > vmin + 0.55 * (vmax - vmin) else TXT,
                        weight="bold" if cell in hot else "normal")
                if cell in hot:
                    ax.add_patch(plt.Rectangle((jj - .47, ii - .47), .94, .94, fill=False, ec=C1, lw=2.5))
        ax.set_xticks(range(4), [f"열{j}" for j in range(1, 5)]); ax.set_yticks(range(4), [f"{i}행" for i in range(4, 0, -1)])
        ax.grid(False); [s.set_visible(False) for s in ax.spines.values()]
        ax.set_title(f"{r.hotspot} · 1등 {r.design}\n최고 {r.Tmax_C:.1f} ℃" + ("\n(F1 111.6 은 사진 없음)" if r.hotspot == "1_3+1_4" else ""))
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
    fig.colorbar(sm, ax=axs, fraction=0.015, pad=0.02, label="칸 평균 온도 (℃)")
    fig.suptitle(f"바닥 16칸 평균 온도 — 핫스팟별 1등 모양 (칸 사진이 있는 것 중, {V} m/s, 파란 테두리 = 핫스팟, 위가 4행)", fontsize=12, weight="bold", y=1.04)
    save(fig, "5_cell_temperature_maps.png")


# ---------- 6. 채널 유량 분배 ----------
def chart_channels():
    f = pd.read_csv(ROOT / "data/ml/flow.csv"); f = f[f.inlet_v_mps.round(3) == V]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    nm = {"M0": "M0 매니폴드 없음", "D0": "D0 이중 바람개비", "D1": "D1 말굽"}
    for k, c, m in [("M0", C2, "s"), ("D0", C3, "^"), ("D1", C1, "o")]:
        g = f[f.design == k].sort_values("x_mm")
        share = g.share / g.share.mean()
        ax.plot(g.x_mm, share, "-", color=c, lw=2, marker=m, ms=6, mec="white", mew=1.2)
        ax.lines[-1].set_label(f"{nm[k]} (가장 적은 채널 {share.min():.2f} · 가장 많은 {share.max():.2f})")
    ax.axhline(1, color="#999999", ls=":", lw=1); ax.legend(frameon=False, loc="upper left", fontsize=9)
    for x in (3, 6, 9):
        ax.axvline(x, color="#e0e0e0", lw=1)
    ax.set_xlabel("채널 위치 x (mm) — 22개 채널, 세로선 = 칸 경계"); ax.set_ylabel("채널 유량 / 평균 (1 = 고르게)"); ax.set_ylim(0.5, 1.95)
    ax.set_xlim(0, 12); ax.set_title(f"채널 22개에 물이 얼마나 고르게 나눠지나 ({V} m/s, y = 6 mm 단면 사진에서 읽음)")
    save(fig, "6_channel_flow_split.png")


# ---------- 표 ----------
def table():
    a = d[d.v == V]
    rows = []
    for h, g in a.groupby("hotspot"):
        g = g.sort_values("Tmax_C")
        b = g.iloc[0]
        rows.append({"핫스팟": h, "모양수": g.design.nunique(), "1등": b.design, "최고온도_C": b.Tmax_C, "압력_Pa": b.p_max_Pa,
                     "2등": g.design.iloc[1] if len(g) > 1 else "", "2등온도_C": g.Tmax_C.iloc[1] if len(g) > 1 else np.nan,
                     "꼴등": g.design.iloc[-1] if len(g) > 2 else "", "꼴등온도_C": g.Tmax_C.iloc[-1] if len(g) > 2 else np.nan})
    t = pd.DataFrame(rows).sort_values(["모양수", "최고온도_C"], ascending=[False, True])
    t.to_csv(OUT / "summary_by_hotspot.csv", index=False, encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(12, 0.36 * len(t) + 1.2)); ax.axis("off")
    cells = [[r.핫스팟, r.모양수, r["1등"], f"{r.최고온도_C:.1f}", "" if pd.isna(r.압력_Pa) else f"{r.압력_Pa:,.0f}",
              r["2등"], "" if pd.isna(r["2등온도_C"]) else f"{r['2등온도_C']:.1f}", r.꼴등, "" if pd.isna(r.꼴등온도_C) else f"{r.꼴등온도_C:.1f}"] for _, r in t.iterrows()]
    tb = ax.table(cellText=cells, colLabels=["핫스팟", "돌린 모양 수", "1등", "1등 ℃", "1등 압력 Pa", "2등", "2등 ℃", "꼴등", "꼴등 ℃"],
                  loc="center", cellLoc="center")
    tb.auto_set_font_size(False); tb.set_fontsize(9.5); tb.scale(1, 1.35)
    for (i, j), cl in tb.get_celld().items():
        cl.set_edgecolor("#e6e6e6")
        if i == 0:
            cl.set_facecolor("#f3f3f3"); cl.set_text_props(weight="bold")
        elif j in (2, 3):
            cl.set_text_props(weight="bold", color=C1)
    ax.set_title(f"핫스팟별 1등 표 ({V} m/s, 55 mL/min) — 전체 {a.run_id.nunique() if 'run_id' in a else len(a)} Run", fontsize=12, weight="bold")
    save(fig, "0_table_best_by_hotspot.png")
    return t


if __name__ == "__main__":
    t = table(); chart_rank(); chart_flow(); g = chart_tradeoff(); b = chart_blind(); chart_cells(); chart_channels()
    print(t.head(8).to_string(index=False))
    print(f"전체 Run {len(d)} · 모양 {d.design.nunique()} · 핫스팟 {d.hotspot.nunique()}")
