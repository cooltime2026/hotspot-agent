"""모든 핫스팟 경우의 수 한 번에 자동설계 (모양 후보를 한 번만 만들어 재사용).

  python ml/auto_design_all.py                 # → out/auto_design_all/
  python ml/auto_design_all.py --pool 1500

경우의 수: 2칸 핫스팟 C(16,2)=120 + 1칸 16 = 136, 유량 55~100 mL/min 1 단위(표는 55/65/75/85/100).
  학습 데이터 = 이웃한 2칸뿐 → 나머지(떨어진 2칸, 1칸)는 'kind' 로 표시하고 믿음 낮음.
모양 후보: 띠 가족(7~15띠) 무작위 + 학습한 A·B·C 모양 + 그 주변. 제작 가능한 것만.
출력 (핫스팟마다):
  best_by_flow.csv  — 유량별로 예측 최고온도(상한 = 평균+1σ)가 가장 낮은 모양
  best_by_target.csv — 목표 온도(85/100/120 ℃)를 상한 기준으로 지키는 것 중 펌프 동력 최소 (못 지키면 빈칸)
  candidates.json   — 후보 모양 변수 (STEP은 auto_design.py --hotspot 으로 필요한 것만 만들기)
※ 모두 '예측'. 처음 보는 핫스팟 종류는 오차가 더 큼(시험 5 ℃ 이상).
"""
from __future__ import annotations
import argparse, itertools, json, pickle, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "ml"))
import auto_design as AD  # noqa: E402  (캐시 적용된 PM 사용)
import family_model as FM  # noqa: E402
import shape_features as SF  # noqa: E402
from common import T_IN  # noqa: E402
from geometry import param_manifold as PM  # noqa: E402

REUSE = False
QS = [float(q) for q in np.arange(55, 101, 1)]     # 유량 55~100, 1 mL/min 단위 (목표별 최소 유량 찾기)
Q_TABLE = [55.0, 65.0, 75.0, 85.0, 100.0]          # best_by_flow 표에 남길 유량
TARGETS = [85.0, 100.0, 120.0]
CELLS = [f"{r}_{c}" for r in range(1, 5) for c in range(1, 5)]


def all_hotspots():
    out = []
    for a, b in itertools.combinations(CELLS, 2):
        ra, ca = map(int, a.split("_")); rb, cb = map(int, b.split("_"))
        kind = "이웃 2칸(학습 종류)" if abs(ra - rb) + abs(ca - cb) == 1 else "떨어진 2칸(학습 밖)"
        out.append((f"{a}+{b}", kind))
    out += [(c, "1칸(학습 밖)") for c in CELLS]
    return out


def shape_pool(n_rand, seed):
    rng = np.random.default_rng(seed)
    base = [p for p in FM.family_params(False).values() if AD.NMIN <= PM.resolve(p)["n"] <= AD.NMAX]
    pool = list(base)
    for p in base:
        pool += AD.neighbors(rng, p, 8, scale=0.10)
    pool += AD.random_params(rng, n_rand)
    rows = []
    for p in pool:
        r = PM.resolve(p)
        s = SF.shape_summary(PM.openings(p), (1.5, 10.5))
        rows.append(dict(**{k: r[k] for k in FM.KEYS}, s_eff=r["s_eff"], logG=float(np.log(s["G"]))))
    return pd.DataFrame(rows).drop_duplicates(subset=FM.KEYS).reset_index(drop=True)


def evaluate(M, S, hs):
    cells = hs.split("+")
    hy = np.mean([(int(c.split("_")[0]) - .5) * 3 for c in cells])
    dy = np.abs(hy - S.yf.values) / 12 * np.minimum(S.s_eff.values, 1.0)
    seen = hs in M["T"].seen
    sig = M["T"].sig_seen if seen else M["T"].sig_unseen
    # 학습 밖 종류는 불확실성 2배 (시험으로 잰 값이 없음 → 보수적으로)
    if len(cells) != 2 or sum(abs(int(a) - int(b)) for a, b in zip(cells[0].split("_"), cells[1].split("_"))) != 1:
        sig *= 2
    P = []
    for Q in QS:
        rows = pd.DataFrame(dict(hotspot=[hs] * len(S), Q=Q, logG=S.logG.values, wf=S.wf.values, dy_hs=dy))
        m = M["T"].predict(rows)
        T = T_IN + np.exp(m); Tup = T_IN + np.exp(m + sig)
        dp = np.array([M["P"].predict(dict(n=n, s_eff=np.log1p(se), wf=wf, b=b, logG=lg), Q)
                       for n, se, wf, b, lg in zip(S.n, S.s_eff, S.wf, S.b, S.logG)]) if Q == QS[0] else dp55 * (Q / 55) ** M["P"].m
        if Q == QS[0]:
            dp55 = dp
        P.append(pd.DataFrame(dict(sid=S.index, Q=Q, T=T, T_hi=Tup, dp=dp, W=dp * Q / 60e6 * 1e3)))
    return pd.concat(P, ignore_index=True), seen


def main(n_rand, seed):
    t0 = time.time()
    M = AD.load(); out = ROOT / "out" / "auto_design_all"; out.mkdir(parents=True, exist_ok=True)
    cj = out / "candidates.json"
    S = pd.read_json(cj, orient="index") if (REUSE and cj.exists()) else shape_pool(n_rand, seed)
    print(f"모양 후보 {len(S)}개 만듦 ({time.time() - t0:.0f} s)")
    S.to_json(out / "candidates.json", orient="index", indent=1)
    byflow, bytarget = [], []
    for hs, kind in all_hotspots():
        E, seen = evaluate(M, S, hs)
        for Q, g in E[E.Q.isin(Q_TABLE)].groupby("Q"):
            b = g.loc[g.T_hi.idxmin()]; s = S.loc[int(b["sid"])]
            byflow.append(dict(hotspot=hs, kind=kind, seen=seen, Q_mLmin=Q, v_mps=round(Q / 55 * 0.912, 3), shape_id=int(b["sid"]),
                               **{k: s[k] for k in FM.KEYS}, Tmax_pred=round(b["T"], 1), Tmax_upper=round(b.T_hi, 1),
                               dp_Pa=round(b.dp), W_mW=round(b.W, 2)))
        for tl in TARGETS:
            ok = E[E.T_hi <= tl]
            if len(ok):
                b = ok.loc[ok.W.idxmin()]; s = S.loc[int(b["sid"])]
                bytarget.append(dict(hotspot=hs, kind=kind, seen=seen, target_C=tl, Q_mLmin=b.Q, v_mps=round(b.Q / 55 * 0.912, 3),
                                     shape_id=int(b["sid"]), **{k: s[k] for k in FM.KEYS}, Tmax_pred=round(b["T"], 1),
                                     Tmax_upper=round(b.T_hi, 1), dp_Pa=round(b.dp), W_mW=round(b.W, 2)))
            else:
                bytarget.append(dict(hotspot=hs, kind=kind, seen=seen, target_C=tl, Q_mLmin=np.nan))
    pd.DataFrame(byflow).to_csv(out / "best_by_flow.csv", index=False)
    pd.DataFrame(bytarget).to_csv(out / "best_by_target.csv", index=False)
    print(f"핫스팟 {len(all_hotspots())}개 × 유량 {len(QS)}개 끝 ({time.time() - t0:.0f} s) → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--pool", type=int, default=1200); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--reuse", action="store_true", help="이전에 만든 모양 후보(candidates.json) 다시 쓰기")
    a = ap.parse_args(); REUSE = a.reuse; main(a.pool, a.seed)
