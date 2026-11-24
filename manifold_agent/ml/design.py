"""★ 자동 최적 매니폴드 설계 — 명령 하나로: 핫스팟 → 최적 모양 STEP + 최적 유량 + 예상 성능.

  python ml/design.py 2_2,3_2                  # 핫스팟만 (목표 100 ℃ 기본)
  python ml/design.py 2_2,3_2 --target 85      # 목표 최고온도 지정
  python ml/design.py 1_3,1_4 --flow 75        # 유량 고정 (mL/min)
  python ml/design.py 2_2,3_2 --nostep         # STEP 없이 숫자만 (빠름)

하는 일
  1) 띠형 매니폴드 후보 1,671개 (out/auto_design_all/candidates.json, 학습한 A·B·C 모양 포함)
  2) 학습한 모델(ml/family_model.pkl, v2b)로 모든 후보 × 유량 55~100 mL/min(1 단위) 최고온도·압력 예측
  3) 목표(예측 상한 = 평균+1σ ≤ 목표)를 지키면서 펌프 동력이 가장 적은 모양+유량 선택
     (못 지키면 가장 시원한 것 + '못 지킴' 표시)
  4) 그 주변을 한 번 더 찾아 다듬기 → STEP 만들기 → 그림·요약 저장
결과: out/design/<핫스팟>_T<목표>/  (design.step, summary.png, result.json, result.txt)
믿음 정도: 이웃 2칸 핫스팟 중 실제로 돌려본 위치 ±4 ℃ / 안 돌려본 이웃 2칸 ±5 ℃ / 1칸·떨어진 2칸은 학습 밖.
          1행·4행 가로 핫스팟은 낙관적으로 나올 수 있음(실측보다 낮게).
"""
from __future__ import annotations
import argparse, json, pickle, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "ml"))
import auto_design as AD  # noqa: E402  (모양 계산 캐시)
import family_model as FM  # noqa: E402
import shape_features as SF  # noqa: E402
from geometry import param_manifold as PM  # noqa: E402

QS = np.arange(55.0, 100.01, 1.0)
T_IN = 20.0


def norm_hotspot(h):
    cells = sorted(c.strip() for c in h.replace("+", ",").split(",") if c.strip())
    for c in cells:
        r, k = map(int, c.split("_"))
        assert 1 <= r <= 4 and 1 <= k <= 4, f"칸 이름은 1_1 ~ 4_4: {c}"
    return "+".join(cells)


def kind_of(hs, M):
    cs = [tuple(map(int, c.split("_"))) for c in hs.split("+")]
    adj = len(cs) == 2 and abs(cs[0][0] - cs[1][0]) + abs(cs[0][1] - cs[1][1]) == 1
    if adj and hs in M["T"].seen:
        k, err = "이웃 2칸, 실제로 돌려본 위치", "±4 ℃ 정도"
    elif adj:
        k, err = "이웃 2칸, 안 돌려본 위치", "±5 ℃ 정도"
    else:
        k, err = "1칸 또는 떨어진 2칸 (학습 밖)", "믿기 어려움 (SimScale 확인 필요)"
    edge = any(r in (1, 4) for r, _ in cs) and len({r for r, _ in cs}) == 1
    return k, err, edge


def pressure_batch(M, S):
    P = M["P"]
    X = np.column_stack([S.n, np.log1p(S.s_eff), S.wf, S.b, S.logG])
    return np.exp(P.gp.predict((X - P.mu) / P.sd))          # 55 mL/min 압력


def score(M, S, hs, qs, target):
    hy = np.mean([(int(c.split("_")[0]) - .5) * 3 for c in hs.split("+")])
    dy = np.abs(hy - S.yf.values) / 12 * np.minimum(S.s_eff.values, 1.0)
    k, _, _ = kind_of(hs, M)
    sig = M["T"].sig_seen if "돌려본" in k and "안" not in k else M["T"].sig_unseen
    if "학습 밖" in k:
        sig *= 2
    dp55 = pressure_batch(M, S)
    best = None
    for Q in qs:
        rows = pd.DataFrame(dict(hotspot=[hs] * len(S), Q=Q, logG=S.logG.values, wf=S.wf.values, dy_hs=dy))
        m = M["T"].predict(rows); T = T_IN + np.exp(m); Thi = T_IN + np.exp(m + sig)
        dp = dp55 * (Q / 55) ** M["P"].m; W = dp * Q / 60e6 * 1e3
        for i in range(len(S)):
            ok = Thi[i] <= target
            key = (0, W[i]) if ok else (1, Thi[i], W[i])
            if best is None or key < best["key"]:
                best = dict(key=key, i=i, Q=float(Q), T=float(T[i]), Thi=float(Thi[i]), dp=float(dp[i]), W=float(W[i]), ok=bool(ok))
    return best


