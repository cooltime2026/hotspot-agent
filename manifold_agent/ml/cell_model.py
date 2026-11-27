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
import json, re, sys, warnings
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
    W = hot_cells if isinstance(hot_cells, dict) else {k: 1.0 for k in hot_cells}     # 칸마다 발열 몫 (hs_weights) 또는 두 칸 0/1
    lq = np.log(Q / 55); lG = np.log(summary["G"]); rows = []
    for r, c in CELLS:
        nb = [(r + dr, c + dc) for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)] if 1 <= r + dr <= 4 and 1 <= c + dc <= 4]
        f = cf[(r, c)]; h = float(W.get((r, c), 0.0)); nh = sum(W.get(n, 0.0) for n in nb)
        lf = np.log(f["flow_loc"] + 1e-4); nlf = np.mean([np.log(cf[n]["flow_loc"] + 1e-4) for n in nb]); nd = np.mean([cf[n]["dead"] for n in nb])
        rows.append(dict(hot=h, nhot=nh, lflow=lf, dead=f["dead"], fresh=f["dfresh"] / 12, path=min(f["path_in"], 12) / 12,
                         nlflow=nlf, ndead=nd, edge_r=float(r in (1, 4)), edge_c=float(c in (1, 4)), lq=lq, logG=lG,
                         hot_lq=h * lq, hot_lflow=h * lf, hot_dead=h * f["dead"], hot_fresh=h * f["dfresh"] / 12, nhot_lq=nh * lq, dead_lq=f["dead"] * lq))
    return rows


def hs_weights(hs, q0=50.0):
    """아무 배치 핫스팟 [{x,y,lx,ly,q}] → (칸마다 발열 몫 {(r,c): w}, 발열 큰 두 칸 이름표 'r_c+r_c', exact). 페이지 mlCells 와 같은 식.
    w = 칸에 겹친 면적 × (q − 기본 열유속) / (9 mm² × (300 − 기본)). 가장 큰 칸이 1 을 넘으면 모두 같은 비율로 줄임."""
    w = {}
    for h in hs:
        for r, c in CELLS:
            ox = min(h["x"] + h["lx"] / 2, c * 3) - max(h["x"] - h["lx"] / 2, (c - 1) * 3)
            oy = min(h["y"] + h["ly"] / 2, r * 3) - max(h["y"] - h["ly"] / 2, (r - 1) * 3)
            if ox > 0 and oy > 0:
                w[(r, c)] = w.get((r, c), 0.0) + ox * oy * max(0.0, h["q"] - q0) / (9 * (300 - q0))
    al = sorted([(k, v) for k, v in w.items() if v > .02], key=lambda x: -x[1])     # 파이썬 정렬은 안정적(같은 값이면 넣은 순서) = JS 와 같음
    mx = al[0][1] if al else 1.0; sc = 1 / mx if mx > 1 else 1.0
    exact = len(al) <= 2 and all(abs(v - 1) < .02 for _, v in al) and abs(q0 - 50) < 1
    return {k: v * sc for k, v in al}, "+".join(f"{r}_{c}" for (r, c), _ in al[:2]), exact


def free_hs(design):
    """아무 배치로 만든 새 설계(ml/design_any.py)면 그 핫스팟 목록 [{x,y,lx,ly,q}], 아니면 None"""
    f = ROOT / f"out/new_designs/{design}_mask.json"
    if re.match(r"^N\d", str(design)) and f.exists():
        return json.load(open(f)).get("hs")
    return None


def hs_sig(hs):
    """핫스팟 목록의 서명 (페이지 mlCells.sig 와 같음) — 같은 배치인지 알아보는 이름표"""
    return "free:" + ";".join(sorted(f"{h['x']:.2f},{h['y']:.2f},{h['lx']:.2f},{h['ly']:.2f},{h['q']:.2f}" for h in hs))


