"""자동설계: 사용자 핫스팟 → 숫자 6개(띠형 매니폴드) + 유량 최적화 → STEP + 예측값·불확실성.

  python ml/auto_design.py --hotspot 2_2,3_2                    # 목표 최고온도 기본 85 ℃
  python ml/auto_design.py --hotspot 1_3,1_4 --tlimit 120 --top 3 --step
  python ml/auto_design.py --hotspot 2_2,3_2 --q 75                # 유량 고정 (mL/min)
  python ml/auto_design.py --hotspot 2_2,3_2 --v 0.912 1.658       # 유속 고정 (m/s), 여러 개면 그중 최적

목적: 목표 온도(예측 상한 = 평균 + 1σ)를 지키는 운전점 중 펌프 동력(Δp·Q)이 가장 작은 것.
      목표를 못 지키면 최고온도(상한)가 가장 낮은 것.
제약: 제작 가능(param_manifold 제약), 유량 55~100 mL/min, 띠 ≤ 15개 (학습 데이터 범위, 밖은 외삽이라 금지).
탐색: 무작위 후보 + 기존 학습 모양 주변 → 상위 후보 국소 탐색. 학습 데이터에서 너무 먼 모양은 불확실성이 커져 자연히 불리.
결과: out/auto_design/<핫스팟>/ 에 후보 표(csv) + 상위 N개 STEP·그림 + 비교(같은 핫스팟의 기존 최선 실측값).
※ 예측은 SimScale로 검증 전까지 '예측'일 뿐. 제안 3개를 돌려보고 틀리면 재학습.
"""
from __future__ import annotations
import argparse, json, pickle, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "ml"))
import family_model as FM  # noqa: E402
from common import T_IN  # noqa: E402
from geometry import param_manifold as PM  # noqa: E402

QS = np.array([55.0, 65.0, 75.0, 85.0, 100.0])
V_OF_Q = lambda q: q / 55 * 0.912
NMAX = 15        # 학습 데이터의 띠 개수 범위(5~15) 밖은 외삽이라 금지

# 속도: 같은 모양의 resolve·masks 를 여러 번 계산하지 않게 캐시 (결과는 같음)
_res_orig, _mask_orig, _cache_r, _cache_m = PM.resolve, PM.masks, {}, {}
def _key(p):
    return tuple(sorted((k, float(v)) for k, v in p.items()))
def _resolve_c(p):
    k = _key(p)
    if k not in _cache_r:
        _cache_r[k] = _res_orig(p)
    return dict(_cache_r[k])
def _masks_c(p):
    k = _key(p)
    if k not in _cache_m:
        _cache_m[k] = _mask_orig(p)
    return _cache_m[k]
PM.resolve, PM.masks = _resolve_c, _masks_c


def load():
    return pickle.load(open(FM.PKL, "rb"))


def predict(M, p, hs, Q, f=None):
    if f is None:
        f = FM.features(p, hs, Q)
    m, s = M["T"].predict([dict(hotspot=hs, Q=Q, **{c: f[c] for c in FM.SFEATS})], std=True)
    T = T_IN + np.exp(m[0]); Tup = T_IN + np.exp(m[0] + s[0])
    dp, sp = M["P"].predict(f, Q, std=True)
    W = dp * Q / 60e6 * 1e3          # mW
    return dict(T=T, T_hi=Tup, sig=float(s[0]), dp=dp, dp_sig=sp, W=W)


def evaluate(M, p, hs, tlimit):
    best = None
    f = FM.features(p, hs, QS[0])          # 모양 특징은 유량과 무관 → 한 번만 계산 (속도 약 5배)
    for Q in QS:
        r = predict(M, p, hs, Q, f); r["Q"] = Q
        ok = r["T_hi"] <= tlimit
        key = (0, r["W"]) if ok else (1, r["T_hi"])
        if best is None or key < best["key"]:
            best = dict(r, key=key, ok=ok)
    return best


def random_params(rng, k):
    out = []
    while len(out) < k:
        p = {kk: rng.uniform(*PM.BOUNDS[kk]) for kk in FM.KEYS}
        p["n"] = int(round(p["n"])) | 1
        p = {kk: (round(v, 2) if kk != "n" else v) for kk, v in p.items()}
        r = PM.resolve(p)
        if PM.masks(r)[2] and r["n"] <= NMAX:
            out.append({kk: r[kk] for kk in FM.KEYS})
    return out


def neighbors(rng, p, k, scale=0.12):
    out = []
    for _ in range(k * 4):
        q = dict(p)
        for kk in FM.KEYS:
            lo, hi = PM.BOUNDS[kk]
            q[kk] = float(np.clip(q[kk] + rng.normal(0, scale) * (hi - lo), lo, hi))
        q["n"] = int(round(q["n"])) | 1; q["n"] = int(np.clip(q["n"], 7, 17))
        q = {kk: (round(v, 2) if kk != "n" else v) for kk, v in q.items()}
        r = PM.resolve(q)
        if PM.masks(r)[2] and r["n"] <= NMAX:
            out.append({kk: r[kk] for kk in FM.KEYS})
        if len(out) >= k:
            break
    return out


