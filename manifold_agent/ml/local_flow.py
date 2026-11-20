"""새 가족 L(국소 개방) — 온도 예측(두 방법) + 유량 자동 선택.

  python ml/local_flow.py                       # L1~L4, 목표 85/100/120 ℃ 모두
  python ml/local_flow.py --shape L1 --tlimit 80

예측 (out/step_local/L_predictions.csv 와 같은 방법, 유량은 55~100 mL/min 1 단위):
  방법 1 '물 몫 모델': 띠 데이터로 학습한 log(Tmax−20) = 핫스팟위치(+×유량) + 유량 + log(핫스팟 칸 물 몫) + wf + dy_hs.
  방법 2 '물리 비례': 띠15 기준 온도 × (물 몫 배율)^(핫스팟별 유량 기울기).
     기준 온도: 실측(B1·B4 띠15) 55·100 이 있으면 그 둘을 멱법칙으로 이음, 없으면 v2b 예측.
유량 선택: '안전' = 두 방법 중 더 뜨거운 쪽이 목표 이하가 되는 가장 적은 유량 (펌프 동력 최소).
  둘 중 하나만 지키면 그 방법 기준 유량도 같이 보여 줌. 100 mL/min 으로도 못 지키면 '못 지킴'.
압력: 띠15 압력 × (전체 전도도 비), 유량 지수 m (family_model).
※ L 가족은 SimScale 데이터가 없음 → 모두 추정. L1 검증 후 다시 학습할 것.
"""
from __future__ import annotations
import argparse, json, pickle, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "ml"))
import family_model as FM  # noqa: E402
import shape_features as SF  # noqa: E402
from geometry import local_manifold as LM, param_manifold as PM  # noqa: E402
from sklearn.linear_model import RidgeCV  # noqa: E402

QS = np.arange(55.0, 100.01, 1.0)
MEAS15 = {"2_2+3_2": (np.mean([83.68, 85.43]), np.mean([68.14, 68.44])),   # B1·B4 (띠 15) 55 / 100 mL/min
          "1_3+1_4": (132.7, 115.8)}                                          # B4


def flow_share_model():
    df = FM.table(False)
    feats, inter = ["log_flow_mean", "wf", "dy_hs"], ["log_flow_mean"]

    def X(rows):
        d = pd.DataFrame(rows); H = np.array([FM.hs_pos(h) for h in d.hotspot]); lq = np.log(d.Q.values / 55)[:, None]
        return np.hstack([H, lq, H * lq] + [d[[f]].values for f in feats] + [H * d[[f]].values for f in inter])
    m = RidgeCV(alphas=np.logspace(-3, 2, 20)).fit(X(df), np.log(df.Tmax.values - 20))
    o = df[df.aug == "original"]
    g = o.pivot_table(index=["design", "hotspot"], columns="Q", values="Tmax").dropna()
    sl = np.log((g[100.0] - 20) / (g[55.0] - 20)) / np.log(100 / 55)
    return m, X, sl.groupby(level=1).mean().to_dict(), float(sl.mean())


def predict_curves(p, M, mfs, X, slopes, slope_all):
    hs = p["aimed_hotspot"] if "aimed_hotspot" in p else p["hotspot"]
    base = {k: p[k] for k in LM.BASE}
    sl = SF.shape_summary(LM.openings(p), (1.5, 10.5)); sb = SF.shape_summary(PM.openings(base), (1.5, 10.5))
    fl = SF.hotspot_features(sl, hs, 55); fb = SF.hotspot_features(sb, hs, 55)
    ratio = float(np.exp(fl["log_flow_mean"] - fb["log_flow_mean"])); Gr = sb["G"] / sl["G"]
    rows = [dict(hotspot=hs, Q=Q, log_flow_mean=fl["log_flow_mean"], wf=p["wf"], dy_hs=0.0) for Q in QS]
    T1 = 20 + np.exp(mfs.predict(X(rows)))
    s = slopes.get(hs, slope_all)
    if hs in MEAS15:
        t55, t100 = MEAS15[hs]; k = np.log((t100 - 20) / (t55 - 20)) / np.log(100 / 55)
        Tb = 20 + (t55 - 20) * (QS / 55) ** k
    else:
        fbase = FM.features(base, hs, 55)
        Tb = 20 + np.exp(M["T"].predict([dict(hotspot=hs, Q=Q, **{c: fbase[c] for c in FM.SFEATS}) for Q in QS]))
    T2 = 20 + (Tb - 20) * ratio ** s
    fbase = FM.features(base, hs, 55)
    dp55 = M["P"].predict({**fbase, "s_eff": np.log1p(PM.resolve(base)["s_eff"])}, 55.0) * Gr
    dp = dp55 * (QS / 55) ** M["P"].m
    return hs, ratio, T1, T2, dp


def pick(QS_, T, dp, tl):
    ok = T <= tl
    if not ok.any():
        return None
    i = int(np.argmax(ok))            # 가장 적은 유량 (T 는 유량에 따라 감소)
    return dict(Q=float(QS_[i]), v=round(QS_[i] / 55 * 0.912, 3), T=round(float(T[i]), 1), dp=round(float(dp[i])),
                W=round(float(dp[i] * QS_[i] / 60e6 * 1e3), 2))


def main(shapes, targets):
    M = pickle.load(open(FM.PKL, "rb")); mfs, X, slopes, s_all = flow_share_model()
    R = json.loads((ROOT / "out/step_local/round_L.json").read_text())
    out = []
    for name in shapes:
        hs, ratio, T1, T2, dp = predict_curves(R[name], M, mfs, X, slopes, s_all)
        Ts = np.maximum(T1, T2)
        print(f"{name} (핫스팟 {hs}, 핫스팟 칸 물 ×{ratio:.2f}): 55 mL → 모델 {T1[0]:.1f} / 물리 {T2[0]:.1f} ℃, 100 mL → {T1[-1]:.1f} / {T2[-1]:.1f} ℃")
        for tl in targets:
            safe, a, b = pick(QS, Ts, dp, tl), pick(QS, T1, dp, tl), pick(QS, T2, dp, tl)
            fmt = lambda r: f"{r['Q']:.0f} mL/min (v {r['v']}) → {r['T']} ℃, {r['dp']} Pa, {r['W']} mW" if r else "못 지킴 (100 mL/min 으로도)"
            print(f"   목표 {tl:.0f} ℃: 안전(두 방법 다) {fmt(safe)} | 모델만 {fmt(a)} | 물리만 {fmt(b)}")
            out.append(dict(shape=name, hotspot=hs, target_C=tl, flow_share_ratio=round(ratio, 2),
                            **{f"safe_{k}": v for k, v in (safe or {}).items()},
                            **{f"model_{k}": v for k, v in (a or {}).items()}, **{f"physics_{k}": v for k, v in (b or {}).items()}))
    pd.DataFrame(out).to_csv(ROOT / "out/step_local/L_flow_choice.csv", index=False)
    print("저장: out/step_local/L_flow_choice.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shape", nargs="+", default=["L1", "L2", "L3", "L4"])
    ap.add_argument("--tlimit", type=float, nargs="+", default=[85.0, 100.0, 120.0])
    a = ap.parse_args(); main(a.shape, a.tlimit)
