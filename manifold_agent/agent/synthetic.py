"""⚠ 가짜(가상) 데이터 생성기 — SimScale 결과가 오기 전 파이프라인 시험용.

실제 물리 결과가 아니다. 간단한 해석식(열 퍼짐 + 하류 가열 + 매니폴드별 열전달 패턴)으로
SimScale 출력과 '같은 형식'의 CSV만 만든다. 생성된 폴더에는 FAKE_DATA.txt가 들어간다.
실제 물처럼 점도 변화에 의한 약한 비선형성도 넣어서, 중첩 검증이 오차를 잡아내는지 시험한다.
"""
from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np
from . import config as C
from .superpose import Hotspot, hotspots_to_cell_flux

NP = 20  # 측정점 20x20
_pts = (np.arange(NP) + 0.5) / NP
PX, PY = np.meshgrid(_pts, _pts)
PX, PY = PX.ravel(), PY.ravel()           # 정규화 좌표 0..1, 유동 방향 +x

def _h_pattern(m, x, y):
    """매니폴드마다 다른 가상 열전달 패턴 (임의, 가짜)."""
    r = np.random.default_rng(sum(map(ord, m)))
    a, b, c, d = r.uniform(-.3, .3, 4); e = r.uniform(.85, 1.2)
    return e + a * x + b * y + c * np.cos(2 * np.pi * (x + d)) * np.sin(np.pi * y) * .5

_DP_COEF = {m: 1 + 0.15 * (sum(map(ord, m)) % 7) for m in C.MANIFOLDS}

def true_rise(m, flow, flux_map):
    """'가상 진짜' 온도상승 (선형부 + 약한 비선형)."""
    n = C.N_CELL; d = 1 / n
    lin = np.zeros(NP * NP)
    for k, qf in enumerate(flux_map):
        if qf == 0: continue
        r, c = divmod(k, n)
        cx, cy = (c + .5) * d, (r + .5) * d
        hloc = _h_pattern(m, cx, cy) * (flow / 55) ** 0.5
        spread = np.exp(-((PX - cx) ** 2 + (PY - cy) ** 2) / (2 * 0.09 ** 2))
        wake = (PX > cx) * np.exp(-((PY - cy) ** 2) / (2 * 0.06 ** 2)) * (1 - np.exp(-(PX - cx) / 0.3))
        lin += (qf / 100) * (14 * spread / hloc + 2.5 * (55 / flow) * wake)
    return lin * (1 - 0.0015 * lin)      # 뜨거울수록 점도↓ → 조금 덜 오름 (비선형)

def write(root="data/synthetic"):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    (root / "FAKE_DATA.txt").write_text("이 폴더는 가상 데이터입니다. 실제 SimScale 결과가 아닙니다.\n")
    xmm, ymm = PX * C.CHIP_MM, PY * C.CHIP_MM
    for m in C.MANIFOLDS:
        for q in C.FLOWS_MLMIN:
            d = root / m / f"Q{q}"; d.mkdir(parents=True, exist_ok=True)
            for k in range(C.N_CELL ** 2):
                fm = np.zeros(C.N_CELL ** 2); fm[k] = C.Q0_WCM2
                T = C.T_IN_C + true_rise(m, q, fm)
                r, c = divmod(k, C.N_CELL)
                with open(d / f"cell_{r+1}_{c+1}.csv", "w", newline="") as f:
                    w = csv.writer(f); w.writerow(["x_mm", "y_mm", "T_C"])
                    w.writerows(zip(np.round(xmm, 4), np.round(ymm, 4), np.round(T, 4)))
    with open(root / "pressure.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["manifold", "flow_mlmin", "dp_pa"])
        for m in C.MANIFOLDS:
            for q in C.FLOWS_MLMIN:
                w.writerow([m, q, round(5000 * _DP_COEF[m] * (q / 55) ** 1.2, 2)])
    # 검증용 '직접 실행' 케이스 (SimScale에서 다중 핫스팟을 직접 돌린 것에 해당)
    rng = np.random.default_rng(7)
    vdir = root / "validation"; vdir.mkdir(exist_ok=True)
    cases = []
    for i in range(10):
        m = C.MANIFOLDS[i % len(C.MANIFOLDS)]; flow = [35, 48, 65, 88][i % 4]
        hs = [Hotspot(*map(float, (rng.uniform(2, 10), rng.uniform(2, 10), 3, 3, rng.choice([100, 150, 200]))))
              for _ in range(rng.integers(2, 4))]
        T = C.T_IN_C + true_rise(m, flow, hotspots_to_cell_flux(hs))
        name = f"val_{i+1:02d}"
        with open(vdir / f"{name}.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["x_mm", "y_mm", "T_C"])
            w.writerows(zip(np.round(xmm, 4), np.round(ymm, 4), np.round(T, 4)))
        cases.append({"name": name, "manifold": m, "flow_mlmin": flow, "hotspots": [h.__dict__ for h in hs]})
    (vdir / "cases.json").write_text(json.dumps(cases, indent=1, ensure_ascii=False))
    return root

if __name__ == "__main__":
    print("가상 데이터 생성:", write())