def measured_best(hs, tlimit):
    """같은 핫스팟에서 실제로 돌린 가족 형상의 결과 (비교용)"""
    df = FM.table(False); o = df[(df.aug == "original") & (df.hotspot == hs)]
    if o.empty:
        return None
    o = o.assign(W=o.pmax * o.Q / 60e6 * 1e3)
    ok = o[o.Tmax <= tlimit]
    r = (ok.sort_values("W") if len(ok) else o.sort_values("Tmax")).iloc[0]
    return dict(design=r.design, Q=r.Q, Tmax=r.Tmax, dp=r.pmax, W=r.W, ok=len(ok) > 0)


def run(hs, tlimit, top, n_rand, seed, step):
    hs = "+".join(sorted(hs.replace(",", "+").split("+")))
    M = load(); rng = np.random.default_rng(seed)
    cands = [{k: v for k, v in p.items()} for p in FM.family_params(False).values()] + random_params(rng, n_rand)
    res = []
    for p in cands:
        e = evaluate(M, p, hs, tlimit); res.append((e["key"], p, e))
    res.sort(key=lambda t: t[0])
    for _, p, _ in res[:8]:                                  # 상위 8개 주변 국소 탐색
        for q in neighbors(rng, p, 25):
            e = evaluate(M, q, hs, tlimit); res.append((e["key"], q, e))
    res.sort(key=lambda t: t[0])
    pick, seen = [], []
    for key, p, e in res:                                    # 서로 다른 모양으로 top개
        z = np.array([(p[k] - PM.BOUNDS[k][0]) / (PM.BOUNDS[k][1] - PM.BOUNDS[k][0]) for k in FM.KEYS])
        if all(np.linalg.norm(z - s) > 0.15 for s in seen):
            pick.append((p, e)); seen.append(z)
        if len(pick) >= top:
            break
    out = ROOT / "out" / "auto_design" / hs.replace("+", "-"); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, (p, e) in enumerate(pick, 1):
        r = PM.resolve(p)
        rows.append(dict(rank=i, hotspot=hs, **{k: r[k] for k in FM.KEYS}, s_eff=r["s_eff"], Q_mLmin=e["Q"], v_mps=round(V_OF_Q(e["Q"]), 3),
                         Tmax_pred=round(e["T"], 1), Tmax_upper=round(e["T_hi"], 1), sigma_log=round(e["sig"], 3),
                         dp_pred_Pa=round(e["dp"]), W_pump_mW=round(e["W"], 2), meets_target=e["ok"]))
    tab = pd.DataFrame(rows); tab.to_csv(out / "proposals.csv", index=False)
    mb = measured_best(hs, tlimit)
    print(f"핫스팟 {hs}, 목표 최고온도 ≤ {tlimit} ℃ (예측 상한 기준)")
    for _, r in tab.iterrows():
        print(f"  제안 {r['rank']}: n={r.n} yf={r.yf} s={r.s} xf={r.xf} b={r.b} wf={r.wf} | 유량 {r.Q_mLmin:.0f} mL/min (v {r.v_mps}) → "
              f"최고온도 {r.Tmax_pred} ℃ (상한 {r.Tmax_upper}), 압력 {r.dp_pred_Pa} Pa, 펌프 {r.W_pump_mW} mW {'✓' if r.meets_target else '✗ 목표 못 지킴'}")
    if mb:
        print(f"  참고(실측 최선): {mb['design']} {mb['Q']:.0f} mL/min → {mb['Tmax']} ℃, {mb['dp']:.0f} Pa, 펌프 {mb['W']:.2f} mW {'✓' if mb['ok'] else '✗'}")
    if step:
        for i, (p, e) in enumerate(pick, 1):
            name = f"AD_{hs.replace('+', '-').replace('_', '')}_{i}"
            info = PM.build_step_smooth(name, p, outdir=str(out))
            print(f"  STEP {name}.step: 물 덩어리 {info['fluid_solids']}개, 최소 벽 {info['min_gap_mm']} mm")
    (out / "summary.json").write_text(json.dumps(dict(hotspot=hs, tlimit=tlimit, proposals=rows, measured_best=mb), ensure_ascii=False, indent=1, default=float))
    return tab, mb


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hotspot", required=True); ap.add_argument("--tlimit", type=float, default=85)
    ap.add_argument("--top", type=int, default=3); ap.add_argument("--rand", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--step", action="store_true")
    ap.add_argument("--q", type=float, nargs="+", help="유량 고정 [mL/min] (여러 개 가능). 없으면 55~100 중 최적을 찾음")
    ap.add_argument("--v", type=float, nargs="+", help="입구 유속 고정 [m/s] (0.912 = 55 mL/min, 1.658 = 100 mL/min)")
    a = ap.parse_args()
    if a.v:
        QS = np.array([v / 0.912 * 55 for v in a.v])
    elif a.q:
        QS = np.array(a.q, dtype=float)
    out_rng = [q for q in QS if q < 54.5 or q > 100.5]
    if out_rng:
        print(f"⚠ 유량 {[round(q, 1) for q in out_rng]} mL/min 은 학습 범위(55~100) 밖 → 예측 믿기 어려움(외삽)")
    run(a.hotspot, a.tlimit, a.top, a.rand, a.seed, a.step)
