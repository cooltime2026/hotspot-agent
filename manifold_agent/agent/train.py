"""신경망 학습 + 정직한 성능 리포트.

python -m agent.train --data data/synthetic --out out/model_synthetic
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from . import config as C
from .superpose import Library
from .datagen import build, features, flux_maps, labels, to_target, from_target

NM = len(C.MANIFOLDS)


def report(y_true, y_pred):
    tt, tp = y_true[:, :NM], y_pred[:, :NM]
    rel = np.abs(tt - tp) / np.maximum(tt, 1e-6) * 100
    big = tt >= 10
    return {
        "Tmax상승_MAE_K": float(np.abs(tt - tp).mean()),
        "Tmax상승_최대절대오차_K": float(np.abs(tt - tp).max()),
        "Tmax상승_평균오차_%": float(rel.mean()),
        "Tmax상승_95%오차_%": float(np.percentile(rel, 95)),
        "Tmax상승_최대오차_%": float(rel.max()),
        "상승10K이상_최대오차_%": float(rel[big].max()) if big.any() else None,
        "추천1순위_일치율_%": float((tt.argmin(1) == tp.argmin(1)).mean() * 100),
        "샘플수": int(len(tt)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    lib = Library(a.data)

    t0 = time.time(); X, Y = build(lib)
    print(f"학습 데이터 {len(X):,}개 생성 ({time.time()-t0:.1f}s)")
    Xtr, Xte, Ytr, Yte = train_test_split(features(X), Y, test_size=0.15, random_state=0)
    ys = StandardScaler().fit(to_target(Ytr))
    net = MLPRegressor(hidden_layer_sizes=(256, 256, 128), learning_rate_init=1e-3, batch_size=256,
                       max_iter=400, early_stopping=True, n_iter_no_change=40, tol=1e-6, random_state=0)
    t0 = time.time(); net.fit(Xtr, ys.transform(to_target(Ytr))); dt = time.time() - t0
    print(f"학습 완료 {dt:.0f}s, epoch {net.n_iter_}")
    pred = lambda Z: from_target(ys.inverse_transform(net.predict(Z)))

    rep = {"학습시간_s": round(dt, 1), "epochs": net.n_iter_,
           "테스트_학습유량(5수준)": report(Yte, pred(Xte))}
    # 학습에 없던 중간 유량: 신경망 vs 중첩+유량보간 (5수준 사이를 log 선형보간한 값)
    F = flux_maps(np.random.default_rng(99), draws_per_combo=0, n_random=2000)
    for q in [35, 48, 65, 88]:
        Xq = features(np.c_[F, np.full(len(F), q)])
        rep[f"중간유량_{q}mLmin_vs_중첩보간"] = report(labels(lib, q, F), pred(Xq))
    joblib.dump({"net": net, "yscaler": ys, "data": str(a.data)}, out / "model.joblib")
    (out / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    np.save(out / "loss_curve.npy", np.array(net.loss_curve_))
    print(json.dumps(rep, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