def table():
    c = pd.read_csv(ROOT / "data/ml/cell_temps.csv")
    c = c[c.design != "L1"].reset_index(drop=True)
    # E 가족은 뺌 (2026-11-27): E1 은 구멍→헤더→첫 띠 '지름길'로 물이 거의 다 빠져 201.5 ℃. 모델의 흐름 특징(저항 비례 분배)으로 표현 못 하는 현상이라
    # 넣으면 다른 모양 예측이 망가짐(고른 모양 손해 4.6 → 7.5 ℃). 데이터(direct_runs·cell_temps)에는 그대로 있음.
    c = c[~c.design.str.match(r"^E\d")].reset_index(drop=True)
    Qof = {0.497: 29.98, 0.663: 39.99, 0.912: 55.01, 1.243: 74.98, 1.658: 100.01}
    S = {k: SM.summary_of(k) for k in c.design.unique()}
    R = []
    for i, x in c.iterrows():
        fh = free_hs(x.design)      # 아무 배치 Run: 칸마다 발열 몫으로 학습 (2026-11-28)
        hot = hs_weights(fh)[0] if fh else [tuple(map(int, h.split("_"))) for h in x.hotspot.split("+")]
        for (r, cc), f in zip(CELLS, cell_rows(S[x.design], hot, Qof.get(round(x.inlet_v_mps, 3), x.inlet_v_mps / 0.912 * 55.01))):
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
    fam = run.design.where(run.design.isin(SM.PRESET) | run.design.str.match(r"^[SN]\d"), "띠가족")
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
    # 모양·핫스팟마다 하나 (hs = 그 실측의 핫스팟). 후보와 비교할 때 핫스팟 위치를 맞춰 옮긴 뒤 겹침을 봄 (align_w, 2026-11-28)
    for (k, h), g in run[run.design.str.match(r"^S\d")].groupby(["design", "hotspot"]):
        m = json.load(open(SM.V17 / f"{k}_mask.json"))
        P = np.array(m["cav"]).reshape(240, 240).reshape(120, 2, 120, 2).max(axis=(1, 3)).astype(np.uint8)
        fam = (m.get("base") or "").replace("머신러닝 설계 · ", "").split(" · ")[0].split(" (")[0]
        shapes.append(dict(name=k, fam=fam, hs=h, r=float(g.r.mean()), P=base64.b64encode(P.tobytes()).decode()))
    for (k, h), g in run[run.design.str.match(r"^N\d")].groupby(["design", "hotspot"]):   # 머신러닝 새 설계 (ml/build_new.py) — 진화 출발 종류 이름으로
        m = json.load(open(ROOT / f"out/new_designs/{k}_mask.json"))
        P = np.array(m["cav"]).reshape(240, 240).reshape(120, 2, 120, 2).max(axis=(1, 3)).astype(np.uint8)
        shapes.append(dict(name=k, fam=m["fam"], hs=h, head=int(m.get("head", 0)), r=float(g.r.mean()), P=base64.b64encode(P.tobytes()).decode()))
    by_hs = {h: float(g.r.mean()) for h, g in strip.groupby("hotspot")}   # 핫스팟별 (실측이 있으면 이쪽 우선)
    nnh = [k for k in run.design.unique() if re.match(r"^N\d", k) and not json.load(open(ROOT / f"out/new_designs/{k}_mask.json")).get("head")]
    nh = run[run.design.isin(["D0", "D1"] + nnh) | run.design.str.match(r"^S\d")]   # 헤더 없는 계열(채널 0.6~11.4): 모양별 평균의 평균
    nohead = float(nh.groupby("design").r.mean().mean())
    shapes += f_shapes(M) + preset_shapes(M)
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
        for _, x in g.iterrows():
            hs = x.heat.split("at ")[1].replace(",", "+"); cells = [tuple(map(int, c.split("_"))) for c in hs.split("+")]
            side = "top" if all(r == 4 for r, _ in cells) else "bottom"
            P, _ = FF.f_masks(SFd.F[k], side)
            s = SF.shape_summary(SF.openings_from_mask(P, 2, 1.5, 10.5))
            p = pred_cells(M, pd.DataFrame(cell_rows(s, cells, x.total_flow_mL_min))).max()
            Ph = np.where(P == 2, 1, np.where(P == 1, 2, 0)).astype(np.uint8)       # HTML 규칙 (1 = 입구망)
            out.append(dict(name=k, fam="F형", hs="+".join(sorted(hs.split("+"))), r=float(np.log(x.Tmax_bottom_C - 20) - np.log(p - 20)), P=base64.b64encode(Ph.tobytes()).decode()))
    return out


