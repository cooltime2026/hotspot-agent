"""채널층 수평 단면(z=0.0003) 사진 → 채널 22개 값 표 (data/ml/planview_channels.csv).

  python ml/planview_batch.py
- 목록 PLAN: (형상, 핫스팟, 입구유속, 사진번호, 종류 vel|p). 새 사진은 여기에 추가.
- vel: 채널별 평균 속도(채널 길이 방향 평균, 헤더 1 mm 제외) → share = 채널/22채널 평균.
- p  : 채널별 평균 압력과 채널 양 끝(아래 1.8~2.5, 위 9.5~10.2 mm) 압력, 그 차이.
- 정확도: 색상바가 자동 범위라 1띠 = 범위/20. 띠 수(n_band_levels)가 2~3이면 정성용.
"""
import csv, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "flowdigit"))
import planview  # noqa: E402

VMAX = {"M1": {0.497: 1.28, 0.663: 1.69, 0.912: 2.296, 1.243: 3.131, 1.658: 4.202},
        "M4": {0.497: 0.716, 0.663: 0.9473, 0.912: 1.293, 1.243: 1.748, 1.658: 2.31}}
PLAN = [
 ("M1","2_1+2_2",0.497,396,"vel"),("M1","2_1+2_2",0.497,397,"p"),
 ("M1","2_1+2_2",0.663,404,"vel"),("M1","2_1+2_2",0.663,403,"p"),
 ("M1","2_1+2_2",0.912,411,"vel"),("M1","2_1+2_2",0.912,410,"p"),
 ("M1","2_1+2_2",1.658,425,"vel"),("M1","2_1+2_2",1.658,426,"p"),
 ("M1","2_3+2_4",0.497,437,"vel"),("M1","2_3+2_4",0.497,438,"p"),
 ("M1","2_3+2_4",0.663,448,"vel"),("M1","2_3+2_4",0.663,449,"p"),
 ("M1","2_3+2_4",0.912,460,"vel"),("M1","2_3+2_4",0.912,459,"p"),
 ("M1","2_3+2_4",1.243,467,"vel"),("M1","2_3+2_4",1.243,468,"p"),
 ("M1","2_3+2_4",1.658,475,"vel"),("M1","2_3+2_4",1.658,476,"p"),
 ("M1","3_1+3_2",0.497,482,"vel"),("M1","3_1+3_2",0.497,483,"p"),
 ("M1","3_1+3_2",0.663,490,"vel"),("M1","3_1+3_2",0.663,491,"p"),
 ("M4","2_3+3_2",0.497,542,"vel"),("M4","2_3+3_2",0.497,543,"p"),
 ("M4","2_3+3_2",0.663,550,"vel"),("M4","2_3+3_2",0.663,551,"p"),
 ("M4","2_3+3_2",0.912,558,"vel"),("M4","2_3+3_2",0.912,559,"p"),
 ("M4","2_3+3_2",1.243,566,"vel"),("M4","2_3+3_2",1.243,567,"p"),
 ("M4","2_3+3_2",1.658,575,"vel"),("M4","2_3+3_2",1.658,576,"p"),
 ("M4","3_3+3_4",0.497,586,"vel"),("M4","3_3+3_4",0.497,587,"p"),
 ("M4","3_3+3_4",0.912,595,"vel"),("M4","3_3+3_4",0.912,597,"p"),
 ("M4","3_3+3_4",1.658,604,"vel"),("M4","3_3+3_4",1.658,606,"p"),
 ("M4","3_1+3_4",0.497,500,"vel"),("M4","3_1+3_4",0.497,501,"p"),
 ("M4","3_1+3_4",0.663,508,"vel"),("M4","3_1+3_4",0.663,509,"p"),
 ("M4","3_1+3_4",0.912,516,"vel"),("M4","3_1+3_4",0.912,517,"p"),
 ("M4","3_1+3_4",1.243,524,"vel"),("M4","3_1+3_4",1.243,525,"p"),
 ("M4","3_1+3_4",1.658,532,"vel"),("M4","3_1+3_4",1.658,533,"p"),
]


def main():
    runs = {(r["design"], "+".join(sorted(r["heat"].split(" at ")[1].split(","))), float(r["inlet_velocity_m_s"])): r
            for r in csv.DictReader(open(ROOT / "data/direct_runs.csv", encoding="utf-8"))}
    out = []
    for d, h, v, n, kind in PLAN:
        r = runs[(d, h, v)]
        hi, lo = (VMAX[d][v], 0.0) if kind == "vel" else (float(r["p_max_Pa"]), float(r["p_min_Pa"]))
        res = planview.read(str(ROOT / f"images/{n}.png"), hi, 1.5, 10.5, lo)
        P, ym = res["prof"], res["ymm"]
        core = (ym > 2.5) & (ym < 9.5)
        m = np.nanmean(P[:, core], 1)
        levels = len(np.unique(np.round(m / ((hi - lo) / 20))))
        row = dict(design=d, hotspot=h, inlet_v_mps=v, img=n, kind=kind, band=round((hi - lo) / 20, 4),
                   n_band_levels=levels)
        if kind == "vel":
            s = m / np.nanmean(m)
            row.update({f"ch{j}": round(x, 3) for j, x in enumerate(s)})
            row["max_min"] = round(np.nanmax(s) / np.nanmin(s), 2)
        else:
            a = np.nanmean(P[:, (ym > 1.8) & (ym < 2.5)], 1); b = np.nanmean(P[:, (ym > 9.5) & (ym < 10.2)], 1)
            mid = np.nanmean(P[:, (ym > 5.5) & (ym < 6.5)], 1)
            row.update({f"ch{j}": round(x, 1) for j, x in enumerate(m)})
            row["dp_mid_minus_ends_Pa"] = round(float(np.nanmean(mid - (a + b) / 2)), 1)
            row["dp_left5_minus_right5_Pa"] = round(float(np.nanmean(m[:5]) - np.nanmean(m[-5:])), 1)
        out.append(row)
        print(f"{d} {h} v={v} img {n} {kind}: 값 단계 {levels}개 (1띠 {row['band']})",
              f"분배 최대/최소 {row.get('max_min')}" if kind == "vel" else
              f"가운데−양끝 {row['dp_mid_minus_ends_Pa']} Pa, 왼쪽5−오른쪽5 {row['dp_left5_minus_right5_Pa']} Pa")
    keys = sorted({k for r in out for k in r}, key=lambda k: (k.startswith("ch"), int(k[2:]) if k.startswith("ch") and k[2:].isdigit() else 0, k))
    with open(ROOT / "data/ml/planview_channels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
    print("저장: data/ml/planview_channels.csv", len(out), "행")


if __name__ == "__main__":
    main()
