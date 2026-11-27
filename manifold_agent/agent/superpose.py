"""SimScale 결과 로드 + 중첩(더하기) 계산.

데이터 폴더 구조 (SimScale 내보내기 결과를 이렇게 넣는다):
    data/<dataset>/<manifold>/Q<유량>/cell_<r>_<c>.csv   열: x_mm, y_mm, T_C
        - <r>,<c> = 1..4 (r: y방향 행, c: x방향 열)
        - 그 칸에만 Q0_WCM2 열유속, 나머지 칸 단열로 돌린 결과
        - 모든 파일의 측정점(x_mm, y_mm) 순서가 같아야 한다
    data/<dataset>/pressure.csv                           열: manifold, flow_mlmin, dp_pa
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from . import config as C


@dataclass
class Hotspot:
    x: float   # 중심 x [mm], 칩 왼쪽 아래 모서리 기준
    y: float   # 중심 y [mm]
    w: float   # 가로 크기 [mm]
    h: float   # 세로 크기 [mm]
    q: float   # 열유속 [W/cm^2]


def _read_field(path: Path):
    xs, ys, ts = [], [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            xs.append(float(row["x_mm"])); ys.append(float(row["y_mm"])); ts.append(float(row["T_C"]))
    return np.array(xs), np.array(ys), np.array(ts)


class Library:
    """매니폴드 × 유량 × 칸 별 '단위 열유속 온도상승' 저장소."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.G = {}          # (manifold, flow) -> array (16, P)  온도상승 [K] at Q0
        self.xy = None       # (P, 2) 측정점 좌표 [mm]
        for m in C.MANIFOLDS:
            for q in C.FLOWS_MLMIN:
                rows = []
                for r in range(1, C.N_CELL + 1):
                    for c in range(1, C.N_CELL + 1):
                        p = self.root / m / f"Q{q}" / f"cell_{r}_{c}.csv"
                        if not p.exists():
                            raise FileNotFoundError(f"없음: {p}")
                        x, y, t = _read_field(p)
                        if self.xy is None:
                            self.xy = np.c_[x, y]
                        elif not np.allclose(self.xy, np.c_[x, y]):
                            raise ValueError(f"측정점 좌표가 다른 파일과 다름: {p}")
                        rows.append(t - C.T_IN_C)
                self.G[(m, q)] = np.array(rows)
        self.dp = {}
        with open(self.root / "pressure.csv", newline="") as f:
            for row in csv.DictReader(f):
                self.dp[(row["manifold"], int(float(row["flow_mlmin"])))] = float(row["dp_pa"])

    # ---- 유량 보간 (log 유량 기준 선형) ----
    def _bracket(self, flow):
        fl = C.FLOWS_MLMIN
        flow = float(np.clip(flow, fl[0], fl[-1]))
        for a, b in zip(fl[:-1], fl[1:]):
            if a <= flow <= b:
                t = (np.log(flow) - np.log(a)) / (np.log(b) - np.log(a))
                return a, b, t
        raise ValueError(flow)

    def unit_fields(self, manifold, flow):
        a, b, t = self._bracket(flow)
        return (1 - t) * self.G[(manifold, a)] + t * self.G[(manifold, b)]

    def pressure_pa(self, manifold, flow):
        a, b, t = self._bracket(flow)
        return float(np.exp((1 - t) * np.log(self.dp[(manifold, a)]) + t * np.log(self.dp[(manifold, b)])))

    def temperature(self, manifold, flow, cell_flux):
        """cell_flux: (16,) 칸별 열유속 [W/cm^2]. 반환: 측정점 온도 [°C]."""
        return C.T_IN_C + (np.asarray(cell_flux) / C.Q0_WCM2) @ self.unit_fields(manifold, flow)


def hotspots_to_cell_flux(hotspots: list[Hotspot], chip_mm=C.CHIP_MM, n=C.N_CELL):
    """핫스팟(사각형)을 칸별 평균 열유속으로 변환 (칸과 겹치는 면적 비율)."""
    d = chip_mm / n
    flux = np.zeros(n * n)
    for hs in hotspots:
        x0, x1 = hs.x - hs.w / 2, hs.x + hs.w / 2
        y0, y1 = hs.y - hs.h / 2, hs.y + hs.h / 2
        for r in range(n):
            for c in range(n):
                ox = max(0.0, min(x1, (c + 1) * d) - max(x0, c * d))
                oy = max(0.0, min(y1, (r + 1) * d) - max(y0, r * d))
                flux[r * n + c] += hs.q * ox * oy / (d * d)
    return flux