PRESET_SHAPES = ["D1"]      # 실측이 많은 프리셋 (v17 형, 1 = 입구망). 진화 출발점·2~5위 후보에도 씀 (2026-11-28)


def preset_mask(k):
    P = np.array(SF._designs()[k]["P"]).reshape(120, 120)
    inl = [tuple(p) for p in SF._meta()[k]["inlets"]]; ports = [tuple(p) for p in SF._designs()[k]["ports"]]
    sv = 1 if any(np.hypot(a[0] - b[0], a[1] - b[1]) < 0.3 for a in inl for b in ports[:2]) else 2
    return np.where(P == sv, 1, np.where(P > 0, 2, 0)).astype(np.uint8)


def preset_shapes(M):
    """프리셋(D1) 실측 — 최고온도로 핫스팟마다 보정값 (칸 사진 없는 Run 도 씀)."""
    import base64
    runs = pd.read_csv(ROOT / "data/direct_runs.csv"); out = []
    for k in PRESET_SHAPES:
        Ph = preset_mask(k); s = SM.summary_of(k); rs = {}
        for _, x in runs[runs.design == k].iterrows():
            hs = "+".join(sorted(x.heat.split("at ")[1].split(","))); cells = [tuple(map(int, c.split("_"))) for c in hs.split("+")]
            p = pred_cells(M, pd.DataFrame(cell_rows(s, cells, x.total_flow_mL_min))).max()
            rs.setdefault(hs, []).append(np.log(x.Tmax_bottom_C - 20) - np.log(p - 20))
        for hs, r in rs.items():
            out.append(dict(name=k, fam=k, hs=hs, r=float(np.mean(r)), P=base64.b64encode(Ph.tobytes()).decode()))
    return out


def align_w(P, A, hs_a, hs_b):
    """실측 모양 A(핫스팟 hs_a)를 후보 핫스팟 hs_b 위치로 옮겨(3 mm 칸 단위, 위아래 뒤집기 포함) 후보 P 와 겹침² (2026-11-28).
    모양의 실측 보정은 '그 핫스팟에 맞춘 배치'의 효과이므로, 다른 핫스팟 후보에는 같은 배치로 옮겨서 비교.
    두 칸 핫스팟의 방향(가로·세로)이 다르면 0. 같은 핫스팟이면 그냥 겹침² (= 예전과 같음).
    P, A: 120×120 (행 = y/0.1). hs: '2_2+3_2' 또는 [(2,2),(3,2)]."""
    cv = lambda h: sorted(tuple(map(int, c.split("_"))) for c in h.split("+")) if isinstance(h, str) else sorted(h)
    ca, cb = cv(hs_a), cv(hs_b)
    ori = lambda c: "s" if len(c) == 1 else ("h" if c[0][0] == c[1][0] else "v")
    if ori(ca) != ori(cb) and "s" not in (ori(ca), ori(cb)):
        return 0.0
    Pb = P > 0; best = 0.0
    for flip in (False, True):
        A2 = A[::-1] if flip else A
        c2 = [(5 - r, c) for r, c in ca] if flip else ca
        dr = (min(r for r, _ in cb) - min(r for r, _ in c2)) * 30; dc = (min(c for _, c in cb) - min(c for _, c in c2)) * 30
        B = np.zeros_like(A2)
        ys, yd = (slice(0, 120 - dr), slice(dr, 120)) if dr >= 0 else (slice(-dr, 120), slice(0, 120 + dr))
        xs, xd = (slice(0, 120 - dc), slice(dc, 120)) if dc >= 0 else (slice(-dc, 120), slice(0, 120 + dc))
        B[yd, xd] = A2[ys, xs]
        u = (Pb | (B > 0)).sum()
        if u:
            best = max(best, (Pb & (B > 0)).sum() / u)
    return best ** 2


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    a = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    test(a) if cmd == "test" else fit(a)
