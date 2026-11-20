"""머신러닝 공통 약속 (HANDOFF.md 2·3장과 같음).

- 판 12x12 mm, 원점 = 왼쪽 아래, 채널은 y 방향.
- 바닥 칸 이름 r_c : r = y 행(아래부터 1~4), c = x 열(왼쪽부터 1~4), 칸 3x3 mm.
- 가열: 바닥 전체 50 W/cm2, 핫스팟 칸만 300 W/cm2.
- 입구 2개, 포트 지름 0.8 mm, 각 입구에 같은 유속.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
IMAGES = ROOT / "images"

DESIGNS = ["M0", "M1", "M3", "M4", "M5", "D0", "D1", "D2", "D4", "D5", "D6"]
INLET_V = [0.497, 0.663, 0.912, 1.243, 1.658]           # SimScale 입구 유속 5단계 [m/s]

# 물성 (팀 값)
RHO, CP, K_F, MU = 997.3, 4180.0, 0.5967, 9.313e-4
T_IN = 20.0
Q_BASE, Q_HOT = 50.0, 300.0                              # W/cm2

# 채널 22개
N_CH = 22
CH_X = 0.75 + 0.5 * np.arange(N_CH)                      # 채널 중심 x [mm]
CH_W, CH_H = 0.25e-3, 0.4e-3
CH_A = CH_W * CH_H
CH_DH = 2 * CH_W * CH_H / (CH_W + CH_H)

# 형상별 입출구 위치 [mm]·좌우 대칭 여부 → data/design_meta.json (채팅끼리 합칠 때 merge.py가 같이 합침)
# 새 형상을 시작하면 윗면 압력 그림으로 입구(높은 압력 포트)를 확인해서 여기에 추가할 것.
import json as _json
_META = _json.loads((Path(__file__).resolve().parents[1] / "data" / "design_meta.json").read_text(encoding="utf-8"))
PORTS = {k: dict(inlets=[tuple(p) for p in v["inlets"]] if v.get("inlets") else None,
                 outlets=[tuple(p) for p in v["outlets"]] if v.get("outlets") else None) for k, v in _META.items()}
# x = 6 기준 좌우 거울 대칭(형상·입출구 모두, 확인된 것만). 대칭 쌍 데이터를 자동으로 늘릴 때 사용.
MIRROR_X = {k for k, v in _META.items() if v.get("mirror_x")}
# y = 6 기준 위아래 거울 대칭(확인된 것만): 행 r → 5−r
MIRROR_Y = {k for k, v in _META.items() if v.get("mirror_y")}


def flow_from_v(v):
    """입구 유속 [m/s] → 총유량 [mL/min] (입구 2개, 지름 0.8 mm)"""
    return v * np.pi * (0.4e-3) ** 2 * 2 * 6e7


def reynolds_channel(Q_mLmin):
    """채널 평균 레이놀즈수 (22채널 고르게 나눴다고 할 때)"""
    u = Q_mLmin / 6e7 / (N_CH * CH_A)
    return RHO * u * CH_DH / MU


def parse_cells(s: str):
    """'3_4+4_4' / '3_4,4_4' / '50 W/cm2 + 300 W/cm2 at 3_4,4_4' → ['3_4','4_4'] (정렬)"""
    if " at " in s:
        s = s.split(" at ", 1)[1]
    cells = [c.strip() for c in s.replace("+", ",").split(",") if c.strip()]
    for c in cells:
        r, cc = c.split("_")
        if not (1 <= int(r) <= 4 and 1 <= int(cc) <= 4):
            raise ValueError(f"칸 이름 오류: {c} (r_c, 1~4)")
    return sorted(cells)


def heat_map(cells):
    """16칸 열유속 지도 [W/cm2], 순서 = 1_1,1_2,...,4_4"""
    m = np.full((4, 4), Q_BASE)
    for c in cells:
        r, cc = map(int, c.split("_")); m[r - 1, cc - 1] = Q_HOT
    return m.reshape(-1)


def cells_centroid(cells):
    xs = [(int(c.split("_")[1]) - 0.5) * 3 for c in cells]
    ys = [(int(c.split("_")[0]) - 0.5) * 3 for c in cells]
    return float(np.mean(xs)), float(np.mean(ys))


def mirror_cells_x(cells):
    return sorted(f"{c.split('_')[0]}_{5 - int(c.split('_')[1])}" for c in cells)


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


CELL_NAMES = [f"{r}_{c}" for r in range(1, 5) for c in range(1, 5)]


def mirror_cells_y(cells):
    return sorted(f"{5 - int(c.split('_')[0])}_{c.split('_')[1]}" for c in cells)
