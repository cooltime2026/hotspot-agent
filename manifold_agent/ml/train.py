"""온도·압력 모델 학습 / 검증 / 예측.

  python ml/train.py validate                     # 데이터 일부를 빼고 맞혀 보는 시험 → 오차 표
  python ml/train.py fit                          # 전체 데이터로 학습 → ml/models.pkl
  python ml/train.py predict --design D0 --hotspot 1_4,2_4 --Q 60

모델
  압력  : 형상별 Δp = a·Q + b·Q²  (압력은 핫스팟과 무관함을 40개 Run에서 확인)
  온도  : 목표 = log(Tmax − 20).
          (1) 경향식  log ΔT = a(형상,핫스팟) + n(형상,핫스팟)·log Q   → 이미 돌린 핫스팟의 다른 유량만 예측 가능
          (2) GP      입력 = [log Q, 핫스팟 x, 핫스팟 y, 입구까지 거리, 형상] → 안 돌린 핫스팟 위치도 예측 시도
          (3) 기준선  같은 유량의 다른 핫스팟 평균 (모델이 이것보다 나아야 의미 있음)
"""
from __future__ import annotations
import argparse, pickle, sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, PORTS, T_IN, parse_cells, cells_centroid  # noqa: E402

from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel

warnings.filterwarnings("ignore")
MODEL_PATH = Path(__file__).resolve().parent / "models.pkl"


def load():
    p = DATA / "ml" / "thermal.csv"
    if not p.exists():
        sys.exit("먼저 python ml/dataset.py")
    return pd.read_csv(p)


# ---------------- 압력 ----------------
def fit_pressure(df):
    out = {}
    for d, g in df[df.augmented == "original"].groupby("design"):
        g = g.groupby("Q_mLmin").p_max_Pa.mean().reset_index()
        if len(g) < 3:                       # 유량 3개 미만이면 aQ+bQ² 못 믿음
            continue
        Q = g.Q_mLmin.values; A = np.c_[Q, Q ** 2]
        out[d] = np.linalg.lstsq(A, g.p_max_Pa.values, rcond=None)[0]
    return out


def pred_pressure(coef, Q):
    a, b = coef; return a * Q + b * Q ** 2


# ---------------- 온도: GP ----------------
DESIGN_ORDER = ["M0", "M1", "M3", "M4", "M5", "D0", "D1", "D2", "D4", "D5", "D6"]


def features(df):
    X = np.c_[np.log(df.Q_mLmin.values) - np.log(55), df.hs_x_mm.values / 12, df.hs_y_mm.values / 12,
              np.nan_to_num(df.hs_to_inlet_mm.values, nan=6.0) / 12]
    oh = np.array([[1.0 if d == k else 0.0 for k in DESIGN_ORDER] for d in df.design])
    return np.c_[X, oh]


def make_gp(n_dim):
    ls = np.r_[[1.0, 0.3, 0.3, 0.3], np.ones(n_dim - 4)]
    k = C(1.0, (1e-3, 1e2)) * RBF(ls, (1e-2, 1e2)) + WhiteKernel(1e-4, (1e-6, 1e-1))
    return GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=3, random_state=0)


def fit_gp(df):
    X = features(df); y = np.log(df.dT_C.values)
    return make_gp(X.shape[1]).fit(X, y)


def gp_predict(gp, df):
    m, s = gp.predict(features(df), return_std=True)
    return T_IN + np.exp(m), s          # s: log 기준 표준편차 (≈ 상대오차)


# ---------------- 온도: 경향식 ----------------
def fit_powerlaw(g):
    n, a = np.polyfit(np.log(g.Q_mLmin), np.log(g.dT_C), 1); return a, n


