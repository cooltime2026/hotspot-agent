"""학습한 모델로 '아무 핫스팟' → 최적 매니폴드 + 최적 유량 추천.

  python ml/design_ai.py fit                                 # 전체 데이터로 앙상블 학습 → ml/design_ai.pkl
  python ml/design_ai.py ask --hotspot 2_2,3_3 [--tlimit 100] # 핫스팟 하나 물어보기
  python ml/design_ai.py all [--tlimit 100]                  # 두 칸 핫스팟 120가지 전부 → data/ml/ai_best_by_hotspot.csv + 그림

모델 (ml/benchmark.py 시험에서 가장 정확: 안 돌린 위치 평균 9.7 ℃, 기준선 21 ℃)
  최고온도: log(Tmax−20) = 평균[ 그래디언트부스팅(공용), GP(공용, 형상 표시), GP(형상별, 입출구 거리) ]
  압력강하: 형상별 Δp = a·Q + b·Q² (오차 ≤2%)
  펌프 동력 = Δp · Q
추천: 형상마다 '최고온도 ≤ 목표'를 만족하는 최소 유량(30~100 mL/min 안)을 찾고, 그때 펌프 동력이 가장 작은 형상.
믿음 표시: 세 모델이 서로 얼마나 다른지(퍼짐)와 그 위치를 직접 돌렸는지.
주의: 형상은 데이터가 있는 6개(D0 D1 M0 M1 M3 M4) 중에서만 고름. 새 모양을 만드는 것은 아직 아님.
"""
from __future__ import annotations
import argparse, itertools, pickle, sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, T_IN, parse_cells, CELL_NAMES  # noqa: E402
import benchmark as B  # noqa: E402

warnings.filterwarnings("ignore")
PKL = Path(__file__).resolve().parent / "design_ai.pkl"
MEMBERS = ["그래디언트부스팅 공용", "GP 공용 (모든 형상 + 형상 표시)", "GP 형상별 (입출구 거리 포함)"]
QGRID = np.round(np.arange(30, 100.01, 0.5), 2)


def fit():
    df = pd.read_csv(DATA / "ml" / "thermal.csv"); df = df[df.design.isin(B.DES)].reset_index(drop=True)
    X = B.build(df); y = np.log(df.dT_C.values)
    spec = {n: (own, cols, mk) for n, own, cols, mk in B.MODELS}
    models = {}
    for n in MEMBERS:
        own, cols, mk = spec[n]
        if own:
            models[n] = {d: mk(len(cols)).fit(X.loc[df.design == d, cols].values, y[(df.design == d).values]) for d in B.DES}
        else:
            models[n] = mk(len(cols)).fit(X[cols].values, y)
    press = {}
    o = df[df.augmented == "original"]
    for d, g in o.groupby("design"):
        g = g.groupby("Q_mLmin").p_max_Pa.mean()
        press[d] = np.linalg.lstsq(np.c_[g.index, g.index ** 2], g.values, rcond=None)[0]
    seen = {d: sorted(set(df[df.design == d].hotspot)) for d in B.DES}
    pickle.dump(dict(models=models, cols={n: spec[n][1] for n in MEMBERS}, own={n: spec[n][0] for n in MEMBERS},
                     press=press, seen=seen), open(PKL, "wb"))
    print("저장:", PKL.relative_to(DATA.parent), " 학습 행:", len(df))


def load():
    if not PKL.exists():
        fit()
    return pickle.load(open(PKL, "rb"))


def predict(m, design, hotspot, Q):
    Q = np.atleast_1d(np.asarray(Q, float))
    df = pd.DataFrame(dict(design=design, hotspot="+".join(parse_cells(hotspot)), Q_mLmin=Q))
    X = B.build(df); lps = []
    for n in MEMBERS:
        mod = m["models"][n][design] if m["own"][n] else m["models"][n]
        lps.append(mod.predict(X[m["cols"][n]].values))
    lps = np.array(lps)
    T = T_IN + np.exp(lps.mean(0))
    spread = (np.exp(lps.max(0)) - np.exp(lps.min(0)))          # 세 모델 차이 [℃]
    a, b = m["press"][design]; dp = a * Q + b * Q ** 2
    return T, spread, dp, dp * Q / 6e7 * 1e3                      # ℃, ℃, Pa, mW


def best_for(m, hotspot, tlimit):
    h = "+".join(parse_cells(hotspot)); rows = []
    for d in B.DES:
        T, sp, dp, W = predict(m, d, h, QGRID)
        ok = np.nonzero(T <= tlimit)[0]
        seen = h in m["seen"][d]
        if len(ok):
            i = ok[0]
            rows.append(dict(design=d, ok=True, Q=QGRID[i], Tmax=T[i], spread=sp[i], dp=dp[i], W_mW=W[i], measured=seen,
                             T30=T[0], T100=T[-1]))
        else:
            rows.append(dict(design=d, ok=False, Q=np.nan, Tmax=T[-1], spread=sp[-1], dp=dp[-1], W_mW=np.nan, measured=seen,
                             T30=T[0], T100=T[-1]))
    r = pd.DataFrame(rows)
    r = pd.concat([r[r.ok].sort_values("W_mW"), r[~r.ok].sort_values("T100")])
    return r


