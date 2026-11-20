"""여러 머신러닝 모델을 같은 시험으로 비교 (안 돌린 핫스팟 위치 맞히기).

  python ml/benchmark.py            # 결과 표 → data/ml/benchmark.csv

시험 방법 (정직한 시험)
  형상마다 핫스팟 위치 하나를 통째로 빼고(그 형상에서 확인된 대칭 짝도 같이 뺌) 나머지로 학습 →
  뺀 위치의 모든 유량 최고온도를 예측 → 평균 절대오차 [℃].
  다른 형상 데이터는 학습에 써도 됨(공용 모델이 형상 사이에서 배우는지 보려고).

입력 특징 (핫스팟 칸마다 계산해서 두 칸 중 '나쁜 쪽'과 평균을 씀)
  log Q, 칸 중심 x·y, 가장 가까운 입구·출구까지 거리, 판 가장자리까지 거리, 두 칸 사이 거리,
  형상(원핫). 목표 = log(Tmax − 20).
"""
from __future__ import annotations
import sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, PORTS, T_IN, MIRROR_X, MIRROR_Y, mirror_cells_x, mirror_cells_y, parse_cells  # noqa: E402
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

warnings.filterwarnings("ignore")
DES = ["D0", "D1", "M0", "M1", "M3", "M4"]


def cell_xy(c):
    r, k = map(int, c.split("_")); return (k - 0.5) * 3, (r - 0.5) * 3


def geo_features(design, hotspot):
    cells = parse_cells(hotspot); P = PORTS[design]
    f = []
    for c in cells:
        x, y = cell_xy(c)
        di = min(np.hypot(x - a, y - b) for a, b in P["inlets"])
        do = min(np.hypot(x - a, y - b) for a, b in P["outlets"])
        de = min(x, 12 - x, y, 12 - y)
        f.append((x, y, di, do, de))
    f = np.array(f)
    sep = np.hypot(*(f[0, :2] - f[1, :2])) if len(f) > 1 else 0.0
    return dict(x_mean=f[:, 0].mean() / 12, y_mean=f[:, 1].mean() / 12,
                din_min=f[:, 2].min() / 12, din_max=f[:, 2].max() / 12,
                dout_min=f[:, 3].min() / 12, dout_max=f[:, 3].max() / 12,
                edge_min=f[:, 4].min() / 12, sep=sep / 12)


GEO = ["x_mean", "y_mean", "din_min", "din_max", "dout_min", "dout_max", "edge_min", "sep"]


def build(df):
    g = pd.DataFrame([geo_features(d, h) for d, h in zip(df.design, df.hotspot)], index=df.index)
    X = pd.concat([pd.DataFrame({"logQ": np.log(df.Q_mLmin / 55)}, index=df.index), g], axis=1)
    for d in DES:
        X["is_" + d] = (df.design == d).astype(float)
    return X


def mirrors(d, h):
    c = parse_cells(h); s = set()
    if d in MIRROR_X: s.add("+".join(mirror_cells_x(c)))
    if d in MIRROR_Y: s.add("+".join(mirror_cells_y(c)))
    if d in MIRROR_X and d in MIRROR_Y: s.add("+".join(mirror_cells_x(mirror_cells_y(c))))
    return s


def gp(n):
    k = C(1.0, (1e-3, 1e2)) * RBF(np.ones(n), (1e-2, 1e2)) + WhiteKernel(1e-3, (1e-6, 1e-1))
    return GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=2, random_state=0)