# ---------------- 검증 ----------------
def validate():
    df = load(); orig = df[df.augmented == "original"]
    print("=" * 70); print("압력: 유량 하나씩 빼고 맞히기 (형상별 aQ+bQ²)")
    for d, g in orig.groupby("design"):
        gq = g.groupby("Q_mLmin").p_max_Pa.mean()
        if len(gq) < 4:
            print(f"  {d}: 유량 {len(gq)}개뿐 → 시험 생략"); continue
        errs = []
        for q in gq.index:
            tr = gq.drop(q); A = np.c_[tr.index, tr.index ** 2]
            c = np.linalg.lstsq(A, tr.values, rcond=None)[0]
            errs.append((pred_pressure(c, q) - gq[q]) / gq[q] * 100)
        print(f"  {d}: 오차 % = {' '.join(f'{e:+.1f}' for e in errs)}  (최대 {np.max(np.abs(errs)):.1f}%)")

    print("=" * 70); print("온도 시험 A: 유량 하나 빼기 (같은 핫스팟의 다른 유량은 앎) — 경향식")
    eA = []
    for (d, h), g in orig.groupby(["design", "hotspot"]):
        if g.Q_mLmin.nunique() < 4:
            continue
        for i in g.index:
            a, n = fit_powerlaw(g.drop(i))
            p = T_IN + np.exp(a + n * np.log(g.Q_mLmin[i]))
            eA.append(p - g.Tmax_C[i])
    eA = np.array(eA)
    print(f"  Run {len(eA)}개: 평균 절대오차 {np.abs(eA).mean():.2f} ℃, 최대 {np.abs(eA).max():.2f} ℃")
    print("  ※ 30·100 mL/min (양 끝)을 빼면 바깥으로 늘려 맞히는 것이라 오차가 더 큼")

    print("=" * 70); print("온도 시험 B: 핫스팟 위치 하나를 통째로 빼기 (D0, 안 돌린 위치 예측) — GP vs 기준선")
    d0 = df[df.design == "D0"]
    rows = []
    for h in sorted(d0[d0.augmented == "original"].hotspot.unique()):
        te = d0[(d0.hotspot == h) & (d0.augmented == "original")]
        tr = df[~((df.design == "D0") & (df.hotspot == h))]
        gp = fit_gp(tr); p, s = gp_predict(gp, te)
        base = np.array([tr[(tr.design == "D0") & (np.isclose(tr.Q_mLmin, q))].Tmax_C.mean() for q in te.Q_mLmin])
        for q, t, pp, b, ss in zip(te.Q_mLmin, te.Tmax_C, p, base, s):
            rows.append(dict(hotspot=h, Q=q, true=t, gp=pp, base=b, gp_err=pp - t, base_err=b - t, gp_sd=ss))
    r = pd.DataFrame(rows)
    by = r.groupby("hotspot").agg(true30=("true", "first"), gp_mae=("gp_err", lambda x: np.abs(x).mean()),
                                   base_mae=("base_err", lambda x: np.abs(x).mean()),
                                   gp_bias=("gp_err", "mean"))
    print(by.round(1).to_string())
    print(f"  전체 평균 절대오차: GP {np.abs(r.gp_err).mean():.1f} ℃ / 기준선(다른 위치 평균) {np.abs(r.base_err).mean():.1f} ℃")
    inside = (np.abs(np.log(r.true - T_IN) - np.log(r.gp - T_IN)) <= 2 * r.gp_sd).mean()
    print(f"  GP가 스스로 말한 95% 범위 안에 실제값이 든 비율: {inside*100:.0f}%")
    out = DATA / "ml" / "validation_hotspot_out.csv"; r.round(3).to_csv(out, index=False)
    print("=" * 70); print("온도 시험 C: 형상 전용 GP로 위치 빼기 (좌우·상하 거울 짝도 같이 뺌)")
    from common import mirror_cells_x, mirror_cells_y, MIRROR_X, MIRROR_Y
    for d, sub in df.groupby("design"):
        hs = sorted(sub[sub.augmented == "original"].hotspot.unique())
        if len(hs) < 3:
            continue
        es = []
        for h in hs:
            c0 = parse_cells(h)               # 거울 짝(좌우·상하·둘 다)을 모두 빼야 정답이 새지 않음
            mh = set()                        # 그 형상에서 확인된 대칭만
            if d in MIRROR_X: mh.add("+".join(mirror_cells_x(c0)))
            if d in MIRROR_Y: mh.add("+".join(mirror_cells_y(c0)))
            if d in MIRROR_X and d in MIRROR_Y: mh.add("+".join(mirror_cells_x(mirror_cells_y(c0))))
            te = sub[(sub.hotspot == h) & (sub.augmented == "original")]
            tr = sub[(sub.hotspot != h) & (~sub.hotspot.isin(mh))]
            p, _ = gp_predict(fit_gp(tr), te); es.append((h, float(np.abs(p - te.Tmax_C.values).mean())))
        print(f"  {d}: " + ", ".join(f"{h} {e:.1f}" for h, e in es) + f"  → 평균 {np.mean([e for _, e in es]):.1f} ℃")
    print(f"  상세: {out.relative_to(DATA.parent)}")
    return r