def pool_with(S, extra):
    rows = []
    for p in extra:
        r = PM.resolve(p)
        s = SF.shape_summary(PM.openings(p), (1.5, 10.5))
        rows.append(dict(**{k: r[k] for k in FM.KEYS}, s_eff=r["s_eff"], logG=float(np.log(s["G"]))))
    return pd.concat([S, pd.DataFrame(rows)], ignore_index=True)


def figure(hs, p, res, out):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.patches import Rectangle, Circle
    for f in font_manager.findSystemFonts():
        if "wqy" in f.lower() or "nanum" in f.lower() or ("noto" in f.lower() and "cjk" in f.lower()):
            font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name(); break
    hot = [tuple(map(int, c.split("_"))) for c in hs.split("+")]
    fig, ax = plt.subplots(1, 2, figsize=(16, 8.8))

    def frame(a):
        a.set_xlim(0, 12); a.set_ylim(12, 0); a.set_aspect("equal")
        for t in (3, 6, 9): a.axhline(t, c="k", lw=1.2); a.axvline(t, c="k", lw=1.2)
        a.add_patch(Rectangle((0, 0), 12, 12, fill=False, ec="k", lw=2)); a.set_xticks([]); a.set_yticks([])
        for (x, y), l, col in [((3, 1), "출구", "white"), ((3, 11), "출구", "white"), ((9, 1), "입구", "gold"), ((9, 11), "입구", "gold")]:
            a.add_patch(Circle((x, y), 0.45, fc=col, ec="k", lw=1.5, zorder=8))
            a.text(x + (-1.25 if l == "출구" else 1.25), y, f"{l} ({x},{y})", ha="center", va="center", fontsize=9, zorder=9,
                   bbox=dict(fc="white", ec="none", alpha=.85, pad=1))
    a = ax[0]
    for r in range(1, 5):
        for c in range(1, 5):
            h = (r, c) in hot
            a.add_patch(Rectangle((3 * c - 3, 3 * r - 3), 3, 3, fc=(1, .15, .1, .55) if h else (.85, .9, 1, .5), ec="k", lw=1))
            yy = 3 * r - 1.5 if r in (2, 3) else (3 * r - 1.5 + (0.6 if r == 1 else -0.6))
            a.text(3 * c - 1.5, yy, f"{r}_{c}\n{'300' if h else '50'} W/cm²", ha="center", va="center", fontsize=13 if h else 10,
                   fontweight="bold" if h else "normal")
    frame(a); a.set_title(f"① 핫스팟 {hs} — 바닥에서 본 모습 (SimScale BOTTOM)", fontsize=13)
    a = ax[1]
    P = PM.masks(p)[0]; img = np.ones((*P.shape, 3)) * .95; img[P == 1] = (.45, .6, .9); img[P == 2] = (.9, .45, .42)
    a.imshow(img, extent=(0, 12, 0, 12), origin="lower")
    for r, c in hot: a.add_patch(Rectangle((3 * c - 3, 3 * r - 3), 3, 3, fill=False, ec="red", lw=3, zorder=6))
    frame(a)
    a.set_title(f"② 최적 매니폴드 — 관통층 구멍 (띠 {p['n']}개)  파랑=출구망, 빨강=입구망\n"
                f"n={p['n']} yf={p['yf']} s={p['s']} xf={p['xf']} b={p['b']} wf={p['wf']}", fontsize=12)
    fig.suptitle(f"자동 최적 설계: 유량 {res['Q']:.0f} mL/min (입구 유속 {res['v']} m/s) → 예상 최고온도 {res['T']:.1f} ℃ "
                 f"(상한 {res['Thi']:.1f}), 압력 {res['dp']:.0f} Pa, 펌프 {res['W']:.1f} mW\n"
                 f"목표 {res['target']:.0f} ℃: {'지킴 (O)' if res['ok'] else '못 지킴 (X) — 가장 시원한 설계'}   ·   믿음: {res['kind']} → {res['err']}",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.9]); fig.savefig(out / "summary.png", dpi=100); plt.close(fig)


