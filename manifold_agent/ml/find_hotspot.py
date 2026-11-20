"""바닥 온도 사진만 보고 핫스팟 두 칸 찾기 (핫스팟을 모른다고 가정).

  python ml/find_hotspot.py <사진번호> <Tmax> [<사진번호> <Tmax> ...] [--orient rot180_flip]

- 사진 여러 장(같은 핫스팟, 다른 유량)을 주면 점수를 합쳐서 더 확실하게 고름.
- 화면 → 칸 방향(--orient): 기본 rot180_flip = 지금까지 D0·M0·M1 사진 대부분과 같은 카메라 방향.
  (M4 3_1+3_4는 좌우 대칭 핫스팟이라 flip 여부를 사진으로 못 가림 → 같은 규칙으로 가정, 미확인)
- 방법 두 가지:
  ① 주변 대비 = 칸 평균 − 이웃 칸(상하좌우) 평균. 300 W/cm² 칸은 주변보다 튀어나옴.
  ② 칸 최고 = 칸 안 최고 온도.
  판정은 ①로 함. 확신 = (1위 − 2위)/1위 점수 차이.
  기존 사진 74장(정답 앎, 1장씩) 시험: 전체 91% 정답. 차이 ≥ 0.10이면 67장 중 97%, < 0.10이면 7장 중 29%.
  → 차이 < 0.10이면 '확신 낮음' → 핫스팟 설정 화면과 대조할 것. ②는 흰색(최고) 띠가 포화돼 동점이 많아 참고용.
"""
from __future__ import annotations
import argparse, itertools, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "flowdigit")); sys.path.insert(0, str(ROOT / "ml"))
import tempmap                       # noqa: E402
from common import CELL_NAMES        # noqa: E402

PAIRS = list(itertools.combinations(range(16), 2))


def orient(a, name):
    k = {"rot0": 0, "rot90": 1, "rot180": 2, "rot270": 3}[name.split("_")[0]]
    return np.rot90(a[:, ::-1] if "flip" in name else a, k)[::-1, :]     # 행 0 = r 1


def excess(Mn):
    ex = np.zeros((4, 4))
    for r in range(4):
        for c in range(4):
            nb = [Mn[i, j] for i, j in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)) if 0 <= i < 4 and 0 <= j < 4]
            ex[r, c] = Mn[r, c] - np.mean(nb)
    return ex.reshape(-1)


def analyse(items, orient_name="rot180_flip"):
    ref = tempmap.read(str(ROOT / "images/331.png"), 131.8)["lut"]
    E = np.zeros(16); X = np.zeros(16); maps = []
    for img, tmax in items:
        r = tempmap.read(str(ROOT / f"images/{img}.png"), tmax, ref_lut=ref)
        Mn, Mx = orient(r["mean"], orient_name), orient(r["max"], orient_name)
        dT = tmax - 20.0                                   # 유량마다 온도 크기가 달라서 정규화
        E += excess(Mn) / dT; X += Mx.reshape(-1) / dT; maps.append((img, Mn))
    def rank(s):
        return sorted(PAIRS, key=lambda p: -(s[p[0]] + s[p[1]]))
    rE, rX = rank(E), rank(X)
    name = lambda p: "+".join(CELL_NAMES[i] for i in p)
    return dict(excess=[(name(p), (E[p[0]] + E[p[1]]) / len(items)) for p in rE[:3]],
                cmax=[(name(p), (X[p[0]] + X[p[1]]) / len(items)) for p in rX[:3]],
                agree=rE[0] == rX[0], pick=name(rE[0]), maps=maps,
                gap=((E[rE[0][0]] + E[rE[0][1]]) - (E[rE[1][0]] + E[rE[1][1]])) / (E[rE[0][0]] + E[rE[0][1]]))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("pairs", nargs="+")
    ap.add_argument("--orient", default="rot180_flip"); a = ap.parse_args()
    v = a.pairs; items = [(int(v[i]), float(v[i + 1])) for i in range(0, len(v), 2)]
    r = analyse(items, a.orient)
    for img, Mn in r["maps"]:
        print(f"사진 {img} 칸 평균 온도 [℃] (위 = 4행, 아래 = 1행, 왼쪽 = 1열)")
        for row in Mn[::-1]:
            print("   " + "  ".join(f"{x:6.1f}" for x in row))
    print("① 주변 대비 상위:", ", ".join(f"{n} ({s:.3f})" for n, s in r["excess"]))
    print("② 칸 최고 상위  :", ", ".join(f"{n} ({s:.3f})" for n, s in r["cmax"]))
    ok = r["gap"] >= 0.10
    print(f"→ 판정: {r['pick']}  (1·2위 차이 {r['gap']:.2f}: {'확신 높음, 시험 97%' if ok else '확신 낮음, 시험 29% → 설정 화면과 대조'})")


if __name__ == "__main__":
    main()