# 모델: (이름, 같은 형상만 쓰는지, 특징 열, 만드는 함수)
MODELS = [
    ("GP 형상별 (위치 x,y만)", True, ["logQ", "x_mean", "y_mean"], lambda n: gp(n)),
    ("GP 형상별 (입출구 거리 포함)", True, ["logQ"] + GEO, lambda n: gp(n)),
    ("GP 공용 (모든 형상 + 형상 표시)", False, ["logQ"] + GEO + ["is_" + d for d in DES], lambda n: gp(n)),
    ("Ridge 공용 (선형)", False, ["logQ"] + GEO + ["is_" + d for d in DES], lambda n: Ridge(1e-2)),
    ("랜덤포레스트 공용", False, ["logQ"] + GEO + ["is_" + d for d in DES], lambda n: RandomForestRegressor(300, min_samples_leaf=2, random_state=0)),
    ("그래디언트부스팅 공용", False, ["logQ"] + GEO + ["is_" + d for d in DES], lambda n: GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, random_state=0)),
]


ENSEMBLES = {
    "앙상블 (부스팅+GP공용+GP형상별거리)": ["그래디언트부스팅 공용", "GP 공용 (모든 형상 + 형상 표시)", "GP 형상별 (입출구 거리 포함)"],
    "앙상블 (부스팅+GP공용)": ["그래디언트부스팅 공용", "GP 공용 (모든 형상 + 형상 표시)"],
    "앙상블 (5개 전부, Ridge 제외)": ["그래디언트부스팅 공용", "GP 공용 (모든 형상 + 형상 표시)", "GP 형상별 (입출구 거리 포함)",
                              "GP 형상별 (위치 x,y만)", "랜덤포레스트 공용"],
}


def baseline(tr, te):
    """기준선: 같은 형상·같은 유량의 다른 위치 평균 (모델이 이것보다 나아야 의미 있음)"""
    out = []
    for _, r in te.iterrows():
        s = tr[(tr.design == r.design) & np.isclose(tr.Q_mLmin, r.Q_mLmin, atol=0.5)]
        out.append(s.Tmax_C.mean() if len(s) else np.nan)
    return np.array(out)


def run():
    df = pd.read_csv(DATA / "ml" / "thermal.csv")
    df = df[df.design.isin(DES)].reset_index(drop=True)
    X = build(df); y = np.log(df.dT_C.values)
    rows = []
    for d in DES:
        orig = df[(df.design == d) & (df.augmented == "original")]
        for h in sorted(orig.hotspot.unique()):
            drop = {h} | mirrors(d, h)
            test = (df.design == d) & (df.hotspot == h) & (df.augmented == "original")
            train_all = ~((df.design == d) & df.hotspot.isin(drop))
            te = df[test]
            rec = dict(design=d, hotspot=h, n_test=int(test.sum()))
            rec["기준선(같은 형상 다른 위치 평균)"] = np.nanmean(np.abs(baseline(df[train_all & (df.design == d)], te) - te.Tmax_C.values))
            preds = {}
            for name, own, cols, mk in MODELS:
                tr = train_all & ((df.design == d) if own else True)
                if tr.sum() < 5 or (own and df[tr].hotspot.nunique() < 2):
                    rec[name] = np.nan; continue
                m = mk(len(cols)).fit(X.loc[tr, cols].values, y[tr.values])
                lp = m.predict(X.loc[test, cols].values); preds[name] = lp
                p = T_IN + np.exp(lp)
                rec[name] = float(np.mean(np.abs(p - te.Tmax_C.values)))
            for ename, members in ENSEMBLES.items():
                got = [preds[k] for k in members if k in preds]
                if got:
                    p = T_IN + np.exp(np.mean(got, axis=0))
                    rec[ename] = float(np.mean(np.abs(p - te.Tmax_C.values)))
            rows.append(rec)
    r = pd.DataFrame(rows)
    r.round(2).to_csv(DATA / "ml" / "benchmark.csv", index=False)
    cols = [c for c in r.columns if c not in ("design", "hotspot", "n_test")]
    print("안 돌린 핫스팟 위치 맞히기: 평균 절대오차 [℃] (형상별 평균, 낮을수록 좋음)")
    print(r.groupby("design")[cols].mean().round(1).T.to_string())
    print("\n전체 평균:")
    print(r[cols].mean().round(1).sort_values().to_string())
    return r


if __name__ == "__main__":
    run()
