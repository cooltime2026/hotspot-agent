"""F형(핫스팟 줄 전용 입구) 마스크 — geometry/split_feed.py 의 0.1 mm 격자판. HTML(selfeat/patch_ml)의 mlMasksF 와 같은 규칙.
  side='bottom' : 1행 핫스팟용 (아래 입구 (9,1) → 아래 헤더 전용)   side='top' : 4행용 (위아래 뒤집음)
반환 P, U (120×120, 우리 규칙 1 = A망 출구, 2 = B망 입구)
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geometry import param_manifold as PM  # noqa: E402

def f_masks(p, side="bottom"):
    P, U, ok, _ = PM.masks({k: p[k] for k in ["n", "yf", "s", "xf", "b", "wf"]})
    P, U = P.copy(), U.copy()
    rows = np.where(P[:, 60] == 1)[0]                       # x = 6 에서 가장 아래 A 띠
    r0 = rows[0]; r1 = r0
    while r1 + 1 < 120 and P[r1 + 1, 60] == 1: r1 += 1
    P[r0:r1 + 1, 104:114] = 1                               # 첫 띠(A)를 x 11.4 까지
    P[6:14, 86:111] = 2                                     # 헤더 위 구멍 (x 8.6~11.1, y 0.6~1.4)
    ycut = int(round(((r1 + 1) * 0.1 + 0.2) / 0.1))
    blk = U[15:ycut, 104:115]; blk[blk == 2] = 0             # 오른쪽 등뼈 아래 끝 자름
    if side == "top":
        P, U = P[::-1].copy(), U[::-1].copy()
    return P, U
