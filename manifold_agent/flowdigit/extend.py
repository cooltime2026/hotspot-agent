"""절단면(y) 몇 개의 채널 유량을 채널 전체 길이로 확장.

원리(질량 보존): 채널은 옆이 막힌 관이라 위쪽이 관통층(P 마스크)으로 뚫리지 않은 '막힌 구간'에서는
축방향 유량이 일정하다. 따라서
  - 막힌 구간 안의 절단면 1곳 값 = 그 구간 전체의 유량
  - 뚫린 구간(물이 드나드는 곳)에서는 양쪽 막힌 구간 값 사이를 선형으로 잇는다(근사)
  - 방향(부호)은 형상에서 결정: HTML en[e][j] (채널 양끝이 닿는 망: 1 입구, 2 출구)
"""
from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "geometry/src/designs.json").read_text())
A = 0.25e-3 * 0.4e-3
YG = np.round(np.arange(0.6, 11.4 + 1e-9, 0.1), 2)      # 0.1 mm 격자 (HTML과 같은 간격)


def openings(key, j):
    d = D[key]; P = np.array(d["P"]).reshape(120, 120) > 0
    y0, y1 = d.get("ext") or (1.5, 10.5)
    xc = 0.75 + 0.5 * j; ix = [i for i in range(120) if abs((i + 0.5) * 0.1 - xc) <= 0.125]
    iv = []
    for iy in range(120):
        y = (iy + 0.5) * 0.1
        if y0 <= y <= y1 and P[iy, ix].any():
            if iv and iy == iv[-1][1] + 1:
                iv[-1][1] = iy
            else:
                iv.append([iy, iy])
    return [(round(a * 0.1, 2), round((b + 1) * 0.1, 2)) for a, b in iv], (y0, y1)


def closed_segments(key, j):
    op, (y0, y1) = openings(key, j)
    edges = [y0] + [v for a, b in op for v in (a, b)] + [y1]
    segs = [(edges[i], edges[i + 1]) for i in range(0, len(edges) - 1, 2) if edges[i + 1] - edges[i] > 1e-6]
    return segs, op


def suggest_cuts(key, margin=0.3, min_len=0.8):
    """모든 채널의 모든 막힌 구간에 절단면이 하나 이상 들어가도록 최소 개수의 y 위치 (탐욕법)"""
    need = []
    for j in range(22):
        segs, _ = closed_segments(key, j)
        need += [(a + margin, b - margin) for a, b in segs if b - a >= min_len]
    need.sort(key=lambda s: s[1]); cuts = []
    for a, b in need:
        if not any(a <= c <= b for c in cuts):
            cuts.append(round(b, 1))
    return sorted(cuts)


def extend_D1(rows_by_v, scale_to_mass=True):
    """D1: 막힌 구간(1.2~10.8, 가운데 4개 2.5~9.5)이 y=6을 포함 → 한 장으로 전체 확장 가능."""
    en = D["D1"]["en"]                                  # en[0][j]: 아래 끝 망, en[1][j]: 위 끝 망
    out = {}
    for v, m in rows_by_v.items():
        Q = v * np.pi * (0.4e-3) ** 2 * 2
        q = m * A                                        # 크기 [m^3/s]
        sign = np.array([+1 if en[0][j] == 1 else -1 for j in range(22)])   # 아래가 입구면 +y
        circ = np.array([0 if en[0][j] == 1 else 1 for j in range(22)])     # 회로 구분
        if scale_to_mass:                                # 회로마다 합 = Q/2 로 보정(사진 오차 보정)
            for c in (0, 1):
                k = circ == c; q[k] *= (Q / 2) / q[k].sum()
        F = np.zeros((22, len(YG)))
        for j in range(22):
            segs, op = closed_segments("D1", j)
            a, b = segs[1] if len(segs) > 1 else segs[0]   # 가운데 막힌 구간 (양끝 뚫림 사이)
            for i, y in enumerate(YG):
                if a <= y <= b:
                    f = 1.0
                elif y < a:                                 # 아래쪽 뚫린 구간: 0 → 1 선형
                    lo = op[0][0]; f = np.clip((y - lo) / max(a - lo, 1e-6), 0, 1)
                else:
                    hi = op[-1][1]; f = np.clip((hi - y) / max(hi - b, 1e-6), 0, 1)
                F[j, i] = sign[j] * q[j] * f
        out[v] = F
    return out


if __name__ == "__main__":
    for key in ["M0", "M1", "M3", "M4", "M5", "D0", "D1", "D2", "D4", "D5", "D6"]:
        if key == "M0":
            print("M0  (매니폴드 없음: 헤더형, 채널 중간에 뚫린 곳 없음) 추천 절단면 y = [6.0]"); continue
        print(f"{key:3s} 추천 절단면 y = {suggest_cuts(key)}")
    rows = list(csv.DictReader(open(ROOT / "data/flow_distribution_from_images.csv")))
    by_v = {}
    for v in [0.497, 0.663, 0.912, 1.243, 1.658]:
        by_v[v] = np.array([float(r["v_axial_mean_mps"]) for r in rows if r["design"] == "D1" and float(r["inlet_v_mps"]) == v])
    Fs = extend_D1(by_v)
    with open(ROOT / "data/D1_channel_flow_full_length.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["design", "inlet_v_mps", "total_Q_mLmin", "channel", "x_mm"] + [f"y{y:.1f}" for y in YG])
        for v, F in Fs.items():
            Q = v * np.pi * (0.4e-3) ** 2 * 2
            for j in range(22):
                w.writerow(["D1", v, round(Q * 6e7, 1), j, 0.75 + 0.5 * j] + [f"{x*6e7:.4f}" for x in F[j]])
    print("D1 전체 길이 유량 저장 (단위 mL/min, +는 +y 방향)")
    F = Fs[0.497]; i6 = int(np.argmin(np.abs(YG - 6)))
    print("  0.497 y=6 채널유량[mL/min]:", " ".join(f"{x*6e7:+.2f}" for x in F[:, i6]))
