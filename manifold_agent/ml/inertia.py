"""관성(유량↑ → 분배 쏠림↑) 요약: 단면 사진별 채널 분배에서 불균일 지표를 Re에 대해 정리.

  python ml/inertia.py  → data/ml/inertia_summary.csv
지표: max/min = 가장 빠른 채널 / 가장 느린 채널,  cv = 채널 유량 표준편차 / 평균
(사진 1장마다 계산 → 같은 유량 여러 장의 표준편차 = 사진 읽기 오차)
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, flow_from_v, reynolds_channel  # noqa: E402

p = pd.read_csv(DATA / "flow_channel_velocity_per_image.csv")
rows = []
for (d, v, y, img), g in p.groupby(["design", "v_in", "cut_y_mm", "img"]):
    s = g.sort_values("ch").q_frac.values; s = s / np.nanmean(s)
    rows.append(dict(design=d, inlet_v_mps=v, Q_mLmin=round(flow_from_v(v), 1), Re_ch=round(reynolds_channel(flow_from_v(v)), 1),
                     cut_y_mm=y, img=img, max_min=round(np.nanmax(s) / np.nanmin(s), 3), cv=round(np.nanstd(s), 4),
                     **{f"s{j}": round(x, 4) for j, x in enumerate(s)}))
df = pd.DataFrame(rows); df.to_csv(DATA / "ml" / "inertia_summary.csv", index=False)
print(df.groupby(["design", "cut_y_mm", "Re_ch"]).agg(사진=("img", "count"), max_min=("max_min", "mean"),
      max_min_sd=("max_min", "std"), cv=("cv", "mean")).round(3).to_string())
print("저장: data/ml/inertia_summary.csv (사진별 채널 분배 s0~s21, 평균 1로 정규화)")
