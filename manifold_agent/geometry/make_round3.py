"""3차 변형 C1~C4: 핫스팟을 '겨냥한' 모양(띠를 핫스팟 줄에 최대로 모음, s=1).
A·B(공간 고르게 채움)에는 '핫스팟 줄에 띠를 강하게 모은' 모양이 적음 → 자동설계가 갈 가능성이 큰 영역을 미리 채움.
(어디가 최적인지는 아직 모름 = 추측으로 고른 후보.)  python geometry/make_round3.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geometry import param_manifold as PM

# 칸 r_c: 칸 3 mm, r행 중심 y = 3r-1.5, c열 중심 x = 3c-1.5
C = {
 "C1": (dict(n=7, yf=2.0, s=1.0, xf=9.0, b=-0.4, wf=0.70), "1_3+1_4"),   # ③ 가장자리 (y 1.5 → yf 하한 2.0)
 "C2": (dict(n=7, yf=6.0, s=1.0, xf=4.5, b=0.0,  wf=0.55), "2_2+3_2"),   # ④ 가운데 세로
 "C3": (dict(n=7, yf=7.5, s=1.0, xf=9.0, b=0.4,  wf=0.60), "3_3+3_4"),   # ②
 "C4": (dict(n=7, yf=4.5, s=1.0, xf=3.0, b=-0.4, wf=0.50), "2_1+2_2"),   # ①
}
# 띠 7개일 때만 강하게 모을 수 있음(띠 많으면 제작 제약 때문에 s_eff < 0.1 → 사실상 고른 간격)
if __name__ == "__main__":
    out = {}
    for k, (p, hs) in C.items():
        r = PM.resolve(p); ok = PM.masks(r)[2]; gap = PM.smooth_polys(r)[2]
        print(k, hs, "resolve", r, "feasible", ok, "min_gap", round(gap, 3))
        i = PM.build_step_smooth(k, r)
        print("  ", {x: i[x] for x in ["min_gap_mm", "fluid_solids", "dead_fluid_filled_mm3", "bottom_faces"]})
        out[k] = {**r, "aimed_hotspot": hs}
    Path("out/step_param_v3/round3.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
