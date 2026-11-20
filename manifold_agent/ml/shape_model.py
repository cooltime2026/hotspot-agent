"""모양 특징(shape_features)으로 학습 → 처음 보는 모양의 최고온도 예측.

  python ml/shape_model.py test     # 형상 하나를 통째로 빼고 맞히기(새 모양 예측 실력) + 위치 빼기 시험
  python ml/shape_model.py fit      # 전체 학습 → ml/shape_model.pkl

입력: shape_features.FEATS (형상 이름은 안 씀). 목표: log(Tmax − 20).
모델: GP(ARD) + 그래디언트부스팅 평균.
"""
from __future__ import annotations
import pickle, sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, T_IN  # noqa: E402
import shape_features as SF  # noqa: E402
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel
from sklearn.ensemble import GradientBoostingRegressor

warnings.filterwarnings("ignore")
PKL = Path(__file__).resolve().parent / "shape_model.pkl"
DES = ["D0", "D1", "M0", "M1", "M3", "M4"]


def table():
    df = pd.read_csv(DATA / "ml" / "thermal.csv"); df = df[df.design.isin(DES)].reset_index(drop=True)
    F = pd.DataFrame([SF.hotspot_features(SF.design_summary(d), h, q) for d, h, q in zip(df.design, df.hotspot, df.Q_mLmin)])
    return df, F


class Ens:
    def __init__(self):
        n = len(SF.FEATS)
        k = C(1.0, (1e-3, 1e2)) * RBF(np.ones(n), (1e-2, 1e3)) + WhiteKernel(1e-3, (1e-6, 1e-1))
        self.gp = GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=2, random_state=0)
        self.gb = GradientBoostingRegressor(n_estimators=400, max_depth=3, learning_rate=0.04, subsample=0.8, random_state=0)

    def fit(self, X, y):
        self.gp.fit(X, y); self.gb.fit(X, y); return self

    def predict(self, X, parts=False):
        a, b = self.gp.predict(X), self.gb.predict(X)
        return (a, b) if parts else (a + b) / 2


def test():
    df, F = table(); X = F[SF.FEATS].values; y = np.log(df.dT_C.values)
    print("시험 1: 형상 하나를 통째로 빼고 맞히기 (처음 보는 모양 = 새 매니폴드 예측 실력)")
    res = []
    for d in DES:
        tr = (df.design != d).values; te = (df.design == d).values & (df.augmented == "original").values
        m = Ens().fit(X[tr], y[tr]); p = T_IN + np.exp(m.predict(X[te]))
        e = np.abs(p - df.Tmax_C.values[te]); bias = np.mean(p - df.Tmax_C.values[te])
        # 기준선: 다른 형상들의 같은 유량 평균
        base = np.array([df[tr & np.isclose(df.Q_mLmin, q, atol=.5)].Tmax_C.mean() for q in df.Q_mLmin[te]])
        res.append((d, e.mean(), bias, np.abs(base - df.Tmax_C.values[te]).mean()))
        print(f"  {d}: 평균 오차 {e.mean():5.1f} ℃ (치우침 {bias:+.1f}), 기준선(다른 형상 평균) {res[-1][3]:5.1f} ℃")
    print(f"  전체 평균: 모델 {np.mean([r[1] for r in res]):.1f} ℃ / 기준선 {np.mean([r[3] for r in res]):.1f} ℃")
    print("시험 2: 핫스팟 위치 하나 빼기 (형상은 앎)")
    import benchmark as B
    errs = []
    for d in DES:
        for h in sorted(df[(df.design == d) & (df.augmented == "original")].hotspot.unique()):
            drop = {h} | B.mirrors(d, h)
            tr = ~((df.design == d) & df.hotspot.isin(drop)).values
            te = ((df.design == d) & (df.hotspot == h) & (df.augmented == "original")).values
            m = Ens().fit(X[tr], y[tr]); p = T_IN + np.exp(m.predict(X[te]))
            errs.append((d, np.abs(p - df.Tmax_C.values[te]).mean()))
    e = pd.DataFrame(errs, columns=["d", "e"])
    print("  " + ", ".join(f"{d} {v:.1f}" for d, v in e.groupby("d").e.mean().items()) + f"  → 평균 {e.e.mean():.1f} ℃")


def fit():
    df, F = table(); m = Ens().fit(F[SF.FEATS].values, np.log(df.dT_C.values))
    pickle.dump(m, open(PKL, "wb")); print("저장:", PKL.name, len(df), "행")


if __name__ == "__main__":
    {"test": test, "fit": fit}[sys.argv[1] if len(sys.argv) > 1 else "test"]()
