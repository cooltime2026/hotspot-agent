"""새 모양 가족 E: '가장자리 직접 급수' (Edge-Feed) — 가장자리 핫스팟용 발명.

  python geometry/edge_feed.py          # E1, E2 만들기 → out/step_edge/

발견 (띠 15개 모양, shape_features 계산):
  가운데 칸(2_2) 물 0.004 / 죽은 구간 0%  vs  가장자리 1_3 물 0.001 / 죽은 33%, 모서리 1_4 죽은 60%.
  이유: 채널 끝(y 1.5~2.0)과 채널층 헤더(y 0.5~1.5)는 공급·회수 구멍이 없어서 '막다른 골목'.
        입구 (9,1) 이 1_3+1_4 바로 위인데 찬물은 덮개층 등뼈 → 띠로 멀리 돌아서 들어감.
아이디어:
  입구 받침(덮개 홈층 U, x 8.3~11.4, y 0.4~1.5) 바로 아래 관통층(P)에 구멍 하나 → 찬물이 채널층 헤더로 바로 떨어짐.
  헤더는 x 0.6~11.4 전체로 이어져 있어 22개 채널의 끝 전부가 '공급' 쪽이 됨.
  첫 띠(0번)는 A망(회수) → 헤더(공급)→첫 띠(회수) 구간이 새로 흐름 = 가장자리 줄이 찬물로 식음.
  띠 배치는 그대로라 나머지 구간은 띠 15개 모양과 같음.
E1: 아래 헤더만 (입구 (9,1) 쪽, 1행 핫스팟용)   E2: 위·아래 헤더 둘 다 (1행·4행 모두)
STEP 규칙은 v3 와 같음 (축 정렬, 0.05 mm 격자, 다른 망 벽 ≥ 0.2 mm).
※ SimScale 데이터 없음 → 예측은 추정.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from geometry import param_manifold as PM  # noqa: E402

BASE = ["n", "yf", "s", "xf", "b", "wf"]
_SP0 = PM.smooth_polys      # 원래 함수 (build 중 바꿔치기 전에 잡아 둠)
HOLE = {"bottom": (8.6, 0.6, 11.1, 1.4), "top": (8.6, 10.6, 11.1, 11.4)}   # 입구 받침 안쪽, 헤더 위


def smooth_polys(p):
    from shapely.geometry import box
    Pl, Ul, _ = _SP0({k: p[k] for k in BASE})
    Pl = list(Pl) + [(2, box(*HOLE[s])) for s in p["feed"]]
    gap = min(a.distance(b) for lay in (Pl, Ul) for va, a in lay for vb, b in lay if va != vb)
    return Pl, Ul, gap


def openings(p):
    """shape_features 용: 띠 구멍 + 헤더(공급, 22개 채널 끝 모두에 연결)"""
    ops = PM.openings({k: p[k] for k in BASE})
    out = []
    for o in ops:
        o = list(o)
        if "bottom" in p["feed"]:
            o.append(("S", 0.5, 1.5))
        if "top" in p["feed"]:
            o.append(("S", 10.5, 11.5))
        out.append(o)
    return out


def build_step(name, p, outdir="out/step_edge"):
    orig = PM.smooth_polys
    PM.smooth_polys = lambda _q: smooth_polys(p)
    try:
        info = PM.build_step_smooth(name, {k: p[k] for k in BASE}, outdir=outdir)
    finally:
        PM.smooth_polys = orig
    info["edge_feed"] = p["feed"]
    (Path(outdir) / f"{name}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1, default=float))
    return info


E = {
    "E1": dict(n=15, yf=6.0, s=0.0, xf=6.0, b=0.0, wf=0.7, feed=["bottom"]),
    "E2": dict(n=15, yf=6.0, s=0.0, xf=6.0, b=0.0, wf=0.7, feed=["bottom", "top"]),
}

if __name__ == "__main__":
    out = {}
    for name, p in E.items():
        _, _, gap = smooth_polys(p)
        b = build_step(name, p)
        print(name, p["feed"], "최소 벽", round(gap, 3), {k: b[k] for k in ["fluid_solids", "min_gap_mm", "fluid_mm3", "bottom_faces"]})
        out[name] = p
    Path("out/step_edge/round_E.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