def ask(hotspot, tlimit):
    m = load(); r = best_for(m, hotspot, tlimit)
    h = "+".join(parse_cells(hotspot))
    print(f"핫스팟 {h}, 목표 최고온도 ≤ {tlimit} ℃ (유량 30~100 mL/min 안에서)")
    for _, x in r.iterrows():
        tag = "직접 돌린 위치" if x.measured else "예측(안 돌린 위치)"
        if x.ok:
            print(f"  {x.design}: 최소 유량 {x.Q:.1f} mL/min → 최고 {x.Tmax:.1f} ℃, 압력 {x.dp:.0f} Pa, 펌프 {x.W_mW:.2f} mW"
                  f"   [모델 간 차이 ±{x.spread/2:.1f} ℃, {tag}]")
        else:
            print(f"  {x.design}: 불가 (100 mL/min에서도 {x.T100:.1f} ℃)   [모델 간 차이 ±{x.spread/2:.1f} ℃, {tag}]")
    b = r[r.ok]
    print("→ 추천:", f"{b.iloc[0].design}, {b.iloc[0].Q:.1f} mL/min" if len(b) else "목표를 만족하는 형상 없음 (목표를 올리거나 새 형상 필요)")


def all_pairs(tlimit):
    m = load(); out = []
    for a, b in itertools.combinations(CELL_NAMES, 2):
        h = f"{a}+{b}"; r = best_for(m, h, tlimit); ok = r[r.ok]
        rec = dict(hotspot=h, best=ok.iloc[0].design if len(ok) else "불가",
                   Q=ok.iloc[0].Q if len(ok) else np.nan, W_mW=ok.iloc[0].W_mW if len(ok) else np.nan,
                   spread=ok.iloc[0].spread if len(ok) else r.iloc[0].spread,
                   measured=bool(ok.iloc[0].measured) if len(ok) else False,
                   coolest_at100=r.sort_values("T100").iloc[0].design, T100_min=r.T100.min())
        for _, x in r.iterrows():
            rec[f"T100_{x.design}"] = round(x.T100, 1); rec[f"Q_{x.design}"] = x.Q
        out.append(rec)
    df = pd.DataFrame(out)
    p = DATA / "ml" / f"ai_best_by_hotspot_T{int(tlimit)}.csv"; df.round(2).to_csv(p, index=False)
    print("저장:", p.relative_to(DATA.parent))
    print(f"목표 ≤ {tlimit} ℃: 형상별 1등 횟수 (120가지 두 칸 핫스팟)")
    print(df.best.value_counts().to_string())
    print("100 mL/min에서 가장 시원한 형상 1등 횟수:")
    print(df.coolest_at100.value_counts().to_string())
    figure(df, tlimit)
    return df


def figure(df, tlimit):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in font_manager.findSystemFonts():
        if "wqy-zenhei" in f:
            font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
    colors = {"D0": "#e8443a", "D1": "#f5a623", "M0": "#8c8c8c", "M1": "#4a90e2", "M3": "#2e7d32", "M4": "#8e44ad", "불가": "#000000"}
    adj = df[df.hotspot.apply(lambda h: (lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1)(*[tuple(map(int, c.split("_"))) for c in h.split("+")]))]
    fig, axs = plt.subplots(1, 2, figsize=(13, 6.5))
    for ax, horiz in zip(axs, [True, False]):
        sub = adj[adj.hotspot.apply(lambda h: h.split("+")[0].split("_")[0] == h.split("+")[1].split("_")[0]) == horiz]
        for _, x in sub.iterrows():
            (r1, c1), (r2, c2) = [tuple(map(int, c.split("_"))) for c in x.hotspot.split("+")]
            cx, cy = (c1 + c2) / 2 * 3 - 1.5, (r1 + r2) / 2 * 3 - 1.5
            w, h = (2.6, 2.2) if horiz else (2.2, 2.6)
            ax.add_patch(plt.Rectangle((cx - w / 2, cy - h / 2), w, h, fc=colors[x.best], ec="white", lw=2, alpha=0.85))
            txt = x.best if x.best == "불가" else f"{x.best}\n{x.Q:.0f}"
            ax.text(cx, cy, txt, ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        for k in range(5):
            ax.axhline(k * 3, color="#ccc", lw=0.8); ax.axvline(k * 3, color="#ccc", lw=0.8)
        ax.set_xlim(0, 12); ax.set_ylim(0, 12); ax.set_aspect("equal")
        ax.set_xticks([1.5, 4.5, 7.5, 10.5], ["1열", "2열", "3열", "4열"]); ax.set_yticks([1.5, 4.5, 7.5, 10.5], ["1행", "2행", "3행", "4행"])
        ax.set_title(("가로로 붙은 두 칸" if horiz else "세로로 붙은 두 칸") + " (숫자 = 최소 유량 mL/min)")
    fig.suptitle(f"머신러닝 추천: 최고온도 ≤ {tlimit:.0f} ℃를 가장 적은 펌프 동력으로 맞추는 매니폴드\n"
                 "(형상마다 입출구 위치가 달라 칸 좌표는 각 형상 STEP 기준. 안 돌린 위치는 예측값: 평균 오차 약 10 ℃)", fontsize=11)
    fig.tight_layout(rect=(0, 0.02, 1, 0.9))
    out = DATA.parent / "out" / "plan" / f"ai_best_T{int(tlimit)}.png"; out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120); print("그림:", out.relative_to(DATA.parent))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("fit")
    a = sp.add_parser("ask"); a.add_argument("--hotspot", required=True); a.add_argument("--tlimit", type=float, default=100)
    b = sp.add_parser("all"); b.add_argument("--tlimit", type=float, default=100)
    x = ap.parse_args()
    if x.cmd == "fit": fit()
    elif x.cmd == "ask": ask(x.hotspot, x.tlimit)
    else: all_pairs(x.tlimit)


if __name__ == "__main__":
    main()
