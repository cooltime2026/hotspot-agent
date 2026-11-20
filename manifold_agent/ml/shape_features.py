"""매니폴드 모양(마스크) → 물리 특징. 형상 이름 대신 이것을 머신러닝 입력으로 쓰면 '처음 보는 모양'도 예측할 수 있음.

채널 22개(중심 x = 0.75 + 0.5 j, 흐름 y 방향)를 하나씩 따라가며 관통층(P 마스크)에서
  공급 구멍(S: 입구 쪽 망) / 회수 구멍(C: 출구 쪽 망)이 어디 있는지 찾는다.
  S와 C가 이웃하면 그 사이 채널 구간에 물이 흐름(길이 L). 같은 종류끼리 이웃하거나 끝에 남은 부분 = 거의 안 흐름(죽은 구간).
  구간 전도도 g = 1/L, 전체 G = Σg. 구간 유량 ∝ Q·g/G.
핫스팟 칸(3×3 mm)마다
  flow_loc : 칸 안 채널 구간들의 (g/G)·겹친 길이 평균 → 그 칸을 지나는 물의 양(상대값)
  dead     : 칸 안 채널 길이 중 죽은 구간 비율
  dfresh   : 칸 중심에서 가장 가까운 공급 구멍까지 y 거리 [mm] (찬물이 얼마나 가까이 들어오나)
  path_in  : 공급 구멍에서 칸까지 물이 지나온 거리 평균 [mm] (그동안 데워짐)
전체: G (클수록 압력 낮음), 열린 채널 수.

모양 정의
  - 기존 형상: geometry/src/designs.json 의 P 마스크. 1/2 중 '사용자 입구 포트에 붙은 망'이 공급(data/design_meta.json 기준).
  - M0: 마스크 없음 → 입구 쪽 헤더(y 0.5~1.5)가 공급, 반대 헤더(10.5~11.5)가 회수.
  - 새 모양: geometry/param_manifold.py 가 만든 P 마스크와 supply 값.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CH_X = 0.75 + 0.5 * np.arange(22)
RES = 0.1


@lru_cache(None)
def _designs():
    return json.loads((ROOT / "geometry/src/designs.json").read_text())


@lru_cache(None)
def _meta():
    return json.loads((ROOT / "data/design_meta.json").read_text(encoding="utf-8"))


def channel_extent(head):
    return (1.5, 10.5) if head else (0.6, 11.4)


def openings_from_mask(P, supply_val, y_lo, y_hi):
    """P: 120x120 (행 = y). 채널마다 [(type 'S'|'C', y0, y1)]"""
    out = []
    for x in CH_X:
        col = P[:, int(round(x / RES))]
        segs, s = [], 0
        for i in range(1, 121):
            if i == 120 or col[i] != col[s]:
                if col[s]:
                    y0, y1 = s * RES, i * RES
                    if y1 > y_lo - 1.0 and y0 < y_hi + 1.0:        # 채널(+헤더) 범위 안
                        segs.append(("S" if col[s] == supply_val else "C", max(y0, y_lo - 1.0), min(y1, y_hi + 1.0)))
                s = i
        out.append(segs)
    return out


def design_openings(design):
    """기존 형상 이름 → (채널별 구멍 목록, 채널 y 범위)"""
    if design == "M0":
        inl = _meta()["M0"]["inlets"][0][1]
        s, c = ((0.5, 1.5), (10.5, 11.5)) if inl < 6 else ((10.5, 11.5), (0.5, 1.5))
        return [[("S", *s), ("C", *c)] for _ in CH_X], (1.5, 10.5)
    d = _designs()[design]
    P = np.array(d["P"]).reshape(120, 120)
    inlets = [tuple(p) for p in _meta()[design]["inlets"]]
    ports = [tuple(p) for p in d["ports"]]
    near = lambda a, b: np.hypot(a[0] - b[0], a[1] - b[1]) < 0.3
    supply_val = 1 if any(near(i, p) for i in inlets for p in ports[:2]) else 2
    lo, hi = channel_extent(d["head"])
    return openings_from_mask(P, supply_val, lo, hi), (lo, hi)


def segments(openings):
    """채널마다 흐르는 구간 [(ys, yc, L)] (ys = 공급 구멍 중심, yc = 회수 구멍 중심) + 구멍 중심 목록"""
    allseg = []
    for ops in openings:
        ops = sorted(ops, key=lambda o: o[1]); segs = []
        for a, b in zip(ops[:-1], ops[1:]):
            if a[0] != b[0]:
                ya, yb = (a[1] + a[2]) / 2, (b[1] + b[2]) / 2
                ys, yc = (ya, yb) if a[0] == "S" else (yb, ya)
                segs.append((ys, yc, max(abs(yb - ya), 0.3)))
        allseg.append(segs)
    return allseg


def shape_summary(openings, extent=(1.5, 10.5)):
    segs = segments(openings)
    G = sum(1 / L for ch in segs for _, _, L in ch)
    n_open = sum(1 for ch in segs if ch)
    return dict(G=G, n_open=n_open, segs=segs, openings=openings, extent=extent)


def cell_features(summary, cell, y_rng=None):
    r, c = map(int, cell.split("_"))
    x0, x1, y0, y1 = (c - 1) * 3, c * 3, (r - 1) * 3, r * 3
    yc_cell = (y0 + y1) / 2
    G = summary["G"]; flows, deads, fresh, paths = [], [], [], []
    for j, x in enumerate(CH_X):
        if not (x0 <= x < x1):
            continue
        segs = summary["segs"][j]
        covered, f, pth = 0.0, 0.0, []
        for ys, yc, L in segs:
            a, b = min(ys, yc), max(ys, yc)
            ov = max(0.0, min(b, y1) - max(a, y0))
            if ov > 0:
                covered += ov; f += (1 / L) / G * ov / 3
                mid = (max(a, y0) + min(b, y1)) / 2; pth.append(abs(mid - ys))
        lo, hi = summary["extent"]; chlen = max(min(hi, y1) - max(lo, y0), 0.1)   # 칸 안 채널 길이
        flows.append(f); deads.append(1 - min(covered, chlen) / chlen)
        sup = [(o[1] + o[2]) / 2 for o in summary["openings"][j] if o[0] == "S"]
        fresh.append(min(abs(yc_cell - s) for s in sup) if sup else 12.0)
        paths.append(np.mean(pth) if pth else 12.0)
    return dict(flow_loc=float(np.mean(flows)), dead=float(np.mean(deads)),
                dfresh=float(np.mean(fresh)), path_in=float(np.mean(paths)))


FEATS = ["logQ", "log_flow_worst", "log_flow_mean", "dead_max", "dfresh_max", "dfresh_mean",
         "path_max", "edge_min", "sep", "logG"]


def hotspot_features(summary, hotspot, Q):
    cells = hotspot.replace(",", "+").split("+")
    cf = [cell_features(summary, c) for c in cells]
    xy = [((int(c.split("_")[1]) - .5) * 3, (int(c.split("_")[0]) - .5) * 3) for c in cells]
    edge = min(min(x, 12 - x, y, 12 - y) for x, y in xy)
    sep = np.hypot(xy[0][0] - xy[-1][0], xy[0][1] - xy[-1][1])
    eps = 1e-4
    return dict(logQ=np.log(Q / 55), log_flow_worst=np.log(min(f["flow_loc"] for f in cf) + eps),
                log_flow_mean=np.log(np.mean([f["flow_loc"] for f in cf]) + eps),
                dead_max=max(f["dead"] for f in cf), dfresh_max=max(f["dfresh"] for f in cf) / 12,
                dfresh_mean=np.mean([f["dfresh"] for f in cf]) / 12, path_max=max(f["path_in"] for f in cf) / 12,
                edge_min=edge / 12, sep=sep / 12, logG=np.log(summary["G"]))


@lru_cache(None)
def design_summary(design):
    ops, ext = design_openings(design)
    return shape_summary(ops, ext)


if __name__ == "__main__":
    for d in ["M0", "M1", "M3", "M4", "D0", "D1"]:
        s = design_summary(d)
        print(d, f"G={s['G']:.1f}", "열린 채널", s["n_open"],
              {c: {k: round(v, 3) for k, v in cell_features(s, c).items()} for c in ["1_1", "2_2", "3_3"]})
