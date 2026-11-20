"""채널별 유량분배 측정용 SimScale 측정점(probe) 파일 생성 + 측정값 → 채널 유량 변환.

python -m geometry.flow_probes          → out/simscale/flow_probes/<키>_channel_probes.csv (단위 m)

배치 (HTML 에이전트와 같은 좌표·채널):
  채널 j = 0..21, 중심 x = 0.75 + 0.5 j mm, 폭 0.25 mm, 높이 z 0.1~0.5 mm, 흐름 방향 y
  단면마다 3x3 가우스 점 (x: 중심 ± 0.7746·0.125, z: 0.3 ± 0.7746·0.2)
  y 측정 위치: 채널 구간 안쪽을 0.5 mm 간격 (M 계열 1.5~10.5 → 18곳, D 계열 0.6~11.4 → 21곳)
이름: ch{j:02d}_y{y*100:04d}_g{a}{b}  (a: x 방향 가우스 점 0..2, b: z 방향 0..2)

변환: Q_j(y) = (hw·hh) Σ_a Σ_b w_a w_b · Uy  (가우스 3점 적분, hw=0.125 mm, hh=0.2 mm)
"""
from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np

N_CH, X0, PITCH = 22, 0.75, 0.5
HW, HH, ZC = 0.125, 0.2, 0.3          # mm
G = np.sqrt(3 / 5); GX = [-G, 0.0, G]; GW = [5 / 9, 8 / 9, 5 / 9]
STEP = 0.5
SRC = Path(__file__).parent / "src" / "designs.json"


def channel_range(key, D):
    if key == "M0":
        return (1.5, 10.5)
    d = D[key]
    if d.get("head"):
        return (1.5, 10.5)
    return tuple(d.get("ext") or (1.5, 10.5))


def stations(y0, y1):
    return np.round(np.arange(y0 + STEP / 2, y1 - STEP / 2 + 1e-9, STEP), 4)


def probes(key, D):
    y0, y1 = channel_range(key, D)
    rows = []
    for j in range(N_CH):
        xc = X0 + PITCH * j
        for y in stations(y0, y1):
            for a, gx in enumerate(GX):
                for b, gz in enumerate(GX):
                    rows.append((f"ch{j:02d}_y{int(round(y*100)):04d}_g{a}{b}", (xc + gx * HW) * 1e-3, y * 1e-3, (ZC + gz * HH) * 1e-3))
    return rows


def channel_flows(uy_by_label: dict) -> dict:
    """{label: Uy [m/s]} → {(j, y_mm): Q [m^3/s]}"""
    acc = {}
    for lab, uy in uy_by_label.items():
        ch, ys, g = lab.split("_")
        j, y, a, b = int(ch[2:]), int(ys[1:]) / 100, int(g[1]), int(g[2])
        acc[(j, y)] = acc.get((j, y), 0.0) + GW[a] * GW[b] * uy
    return {k: v * (HW * 1e-3) * (HH * 1e-3) for k, v in acc.items()}


def main():
    D = json.loads(SRC.read_text())
    out = Path("out/simscale/flow_probes"); out.mkdir(parents=True, exist_ok=True)
    for key in ["M0", "M1", "M3", "M4", "M5", "D0", "D1", "D2", "D4", "D5", "D6"]:
        rows = probes(key, D)
        with open(out / f"{key}_channel_probes.csv", "w", newline="") as f:
            csv.writer(f).writerows([(l, f"{x:.7f}", f"{y:.7f}", f"{z:.7f}") for l, x, y, z in rows])
        print(key, channel_range(key, D), "측정점", len(rows))
    # 자기 점검: 직사각 채널 층류 해석해(급수)로 가우스 적분 정확도 확인
    a, b = HW, HH
    def u(x, z, n=60):
        s = 0
        for k in range(1, n, 2):
            s += (1 - np.cosh(k*np.pi*z/(2*a)) / np.cosh(k*np.pi*b/(2*a))) * np.cos(k*np.pi*x/(2*a)) * (-1)**((k-1)//2) / k**3
        return s
    xs = np.linspace(-a, a, 401); zs = np.linspace(-b, b, 401); X, Z = np.meshgrid(xs, zs)
    exact = np.trapezoid(np.trapezoid(u(X, Z), xs, axis=1), zs)
    gauss = a * b * sum(GW[i]*GW[k]*u(GX[i]*a, GX[k]*b) for i in range(3) for k in range(3))
    print(f"가우스 3x3 적분 오차 (층류 완전발달 프로파일): {(gauss/exact-1)*100:+.2f}%")


if __name__ == "__main__":
    main()
