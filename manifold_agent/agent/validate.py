"""SimScale 직접 실행 케이스와 비교 (최종 검증).

data/<dataset>/validation/cases.json  : [{name, manifold, flow_mlmin, hotspots:[{x,y,w,h,q}]}]
data/<dataset>/validation/<name>.csv  : x_mm, y_mm, T_C  (SimScale에서 그 조합을 직접 돌린 결과)

python -m agent.validate --model out/model_synthetic
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import joblib
import numpy as np
from . import config as C
from .superpose import Library, Hotspot, hotspots_to_cell_flux, _read_field
from .datagen import features, from_target


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); a = ap.parse_args()
    M = joblib.load(Path(a.model) / "model.joblib"); lib = Library(M["data"])
    vdir = Path(M["data"]) / "validation"
    cases = json.loads((vdir / "cases.json").read_text())
    print(f"{'케이스':<8}{'매니폴드':<13}{'유량':>5}{'SimScale':>10}{'중첩':>8}{'신경망':>8}{'중첩오차':>9}{'신경망오차':>10}")
    e_sp, e_nn = [], []
    for c in cases:
        _, _, T = _read_field(vdir / f"{c['name']}.csv")
        flux = hotspots_to_cell_flux([Hotspot(**h) for h in c["hotspots"]])
        m, q = c["manifold"], c["flow_mlmin"]; i = C.MANIFOLDS.index(m)
        true_rise = T.max() - C.T_IN_C
        sp_rise = ((flux / C.Q0_WCM2) @ lib.unit_fields(m, q)).max()
        nn_rise = from_target(M["yscaler"].inverse_transform(M["net"].predict(features([np.r_[flux, q]]))))[0][i]
        es, en = (sp_rise - true_rise) / true_rise * 100, (nn_rise - true_rise) / true_rise * 100
        e_sp.append(abs(es)); e_nn.append(abs(en))
        print(f"{c['name']:<8}{m:<13}{q:>5}{T.max():>9.1f}℃{C.T_IN_C+sp_rise:>7.1f}℃{C.T_IN_C+nn_rise:>7.1f}℃{es:>+8.1f}%{en:>+9.1f}%")
    print(f"\n최고온도 '상승분' 기준 오차 — 중첩: 평균 {np.mean(e_sp):.1f}% / 최대 {np.max(e_sp):.1f}%,"
          f"  신경망: 평균 {np.mean(e_nn):.1f}% / 최대 {np.max(e_nn):.1f}%  (N={len(cases)})")


if __name__ == "__main__":
    main()
