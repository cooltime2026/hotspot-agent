"""띠(빗살)형 매니폴드 가족 전용 모델 — 숫자 6개 + 핫스팟 + 유량 → 최고온도, 압력.

  python ml/family_model.py test     # 형상 하나를 통째로 빼고 맞히기 (새 모양 예측 실력)
  python ml/family_model.py fit      # 전체 학습 → ml/family_model.pkl

데이터: A1~A8, B1~B8, C1~C4 (+ 선택: M1·M3 근사 변수, IoU 0.89/0.69).
가족은 위아래 대칭(y → 12−y)이 정확히 성립(마스크 IoU 1.0, 포트·발열 대칭) →
  핫스팟 행 r → 5−r, yf → 12−yf 로 뒤집은 Run을 같이 학습(augmented=mirror_y).
온도 입력: shape_features 물리 특징(마스크에서 계산) + 띠 변수 + 핫스팟과 띠 모음 위치 관계.
온도 목표: log(Tmax − 20).  모델: GP(ARD) + 그래디언트부스팅 평균 (shape_model.Ens).
압력: 형상마다 pmax = k·(Q/55)^m. log k 를 띠 변수로 GP 회귀, m은 전체 공통(데이터에서 추정).
"""
from __future__ import annotations
import json, pickle, sys, warnings
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "ml"))
from common import DATA, T_IN  # noqa: E402
import shape_features as SF  # noqa: E402
from geometry import param_manifold as PM  # noqa: E402
from geometry.make_round1 import KNOWN  # noqa: E402
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel
from sklearn.ensemble import GradientBoostingRegressor

warnings.filterwarnings("ignore")
PKL = ROOT / "ml" / "family_model.pkl"
KEYS = ["n", "yf", "s", "xf", "b", "wf"]


def family_params(with_m=True):
    P = {}
    for f in ["out/step_param/round1.json", "out/step_param_v3/round2.json", "out/step_param_v3/round3.json"]:
        for k, v in json.loads((ROOT / f).read_text()).items():
            P[k] = {kk: v[kk] for kk in KEYS}
    if with_m:
        P["M1"], P["M3"] = dict(KNOWN[0]), dict(KNOWN[1])
    return P


@lru_cache(None)
def _summary(key):
    p = dict(key)
    return SF.shape_summary(PM.openings(p), (1.5, 10.5))


def mirror_hs(h):
    return "+".join(sorted(f"{5 - int(c.split('_')[0])}_{c.split('_')[1]}" for c in h.split("+")))


def mirror_p(p):
    return {**p, "yf": round(12 - p["yf"], 4)}


TFEATS = SF.FEATS + ["n", "s_eff", "wf", "b", "dy_hs", "dx_hs"]


def features(p, hotspot, Q):
    r = PM.resolve(p)
    f = SF.hotspot_features(_summary(tuple(sorted(p.items()))), hotspot, Q)
    cells = hotspot.split("+")
    hy = np.mean([(int(c.split("_")[0]) - .5) * 3 for c in cells]); hx = np.mean([(int(c.split("_")[1]) - .5) * 3 for c in cells])
    f.update(n=r["n"], s_eff=np.log1p(r["s_eff"]), wf=r["wf"], b=r["b"],
             dy_hs=abs(hy - r["yf"]) / 12 * min(r["s_eff"], 1.0), dx_hs=abs(hx - r["xf"]) / 12 * abs(r["b"]))
    return f


def table(with_m=True):
    P = family_params(with_m)
    df = pd.read_csv(DATA / "direct_runs.csv")
    df = df[df.design.isin(P)].copy()
    df["hotspot"] = df.heat.str.extract(r"at ([\d_,]+)")[0].str.replace(",", "+")
    df["hotspot"] = df.hotspot.apply(lambda h: "+".join(sorted(h.split("+"))))
    df["Q"] = df.total_flow_mL_min.astype(float)
    rows = []
    for _, r in df.iterrows():
        p = P[r.design]
        rows.append(dict(design=r.design, aug="original", hotspot=r.hotspot, Q=r.Q, v=r.inlet_velocity_m_s,
                         Tmax=r.Tmax_bottom_C, pmax=r.p_max_Pa, **{f"p_{k}": p[k] for k in KEYS}, **features(p, r.hotspot, r.Q)))
        mp, mh = mirror_p(p), mirror_hs(r.hotspot)
        rows.append(dict(design=r.design, aug="mirror_y", hotspot=mh, Q=r.Q, v=r.inlet_velocity_m_s,
                         Tmax=r.Tmax_bottom_C, pmax=r.p_max_Pa, **{f"p_{k}": mp[k] for k in KEYS}, **features(mp, mh, r.Q)))
    return pd.DataFrame(rows)