def main(hotspot, target, flow, step, seed):
    t0 = time.time()
    hs = norm_hotspot(hotspot)
    M = pickle.load(open(FM.PKL, "rb"))
    S = pd.read_json(ROOT / "out/auto_design_all/candidates.json", orient="index")
    S = S[(S.n >= AD.NMIN) & (S.n <= AD.NMAX)].reset_index(drop=True)
    qs = np.array([flow]) if flow else QS
    if flow and not (55 <= flow <= 100):
        print(f"⚠ 유량 {flow} mL/min 은 학습 범위(55~100) 밖 → 예측 믿기 어려움")
    b = score(M, S, hs, qs, target)
    # 다듬기: 가장 좋은 모양 주변 40개 더
    rng = np.random.default_rng(seed)
    p0 = {k: (int(S.loc[b["i"], k]) if k == "n" else float(S.loc[b["i"], k])) for k in FM.KEYS}
    S2 = pool_with(S.iloc[[b["i"]]].reset_index(drop=True), AD.neighbors(rng, p0, 40, scale=0.06))
    b2 = score(M, S2, hs, qs, target)
    if b2["key"] < b["key"]:
        b, S = b2, S2
    p = {k: (int(S.loc[b["i"], k]) if k == "n" else round(float(S.loc[b["i"], k]), 2)) for k in FM.KEYS}
    kind, err, edge = kind_of(hs, M)
    res = dict(hotspot=hs, target=target, params=p, Q=b["Q"], v=round(b["Q"] / 55 * 0.912, 3), T=b["T"], Thi=b["Thi"],
               dp=b["dp"], W=b["W"], ok=b["ok"], kind=kind, err=err)
    out = ROOT / "out" / "design" / (f"{hs.replace('+', '-')}_T{target:.0f}" + (f"_Q{flow:.0f}" if flow else ""))
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"핫스팟 {hs}, 목표 최고온도 {target:.0f} ℃" + (f", 유량 {flow:.0f} 고정" if flow else ""),
             f"  → 최적 모양: 띠 {p['n']}개 (n={p['n']} yf={p['yf']} s={p['s']} xf={p['xf']} b={p['b']} wf={p['wf']})",
             f"  → 최적 유량: {b['Q']:.0f} mL/min (입구 유속 {res['v']} m/s)",
             f"  → 예상 최고온도 {b['T']:.1f} ℃ (불확실성 포함 상한 {b['Thi']:.1f} ℃) {'✓ 목표 지킴' if b['ok'] else '✗ 목표 못 지킴 — 이 구조로 가장 시원한 설계'}",
             f"  → 예상 압력 {b['dp']:.0f} Pa, 펌프 동력 {b['W']:.1f} mW",
             f"  → 믿음: {kind} → {err}" + ("  (1행·4행 가로 핫스팟: 실측보다 낮게 예측될 수 있음)" if edge else "")]
    if step:
        info = PM.build_step_smooth("design", p, outdir=str(out))
        lines.append(f"  → STEP: {out / 'design.step'} (물 덩어리 {info['fluid_solids']}개, 최소 벽 {info['min_gap_mm']} mm)")
        res["step_check"] = dict(fluid_solids=info["fluid_solids"], min_gap_mm=info["min_gap_mm"])
    figure(hs, p, res, out)
    lines.append(f"  → 그림: {out / 'summary.png'}   ({time.time() - t0:.0f} 초)")
    (out / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float))
    (out / "result.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="핫스팟 → 최적 매니폴드 STEP + 유량")
    ap.add_argument("hotspot", help="예: 2_2,3_2  또는 1_3+1_4  (칸 이름 r_c: r=행(아래 1), c=열(왼쪽 1), SimScale BOTTOM 시점 기준)")
    ap.add_argument("--target", type=float, default=100.0, help="목표 최고온도 [℃] (기본 100)")
    ap.add_argument("--flow", type=float, help="유량 고정 [mL/min] (없으면 55~100 중 자동)")
    ap.add_argument("--nostep", action="store_true", help="STEP 만들지 않기")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(); main(a.hotspot, a.target, a.flow, not a.nostep, a.seed)
