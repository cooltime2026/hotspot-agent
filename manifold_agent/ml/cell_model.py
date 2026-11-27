"""칸별 온도 모델 — 매니폴드 '고르기'용 (2026-11-27, S1 실패에서 배움).

  python ml/cell_model.py test     # 모양 하나를 통째로 빼고 맞히기 (최고온도 = 16칸 예측의 최댓값)
  python ml/cell_model.py fit      # 전체 학습 → ml/cell_model.json (웹 HTML 이 읽음)

왜: S1(흡입형)은 출구가 왼쪽에만 있어 오른쪽 채널 10개가 죽음 → 핫스팟이 아닌 오른쪽 열이 103~104 ℃.
    핫스팟 칸 특징만 보는 select_model 은 74.9 ℃ 로 예측(실측 107). 칸마다 온도를 예측해 최댓값을 보면 이런 경우를 잡을 수 있음.
데이터: data/ml/cell_temps.csv (바닥 사진 → 16칸 최고온도), 모양 마스크가 있는 Run (띠 A·B·C, M0·M1·M3·M4·D0·D1, S*).
입력(칸마다): 이 칸 핫스팟 여부, 이웃 핫스팟 수, 이 칸·이웃 칸의 물 흐름(log)·죽은 구간·찬물까지 거리, 가장자리 여부, log 유량, logG.
목표: log(칸 최고온도 − 20). 모델: 릿지(선형, 상호작용 몇 개) — 자바스크립트로 옮기기 쉬움.
"""
from __future__ import annotations
import json, sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
import shape_features as SF  # noqa: E402
import select_model as SM  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

warnings.filterwarnings("ignore")
OUT = ROOT / "ml" / "cell_model.json"
CELLS = [(r, c) for r in range(1, 5) for c in range(1, 5)]
FEATS = ["hot", "nhot", "lflow", "dead", "fresh", "path", "nlflow", "ndead", "edge_r", "edge_c", "lq", "logG",
         "hot_lq", "hot_lflow", "hot_dead", "hot_fresh", "nhot_lq", "dead_lq"]


def cell_rows(summary, hot_cells, Q):
    """한 모양·핫스팟·유량 → 16칸 특징 행"""
    cf = {(r, c): SF.cell_features(summary, f"{r}_{c}") for r, c in CELLS}
    hot = set(hot_cells); lq = np.log(Q / 55); lG = np.log(summary["G"]); rows = []
    for r, c in CELLS:
        nb = [(r + dr, c + dc) for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)] if 1 <= r + dr <= 4 and 1 <= c + dc <= 4]
        f = cf[(r, c)]; h = 1.0 if (r, c) in hot else 0.0; nh = sum(1 for n in nb if n in hot)
        lf = np.log(f["flow_loc"] + 1e-4); nlf = np.mean([np.log(cf[n]["flow_loc"] + 1e-4) for n in nb]); nd = np.mean([cf[n]["dead"] for n in nb])
        rows.append(dict(hot=h, nhot=nh, lflow=lf, dead=f["dead"], fresh=f["dfresh"] / 12, path=min(f["path_in"], 12) / 12,
                         nlflow=nlf, ndead=nd, edge_r=float(r in (1, 4)), edge_c=float(c in (1, 4)), lq=lq, logG=lG,
                         hot_lq=h * lq, hot_lflow=h * lf, hot_dead=h * f["dead"], hot_fresh=h * f["dfresh"] / 12, nhot_lq=nh * lq, dead_lq=f["dead"] * lq))
    return rows


def table():
    c = pd.read_csv(ROOT / "data/ml/cell_temps.csv")
    c = c[c.design != "L1"].reset_index(drop=True)
    Qof = {0.497: 29.98, 0.663: 39.99, 0.912: 55.01, 1.243: 74.98, 1.658: 100.01}
    S = {k: SM.summary_of(k) for k in c.design.unique()}
    R = []
    for i, x in c.iterrows():
        hot = [tuple(map(int, h.split("_"))) for h in x.hotspot.split("+")]
        for (r, cc), f in zip(CELLS, cell_rows(S[x.design], hot, Qof[round(x.inlet_v_mps, 3)])):
            R.append(dict(run=i, design=x.design, hotspot=x.hotspot, v=x.inlet_v_mps, Tmax=x.Tmax_C, cell=f"{r}_{cc}",
                          T=x[f"Tcellmax_{r}_{cc}"], **f))
    return pd.DataFrame(R).dropna(subset=["T"]).reset_index(drop=True)


def fit_model(D, alpha):
    X = D[FEATS].values; mu, sd = X.mean(0), X.std(0) + 1e-9
    return dict(mu=mu, sd=sd, m=Ridge(alpha=alpha).fit((X - mu) / sd, np.log(D["T"].values - 20)))


def pred_cells(M, D):
    return 20 + np.exp(M["m"].predict((D[FEATS].values - M["mu"]) / M["sd"]))


