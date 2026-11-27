"""매니폴드 '고르기' 전용 머신러닝 — 모양 그림(관통층 마스크)에서 특징을 뽑아 후보 순위를 매긴다.

  python ml/select_model.py test    # 모양 하나를 통째로 빼고 맞히기 → 처음 보는 모양 순위 실력
  python ml/select_model.py fit     # 전체 학습 → ml/select_model.json (웹 HTML 이 그대로 읽음)

쓰임: HTML v17 의 자동 설계 후보(바람개비·대역·V자·흡입형·직상부 + 머신러닝 띠)를 이 모델 점수로 줄 세워 고른다.
      온도·압력 계산은 HTML 계산식이 한다. 이 모델의 숫자는 '순위'에만 쓴다.
데이터: SimScale 227 Run 중 마스크가 있는 모양 (띠 가족 A·B·C 20개 + M0·M1·M3·M4·D0·D1). L1 은 1 Run 이라 뺌.
입력: 핫스팟 위치 숫자 4개(family_model.hs_pos) + log 유량 + 위치×유량 + 모양 특징(shape_features) — 형상 이름은 안 씀.
목표: log(Tmax − 20). 모델: 릿지(선형) — 자바스크립트로 그대로 옮기기 쉬움.
"""
from __future__ import annotations
import json, sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml")); sys.path.insert(0, str(ROOT))
import shape_features as SF  # noqa: E402
from family_model import hs_pos  # noqa: E402
from geometry import param_manifold as PM  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

warnings.filterwarnings("ignore")
OUT = ROOT / "ml" / "select_model.json"
PRESET = ["M0", "M1", "M3", "M4", "D0", "D1"]
SFEATS = ["log_flow_worst", "log_flow_mean", "dead_max", "dfresh_max", "dfresh_mean", "path_max", "logG", "dead_all", "log_flow_min_all"]
CELLS = [f"{r}_{c}" for r in range(1, 5) for c in range(1, 5)]


def plate_features(s):
    """판 전체(16칸): 죽은 구간 평균, 가장 물이 적은 칸 — 핫스팟 밖이 뜨거워지는 모양을 알아보려고 (2026-11-27 추가)"""
    cf = [SF.cell_features(s, c) for c in CELLS]
    return dict(dead_all=float(np.mean([f["dead"] for f in cf])), log_flow_min_all=float(np.log(min(f["flow_loc"] for f in cf) + 1e-4)))


def summary_of(design):
    if design in PRESET:
        return SF.design_summary(design)
    p = json.load(open(ROOT / f"out/step_param_v3/{design}.json"))["params"]
    return SF.shape_summary(PM.openings({k: p[k] for k in ["n", "yf", "s", "xf", "b", "wf"]}))


def table():
    d = pd.read_csv(ROOT / "data/ml/thermal.csv")
    d = d[(d.augmented == "original") & (d.design != "L1")].reset_index(drop=True)
    S = {k: summary_of(k) for k in d.design.unique()}
    F = pd.DataFrame([{**SF.hotspot_features(S[k], h, q), **plate_features(S[k])} for k, h, q in zip(d.design, d.hotspot, d.Q_mLmin)])
    return d, F


def X_of(hot, Q, F):
    H = np.array([hs_pos(h) for h in hot]); lq = np.log(np.asarray(Q) / 55)[:, None]
    return np.hstack([H, lq, H * lq, F[SFEATS].values])


def fit_model(X, y, alpha=1.0):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    m = Ridge(alpha=alpha).fit((X - mu) / sd, y)
    return dict(mu=mu, sd=sd, m=m)


def predict(M, X):
    return M["m"].predict((X - M["mu"]) / M["sd"])


def test(alpha=1.0):
    d, F = table(); X = X_of(d.hotspot, d.Q_mLmin, F); y = np.log(d.Tmax_C - 20)
    pred = np.zeros(len(d))
    for k in d.design.unique():
        tr = (d.design != k).values
        pred[~tr] = predict(fit_model(X[tr], y[tr], alpha), X[~tr])
    d["pred"] = 20 + np.exp(pred)
    fam = d.design.where(d.design.isin(PRESET), "띠가족")
    print(f"시험: 모양 하나를 통째로 빼고 맞히기 (릿지 alpha={alpha}, {len(d)} Run, 모양 {d.design.nunique()}개)")
    print((d.assign(err=(d.pred - d.Tmax_C).abs(), bias=d.pred - d.Tmax_C, fam=fam)
           .groupby("fam")[["err", "bias"]].mean().round(1).to_string()))
    # 순위 실력: 같은 핫스팟·유량에서 모양 3개 이상
    rows = []
    for (h, q), g in d.groupby(["hotspot", d.Q_mLmin.round()]):
        if g.design.nunique() < 3:
            continue
        rho = spearmanr(g.pred, g.Tmax_C)[0]
        pick = g.loc[g.pred.idxmin()]; best = g.Tmax_C.min()
        rows.append(dict(hotspot=h, Q=q, n=len(g), rho=rho, regret=pick.Tmax_C - best, rand=g.Tmax_C.mean() - best,
                         pick=pick.design, best=g.loc[g.Tmax_C.idxmin(), "design"]))
    r = pd.DataFrame(rows)
    print(f"\n순위 시험 ({len(r)} 묶음: 같은 핫스팟·유량에서 모양 3개 이상)")
    print(f"  순위 상관 평균 {r.rho.mean():.2f}  /  고른 모양과 실제 최선의 차이 평균 {r.regret.mean():.1f} ℃ (아무거나 고르면 {r.rand.mean():.1f} ℃)")
    print(r.round(2).to_string(index=False))
    return d, r


def fit(alpha=1.0):
    d, F = table(); X = X_of(d.hotspot, d.Q_mLmin, F); y = np.log(d.Tmax_C - 20)
    M = fit_model(X, y, alpha)
    js = dict(note="ml/select_model.py — 모양 특징 릿지. 순위 전용.", alpha=alpha, sfeats=SFEATS,
              mu=M["mu"].tolist(), sd=M["sd"].tolist(), xmin=X.min(0).tolist(), xmax=X.max(0).tolist(), coef=M["m"].coef_.tolist(), intercept=float(M["m"].intercept_),
              n_runs=len(d), designs=sorted(d.design.unique().tolist()))
    OUT.write_text(json.dumps(js, ensure_ascii=False, indent=1))
    print("저장:", OUT, len(d), "Run")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    a = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    test(a) if cmd == "test" else fit(a)
