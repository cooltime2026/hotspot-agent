"""단면 사진 전부(data/section_catalog.csv) → 채널별 유속 → 형상·유속·절단면별 평균.

실행: python flowdigit/run_all.py   (어느 폴더에서 실행해도 됨)
출력:
  data/flow_channel_velocity_per_image.csv   사진별 채널 22개
  data/flow_distribution_from_images.csv     형상·유속·절단면 y 별 평균 (+ 불확실도, 품질)
  flowdigit/debug/<번호>.png                 채널을 어디서 읽었는지 표시한 그림 (눈으로 확인용)
  flowdigit/summary.json                     사진별 검출 결과·질량 점검
"""
import csv, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from catalog import ROWS, IMG_DIR          # noqa: E402
from digitize import digitize              # noqa: E402

DATA = os.path.join(HERE, "..", "data")
A = 0.25e-3 * 0.4e-3


def q_total(v):
    return v * np.pi * (0.4e-3) ** 2 * 2


def run_one(r, debug=True):
    n, d, v = int(r["img"]), r["design"], float(r["inlet_v_mps"])
    vmax, cut_y = float(r["vmax_colorbar"]), float(r["cut_y_mm"])
    Q = q_total(v)
    dbg = os.path.join(HERE, "debug", f"{n}.png") if debug else None
    res, info = digitize(os.path.join(IMG_DIR, f"{n}.png"), vmax, dbg)
    rows = [dict(img=n, design=d, v_in=v, Q_mLmin=round(Q * 6e7, 1), cut_y_mm=cut_y, hotspot=r["hotspot"],
                 ch=x["j"], x_mm=0.75 + 0.5 * x["j"], v_mean=round(x["v"], 4),
                 v_center=round(x.get("v_center", np.nan), 4), q_frac=round(x["v"] * A / Q * 22, 4),
                 npx=x["npx"], vmax=vmax) for x in res]
    vs = np.array([x["v"] for x in res])
    summ = dict(img=n, design=d, v_in=v, cut_y=cut_y, ok=True, detected=info["n_detected"],
                band=round(info["band_mps"], 4), n_bands=info["n_bands"],
                ch_px=f'{info["ch_w_px"]:.0f}x{info["ch_h_px"]:.0f}',
                mass=round(float(np.nansum(vs) * A / Q), 3))
    return rows, summ


def aggregate(rows):
    """같은 (형상, 유속, 절단면 y) 사진들 평균. 불확실도 = 표준오차, 사진 1장이면 색상바 반 띠."""
    out = []
    keys = sorted({(r["design"], r["v_in"], r["cut_y_mm"]) for r in rows})
    for d, v, y in keys:
        sub = [r for r in rows if (r["design"], r["v_in"], r["cut_y_mm"]) == (d, v, y)]
        imgs = sorted({r["img"] for r in sub})
        Q = q_total(v)
        band = np.mean([r["vmax"] for r in sub]) / 20
        for j in range(22):
            vv = np.array([r["v_mean"] for r in sub if r["ch"] == j], float)
            vv = vv[np.isfinite(vv)]
            m = float(vv.mean()) if len(vv) else np.nan
            u = float(vv.std(ddof=1) / np.sqrt(len(vv))) if len(vv) > 1 else band / 2
            qc = m * A * 6e7
            out.append(dict(design=d, inlet_v_mps=v, total_Q_mLmin=round(Q * 6e7, 1), cut_y_mm=y, channel=j,
                            x_mm=0.75 + 0.5 * j, v_axial_mean_mps=round(m, 4), v_uncert_mps=round(u, 4),
                            q_channel_mLmin=round(qc, 4), share_vs_uniform=round(qc / (Q * 6e7 / 22), 4),
                            n_images=len(imgs), colorbar_band_mps=round(band, 4), quality=""))
        blk = out[-22:]
        mean_v = np.nanmean([b["v_axial_mean_mps"] for b in blk])
        q = "good" if mean_v >= 3 * band else "low-res(<3 bands)"
        for b in blk:
            b["quality"] = q
    return out


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    os.makedirs(os.path.join(HERE, "debug"), exist_ok=True)
    rows, summ = [], []
    for r in ROWS:
        try:
            rr, s = run_one(r)
            rows += rr; summ.append(s); print(s)
        except Exception as e:
            print(r["img"], r["design"], r["inlet_v_mps"], "실패:", e)
            summ.append(dict(img=int(r["img"]), design=r["design"], ok=False, err=str(e)))
    write_csv(os.path.join(DATA, "flow_channel_velocity_per_image.csv"), rows)
    write_csv(os.path.join(DATA, "flow_distribution_from_images.csv"), aggregate(rows))
    json.dump(summ, open(os.path.join(HERE, "summary.json"), "w"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()