def test(alpha=3.0):
    D = table(); D["p"] = np.nan
    for k in D.design.unique():
        tr = D.design != k
        D.loc[~tr, "p"] = pred_cells(fit_model(D[tr], alpha), D[~tr])
    run = D.groupby("run").agg(design=("design", "first"), hotspot=("hotspot", "first"), v=("v", "first"),
                               Tmax=("Tmax", "first"), pred=("p", "max"))
    fam = run.design.where(run.design.isin(SM.PRESET) | run.design.str.match(r"^S\d"), "띠가족")
    print(f"시험: 모양 하나를 통째로 빼고 맞히기 (칸 모델, 릿지 alpha={alpha}, {len(run)} Run, 칸 {len(D)}개)")
    print(run.assign(err=(run.pred - run.Tmax).abs(), bias=run.pred - run.Tmax, fam=fam).groupby("fam")[["err", "bias"]].mean().round(1).to_string())
    rows = []
    for (h, v), g in run.groupby(["hotspot", "v"]):
        if g.design.nunique() < 3:
            continue
        pick = g.loc[g.pred.idxmin()]
        rows.append(dict(hotspot=h, v=v, n=len(g), rho=spearmanr(g.pred, g.Tmax)[0], regret=pick.Tmax - g.Tmax.min(), rand=g.Tmax.mean() - g.Tmax.min(), pick=pick.design))
    r = pd.DataFrame(rows)
    print(f"\n순위 시험 ({len(r)} 묶음): 순위 상관 평균 {r.rho.mean():.2f} / 고른 모양 손해 {r.regret.mean():.1f} ℃ (아무거나 {r.rand.mean():.1f} ℃)")
    s1 = run[run.design == "S1"]
    if len(s1):
        print(f"S1 (빼고 맞히기): 예측 {s1.pred.iloc[0]:.1f} / 실측 {s1.Tmax.iloc[0]:.1f}")
    return run, r


def fit(alpha=3.0):
    D = table(); M = fit_model(D, alpha); X = D[FEATS].values
    js = dict(type="cell", note="ml/cell_model.py — 칸별 릿지, 최고온도 = 16칸 최댓값. 순위 전용.", alpha=alpha, feats=FEATS,
              mu=M["mu"].tolist(), sd=M["sd"].tolist(), coef=M["m"].coef_.tolist(), intercept=float(M["m"].intercept_),
              xmin=X.min(0).tolist(), xmax=X.max(0).tolist(), n_runs=int(D.run.nunique()), designs=sorted(D.design.unique().tolist()))
    js["resid"] = residuals(D, M)
    OUT.write_text(json.dumps(js, ensure_ascii=False, indent=1))
    print("저장:", OUT, js["n_runs"], "Run", len(D), "칸")
    print("실측 보정:", {k: v for k, v in js["resid"].items() if k != "shapes"}, [(x["name"], x["fam"], round(x["r"], 3)) for x in js["resid"]["shapes"]])


def residuals(D, M):
    """실측 보정값 (log(T−20) 단위, 실측 − 모델). 모델이 못 배우는 모양 차이를 실측으로 메움 (2026-11-27, S2 에서 배움).
    띠 가족(A·B·C): 가족 평균 하나. HTML v17 모양(S*): 모양마다 하나 + 마스크(비슷한 후보일수록 그만큼 적용)."""
    import base64
    D = D.assign(p=pred_cells(M, D))
    run = D.groupby("run").agg(design=("design", "first"), hotspot=("hotspot", "first"), Tmax=("Tmax", "first"), p=("p", "max"))
    run["r"] = np.log(run.Tmax - 20) - np.log(run.p - 20)
    strip = run[run.design.str.match(r"^[ABC]\d")]
    shapes = []
    for k, g in run[run.design.str.match(r"^S\d")].groupby("design"):
        m = json.load(open(SM.V17 / f"{k}_mask.json"))
        P = np.array(m["cav"]).reshape(240, 240).reshape(120, 2, 120, 2).max(axis=(1, 3)).astype(np.uint8)
        fam = (m.get("base") or "").split(" · ")[0].split(" (")[0]
        shapes.append(dict(name=k, fam=fam, r=float(g.r.mean()), P=base64.b64encode(P.tobytes()).decode()))
    by_hs = {h: float(g.r.mean()) for h, g in strip.groupby("hotspot")}   # 핫스팟별 (실측이 있으면 이쪽 우선)
    nh = run[run.design.isin(["D0", "D1"]) | run.design.str.match(r"^S\d")]   # 헤더 없는 계열(채널 0.6~11.4): 모양별 평균의 평균
    nohead = float(nh.groupby("design").r.mean().mean())
    shapes += f_shapes(M)
    return dict(strip=float(strip.r.mean()), strip_n=int(len(strip)), strip_hs=by_hs, nohead=nohead, shapes=shapes)


def f_shapes(M):
    """F형(핫스팟 줄 전용 입구) 실측 — 칸 사진이 없어도 최고온도로 보정값을 만듦 (direct_runs.csv)."""
    import base64
    sys.path.insert(0, str(ROOT))
    import f_family as FF
    from geometry import split_feed as SFd
    runs = pd.read_csv(ROOT / "data/direct_runs.csv"); runs = runs[runs.design.isin(list(SFd.F))]
    out = []
    for k, g in runs.groupby("design"):
        rs = []
        for _, x in g.iterrows():
            hs = x.heat.split("at ")[1].replace(",", "+"); cells = [tuple(map(int, c.split("_"))) for c in hs.split("+")]
            side = "top" if all(r == 4 for r, _ in cells) else "bottom"
            P, _ = FF.f_masks(SFd.F[k], side)
            s = SF.shape_summary(SF.openings_from_mask(P, 2, 1.5, 10.5))
            p = pred_cells(M, pd.DataFrame(cell_rows(s, cells, x.total_flow_mL_min))).max()
            rs.append(np.log(x.Tmax_bottom_C - 20) - np.log(p - 20))
        Ph = np.where(P == 2, 1, np.where(P == 1, 2, 0)).astype(np.uint8)       # HTML 규칙 (1 = 입구망)
        out.append(dict(name=k, fam="F형", r=float(np.mean(rs)), P=base64.b64encode(Ph.tobytes()).decode()))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    a = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    test(a) if cmd == "test" else fit(a)