def fit_all():
    df = load()
    gpd = {}
    for d, g in df.groupby("design"):
        if g[g.augmented == "original"].hotspot.nunique() >= 3:     # 위치 3곳 이상이면 형상 전용 GP (검증상 더 정확)
            gpd[d] = fit_gp(g)
    models = dict(pressure=fit_pressure(df), gp=fit_gp(df), gp_by_design=gpd,
                  powerlaw={(d, h): fit_powerlaw(g) for (d, h), g in
                            df.groupby(["design", "hotspot"]) if g.Q_mLmin.nunique() >= 3},
                  designs=sorted(df.design.unique()))
    pickle.dump(models, open(MODEL_PATH, "wb"))
    print("저장:", MODEL_PATH.relative_to(DATA.parent))
    print("  GP 커널:", models["gp"].kernel_)
    for d, c in models["pressure"].items():
        print(f"  압력 {d}: Δp = {c[0]:.3f}·Q + {c[1]:.4f}·Q²  [Pa, Q mL/min]")


def predict(design, hotspot, Q):
    if not MODEL_PATH.exists():
        fit_all()
    m = pickle.load(open(MODEL_PATH, "rb"))
    cells = parse_cells(hotspot); h = "+".join(cells); xc, yc = cells_centroid(cells)
    pr = PORTS.get(design, {})
    dist = min(np.hypot(xc - x, yc - y) for x, y in pr["inlets"]) if pr.get("inlets") else np.nan
    row = pd.DataFrame([dict(design=design, Q_mLmin=Q, hs_x_mm=xc, hs_y_mm=yc, hs_to_inlet_mm=dist)])
    print(f"{design}  핫스팟 {h}  Q = {Q} mL/min")
    if design not in m["designs"]:
        print("  이 형상은 학습 데이터에 없음 → 예측 불가 (SimScale Run 필요)"); return
    if (design, h) in m["powerlaw"]:
        a, n = m["powerlaw"][(design, h)]
        print(f"  경향식(이 핫스팟 실측 기반): Tmax ≈ {T_IN + np.exp(a + n*np.log(Q)):.1f} ℃")
    gp = m.get("gp_by_design", {}).get(design, m["gp"])
    print(f"  (사용 모델: {'형상 전용 GP' if gp is not m['gp'] else '공용 GP'})")
    p, s = gp_predict(gp, row)
    lo, hi = T_IN + (p[0] - T_IN) * np.exp(-2 * s[0]), T_IN + (p[0] - T_IN) * np.exp(2 * s[0])
    print(f"  GP: Tmax ≈ {p[0]:.1f} ℃  (95% 범위 {lo:.0f}~{hi:.0f} ℃)")
    if design in m["pressure"]:
        print(f"  압력강하 ≈ {pred_pressure(m['pressure'][design], Q):.0f} Pa")
    if not (30 <= Q <= 100):
        print("  주의: 30~100 mL/min 밖 → 데이터 범위 밖 외삽")


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("validate"); sp.add_parser("fit")
    p = sp.add_parser("predict"); p.add_argument("--design", required=True)
    p.add_argument("--hotspot", required=True); p.add_argument("--Q", type=float, required=True)
    a = ap.parse_args()
    {"validate": validate, "fit": fit_all}.get(a.cmd, lambda: predict(a.design, a.hotspot, a.Q))()


if __name__ == "__main__":
    main()
