"""매니폴드 추천 (에이전트 본체).

예) python -m agent.recommend --model out/model_synthetic \
        --hotspot 5,5,4,4,200 --hotspot 15,12,3,3,150 --flow 65 --fluid Al2O3:0.02
  --hotspot x,y,w,h,q  [mm, mm, mm, mm, W/cm^2]  (여러 번 지정 가능, 최대 4개 권장)
"""
from __future__ import annotations
import argparse
from pathlib import Path
import joblib
import numpy as np
from . import config as C
from .superpose import Library, Hotspot, hotspots_to_cell_flux
from .datagen import features, from_target
from .nanofluid import correction

NM = len(C.MANIFOLDS)


def recommend(model_dir, hotspots, flow, fluid="water", weight_dp=0.0):
    M = joblib.load(Path(model_dir) / "model.joblib")
    lib = Library(M["data"])
    warn = []
    if not C.FLOW_MIN <= flow <= C.FLOW_MAX:
        warn.append(f"유량 {flow} mL/min은 학습 범위({C.FLOW_MIN}~{C.FLOW_MAX}) 밖 → 경계값으로 잘라서 계산, 신뢰 불가")
    if len(hotspots) > 4:
        warn.append("핫스팟 5개 이상은 학습 데이터 범위 밖")
    flux = hotspots_to_cell_flux(hotspots)
    flow_c = float(np.clip(flow, C.FLOW_MIN, C.FLOW_MAX))
    y = from_target(M["yscaler"].inverse_transform(M["net"].predict(features([np.r_[flux, flow_c]]))))[0]

    nf = None
    if fluid != "water":
        part, phi = fluid.split(":"); nf = correction(part, float(phi))
    rows = []
    for i, m in enumerate(C.MANIFOLDS):
        rise_nn = y[i]
        rise_sp = ((flux / C.Q0_WCM2) @ lib.unit_fields(m, flow_c)).max()   # 직접 중첩 계산(교차확인)
        dp = lib.pressure_pa(m, flow_c)
        r = {"manifold": m, "Tmax_nn": C.T_IN_C + rise_nn, "Tmax_direct": C.T_IN_C + rise_sp,
             "nonuni": y[NM + i], "dp_kpa": dp / 1000}
        if nf:
            r["Tmax_nf_range"] = (C.T_IN_C + rise_nn * nf["dT_factor_best"], C.T_IN_C + rise_nn * nf["dT_factor_worst"])
            r["dp_kpa"] *= nf["dp_factor"]
        r["score"] = rise_nn + weight_dp * r["dp_kpa"]
        rows.append(r)
    rows.sort(key=lambda r: r["score"])
    return rows, flux, warn, nf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--hotspot", action="append", required=True)
    ap.add_argument("--flow", type=float, required=True, help="mL/min")
    ap.add_argument("--fluid", default="water", help="water 또는 입자:φ (예 Al2O3:0.02)")
    ap.add_argument("--weight-dp", type=float, default=0.0, help="압력강하 가중치 [K per kPa]")
    ap.add_argument("--plot", default=None, help="히트맵 PNG 저장 경로")
    a = ap.parse_args()
    hs = [Hotspot(*map(float, s.split(","))) for s in a.hotspot]
    rows, flux, warn, nf = recommend(a.model, hs, a.flow, a.fluid, a.weight_dp)
    for w in warn: print("⚠", w)
    print(f"\n유량 {a.flow} mL/min, 유체 {a.fluid}, 핫스팟 {len(hs)}개")
    print(f"{'순위':<4}{'매니폴드':<18}{'Tmax 신경망':>12}{'Tmax 직접중첩':>14}{'불균일도':>10}{'Δp kPa':>9}")
    for k, r in enumerate(rows, 1):
        print(f"{k:<4}{C.MANIFOLD_KO[r['manifold']]:<18}{r['Tmax_nn']:>10.1f}℃{r['Tmax_direct']:>12.1f}℃"
              f"{r['nonuni']:>9.1f}K{r['dp_kpa']:>9.2f}")
        if nf:
            lo, hi = r["Tmax_nf_range"]; print(f"     └ 나노유체 보정 Tmax 추정 {lo:.1f}~{hi:.1f}℃ (근사)")
    print(f"\n추천: {C.MANIFOLD_KO[rows[0]['manifold']]}")
    if a.plot:
        from .viz import heatmaps
        heatmaps(a.model, flux, a.flow, rows, a.plot); print("히트맵:", a.plot)


if __name__ == "__main__":
    main()