class Ens:
    def __init__(self, n):
        k = C(1.0, (1e-3, 1e2)) * RBF(np.ones(n), (1e-2, 1e3)) + WhiteKernel(1e-3, (1e-6, 1e-1))
        self.gp = GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=2, random_state=0)
        self.gb = GradientBoostingRegressor(n_estimators=400, max_depth=3, learning_rate=0.04, subsample=0.8, random_state=0)

    def fit(self, X, y):
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        Z = (X - self.mu) / self.sd
        self.gp.fit(Z, y); self.gb.fit(Z, y); return self

    def predict(self, X, std=False):
        Z = (X - self.mu) / self.sd
        a, s = self.gp.predict(Z, return_std=True); b = self.gb.predict(Z)
        m = (a + b) / 2
        # 불확실성 = GP 표준편차 와 두 모델 차이 중 큰 것
        return (m, np.maximum(s, np.abs(a - b) / 2)) if std else m


PFEATS = ["n", "s_eff", "wf", "b", "logG"]


class Pressure:
    """pmax = k·(Q/55)^m. m 공통, log k = GP(띠 변수)."""
    def fit(self, df):
        o = df[df.aug == "original"]
        g = o.groupby(["design", "Q"]).pmax.mean().unstack()
        both = g.dropna()
        self.m = float(np.mean(np.log(both[100.0] / both[55.0]) / np.log(100 / 55))) if 100.0 in g and len(both) else 1.87
        k = (o.pmax / (o.Q / 55) ** self.m).groupby(o.design).mean()
        X = o.groupby("design")[PFEATS].first().loc[k.index].values
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        kern = C(1.0) * RBF(np.ones(len(PFEATS)), (1e-2, 1e3)) + WhiteKernel(1e-3, (1e-6, 1e-1))
        self.gp = GaussianProcessRegressor(kern, normalize_y=True, n_restarts_optimizer=3, random_state=0)
        self.gp.fit((X - self.mu) / self.sd, np.log(k.values)); return self

    def predict(self, feats, Q, std=False):
        X = np.array([[feats[c] for c in PFEATS]])
        lk, s = self.gp.predict((X - self.mu) / self.sd, return_std=True)
        p = float(np.exp(lk[0]) * (Q / 55) ** self.m)
        return (p, float(s[0])) if std else p


def _test(with_m):
    df = table(with_m)
    X = df[TFEATS].values; y = np.log(df.Tmax.values - T_IN)
    fam = [d for d in df.design.unique() if d[0] in "ABC"]
    res = []
    for d in fam:
        tr = (df.design != d).values; te = ((df.design == d) & (df.aug == "original")).values
        m = Ens(len(TFEATS)).fit(X[tr], y[tr]); pr, sd = m.predict(X[te], std=True); p = T_IN + np.exp(pr)
        t = df.Tmax.values[te]
        # 기준선: 다른 가족 형상의 같은 핫스팟·유량 평균 (없으면 같은 유량 평균)
        o = df[tr & (df.aug == "original").values]
        base = []
        for h, q in zip(df.hotspot[te], df.Q[te]):
            s = o[(o.hotspot == h) & np.isclose(o.Q, q)]
            base.append((s if len(s) else o[np.isclose(o.Q, q)]).Tmax.mean())
        lo, hi = T_IN + np.exp(pr - 2 * sd), T_IN + np.exp(pr + 2 * sd)
        pm = Pressure().fit(df[tr]); pp = np.array([pm.predict(df[te].iloc[i], q) for i, q in enumerate(df.Q[te])])
        res.append(dict(d=d, n=te.sum(), mae=np.abs(p - t).mean(), bias=(p - t).mean(), base=np.abs(np.array(base) - t).mean(),
                        cover=np.mean((t >= lo) & (t <= hi)), p_err=np.mean(np.abs(pp / df.pmax.values[te] - 1)) * 100))
    r = pd.DataFrame(res)
    for _, x in r.iterrows():
        print(f"  {x.d:3s} ({x.n} Run): 온도 오차 {x.mae:5.1f} ℃ (치우침 {x.bias:+5.1f}), 기준선 {x.base:5.1f} ℃, "
              f"±2σ 안에 든 비율 {x.cover*100:3.0f}%, 압력 오차 {x.p_err:4.1f}%")
    w = r.n / r.n.sum()
    print(f"  ▶ 전체(Run 가중): 온도 오차 {np.sum(w*r.mae):.1f} ℃ / 기준선 {np.sum(w*r.base):.1f} ℃ / ±2σ 포함 {np.sum(w*r.cover)*100:.0f}% / 압력 오차 {np.sum(w*r.p_err):.1f}%")
    return r


def test():
    for wm in (False, True):
        print(f"\n시험: 형상 하나를 통째로 빼고 맞히기 — M1·M3 근사 {'포함' if wm else '제외'} (대칭 뒤집기 포함 학습)")
        _test(wm)


def fit(with_m=True):
    df = table(with_m)
    X = df[TFEATS].values; y = np.log(df.Tmax.values - T_IN)
    m = Ens(len(TFEATS)).fit(X, y); pm = Pressure().fit(df)
    pickle.dump(dict(T=m, P=pm, with_m=with_m, n_rows=len(df)), open(PKL, "wb"))
    print("저장:", PKL.name, len(df), "행 (원본", int((df.aug == 'original').sum()), ")  압력 지수 m =", round(pm.m, 3))


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "test"
    {"test": test, "fit": lambda: fit(True), "fit_nom": lambda: fit(False)}[a]()
