"""머신러닝 새 설계 N* 표 (2026-11-28): 핫스팟 · 종류 · 예상 온도 · 실측 최선 · 추천 유량.

  python ml/new_summary.py [목표온도=85]   → out/new_designs/summary.md, summary.csv
예상 온도 = 칸 모델 + 실측 보정 (new_result.ml_predict, 페이지와 같은 계산). 새 모양이라 크게 틀릴 수 있음(확인 안 됨).
추천 유량 = 55~100 mL/min, 1 단위로 예상해서 목표 온도를 지키는 가장 적은 유량 (55 아래는 학습 데이터 없음).
입구 속도 = 유량 / (입구 2개 · 지름 0.8 mm 면적 1.005 mm²).  55 mL/min = 0.912 m/s.
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml")); sys.path.insert(0, str(ROOT))
sys.argv = sys.argv[:1] + sys.argv[1:]
import new_result as NR  # noqa: E402

OUT = ROOT / "out" / "new_designs"
AREA = 2 * np.pi * 0.4 ** 2   # mm²


def v_of(Q):
    return Q / 60 * 1000 / AREA / 1000   # m/s


def measured_best():
    d = pd.read_csv(ROOT / "data/direct_runs.csv"); d = d[d.inlet_velocity_m_s.round(3) == 0.912]
    d["hs"] = d.heat.str.split("at ").str[1].map(lambda s: "+".join(sorted(s.split(","))))
    return {h: (g.loc[g.Tmax_bottom_C.idxmin(), "design"], g.Tmax_bottom_C.min()) for h, g in d.groupby("hs")}


def main(target=85.0):
    best = measured_best(); rows = []
    for f in sorted(OUT.glob("N*_mask.json"), key=lambda x: int(x.stem.split("_")[0][1:])):
        m = json.loads(f.read_text()); k = m["name"]; hs = m["hotspot"]; key = "+".join(sorted(hs.split("+")))
        T = {Q: NR.ml_predict(k, hs, Q) for Q in range(55, 101)}
        q = next((Q for Q in range(55, 101) if T[Q] <= target), None)
        lb = m.get("lib_best") or {}
        mb = best.get(key)
        rows.append(dict(name=k, hotspot=hs, family=m["fam"], header=m["head"], seed_T=round(m["seedT"], 1), pred_T55=round(T[55], 1),
                         pred_T100=round(T[100], 1), lib_best=f"{lb.get('name')} {lb.get('T', 0):.1f}" if lb else "", meas_best=f"{mb[0]} {mb[1]:.1f}" if mb else "",
                         Q_for_target=q, v_for_target=round(v_of(q), 3) if q else None, inlets=m["pin"], outlets=m["pout"]))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "summary.csv", index=False)
    md = ["| 이름 | 핫스팟 | 출발 종류 | 예상 ℃ @55 | 예상 ℃ @100 | 출발 모양 예상 | 실측 모양 중 예상 최선 | 이 핫스팟 실측 최선 | %g ℃ 지키는 유량 |" % target,
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['name']} | {r['hotspot']} | {r['family']}{' (헤더형)' if r['header'] else ''} | {r['pred_T55']} | {r['pred_T100']} | {r['seed_T']} | {r['lib_best']} | {r['meas_best'] or '-'} | "
                  + (f"{r['Q_for_target']} mL/min ({r['v_for_target']} m/s)" if r['Q_for_target'] else "100으로도 안 됨") + " |")
    (OUT / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 85.0)
