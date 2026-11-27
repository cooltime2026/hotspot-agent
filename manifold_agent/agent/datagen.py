"""중첩으로 학습 데이터 생성.

- 핫스팟 1~4개의 칸 조합 전수: C(16,1)+C(16,2)+C(16,3)+C(16,4) = 2,516가지
- 각 조합마다 칸별 열유속을 무작위로 뽑음 (여러 번)
- 칸 경계에 걸친 연속 위치/크기 핫스팟도 무작위로 추가
- 유량은 SimScale에서 실제로 돌린 5수준에서만 생성 (중간 유량은 신경망이 보간)
라벨: 매니폴드별 최고온도 상승 [K], 온도 불균일도(max-min) [K]
"""
from __future__ import annotations
import itertools
import numpy as np
from . import config as C
from .superpose import Library, Hotspot, hotspots_to_cell_flux

FLUX_CHOICES = np.array([50, 100, 150, 200, 250, 300], float)


def flux_maps(rng, draws_per_combo=3, n_random=8000):
    n2 = C.N_CELL ** 2
    maps = []
    for k in range(1, 5):
        for cells in itertools.combinations(range(n2), k):
            for _ in range(draws_per_combo):
                f = np.zeros(n2); f[list(cells)] = rng.choice(FLUX_CHOICES, size=k); maps.append(f)
    for _ in range(n_random):  # 연속 위치·크기
        hs = [Hotspot(rng.uniform(0, C.CHIP_MM), rng.uniform(0, C.CHIP_MM),
                      rng.uniform(1, 6), rng.uniform(1, 6), rng.uniform(50, 300))
              for _ in range(rng.integers(1, 5))]
        maps.append(hotspots_to_cell_flux(hs))
    return np.array(maps)


def labels(lib: Library, flow, F):
    """F: (N,16) → (N, 2*매니폴드수) [Tmax상승..., 불균일도...]"""
    tmax, nonu = [], []
    for m in C.MANIFOLDS:
        rise = (F / C.Q0_WCM2) @ lib.unit_fields(m, flow)      # (N, P)
        tmax.append(rise.max(1)); nonu.append(rise.max(1) - rise.min(1))
    return np.c_[np.array(tmax).T, np.array(nonu).T]


def build(lib: Library, seed=0):
    rng = np.random.default_rng(seed)
    F = flux_maps(rng)
    X, Y = [], []
    for q in C.FLOWS_MLMIN:
        X.append(np.c_[F, np.full(len(F), q)]); Y.append(labels(lib, q, F))
    return np.vstack(X), np.vstack(Y)


def features(F_with_flow):
    """신경망 입력 특징: 칸 열유속/100, 정규화 log유량."""
    A = np.asarray(F_with_flow, float)
    lf = (np.log(A[:, -1]) - np.log(C.FLOW_MIN)) / (np.log(C.FLOW_MAX) - np.log(C.FLOW_MIN))
    return np.c_[A[:, :-1] / 100.0, lf]


def to_target(Y):
    """학습 목표: log(1+K). 작은 온도상승에서도 상대오차를 줄이기 위함."""
    return np.log1p(np.asarray(Y))


def from_target(Z):
    return np.expm1(np.asarray(Z))
