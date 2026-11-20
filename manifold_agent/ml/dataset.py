"""모은 CSV → 머신러닝용 표 2개.

  data/ml/thermal.csv  : Run 1개 = 1행.  입력(형상, 유량, 핫스팟 16칸 지도, 핫스팟 위치) → 출력(바닥 최고온도, 압력 최대)
  data/ml/flow.csv     : 채널 1개 × 절단면 1개 = 1행. 입력(형상, 유량, Re, 채널 x, 절단면 y) → 출력(채널 유량 / 균일값)

거울 대칭(common.MIRROR_X)인 형상은 핫스팟을 좌우로 뒤집은 Run을 'augmented=mirror_x'로 추가한다.
(같은 물리라 새 SimScale 실행 없이 데이터가 늘어남. 검증할 땐 원본만 시험 대상으로 씀.)

실행: python ml/dataset.py
"""
from __future__ import annotations
import csv, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DATA, PORTS, MIRROR_X, MIRROR_Y, mirror_cells_y, CELL_NAMES, T_IN, flow_from_v, reynolds_channel,  # noqa: E402
                    parse_cells, heat_map, cells_centroid, mirror_cells_x)

OUT = DATA / "ml"


def _dist(pt, ports):
    if not ports:
        return np.nan
    return float(min(np.hypot(pt[0] - x, pt[1] - y) for x, y in ports))


def thermal_rows():
    rows = list(csv.DictReader(open(DATA / "direct_runs.csv", encoding="utf-8")))
    out = []
    have = {(r["design"], r["inlet_velocity_m_s"], tuple(parse_cells(r["heat"]))) for r in rows}
    for i, r in enumerate(rows):
        cells = parse_cells(r["heat"])
        variants = [(cells, "original")]
        mc = mirror_cells_x(cells)
        if (r["design"] in MIRROR_X and mc != cells
                and (r["design"], r["inlet_velocity_m_s"], tuple(mc)) not in have):   # 직접 돌린 게 있으면 그걸 씀
            variants.append((mc, "mirror_x"))
        my = mirror_cells_y(cells)
        if (r["design"] in MIRROR_Y and my != cells
                and (r["design"], r["inlet_velocity_m_s"], tuple(my)) not in have):
            variants.append((my, "mirror_y"))
        for cs, aug in variants:
            v = float(r["inlet_velocity_m_s"]); Q = flow_from_v(v)
            xc, yc = cells_centroid(cs)
            pr = PORTS.get(r["design"], {})
            row = dict(run_id=i, design=r["design"], augmented=aug, inlet_v_mps=v, Q_mLmin=round(Q, 2),
                       Re_ch=round(reynolds_channel(Q), 2), hotspot="+".join(cs), hs_x_mm=xc, hs_y_mm=yc,
                       hs_to_inlet_mm=round(_dist((xc, yc), pr.get("inlets")), 3),
                       hs_to_outlet_mm=round(_dist((xc, yc), pr.get("outlets")), 3))
            row.update({f"q_{c}": q for c, q in zip(CELL_NAMES, heat_map(cs))})
            row.update(Tmax_C=float(r["Tmax_bottom_C"]), dT_C=round(float(r["Tmax_bottom_C"]) - T_IN, 3),
                       p_max_Pa=float(r["p_max_Pa"]),
                       p_min_Pa=float(r["p_min_Pa"]) if r["p_min_Pa"] else np.nan)
            P = float((heat_map(cs) * 0.09).sum())                      # 칸 0.09 cm2 → 총 발열 [W]
            row.update(P_total_W=round(P, 2), R_th_K_W=round(row["dT_C"] / P, 5),
                       W_pump_mW=round(row["p_max_Pa"] * Q / 6e7 * 1e3, 4))   # 펌프 동력 = Δp·Q
            out.append(row)
    return out


def flow_rows():
    src = DATA / "flow_distribution_from_images.csv"
    out = []
    for r in csv.DictReader(open(src, encoding="utf-8")):
        Q = float(r["total_Q_mLmin"])
        out.append(dict(design=r["design"], inlet_v_mps=float(r["inlet_v_mps"]), Q_mLmin=Q,
                        Re_ch=round(reynolds_channel(Q), 2), cut_y_mm=float(r["cut_y_mm"]),
                        channel=int(r["channel"]), x_mm=float(r["x_mm"]),
                        share=float(r["share_vs_uniform"]),
                        share_uncert=float(r["v_uncert_mps"]) / max(float(r["v_axial_mean_mps"]), 1e-9)
                        * float(r["share_vs_uniform"]),
                        q_channel_mLmin=float(r["q_channel_mLmin"]), quality=r["quality"],
                        n_images=int(r["n_images"])))
    return out


def save(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def add_cell_temps(rows):
    """data/ml/cell_temps.csv (바닥 16칸 평균 온도, ml/cellmaps.py) 를 원본 Run에 붙임. 없으면 빈칸."""
    p = DATA / "ml" / "cell_temps.csv"
    if not p.exists():
        return rows
    ct = {(r["design"], r["hotspot"], round(float(r["inlet_v_mps"]), 3)): r for r in csv.DictReader(open(p, encoding="utf-8"))}
    for r in rows:
        m = ct.get((r["design"], r["hotspot"], round(r["inlet_v_mps"], 3))) if r["augmented"] == "original" else None
        for c in CELL_NAMES:
            r[f"Tcell_{c}"] = float(m[f"Tmean_{c}"]) if m and m[f"Tmean_{c}"] not in ("", "nan") else np.nan
    return rows


def add_channel_temps(rows):
    """data/ml/channel_temps.csv (채널층 물 온도, ml/chantemps.py) 를 원본 Run에 붙임. 믿을 만한 것만."""
    p = DATA / "ml" / "channel_temps.csv"
    ct = {}
    if p.exists():
        ct = {(r["design"], r["hotspot"], round(float(r["inlet_v_mps"]), 3)): r for r in csv.DictReader(open(p, encoding="utf-8"))
              if r["reliable"] == "True"}
    for r in rows:
        m = ct.get((r["design"], r["hotspot"], round(r["inlet_v_mps"], 3))) if r["augmented"] == "original" else None
        r["fluid_max_C"] = float(m["fluid_max_C"]) if m else np.nan
        r["fluid_mean_C"] = float(m["fluid_mean_C"]) if m else np.nan
    return rows


def main():
    t = add_channel_temps(add_cell_temps(thermal_rows())); f = flow_rows()
    save(OUT / "thermal.csv", t); save(OUT / "flow.csv", f)
    n_orig = sum(r["augmented"] == "original" for r in t)
    print(f"thermal.csv: {len(t)}행 (원본 {n_orig}, 대칭 추가 {len(t) - n_orig})")
    for d in sorted({r["design"] for r in t}):
        hs = sorted({r["hotspot"] for r in t if r["design"] == d and r["augmented"] == "original"})
        print(f"  {d}: 핫스팟 {len(hs)}종 {hs}")
    print(f"flow.csv: {len(f)}행, 형상·유속·절단면 조합 {len({(r['design'], r['Q_mLmin'], r['cut_y_mm']) for r in f})}개")


if __name__ == "__main__":
    main()
