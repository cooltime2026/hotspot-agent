"""핫스팟별 최적 매니폴드(+유량) 비교 / 추천용 데이터.

  python ml/optimize.py coverage                 # 핫스팟 × 형상 표: 어떤 조합이 몇 유량 돌았는지
  python ml/optimize.py best --hotspot 3_4,4_4   # 그 핫스팟에서 형상 순위 (아래 3가지 기준)
            [--tlimit 100]                       #   목표 최고온도 [℃] (기본 100)
            [--pump 2]                           #   비교할 펌프 동력 [mW] (기본 2)
  python ml/optimize.py flows                    # 핫스팟마다 최적 유량(목표 온도별), 유량 단계별 효율
  python ml/optimize.py all                      # 모든 핫스팟 → data/ml/best_by_hotspot.csv, data/ml/design_curves.csv

비교 기준 (같은 핫스팟끼리만 비교):
  ① 같은 유량에서 최고온도가 가장 낮은 형상            (유량 30/40/55/75/100 각각)
  ② 같은 펌프 동력(Δp·Q)에서 최고온도가 가장 낮은 형상   (공정한 비교: 압력 손해까지 반영)
  ③ 목표 온도를 만족하는 데 펌프 동력이 가장 적게 드는 형상과 그때 유량  (= 최적 운전점)
②③은 형상·핫스팟마다 Tmax = 20 + a·Q^n, Δp = b·Q + c·Q² 를 맞춰서 유량 사이를 잇는다.
  - 유량 3개 이상 돈 조합만 곡선을 만든다. 30~100 mL/min 밖은 쓰지 않는다(외삽 금지).
  - 'mirror_x'는 좌우 대칭으로 얻은 값(직접 돌린 것 아님)이라 표에 표시한다.

출력 표는 머신러닝 라벨로 그대로 쓸 수 있다: (핫스팟, 기준) → 최적 형상, 최적 유량, 최소 펌프 동력.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, T_IN, parse_cells   # noqa: E402

QMIN, QMAX = 29.9, 100.1
QGRID = np.linspace(30, 100, 141)


def load():
    p = DATA / "ml" / "thermal.csv"
    if not p.exists():
        sys.exit("먼저 python ml/dataset.py")
    return pd.read_csv(p)


def curves(df):
    """(형상, 핫스팟)별 곡선. 유량 3개 미만이면 None."""
    out = {}
    for (d, h), g in df.groupby(["design", "hotspot"]):
        g = g.groupby("Q_mLmin").agg(T=("Tmax_C", "mean"), p=("p_max_Pa", "mean"),
                                     src=("augmented", "first")).reset_index()
        rec = dict(design=d, hotspot=h, n_flow=len(g), source=g.src.iloc[0], pts=g, fit=None)
        if len(g) >= 3:
            n, a = np.polyfit(np.log(g.Q_mLmin), np.log(g["T"] - T_IN), 1)
            bc = np.linalg.lstsq(np.c_[g.Q_mLmin, g.Q_mLmin ** 2], g.p, rcond=None)[0]
            rec["fit"] = dict(a=a, n=n, b=bc[0], c=bc[1], qlo=g.Q_mLmin.min(), qhi=g.Q_mLmin.max())
        out[(d, h)] = rec
    return out


def T_of(f, Q):
    return T_IN + np.exp(f["a"] + f["n"] * np.log(Q))


def dp_of(f, Q):
    return f["b"] * Q + f["c"] * Q ** 2


def pump_mW(f, Q):
    return dp_of(f, Q) * Q / 6e7 * 1e3


def in_range(f):
    return QGRID[(QGRID >= f["qlo"] - 1e-6) & (QGRID <= f["qhi"] + 1e-6)]


def coverage(df):
    tab = df.groupby(["hotspot", "design"]).apply(
        lambda g: f'{g.Q_mLmin.nunique()}' + ("*" if (g.augmented != "original").all() else "")).unstack()
    tab = tab.fillna("-")
    print("핫스팟 × 형상: 돌린 유량 개수  (* = 좌우 대칭으로 얻은 값, - = 없음)")
    print(tab.to_string())
    multi = [h for h in tab.index if (tab.loc[h] != "-").sum() >= 2]
    print(f"\n형상 2개 이상 비교 가능한 핫스팟: {multi if multi else '없음'}")
    return tab


def rank(df, hotspot, tlimit=100.0, pump=2.0, verbose=True):
    h = "+".join(parse_cells(hotspot))
    C = {k: v for k, v in curves(df).items() if k[1] == h}
    rows = []
    if not C:
        if verbose:
            print(f"{h}: 데이터 없음")
        return rows
    if verbose:
        print(f"\n=== 핫스팟 {h}  (형상 {len(C)}개: {', '.join(sorted(k[0] for k in C))}) ===")
    # ① 같은 유량
    allQ = sorted({q for c in C.values() for q in c["pts"].Q_mLmin.round(0)})
    if verbose:
        print("① 같은 유량에서 최고온도 [℃] / 압력 [Pa]")
    for q in allQ:
        vals = []
        for (d, _), c in C.items():
            m = c["pts"][np.isclose(c["pts"].Q_mLmin.round(0), q)]
            if len(m):
                vals.append((float(m["T"].iloc[0]), d, float(m.p.iloc[0])))
        vals.sort()
        if verbose:
            print(f"   {q:5.0f} mL/min: " + "  ".join(f"{d} {t:.1f}℃/{p:.0f}Pa" for t, d, p in vals))
        if len(vals) >= 2:
            rows.append(dict(hotspot=h, criterion="same_flow", condition=f"Q={q:.0f}", best_design=vals[0][1],
                             best_Q_mLmin=q, best_Tmax_C=round(vals[0][0], 2), pump_mW=np.nan,
                             runner_up=vals[1][1], margin_C=round(vals[1][0] - vals[0][0], 2),
                             n_designs=len(vals)))
    fitted = {k: c for k, c in C.items() if c["fit"]}
    if verbose and len(fitted) < len(C):
        print(f"   (곡선 없음 = 유량 3개 미만: {[k[0] for k, c in C.items() if not c['fit']]})")
    # ② 같은 펌프 동력
    res = []
    for (d, _), c in fitted.items():
        f = c["fit"]; Q = in_range(f); W = pump_mW(f, Q)
        if W.min() <= pump <= W.max():
            q = float(np.interp(pump, W, Q)); res.append((T_of(f, q), d, q))
    res.sort()
    if verbose:
        print(f"② 펌프 동력 {pump} mW 에서: " + ("  ".join(f"{d} {t:.1f}℃(Q {q:.0f})" for t, d, q in res)
                                              if res else "범위 안의 형상 없음"))
    if res:
        rows.append(dict(hotspot=h, criterion="same_pump", condition=f"W={pump}mW", best_design=res[0][1],
                         best_Q_mLmin=round(res[0][2], 1), best_Tmax_C=round(res[0][0], 2), pump_mW=pump,
                         runner_up=res[1][1] if len(res) > 1 else "",
                         margin_C=round(res[1][0] - res[0][0], 2) if len(res) > 1 else np.nan, n_designs=len(res)))
    # ③ 목표 온도 최소 동력
    res = []
    for (d, _), c in fitted.items():
        f = c["fit"]; Q = in_range(f); T = T_of(f, Q); ok = T <= tlimit
        if ok.any():
            q = float(Q[ok].min()); res.append((pump_mW(f, q), d, q, T_of(f, q)))
        else:
            res.append((np.inf, d, np.nan, float(T.min())))
    res.sort()
    if verbose:
        print(f"③ 최고온도 ≤ {tlimit} ℃ 를 가장 적은 펌프 동력으로: " + "  ".join(
            f"{d} {w:.2f}mW(Q {q:.0f})" if np.isfinite(w) else f"{d} 불가(100에서 {t:.0f}℃)" for w, d, q, t in res))
    if res and np.isfinite(res[0][0]):
        rows.append(dict(hotspot=h, criterion="min_pump_for_T", condition=f"Tmax<={tlimit}",
                         best_design=res[0][1], best_Q_mLmin=round(res[0][2], 1), best_Tmax_C=round(res[0][3], 2),
                         pump_mW=round(res[0][0], 3), runner_up=res[1][1] if len(res) > 1 else "",
                         margin_C=np.nan, n_designs=sum(np.isfinite(r[0]) for r in res)))
    return rows


def all_hotspots(df, tlimit, pump):
    rows = []
    for h in sorted(df.hotspot.unique()):
        rows += rank(df, h, tlimit, pump, verbose=True)
    out = DATA / "ml" / "best_by_hotspot.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    # 곡선 표 (머신러닝 입력·검증용): 형상·핫스팟·유량 격자별 예측 Tmax, Δp, 펌프 동력
    cr = []
    for (d, h), c in curves(df).items():
        if not c["fit"]:
            continue
        f = c["fit"]
        for q in in_range(f)[::10]:
            cr.append(dict(design=d, hotspot=h, source=c["source"], Q_mLmin=q, Tmax_C=round(T_of(f, q), 2),
                           dp_Pa=round(dp_of(f, q), 1), pump_mW=round(pump_mW(f, q), 4),
                           n_exp=round(f["n"], 4)))
    pd.DataFrame(cr).to_csv(DATA / "ml" / "design_curves.csv", index=False)
    print(f"\n저장: {out.relative_to(DATA.parent)} ({len(rows)}행), data/ml/design_curves.csv ({len(cr)}행)")


def optimal_flows(df, tlimits=(90, 100, 110, 120)):
    """핫스팟(+형상)마다 목표 온도별 최소 유량·펌프 동력, 그리고 유량 단계별 '1 mW 더 쓸 때 몇 ℃ 내려가나'."""
    rows, marg = [], []
    for (d, h), c in sorted(curves(df).items()):
        g = c["pts"].sort_values("Q_mLmin")
        W = g.p * g.Q_mLmin / 6e7 * 1e3
        for i in range(1, len(g)):
            marg.append(dict(design=d, hotspot=h, source=c["source"],
                             Q_from=round(g.Q_mLmin.iloc[i-1]), Q_to=round(g.Q_mLmin.iloc[i]),
                             dT_drop_C=round(g["T"].iloc[i-1] - g["T"].iloc[i], 2),
                             extra_pump_mW=round(W.iloc[i] - W.iloc[i-1], 3),
                             C_per_mW=round((g["T"].iloc[i-1] - g["T"].iloc[i]) / (W.iloc[i] - W.iloc[i-1]), 2)))
        if not c["fit"]:
            continue
        f = c["fit"]; Q = in_range(f); T = T_of(f, Q)
        row = dict(design=d, hotspot=h, source=c["source"], n_exp=round(f["n"], 3),
                   Tmax_at_30=round(float(T[0]), 1), Tmax_at_100=round(float(T[-1]), 1) if f["qhi"] >= 99 else np.nan,
                   Q_max_run=round(f["qhi"]))
        for tl in tlimits:
            ok = T <= tl
            row[f"Qmin_for_{tl}C"] = round(float(Q[ok].min()), 1) if ok.any() else np.nan
            row[f"pump_mW_for_{tl}C"] = round(float(pump_mW(f, Q[ok].min())), 3) if ok.any() else np.nan
        rows.append(row)
    a = pd.DataFrame(rows); b = pd.DataFrame(marg)
    a.to_csv(DATA / "ml" / "optimal_flow_by_hotspot.csv", index=False)
    b.to_csv(DATA / "ml" / "marginal_cooling.csv", index=False)
    pd.set_option("display.width", 200)
    print("목표 온도별 필요한 최소 유량 [mL/min] (NaN = 돌린 유량 범위(Q_max_run까지) 안에서는 불가)")
    print(a[["design", "hotspot", "Q_max_run", "Tmax_at_30", "Tmax_at_100"] + [f"Qmin_for_{t}C" for t in tlimits]]
          .to_string(index=False))
    print("\n유량을 한 단계 올릴 때: 내려간 온도 / 더 든 펌프 동력 (℃ per mW, 클수록 올릴 가치 큼)")
    print(b.pivot_table(index=["design", "hotspot"], columns="Q_to", values="C_per_mW").round(1).to_string())
    print("\n저장: data/ml/optimal_flow_by_hotspot.csv, data/ml/marginal_cooling.csv")


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("coverage"); sp.add_parser("flows")
    p = sp.add_parser("best"); p.add_argument("--hotspot", required=True)
    p.add_argument("--tlimit", type=float, default=100.0); p.add_argument("--pump", type=float, default=2.0)
    p = sp.add_parser("all"); p.add_argument("--tlimit", type=float, default=100.0)
    p.add_argument("--pump", type=float, default=2.0)
    a = ap.parse_args(); df = load()
    if a.cmd == "flows":
        optimal_flows(df)
    elif a.cmd == "coverage":
        coverage(df)
    elif a.cmd == "best":
        rank(df, a.hotspot, a.tlimit, a.pump)
    else:
        all_hotspots(df, a.tlimit, a.pump)


if __name__ == "__main__":
    main()
